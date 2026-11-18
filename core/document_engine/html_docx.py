"""Import local HTML documents into editable DOCX."""

import base64
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

from docx import Document
from docx.shared import Inches
from lxml import html

from core.workers.atomic_output import atomic_output_path

_BLOCKS = {"div", "section", "article", "main", "header", "footer", "blockquote"}
_HEADINGS = {f"h{level}": f"Heading {level}" for level in range(1, 7)}
_SKIP = {"head", "style", "script", "template"}
_FORMATS = {"strong": "bold", "b": "bold", "em": "italic", "i": "italic", "u": "underline"}
_DATA_IMAGE = re.compile(r"data:image/(?:png|jpeg|gif|bmp|tiff);base64,(.*)", re.I | re.S)


def _append_text(paragraph, text, styles, preformatted):
    if not text:
        return
    if not preformatted:
        text = re.sub(r"[ \t\r\n\f]+", " ", text)
        if not paragraph.runs:
            text = text.lstrip()
    if text:
        run = paragraph.add_run(text)
        for style in styles:
            setattr(run, style, True)


def _add_image(paragraph, source, root, width):
    embedded = _DATA_IMAGE.fullmatch(source)
    if embedded:
        data = BytesIO(base64.b64decode("".join(embedded[1].split()), validate=True))
    else:
        parsed = urlsplit(source)
        if parsed.scheme or parsed.netloc:
            return
        path = (root / unquote(parsed.path)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return
        data = str(path)
    shape = paragraph.add_run().add_picture(data)
    if shape.width > width:
        shape.height = int(shape.height * width / shape.width)
        shape.width = width


def _inline(node, paragraph, root, width, styles, preformatted, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return
    if tag == "img":
        if source := node.get("src"):
            _add_image(paragraph, source, root, width)
        return
    if tag == "br":
        paragraph.add_run().add_break()
        return
    if tag in _FORMATS:
        styles = (*styles, _FORMATS[tag])
    preformatted = preformatted or tag == "pre" or "white-space: pre-wrap" in node.get("style", "")
    _append_text(paragraph, node.text, styles, preformatted)
    for child in node:
        _inline(child, paragraph, root, width, styles, preformatted, should_cancel)
        _append_text(paragraph, child.tail, styles, preformatted)


def _body(node, document, root, width, should_cancel, list_style=None):
    paragraph = None
    if node.text and node.text.strip():
        paragraph = document.add_paragraph(node.text.strip())
    for child in node:
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        tag = child.tag
        if not isinstance(tag, str) or tag in _SKIP:
            continue
        if tag in _BLOCKS or tag in {"ol", "ul"}:
            styles = {"ol": "List Number", "ul": "List Bullet"}
            _body(child, document, root, width, should_cancel, styles.get(tag, list_style))
            paragraph = None
        elif tag == "table":
            rows = child.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")
            grid = [row.xpath("./td|./th") for row in rows]
            columns = max(map(len, grid), default=0)
            if columns:
                table = document.add_table(rows=len(grid), cols=columns)
                table.style = "Table Grid"
                for html_cells, row in zip(grid, table.rows, strict=True):
                    for cell, html_cell in zip(row.cells, html_cells, strict=False):
                        _inline(html_cell, cell.paragraphs[0], root, width // columns, (), False, should_cancel)
            paragraph = None
        elif tag in _HEADINGS or tag in {"p", "pre", "li"}:
            style = _HEADINGS.get(tag, list_style if tag == "li" else None)
            _inline(child, document.add_paragraph(style=style), root, width, (), False, should_cancel)
            paragraph = None
        else:
            if paragraph is None:
                paragraph = document.add_paragraph()
            _inline(child, paragraph, root, width, (), False, should_cancel)
        if child.tail and child.tail.strip():
            if paragraph is None:
                paragraph = document.add_paragraph()
            _append_text(paragraph, child.tail, (), False)


def save_body_as_docx(body, root, destination, should_cancel):
    document = Document()
    _body(body, document, root, Inches(6), should_cancel)
    with atomic_output_path(destination) as temporary:
        document.save(temporary)
        if should_cancel():
            raise InterruptedError("Конвертация отменена")


def read_body(source, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    source = Path(source)
    data = source.read_bytes()
    try:
        data = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    body = html.document_fromstring(data, parser=html.HTMLParser(no_network=True)).find("body")
    if body is None:
        raise ValueError("В HTML отсутствует содержимое документа")
    return body


def import_docx(source, destination, should_cancel):
    body = read_body(source, should_cancel)
    source = Path(source)
    save_body_as_docx(body, source.parent.resolve(), destination, should_cancel)
