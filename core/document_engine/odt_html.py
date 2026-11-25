"""Конвертация содержимого ODT в самостоятельный HTML-документ."""

from base64 import b64encode
from pathlib import Path
from re import fullmatch
from urllib.parse import urlsplit
from zipfile import ZipFile

from lxml import etree

from core.document_engine.formatting import points
from core.filesystem import atomic_output_path

ODT_NAMES = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
}

_ELEMENTS = {
    "text:p": "p", "text:h": "h1", "text:span": "span", "text:list": "ul", "text:list-item": "li",
    "text:line-break": "br", "table:table": "table", "table:table-row": "tr",
    "text:a": "a",
    "table:table-cell": "td", "table:table-header-rows": "thead",
    "table:table-column": "col",
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


def _style_trees(content, archive):
    trees = [content]
    if "styles.xml" in archive.namelist():
        trees.insert(0, _read_xml(archive, "styles.xml"))
    return trees


def _styles(trees):
    result = {}
    font_faces = {}
    for tree in trees:
        for font in tree.xpath("//style:font-face", namespaces=ODT_NAMES):
            font_faces[font.get(_q("style:name"))] = font.get(_q("svg:font-family"))
    for tree in trees:
        for style in tree.xpath("//style:style", namespaces=ODT_NAMES):
            props = style.find(_q("style:text-properties"))
            tags = []
            css = {}
            if props is not None:
                for name, value, tag in (
                    ("fo:font-weight", "bold", "strong"),
                    ("fo:font-style", "italic", "em"),
                ):
                    if props.get(_q(name)) == value:
                        tags.append(tag)
                if props.get(_q("style:text-underline-style")) not in {None, "none"}:
                    tags.append("u")
                family = props.get(_q("fo:font-family")) or font_faces.get(props.get(_q("style:font-name")))
                size = props.get(_q("fo:font-size"))
                if family:
                    css["font-family"] = family
                if size:
                    css["font-size"] = size
            for group, attributes in (
                ("text", {"fo:color": "color", "fo:background-color": "background-color"}),
                ("paragraph", {
                    "fo:text-align": "text-align", "fo:line-height": "line-height", "fo:text-indent": "text-indent",
                    "fo:background-color": "background-color",
                    **{f"fo:margin-{side}": f"margin-{side}" for side in ("top", "right", "bottom", "left")},
                }),
                ("table-cell", {
                    "fo:background-color": "background-color", "style:vertical-align": "vertical-align",
                    "fo:border": "border", "fo:padding": "padding",
                    **{f"fo:{prop}-{side}": f"{prop}-{side}" for prop in ("border", "padding")
                       for side in ("top", "right", "bottom", "left")},
                }),
                ("table-row", {"style:min-row-height": "height", "style:row-height": "height"}),
                ("table-column", {"style:column-width": "width"}),
            ):
                if (properties := style.find(_q(f"style:{group}-properties"))) is not None:
                    css.update({key: value for name, key in attributes.items()
                                if (value := properties.get(_q(name))) and ";" not in value})
                    if group == "paragraph" and properties.get(_q("fo:break-before")) == "page":
                        css["page-break-before"] = "always"
                    if group == "paragraph" and properties.get(_q("fo:keep-with-next")) == "always":
                        css["--docx-keep-with-next"] = "1"
            result[style.get(_q("style:name"))] = tags, css
    return result


def _numbered_lists(trees):
    return {
        style.get(_q("style:name"))
        for tree in trees
        for style in tree.xpath("//text:list-style[text:list-level-style-number[@text:level='1']]",
                                namespaces=ODT_NAMES)
    }


def _page_geometry(trees, body):
    masters = [master for tree in trees for master in tree.xpath("//style:master-page", namespaces=ODT_NAMES)]
    if not masters:
        return
    layout_name = masters[0].get(_q("style:page-layout-name"))
    if not layout_name:
        return
    for tree in trees:
        layouts = tree.xpath("//style:page-layout[@style:name=$name]/style:page-layout-properties",
                             namespaces=ODT_NAMES, name=layout_name)
        if not layouts:
            continue
        for name in ("page-width", "page-height", "margin-left", "margin-right", "margin-top", "margin-bottom"):
            value = layouts[0].get(_q(f"fo:{name}"))
            if not value and name.startswith("margin-"):
                value = layouts[0].get(_q("fo:margin"))
            if value == "0pt" or points(value):
                body.set(f"data-{name}", value)
        break


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
        element = etree.SubElement(target, "img", src=f"data:image/{mime};base64,{data}")
        frame = node.getparent()
        if frame is not None and frame.tag == _q("draw:frame"):
            dimensions = ";".join(f"{axis}:{value}" for axis in ("width", "height")
                                  if (value := frame.get(_q(f"svg:{axis}"))))
            if dimensions:
                element.set("style", dimensions)


def _translate(node, target, archive, styles, numbered_lists, should_cancel):
    _check_cancel(should_cancel)
    if not isinstance(node.tag, str):
        return
    if node.tag == _q("table:covered-table-cell"):
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
        if tag == "ul" and node.get(_q("text:style-name")) in numbered_lists:
            tag = "ol"
        if tag == "h1":
            level = int(node.get(_q("text:outline-level"), "1"))
            tag = f"h{min(6, max(1, level))}"
        target = etree.SubElement(target, tag)
        if tag == "p" or (tag.startswith("h") and tag[1:].isdigit()):
            target.set("style", "white-space: pre-wrap")
        if tag == "a":
            href = node.get(_q("xlink:href"), "")
            if href.startswith("#") or urlsplit(href).scheme in {"http", "https", "mailto"}:
                target.set("href", href)
        if tag == "td":
            for kind, html_name in (("columns", "colspan"), ("rows", "rowspan")):
                value = node.get(_q(f"table:number-{kind}-spanned"), "")
                if fullmatch(r"[1-9][0-9]{0,3}", value):
                    target.set(html_name, value)
        if tag == "table" and node.xpath(
            "./table:table-column[@table:style-name]|.//table:table-cell[@table:style-name]", namespaces=ODT_NAMES,
        ):
            target.set("data-docx-table", "true")
    style_name = node.get(_q("text:style-name")) or node.get(_q("table:style-name"))
    tags, css = styles.get(style_name, ((), {}))
    if css:
        serialized = ";".join(f"{key}:{value}" for key, value in css.items())
        existing = target.get("style")
        target.set("style", f"{existing};{serialized}" if existing else serialized)
    for tag in tags:
        target = etree.SubElement(target, tag)
    _append_text(target, node.text)
    for child in node:
        _translate(child, target, archive, styles, numbered_lists, should_cancel)
        _append_text(target, child.tail)


def read_body(source, should_cancel):
    _check_cancel(should_cancel)
    with ZipFile(source) as archive:
        content = _read_xml(archive, "content.xml")
        text = content.find("office:body/office:text", ODT_NAMES)
        if text is None:
            raise ValueError("В файле ODT отсутствует текст документа")
        trees = _style_trees(content, archive)
        styles = _styles(trees)
        numbered_lists = _numbered_lists(trees)
        body = etree.Element("body")
        _page_geometry(trees, body)
        for child in text:
            _translate(child, body, archive, styles, numbered_lists, should_cancel)
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
