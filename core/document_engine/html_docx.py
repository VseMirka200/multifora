"""Импорт локальных HTML-документов в редактируемый DOCX."""

import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from docx import Document
from docx.enum.text import WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from lxml import html
from PIL import Image

from core.document_engine.formatting import font_family, image_size, inline_style, points
from core.document_engine.rtf_export import image_data
from core.filesystem import atomic_output_path

_BLOCKS = {"div", "section", "article", "main", "header", "footer", "blockquote"}
_HEADINGS = {f"h{level}": f"Heading {level}" for level in range(1, 7)}
_SKIP = {"head", "style", "script", "template"}
_FORMATS = {"strong": "bold", "b": "bold", "em": "italic", "i": "italic", "u": "underline"}


def _append_text(paragraph, text, styles, preformatted):
    if not text:
        return
    if not preformatted:
        text = re.sub(r"[ \t\r\n\f]+", " ", text)
        if not paragraph.text:
            text = text.lstrip()
    if text:
        run = paragraph.add_run(text)
        for style, value in styles.items():
            setattr(run.font, style, value)


def _add_image(paragraph, node, root, width, height):
    data = image_data(node, root)
    if data is None:
        return
    with Image.open(data) as picture:
        dimensions = image_size(
            node, picture.width, picture.height, width_limit=width / 12700, height_limit=height / 12700,
        )
        if picture.format not in {"PNG", "JPEG", "GIF", "BMP", "TIFF"}:
            data = BytesIO()
            picture.convert("RGBA").save(data, format="PNG")
    paragraph.add_run().add_picture(str(data) if isinstance(data, Path) else data, *map(Pt, dimensions))


def _font_styles(node, styles, css):
    styles = styles.copy()
    if node.tag in _FORMATS:
        styles[_FORMATS[node.tag]] = True
    if family := font_family(css.get("font-family")):
        styles["name"] = family
    if size := points(css.get("font-size")):
        styles["size"] = Pt(size)
    if "font-weight" in css:
        styles["bold"] = css["font-weight"] in {"bold", "600", "700", "800", "900"}
    if "font-style" in css:
        styles["italic"] = css["font-style"] in {"italic", "oblique"}
    if "text-decoration" in css:
        styles["underline"] = "underline" in css["text-decoration"].split()
    return styles


def _inline(node, paragraph, root, bounds, styles, preformatted, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return
    if tag == "img":
        _add_image(paragraph, node, root, *bounds)
        return
    if tag == "br":
        paragraph.add_run().add_break(WD_BREAK.PAGE if node.get("data-page-break") == "true" else WD_BREAK.LINE)
        return
    css = inline_style(node)
    styles = _font_styles(node, styles, css)
    preformatted = preformatted or tag == "pre" or css.get("white-space") == "pre-wrap"
    start = len(paragraph._p)
    _append_text(paragraph, node.text, styles, preformatted)
    for child in node:
        _inline(child, paragraph, root, bounds, styles, preformatted, should_cancel)
        _append_text(paragraph, child.tail, styles, preformatted)
    if tag == "a" and (href := node.get("href", "")):
        link = OxmlElement("w:hyperlink")
        if href.startswith("#"):
            link.set(qn("w:anchor"), href[1:])
        elif urlsplit(href).scheme in {"http", "https", "mailto"}:
            link.set(qn("r:id"), paragraph.part.relate_to(href, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
        else:
            return
        for run in list(paragraph._p)[start:]:
            link.append(run)
        paragraph._p.append(link)


def _body(node, document, root, bounds, should_cancel, list_style=None, *, styles=None):
    css = inline_style(node)
    styles = _font_styles(node, styles or {}, css)
    paragraph = None
    if node.text and node.text.strip():
        paragraph = document.add_paragraph()
        _append_text(paragraph, node.text, styles, css.get("white-space") == "pre-wrap")
    for child in node:
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        tag = child.tag
        if not isinstance(tag, str) or tag in _SKIP:
            pass
        elif tag in _BLOCKS or tag in {"ol", "ul"}:
            list_styles = {"ol": "List Number", "ul": "List Bullet"}
            _body(child, document, root, bounds, should_cancel, list_styles.get(tag, list_style), styles=styles)
            paragraph = None
        elif tag == "table":
            rows = child.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")
            grid = [row.xpath("./td|./th") for row in rows]
            columns = max((sum(_column_span(cell) for cell in row) for row in grid), default=0)
            if columns:
                table = document.add_table(rows=len(grid), cols=columns)
                table.style = "Table Grid"
                for html_cells, row in zip(grid, table.rows, strict=True):
                    column = 0
                    for html_cell in html_cells:
                        span = _column_span(html_cell)
                        cell = row.cells[column]
                        if span > 1:
                            cell = cell.merge(row.cells[column + span - 1])
                        original = cell.paragraphs[0]._p
                        _body(html_cell, cell, root, (bounds[0] * span // columns, bounds[1]),
                              should_cancel, styles=styles)
                        if len(cell.paragraphs) > 1:
                            cell._tc.remove(original)
                        column += span
            paragraph = None
        elif tag in _HEADINGS or tag in {"p", "pre", "li"}:
            style = _HEADINGS.get(tag, list_style if tag == "li" else None)
            _inline(child, document.add_paragraph(style=style), root, bounds, styles, False, should_cancel)
            paragraph = None
        else:
            if paragraph is None:
                paragraph = document.add_paragraph()
            _inline(child, paragraph, root, bounds, styles, False, should_cancel)
        if child.tail and child.tail.strip():
            if paragraph is None:
                paragraph = document.add_paragraph()
            _append_text(paragraph, child.tail, styles, False)


def _column_span(cell):
    value = cell.get("colspan", "1")
    return max(1, min(63, int(value))) if value.isascii() and value.isdigit() and len(value) <= 2 else 1


def save_body_as_docx(body, root, destination, should_cancel):
    document = Document()
    section = document.sections[0]
    bounds = (
        section.page_width - section.left_margin - section.right_margin,
        section.page_height - section.top_margin - section.bottom_margin - Pt(20),
    )
    _body(body, document, root, bounds, should_cancel)
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
