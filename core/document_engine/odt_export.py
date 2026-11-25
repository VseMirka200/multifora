"""Запись редактируемого ODT из поддерживаемого содержимого HTML и DOCX."""

import base64
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree, html
from PIL import Image

from core.document_engine.formatting import font_family, image_size, inline_style, paragraph_parts, points
from core.document_engine.odt_html import ODT_NAMES
from core.document_engine.table_layout import table_layout
from core.filesystem import atomic_output_path

_MIME = "application/vnd.oasis.opendocument.text"
_MANIFEST = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
_NAMES = {**ODT_NAMES, "manifest": _MANIFEST}
_BLOCK = {
    "p": "text:p", "pre": "text:p", "li": "text:list-item", "ul": "text:list", "ol": "text:list",
    "td": "table:table-cell", "th": "table:table-cell",
}
_STYLES = {"strong": "Bold", "b": "Bold", "em": "Italic", "i": "Italic", "u": "Underline"}
_TRANSPARENT = {"tbody", "tfoot", "div", "section", "article", "main", "header", "footer", "blockquote"}
_SKIP = {"script", "style", "template", "head"}
_EMBEDDED = re.compile(r"data:image/(?:png|jpeg|gif|bmp|tiff|webp);base64,(.*)", re.I | re.S)
_TEXT_PROPERTIES = {"color": "fo:color", "background-color": "fo:background-color"}
_PARAGRAPH_PROPERTIES = {
    "text-align": "fo:text-align", "margin-top": "fo:margin-top", "margin-bottom": "fo:margin-bottom",
    "margin-left": "fo:margin-left", "margin-right": "fo:margin-right", "text-indent": "fo:text-indent",
    "line-height": "fo:line-height", "page-break-before": "fo:break-before",
    "background-color": "fo:background-color",
}
_PAGE_PROPERTIES = {
    "page_width": "fo:page-width", "page_height": "fo:page-height",
    **{f"{side}_margin": f"fo:margin-{side}" for side in ("left", "right", "top", "bottom")},
}


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
        width, height = image_size(node, picture.width, picture.height, width_limit=432, height_limit=690)
        name = f"Pictures/image-{len(images) + 1}.png"
        images[name] = png.getvalue()
    if parent.tag in {_q("office:text"), _q("table:table-cell")}:
        parent = _element(parent, "text:p")
    frame = _element(parent, "draw:frame", {
        "text:anchor-type": "as-char", "svg:width": f"{width:.4f}pt", "svg:height": f"{height:.4f}pt",
    })
    _element(frame, "draw:image", {"xlink:href": name, "xlink:type": "simple"})


def _style(styles, family, properties, *, text_properties=None):
    if not properties and not text_properties:
        return None
    key = family, tuple(sorted(properties.items())), tuple(sorted((text_properties or {}).items()))
    return styles.setdefault(key, f"Format{len(styles) + 1}")


def _apply_style(element, styles, family, properties, *, text_properties=None):
    if name := _style(styles, family, properties, text_properties=text_properties):
        prefix = "text" if family in {"text", "paragraph"} else "table"
        element.set(_q(f"{prefix}:style-name"), name)


def _table(node, parent, source_root, images, styles, should_cancel):
    table = _element(parent, "table:table")
    widths, _, placements = table_layout(node, 500)
    declared = node.xpath("./col|./colgroup/col")
    for index in range(len(widths)):
        column = _element(table, "table:table-column")
        width = points(inline_style(declared[index]).get("width")) if index < len(declared) else None
        if width:
            _apply_style(column, styles, "table-column", {"style:column-width": f"{width:g}pt"})
    cells = {(row, column): (cell, across, down) for cell, row, column, across, down in placements}
    covered_until = [0] * len(widths)
    header = None
    for row, source_row in enumerate(node.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")):
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        row_parent = table
        if source_row.getparent().tag == "thead":
            if header is None:
                header = _element(table, "table:table-header-rows")
            row_parent = header
        row_element = _element(row_parent, "table:table-row")
        if height := points(inline_style(source_row).get("height")):
            _apply_style(row_element, styles, "table-row", {"style:min-row-height": f"{height:g}pt"})
        for column in range(len(widths)):
            if covered_until[column] > row:
                _element(row_element, "table:covered-table-cell")
            elif placement := cells.get((row, column)):
                cell, across, down = placement
                _translate(cell, row_element, source_root, images, styles, should_cancel,
                           cell_span=(across, down))
                covered_until[column] = row + down
                covered_until[column + 1:column + across] = [row + down] * (across - 1)
            else:
                _element(_element(row_element, "table:table-cell"), "text:p")


def _translate(node, parent, source_root, images, styles, should_cancel, *, cell_span=(1, 1)):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return
    css = inline_style(node)
    if tag == "table":
        _table(node, parent, source_root, images, styles, should_cancel)
        return
    if tag in _BLOCK:
        parent = _element(parent, _BLOCK[tag])
        if tag in {"ol", "ul"}:
            parent.set(_q("text:style-name"), "NumberedList" if tag == "ol" else "BulletList")
        if tag in {"td", "th"}:
            for axis, span in zip(("columns", "rows"), cell_span, strict=True):
                if span > 1:
                    parent.set(_q(f"table:number-{axis}-spanned"), str(span))
            cell_properties = {f"fo:{name}": css[name] for name in (
                "background-color", "border", "padding", "border-top", "border-right", "border-bottom", "border-left",
                "padding-top", "padding-right", "padding-bottom", "padding-left",
            ) if name in css}
            if css.get("vertical-align") in {"top", "middle", "bottom"}:
                cell_properties["style:vertical-align"] = css["vertical-align"]
            _apply_style(parent, styles, "table-cell", cell_properties)
        if tag in {"li", "th", "td"} and not any(child.tag in _BLOCK or child.tag == "table" for child in node):
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
    elif tag == "a" and (href := node.get("href", "")) and (
        href.startswith("#") or urlsplit(href).scheme in {"http", "https", "mailto"}
    ):
        if parent.tag == _q("office:text"):
            parent = _element(parent, "text:p")
        parent = _element(parent, "text:a", {"xlink:href": href, "xlink:type": "simple"})
    elif tag not in _TRANSPARENT and parent.tag == _q("office:text"):
        parent = _element(parent, "text:p")
    is_paragraph = tag in {"p", "pre"} or (len(tag) == 2 and tag[0] == "h" and tag[1] in "123456")
    family = font_family(css.get("font-family"))
    size = points(css.get("font-size"))
    text_properties = {target: css[key] for key, target in _TEXT_PROPERTIES.items() if key in css}
    if family:
        text_properties["fo:font-family"] = family
    if size:
        text_properties["fo:font-size"] = f"{size:g}pt"
    if is_paragraph:
        properties = {target: css[key] for key, target in _PARAGRAPH_PROPERTIES.items() if key in css}
        text_properties.pop("fo:background-color", None)
        if properties.get("fo:break-before") == "always":
            properties["fo:break-before"] = "page"
        if css.get("--docx-keep-with-next"):
            properties["fo:keep-with-next"] = "always"
        _apply_style(parent, styles, "paragraph", properties, text_properties=text_properties)
    elif text_properties and parent.tag in {_q("text:p"), _q("text:h"), _q("text:span"), _q("text:a")}:
        name = _style(styles, "text", text_properties)
        parent = _element(parent, "text:span", {"text:style-name": name})
    _append(parent, node.text)
    for child in node:
        _translate(child, parent, source_root, images, styles, should_cancel)
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
    for name, kind, attributes in (
        ("NumberedList", "number", {"style:num-format": "1", "style:num-suffix": "."}),
        ("BulletList", "bullet", {"text:bullet-char": "•"}),
    ):
        list_style = _element(styles, "text:list-style", {"style:name": name})
        for level in range(1, 11):
            _element(list_style, f"text:list-level-style-{kind}", {"text:level": str(level), **attributes})
    text = _element(_element(root, "office:body"), "office:text")
    formatting = {}
    _append(text, body.text)
    pending_break = False
    for child in body:
        parts = paragraph_parts(child) if child.xpath("./br[@data-page-break='true']") else (child,)
        for part in parts:
            if pending_break:
                if part is not None and (part.tag == "p" or part.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}):
                    part.set("style", part.get("style", "") + ";page-break-before:always")
                else:
                    _apply_style(_element(text, "text:p"), formatting, "paragraph", {"fo:break-before": "page"})
            pending_break = part is None
            if part is not None:
                _translate(part, text, source_root, images, formatting, should_cancel)
        _append(text, child.tail)
    if pending_break:
        _apply_style(_element(text, "text:p"), formatting, "paragraph", {"fo:break-before": "page"})
    for (family, properties, text_properties), name in formatting.items():
        style = _element(styles, "style:style", {"style:name": name, "style:family": family})
        if properties:
            _element(style, f"style:{family}-properties", dict(properties))
        if text_properties:
            _element(style, "style:text-properties", dict(text_properties))
    return root


def _page_styles(section):
    root = etree.Element(_q("office:document-styles"), {_q("office:version"): "1.2"}, nsmap=_NAMES)
    automatic = _element(root, "office:automatic-styles")
    layout = _element(automatic, "style:page-layout", {"style:name": "PageLayout"})
    properties = {name: f"{value.pt:g}pt" for attribute, name in _PAGE_PROPERTIES.items()
                  if (value := getattr(section, attribute)) is not None}
    properties["style:print-orientation"] = "landscape" if section.orientation.name == "LANDSCAPE" else "portrait"
    _element(layout, "style:page-layout-properties", properties)
    masters = _element(root, "office:master-styles")
    _element(masters, "style:master-page", {"style:name": "Standard", "style:page-layout-name": "PageLayout"})
    return root


def export_odt(source, destination, source_format, should_cancel):
    page_styles = None
    if source_format == "DOCX":
        from docx import Document

        from core.document_engine.docx_html import _body_html

        document = Document(source)
        body = html.fragment_fromstring(_body_html(document, should_cancel), create_parent="body")
        if document.sections:
            page_styles = _page_styles(document.sections[0])
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
    if page_styles is not None:
        _element(manifest, "manifest:file-entry", {
            "manifest:full-path": "styles.xml", "manifest:media-type": "text/xml",
        })
    for name in images:
        _element(manifest, "manifest:file-entry", {"manifest:full-path": name, "manifest:media-type": "image/png"})
    with atomic_output_path(destination) as temporary, ZipFile(Path(temporary), "w") as archive:
        archive.writestr("mimetype", _MIME)
        archive.writestr("content.xml", etree.tostring(document, encoding="utf-8"), ZIP_DEFLATED)
        if page_styles is not None:
            archive.writestr("styles.xml", etree.tostring(page_styles, encoding="utf-8"), ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", etree.tostring(manifest, encoding="utf-8"), ZIP_DEFLATED)
        for name, image in images.items():
            archive.writestr(name, image)
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
