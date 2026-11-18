"""Write editable OpenDocument Text from supported HTML and DOCX content."""

import base64
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree, html
from PIL import Image

from core.document_engine.odt_html import ODT_NAMES
from core.workers.atomic_output import atomic_output_path

_MIME = "application/vnd.oasis.opendocument.text"
_MANIFEST = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
_SVG = "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
_NAMES = {**ODT_NAMES, "manifest": _MANIFEST, "svg": _SVG}
_BLOCK = {
    "p": "text:p", "pre": "text:p", "li": "text:list-item", "ul": "text:list", "ol": "text:list",
    "table": "table:table", "tr": "table:table-row", "td": "table:table-cell", "th": "table:table-cell",
    "thead": "table:table-header-rows",
}
_STYLES = {"strong": "Bold", "b": "Bold", "em": "Italic", "i": "Italic", "u": "Underline"}
_TRANSPARENT = {"tbody", "tfoot", "div", "section", "article", "main", "header", "footer", "blockquote"}
_SKIP = {"script", "style", "template", "head"}
_EMBEDDED = re.compile(r"data:image/(?:png|jpeg|gif|bmp|tiff|webp);base64,(.*)", re.I | re.S)


def _q(name):
    prefix, local = name.split(":")
    return f"{{{_NAMES[prefix]}}}{local}"


def _element(parent, name, properties=None):
    return etree.SubElement(parent, _q(name), {_q(key): value for key, value in (properties or {}).items()})


def _append(parent, text):
    if not text:
        return
    if parent.tag == _q("office:text"):
        if text.strip():
            _element(parent, "text:p").text = text.strip()
    elif len(parent):
        parent[-1].tail = (parent[-1].tail or "") + text
    else:
        parent.text = (parent.text or "") + text


def _image(node, parent, source_root, images):
    source = node.get("src", "")
    if match := _EMBEDDED.fullmatch(source):
        data = BytesIO(base64.b64decode("".join(match[1].split()), validate=True))
    else:
        parsed = urlsplit(source)
        if parsed.scheme or parsed.netloc:
            _append(parent, node.get("alt"))
            return
        path = (source_root / unquote(parsed.path)).resolve()
        if not path.is_relative_to(source_root) or not path.is_file():
            _append(parent, node.get("alt"))
            return
        data = path
    with Image.open(data) as picture, BytesIO() as png:
        picture.convert("RGBA").save(png, "PNG")
        width = min(6.0, picture.width / 96)
        height = width * picture.height / picture.width
        name = f"Pictures/image-{len(images) + 1}.png"
        images[name] = png.getvalue()
    if parent.tag in {_q("office:text"), _q("table:table-cell")}:
        parent = _element(parent, "text:p")
    frame = _element(parent, "draw:frame", {
        "text:anchor-type": "as-char", "svg:width": f"{width:.3f}in", "svg:height": f"{height:.3f}in",
    })
    _element(frame, "draw:image", {"xlink:href": name, "xlink:type": "simple"})


def _translate(node, parent, source_root, images, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return
    if tag in _BLOCK:
        parent = _element(parent, _BLOCK[tag])
        if tag in {"li", "th", "td"} and not any(child.tag in _BLOCK for child in node):
            parent = _element(parent, "text:p")
    elif len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
        parent = _element(parent, "text:h", {"text:outline-level": tag[1]})
    elif tag in _STYLES:
        if parent.tag == _q("office:text"):
            parent = _element(parent, "text:p")
        parent = _element(parent, "text:span", {"text:style-name": _STYLES[tag]})
    elif tag == "br":
        _element(parent, "text:line-break")
    elif tag == "img":
        _image(node, parent, source_root, images)
        return
    elif tag not in _TRANSPARENT and parent.tag == _q("office:text"):
        parent = _element(parent, "text:p")
    _append(parent, node.text)
    for child in node:
        _translate(child, parent, source_root, images, should_cancel)
        _append(parent, child.tail)


def _document(body, source_root, images, should_cancel):
    root = etree.Element(_q("office:document-content"), {_q("office:version"): "1.2"}, nsmap=_NAMES)
    styles = _element(root, "office:automatic-styles")
    for name, key, value in (
        ("Bold", "fo:font-weight", "bold"),
        ("Italic", "fo:font-style", "italic"),
        ("Underline", "style:text-underline-style", "solid"),
    ):
        style = _element(styles, "style:style", {"style:name": name, "style:family": "text"})
        _element(style, "style:text-properties", {key: value})
    text = _element(_element(root, "office:body"), "office:text")
    _append(text, body.text)
    for child in body:
        _translate(child, text, source_root, images, should_cancel)
        _append(text, child.tail)
    return root


def export_odt(source, destination, source_format, should_cancel):
    if source_format == "DOCX":
        from core.document_engine.docx_html import body_html

        body = html.fragment_fromstring(body_html(source, should_cancel), create_parent="body")
    elif source_format == "RTF":
        from core.document_engine.rtf_import import read_body

        body = read_body(source, should_cancel)
    else:
        from core.document_engine.html_docx import read_body

        body = read_body(source, should_cancel)
    images = {}
    document = _document(body, Path(source).parent.resolve(), images, should_cancel)
    manifest = etree.Element(_q("manifest:manifest"), nsmap={"manifest": _MANIFEST})
    manifest.set(_q("manifest:version"), "1.2")
    for name, mime in (("/", _MIME), ("content.xml", "text/xml")):
        _element(manifest, "manifest:file-entry", {"manifest:full-path": name, "manifest:media-type": mime})
    for name in images:
        _element(manifest, "manifest:file-entry", {"manifest:full-path": name, "manifest:media-type": "image/png"})
    with atomic_output_path(destination) as temporary, ZipFile(Path(temporary), "w") as archive:
        archive.writestr("mimetype", _MIME)
        archive.writestr("content.xml", etree.tostring(document, encoding="utf-8"), ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", etree.tostring(manifest, encoding="utf-8"), ZIP_DEFLATED)
        for name, image in images.items():
            archive.writestr(name, image)
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
