"""Lay out document paragraphs, pictures and tables in searchable PDF."""

from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from lxml import html
from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from core.document_engine.rtf_export import image_data
from core.document_engine.text_pdf import _FONT_NAME, _text_font, register_font_family
from core.workers.atomic_output import atomic_output_path

_BLOCKS = {"div", "section", "article", "main", "header", "footer", "blockquote", "ul", "ol"}
_INLINE = {"strong": "b", "b": "b", "i": "i", "em": "i", "u": "u"}
_SKIP = {"script", "style", "template", "head"}
_MARGIN = 54


@dataclass(frozen=True)
class _PageLayout:
    size: tuple = A4
    margins: tuple = (_MARGIN, _MARGIN, _MARGIN, _MARGIN)
    header: tuple = ()
    footer: tuple = ()
    header_distance: float = 20
    footer_distance: float = 20


def _docx_layout(document):
    section = document.sections[0]
    if section.page_width is None or section.page_height is None:
        return _PageLayout()
    margins = (section.left_margin, section.right_margin, section.top_margin, section.bottom_margin)
    return _PageLayout(
        (section.page_width.pt, section.page_height.pt),
        tuple(margin.pt if margin is not None else _MARGIN for margin in margins),
        tuple(p.text for p in section.header.paragraphs) if not section.header.is_linked_to_previous else (),
        tuple(p.text for p in section.footer.paragraphs) if not section.footer.is_linked_to_previous else (),
        section.header_distance.pt if section.header_distance is not None else 20,
        section.footer_distance.pt if section.footer_distance is not None else 20,
    )


def _check_cancel(should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")


def _read_body(source, source_format, should_cancel):
    if source_format == "ODT":
        from core.document_engine.odt_html import read_body

        return read_body(source, should_cancel)
    if source_format == "RTF":
        from core.document_engine.rtf_import import read_body

        return read_body(source, should_cancel)
    from core.document_engine.html_docx import read_body

    return read_body(source, should_cancel)


def _inline(node, should_cancel):
    _check_cancel(should_cancel)
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return ""
    if tag == "br":
        return "<br/>"
    if tag == "img":
        return escape(node.get("alt", ""))
    text = escape(node.text or "")
    for child in node:
        text += _inline(child, should_cancel) + escape(child.tail or "")
    if tag in _INLINE:
        return f"<{_INLINE[tag]}>{text}</{_INLINE[tag]}>"
    if tag == "a":
        url = node.get("href", "")
        if urlsplit(url).scheme in {"https", "http", "mailto"}:
            return f'<link href="{escape(url, quote=True)}">{text}</link>'
    return text


def _pictures(node, root, width, should_cancel):
    for picture in node.iter("img"):
        _check_cancel(should_cancel)
        data = image_data(picture, root)
        if data is None:
            continue
        with PillowImage.open(data) as image:
            height = image.height * 0.75
            image_width = image.width * 0.75
        scale = min(1, width / image_width, (A4[1] - 2 * _MARGIN - 24) / height)
        if hasattr(data, "seek"):
            data.seek(0)
        yield Image(str(data) if isinstance(data, Path) else data, width=image_width * scale, height=height * scale)


def _flowables(container, root, width, should_cancel, *, in_cell=False):
    for node in container:
        _check_cancel(should_cancel)
        tag = node.tag
        if not isinstance(tag, str) or tag in _SKIP:
            continue
        if tag in _BLOCKS:
            if node.text and node.text.strip():
                yield _paragraph(escape(node.text))
            yield from _flowables(node, root, width, should_cancel, in_cell=in_cell)
            continue
        if tag == "table" and not in_cell:
            rows = [row.xpath("./td|./th") for row in node.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")]
            columns = max(map(len, rows), default=0)
            if columns:
                cells = [
                    [
                        [
                            _paragraph(_inline(cell, should_cancel)),
                            *_pictures(cell, root, max(1, width / columns - 12), should_cancel),
                        ]
                        for cell in row
                    ]
                    + [""] * (columns - len(row))
                    for row in rows
                ]
                table = LongTable(cells, colWidths=[width / columns] * columns, splitInRow=1)
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                yield table
                yield Spacer(1, 8)
            continue
        if tag == "br" and node.get("data-page-break") == "true":
            yield PageBreak()
            continue
        content = _inline(node, should_cancel)
        if tag == "li":
            content = "• " + content
        heading = len(tag) == 2 and tag[0] == "h" and tag[1] in "123456"
        if content.strip():
            yield _paragraph(f"<b>{content}</b>" if heading else content, size=15 if heading else 11)
        else:
            yield Spacer(1, 12)
        yield from _pictures(node, root, width, should_cancel)
        if node.xpath(".//br[@data-page-break='true']"):
            yield PageBreak()
        if node.tail and node.tail.strip():
            yield _paragraph(escape(node.tail))


def _paragraph(content, *, size=11):
    return Paragraph(content or " ", ParagraphStyle(
        "Multifora", fontName=_FONT_NAME, fontSize=size, leading=size * 1.3, spaceAfter=5,
    ))


def export_pdf(source, destination, source_format, should_cancel):
    layout = _PageLayout()
    if source_format == "DOCX":
        from docx import Document

        from core.document_engine.docx_html import _body_html

        _check_cancel(should_cancel)
        document = Document(source)
        layout = _docx_layout(document)
        body = html.fragment_fromstring(_body_html(document, should_cancel), create_parent="body")
    else:
        body = _read_body(source, source_format, should_cancel)
    text = "".join((*body.itertext(), *layout.header, *layout.footer)).replace("\u00a0", " ")
    if _text_font(text + "•") is None:
        from core.document_engine.qt_pdf import write_pdf

        return write_pdf(body, source, destination, should_cancel)
    register_font_family()
    root = Path(source).parent.resolve()
    left, right, top, bottom = layout.margins
    width = layout.size[0] - left - right - 12
    if width <= 0 or layout.size[1] - top - bottom <= 12:
        raise ValueError("Некорректные размеры страницы документа")
    story = []
    if body.text and body.text.strip():
        story.append(_paragraph(escape(body.text)))
    story.extend(_flowables(body, root, width, should_cancel))
    if not story:
        story.append(Spacer(1, 12))
    with atomic_output_path(destination) as temporary:
        pdf = SimpleDocTemplate(
            temporary, pagesize=layout.size, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
        )
        def check_page(canvas, _document):
            _check_cancel(should_cancel)
            canvas.saveState()
            canvas.setFont(_FONT_NAME, 9)
            for index, line in enumerate(layout.header):
                canvas.drawString(left, layout.size[1] - layout.header_distance - (index + 1) * 10, line)
            for index, line in enumerate(reversed(layout.footer)):
                canvas.drawString(left, layout.footer_distance + index * 10, line)
            canvas.restoreState()

        pdf.build(story, onFirstPage=check_page, onLaterPages=check_page)
        _check_cancel(should_cancel)
