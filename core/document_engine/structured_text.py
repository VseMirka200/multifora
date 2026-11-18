"""Plain-text export for HTML and OpenDocument Text."""

from pathlib import Path
from zipfile import ZipFile

from lxml import etree, html

from core.workers.atomic_output import atomic_output_path

_ODT_NAMES = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}
_HTML_BREAKS = {"p", "div", "br", "li", "tr", "section", "article", "blockquote", *(f"h{i}" for i in range(1, 7))}


def _check_cancel(should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")


def _html_text(source, should_cancel):
    data = source.read_bytes()
    try:
        data = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass  # The parser can still read legacy encodings declared in HTML.
    document = html.document_fromstring(data, parser=html.HTMLParser(no_network=True))
    for node in document.xpath("//head|//script|//style|//template|//comment()"):
        node.drop_tree()
    parts = []
    for event, node in etree.iterwalk(document, events=("start", "end")):
        _check_cancel(should_cancel)
        if event == "start":
            if node.tag in _HTML_BREAKS and parts:
                parts.append("\n")
            if node.text:
                parts.append(node.text)
        else:
            if node.tag in _HTML_BREAKS:
                parts.append("\n")
            elif node.tag in {"td", "th"}:
                parts.append("\t")
            if node.tail:
                parts.append(node.tail)
    return "\n".join(line.strip() for line in "".join(parts).splitlines() if line.strip())


def _odt_paragraph(node):
    parts = [node.text or ""]
    for child in node:
        if child.tag == f"{{{_ODT_NAMES['text']}}}s":
            count = int(child.get(f"{{{_ODT_NAMES['text']}}}c", "1"))
            if not 1 <= count <= 1_000_000:
                raise ValueError("Некорректное число пробелов в ODT")
            parts.append(" " * count)
        elif child.tag == f"{{{_ODT_NAMES['text']}}}tab":
            parts.append("\t")
        elif child.tag == f"{{{_ODT_NAMES['text']}}}line-break":
            parts.append("\n")
        else:
            parts.append(_odt_paragraph(child))
        parts.append(child.tail or "")
    return "".join(parts)


def _odt_text(source, should_cancel):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    with ZipFile(source) as archive, archive.open("content.xml") as content:
        root = etree.parse(content, parser)
    body = root.find("office:body/office:text", _ODT_NAMES)
    if body is None:
        raise ValueError("В файле ODT отсутствует текст документа")
    lines = []
    for node in body.xpath(".//text:p | .//text:h", namespaces=_ODT_NAMES):
        _check_cancel(should_cancel)
        lines.append(_odt_paragraph(node))
    return "\n".join(lines)


def _rtf_text(source, should_cancel):
    from striprtf.striprtf import rtf_to_text

    data = source.read_bytes()
    if not data.lstrip().startswith(br"{\rtf"):
        raise ValueError("Некорректный документ RTF")
    _check_cancel(should_cancel)
    return rtf_to_text(data.decode("latin-1")).encode("utf-16", "surrogatepass").decode("utf-16")


def export_text(source, destination, source_format, should_cancel):
    _check_cancel(should_cancel)
    read = {"ODT": _odt_text, "RTF": _rtf_text, "HTM": _html_text, "HTML": _html_text}[source_format]
    result = read(Path(source), should_cancel)
    with atomic_output_path(destination, allow_empty=True) as temporary:
        Path(temporary).write_text(result, encoding="utf-8", newline="\n")
        _check_cancel(should_cancel)
