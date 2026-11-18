"""Размещение абзацев, изображений и таблиц в PDF с возможностью поиска."""

from copy import deepcopy
from dataclasses import dataclass
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from lxml import etree, html
from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    TableStyle,
)

from core.document_engine.formatting import font_family, image_size, inline_style, points
from core.document_engine.pdf_fonts import pdf_font_family
from core.document_engine.rtf_export import image_data
from core.document_engine.table_layout import table_layout
from core.document_engine.text_pdf import _FONT_NAME, _text_font, register_font_family
from core.filesystem import atomic_output_path

_BLOCKS = {"div", "section", "article", "main", "header", "footer", "blockquote", "ul", "ol"}
_CELL_BLOCKS = _BLOCKS | {"p", "table", "pre", "li", *(f"h{i}" for i in range(1, 7))}
_INLINE = {"strong": "b", "b": "b", "i": "i", "em": "i", "u": "u"}
_SKIP = {"script", "style", "template", "head"}
_MARGIN = 54
_ALIGNMENT = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT, "justify": TA_JUSTIFY}


@dataclass(frozen=True)
class _PageLayout:
    size: tuple = A4
    margins: tuple = (_MARGIN, _MARGIN, _MARGIN, _MARGIN)
    header: tuple = ()
    footer: tuple = ()
    header_distance: float = 20
    footer_distance: float = 20
    frame_padding: float = 6


def _docx_layout(section, previous):
    from docx.enum.section import WD_ORIENT

    width = section.page_width.pt if section.page_width is not None else previous.size[0]
    height = section.page_height.pt if section.page_height is not None else previous.size[1]
    if section.orientation == WD_ORIENT.LANDSCAPE and width < height:
        width, height = height, width
    margins = (section.left_margin, section.right_margin, section.top_margin, section.bottom_margin)
    return _PageLayout(
        (width, height),
        tuple(margin.pt if margin is not None else _MARGIN for margin in margins),
        previous.header if section.header.is_linked_to_previous else tuple(p.text for p in section.header.paragraphs),
        previous.footer if section.footer.is_linked_to_previous else tuple(p.text for p in section.footer.paragraphs),
        section.header_distance.pt if section.header_distance is not None else 20,
        section.footer_distance.pt if section.footer_distance is not None else 20,
        frame_padding=0,
    )


def _docx_sections(source, should_cancel):
    from docx import Document
    from docx.enum.section import WD_SECTION_START

    from core.document_engine.docx_html import _body_html, _typography

    _check_cancel(should_cancel)
    document = Document(source)
    typography = _typography(document)
    result = []
    layout = _PageLayout(frame_padding=0)
    for section in document.sections:
        previous = layout
        layout = _docx_layout(section, previous)
        body = html.fragment_fromstring(
            _body_html(section, should_cancel, typography, skip_section_mark=True), create_parent="body"
        )
        start = section.start_type
        if result and start == WD_SECTION_START.CONTINUOUS and layout == previous:
            result[-1][0].extend(body)
        else:
            parity = {WD_SECTION_START.ODD_PAGE: 1, WD_SECTION_START.EVEN_PAGE: 0}.get(start)
            result.append((body, layout, parity))
    return result


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
    css = inline_style(node)
    family = font_family(css.get("font-family"))
    font = pdf_font_family(family) if family else None
    size = points(css.get("font-size"))
    for enabled, markup in (
        (css.get("font-weight") in {"bold", "600", "700", "800", "900"}, "b"),
        (css.get("font-style") in {"italic", "oblique"}, "i"),
        ("underline" in css.get("text-decoration", "").split(), "u"),
    ):
        if enabled:
            text = f"<{markup}>{text}</{markup}>"
    attributes = [f'face="{escape(font, quote=True)}"'] if font else []
    if size is not None:
        attributes.append(f'size="{size:g}"')
    if attributes:
        text = f"<font {' '.join(attributes)}>{text}</font>"
    if tag in _INLINE:
        return f"<{_INLINE[tag]}>{text}</{_INLINE[tag]}>"
    if tag == "a":
        url = node.get("href", "")
        if urlsplit(url).scheme in {"https", "http", "mailto"}:
            return f'<link href="{escape(url, quote=True)}">{text}</link>'
    return text


def _pictures(node, root, width, height, should_cancel):
    alignment = inline_style(node).get("text-align", "").upper()
    for picture in node.iter("img"):
        _check_cancel(should_cancel)
        data = image_data(picture, root)
        if data is None:
            continue
        with PillowImage.open(data) as image:
            picture_width, picture_height = image_size(
                picture, image.width, image.height, width_limit=width, height_limit=height,
            )
        if hasattr(data, "seek"):
            data.seek(0)
        image = Image(str(data) if isinstance(data, Path) else data, width=picture_width, height=picture_height)
        if alignment:
            image.hAlign = alignment if alignment in {"CENTER", "RIGHT"} else "LEFT"
        yield image


def _paragraph_parts(node):
    part = etree.Element(node.tag, attrib=node.attrib)
    part.text = node.text
    for child in node:
        if child.tag == "br" and child.get("data-page-break") == "true":
            if len(part) or part.text:
                yield part
            yield None
            part = etree.Element(node.tag, attrib=node.attrib)
            part.text = child.tail
        else:
            part.append(deepcopy(child))
    if len(part) or part.text:
        yield part


def _qt_page_breaks(body):
    for node in body.xpath(".//*[br[@data-page-break='true']]"):
        parent = node.getparent()
        index = parent.index(node)
        break_before = False
        for part in _paragraph_parts(node):
            if part is None:
                if break_before:
                    parent.insert(index, etree.Element("p", style="page-break-before:always"))
                    index += 1
                break_before = True
                continue
            if break_before:
                part.set("style", part.get("style", "") + ";page-break-before:always")
            parent.insert(index, part)
            index += 1
            break_before = False
        if break_before:
            if node.getnext() is not None and isinstance(node.getnext().tag, str):
                following = node.getnext()
                following.set("style", following.get("style", "") + ";page-break-before:always")
            else:
                parent.insert(index, etree.Element("p", style="page-break-before:always"))
        if node.tail:
            parent.insert(index, etree.Element("span"))
            parent[index].tail = node.tail
        parent.remove(node)


def _table_flowable(node, root, width, height, should_cancel):
    widths, row_count, placements = table_layout(node, width)
    if not widths:
        return None
    grid = [[""] * len(widths) for _ in range(row_count)]
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for cell, row, column, across, down in placements:
        _check_cancel(should_cancel)
        cell_width = max(1, sum(widths[column:column + across]) - 12)
        cell_height = max(1, height - 6)
        if any(child.tag in _CELL_BLOCKS for child in cell):
            content = list(_flowables(cell, root, cell_width, cell_height, should_cancel, in_cell=True))
        else:
            content = [_paragraph(_inline(cell, should_cancel)),
                       *_pictures(cell, root, cell_width, cell_height, should_cancel)]
        grid[row][column] = content
        if across > 1 or down > 1:
            commands.append(("SPAN", (column, row), (column + across - 1, row + down - 1)))
    return LongTable(grid, colWidths=widths, splitInRow=1, style=TableStyle(commands))


def _flowables(container, root, width, height, should_cancel, *, in_cell=False):
    if container.text and container.text.strip():
        yield _paragraph(escape(container.text))
    number = 0
    for node in container:
        _check_cancel(should_cancel)
        tag = node.tag
        if not isinstance(tag, str) or tag in _SKIP:
            pass
        elif tag in _BLOCKS:
            yield from _flowables(node, root, width, height, should_cancel, in_cell=in_cell)
        elif tag == "table":
            if table := _table_flowable(node, root, width, height, should_cancel):
                yield table
                yield Spacer(1, 8)
        elif tag == "br" and node.get("data-page-break") == "true" and not in_cell:
            yield PageBreak()
        else:
            number += tag == "li"
            marker = (f"{number}. " if container.tag == "ol" else "• ") if tag == "li" else ""
            if tag == "img":
                yield from _pictures(node, root, width, height, should_cancel)
            else:
                if not in_cell and inline_style(node).get("page-break-before") == "always":
                    yield PageBreak()
                if not len(node) and not node.text:
                    yield _paragraph("&#160;", node=node)
                for part in _paragraph_parts(node):
                    if part is None:
                        if not in_cell:
                            yield PageBreak()
                        continue
                    content = _inline(part, should_cancel)
                    heading = len(tag) == 2 and tag[0] == "h" and tag[1] in "123456"
                    if marker or "".join(part.itertext()).strip():
                        content = f"<b>{content}</b>" if heading else content
                        yield _paragraph(marker + content, size=15 if heading else 11, node=part)
                    marker = ""
                    yield from _pictures(part, root, width, height, should_cancel)
        if node.tail and node.tail.strip():
            yield _paragraph(escape(node.tail))


def _signed_points(value):
    value = value.strip()
    if value.startswith("-"):
        return -(points(value[1:]) or 0)
    return points(value) or 0


def _paragraph(content, *, size=11, node=None):
    css = inline_style(node) if node is not None else {}
    size = points(css.get("font-size")) or size
    line_height = css.get("line-height", "")
    leading, auto_leading = size * 1.3, "max"
    if line_height.endswith("%") and (percentage := points(line_height[:-1] + "pt")):
        inline_sizes = (points(inline_style(child).get("font-size")) or 0 for child in node.iter())
        leading = max(size, max(inline_sizes, default=0)) * 1.16 * percentage / 100
    elif exact := points(line_height):
        leading = exact
        auto_leading = "max" if css.get("--docx-line-height-at-least") else "off"
    return Paragraph(content or " ", ParagraphStyle(
        "Multifora", fontName=_FONT_NAME, fontSize=size, leading=leading, autoLeading=auto_leading,
        alignment=_ALIGNMENT.get(css.get("text-align"), TA_LEFT),
        leftIndent=_signed_points(css.get("margin-left", "")), rightIndent=_signed_points(css.get("margin-right", "")),
        firstLineIndent=_signed_points(css.get("text-indent", "")),
        spaceBefore=_signed_points(css.get("margin-top", "")),
        spaceAfter=_signed_points(css.get("margin-bottom", "5pt")),
        keepWithNext=bool(css.get("--docx-keep-with-next")),
    ))


def _write_body(body, layout, source, destination, should_cancel):
    text = "".join((*body.itertext(), *layout.header, *layout.footer)).replace("\u00a0", " ")
    if _text_font(text + "•") is None:
        from core.document_engine.qt_pdf import write_pdf

        _qt_page_breaks(body)
        return write_pdf(body, source, destination, should_cancel, layout=layout)
    register_font_family()
    root = Path(source).parent.resolve()
    left, right, top, bottom = layout.margins
    width, height = layout.size[0] - left - right, layout.size[1] - top - bottom
    padding = layout.frame_padding
    if width <= 2 * padding or height <= 2 * padding:
        raise ValueError("Некорректные размеры страницы документа")
    story = list(_flowables(body, root, width - 2 * padding, height - 2 * padding, should_cancel))
    if not story:
        story.append(Spacer(1, 12))
    with atomic_output_path(destination) as temporary:
        pdf = BaseDocTemplate(temporary, pagesize=layout.size)

        def draw_page(canvas, _document):
            _check_cancel(should_cancel)
            canvas.saveState()
            canvas.setFont(_FONT_NAME, 9)
            for index, line in enumerate(layout.header):
                canvas.drawString(left, layout.size[1] - layout.header_distance - (index + 1) * 10, line)
            for index, line in enumerate(reversed(layout.footer)):
                canvas.drawString(left, layout.footer_distance + index * 10, line)
            canvas.restoreState()

        frame = Frame(left, bottom, width, height, padding, padding, padding, padding)
        pdf.addPageTemplates(PageTemplate("body", frames=[frame], onPage=draw_page, pagesize=layout.size))
        pdf.build(story)
        _check_cancel(should_cancel)


def export_pdf(source, destination, source_format, should_cancel):
    if source_format != "DOCX":
        body = _read_body(source, source_format, should_cancel)
        return _write_body(body, _PageLayout(), source, destination, should_cancel)
    sections = _docx_sections(source, should_cancel)
    if len(sections) == 1:
        body, layout, parity = sections[0]
        if parity != 0:
            return _write_body(body, layout, source, destination, should_cancel)

    from pypdf import PdfWriter

    with TemporaryDirectory(prefix="multifora_docx_sections_") as folder, PdfWriter() as writer:
        previous_size = sections[0][1].size
        for index, (body, layout, parity) in enumerate(sections):
            _check_cancel(should_cancel)
            if parity is not None and (len(writer.pages) + 1) % 2 != parity:
                writer.add_blank_page(*previous_size)
            part = Path(folder, f"section-{index}.pdf")
            _write_body(body, layout, source, part, should_cancel)
            writer.append(part)
            previous_size = layout.size
        with atomic_output_path(destination) as temporary:
            with open(temporary, "wb") as output:
                writer.write(output)
            _check_cancel(should_cancel)
