"""Convert the contents of an ODT package to standalone HTML."""

from base64 import b64encode
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from core.workers.atomic_output import atomic_output_path

ODT_NAMES = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}

_ELEMENTS = {
    "text:p": "p", "text:h": "h1", "text:span": "span", "text:list": "ul", "text:list-item": "li",
    "text:line-break": "br", "table:table": "table", "table:table-row": "tr",
    "table:table-cell": "td", "table:table-header-rows": "thead",
}
_IMAGE_MIME = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".bmp": "bmp"}


def _q(name):
    prefix, local = name.split(":")
    return f"{{{ODT_NAMES[prefix]}}}{local}"


_HTML_ELEMENTS = {_q(name): tag for name, tag in _ELEMENTS.items()}


def _check_cancel(should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")


def _read_xml(archive, name):
    with archive.open(name) as content:
        return etree.parse(content, etree.XMLParser(resolve_entities=False, no_network=True))


def _styles(content, archive):
    trees = [content]
    if "styles.xml" in archive.namelist():
        trees.insert(0, _read_xml(archive, "styles.xml"))
    result = {}
    for tree in trees:
        for style in tree.xpath("//style:style", namespaces=ODT_NAMES):
            props = style.find(_q("style:text-properties"))
            if props is not None:
                tags = []
                for name, value, tag in (
                    ("fo:font-weight", "bold", "strong"),
                    ("fo:font-style", "italic", "em"),
                ):
                    if props.get(_q(name)) == value:
                        tags.append(tag)
                result[style.get(_q("style:name"))] = tags
    return result


def _append_text(target, text):
    if text:
        if len(target):
            target[-1].tail = (target[-1].tail or "") + text
        else:
            target.text = (target.text or "") + text


def _append_image(node, target, archive):
    name = node.get(_q("xlink:href"), "").removeprefix("./")
    mime = _IMAGE_MIME.get(Path(name).suffix.lower())
    if mime and name.startswith("Pictures/") and name in archive.namelist():
        data = b64encode(archive.read(name)).decode("ascii")
        etree.SubElement(target, "img", src=f"data:image/{mime};base64,{data}")


def _translate(node, target, archive, styles, should_cancel):
    _check_cancel(should_cancel)
    if not isinstance(node.tag, str):
        return
    if node.tag == _q("draw:image"):
        _append_image(node, target, archive)
        return
    if node.tag in {_q("text:s"), _q("text:tab")}:
        count = int(node.get(_q("text:c"), "1"))
        if not 1 <= count <= 1_000_000:
            raise ValueError("Некорректный пробел в документе ODT")
        _append_text(target, "\t" if node.tag == _q("text:tab") else " " * count)
        return
    if node.tag in _HTML_ELEMENTS:
        tag = _HTML_ELEMENTS[node.tag]
        if tag == "h1":
            level = int(node.get(_q("text:outline-level"), "1"))
            tag = f"h{min(6, max(1, level))}"
        target = etree.SubElement(target, tag)
        if tag == "p" or (tag.startswith("h") and tag[1:].isdigit()):
            target.set("style", "white-space: pre-wrap")
    style_name = node.get(_q("text:style-name"))
    for tag in styles.get(style_name, ()):
        target = etree.SubElement(target, tag)
    _append_text(target, node.text)
    for child in node:
        _translate(child, target, archive, styles, should_cancel)
        _append_text(target, child.tail)


def read_body(source, should_cancel):
    _check_cancel(should_cancel)
    with ZipFile(source) as archive:
        content = _read_xml(archive, "content.xml")
        text = content.find("office:body/office:text", ODT_NAMES)
        if text is None:
            raise ValueError("В файле ODT отсутствует текст документа")
        styles = _styles(content, archive)
        body = etree.Element("body")
        for child in text:
            _translate(child, body, archive, styles, should_cancel)
    return body


def convert_odt(source, destination, target, should_cancel):
    body = read_body(source, should_cancel)
    save_body(body, source, destination, target, should_cancel)


def save_body(body, source, destination, target, should_cancel):
    if target == "DOCX":
        from core.document_engine.html_docx import save_body_as_docx

        return save_body_as_docx(body, Path(source).parent.resolve(), destination, should_cancel)
    document = etree.Element("html")
    head = etree.SubElement(document, "head")
    etree.SubElement(head, "meta", charset="utf-8")
    document.append(body)
    with atomic_output_path(destination) as temporary:
        Path(temporary).write_bytes(
            etree.tostring(document, method="html", encoding="utf-8", doctype="<!doctype html>")
        )
        _check_cancel(should_cancel)
