"""Сборка редактируемого DOCX из страниц встроенного движка разметки."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from PIL import Image as PillowImage
from reportlab.platypus import Image, Paragraph, Table
from reportlab.platypus.paragraph import _HSFrag

from core.document_engine.rich_pdf import _check_cancel, export_pdf
from core.filesystem import atomic_output_path


def merge_docx_pages(paths, destination, page_order, should_cancel, progress):
    requested = set(page_order)
    if len(requested) != len(page_order) or any(
        not 0 <= source < len(paths) or page < 0 for source, page in requested
    ):
        raise ValueError("Некорректный порядок страниц DOCX.")

    pages = {}
    with TemporaryDirectory(prefix="multifora_docx_pages_") as staging:
        for source in dict.fromkeys(source for source, _ in page_order):
            def capture(page, layout, flowable):
                key = source, page
                if key in requested:
                    _, blocks = pages.setdefault(key, (layout, []))
                    if flowable is not None:
                        blocks.append(flowable)

            export_pdf(paths[source], Path(staging) / f"{source}.pdf", "DOCX", should_cancel, capture=capture)

        if pages.keys() != requested:
            raise ValueError("Состав страниц изменился. Загрузите миниатюры заново.")

        document = Document()
        for index, key in enumerate(page_order):
            _check_cancel(should_cancel)
            layout, blocks = pages[key]
            section = document.add_section(WD_SECTION_START.NEW_PAGE) if index else document.sections[0]
            _apply_layout(section, layout)
            for block in blocks:
                _add_block(document, block, should_cancel)
            if not blocks:
                document.add_paragraph()
            progress(int((index + 1) * 95 / len(page_order)))

        with atomic_output_path(destination) as temporary:
            document.save(temporary)
            _check_cancel(should_cancel)
    progress(100)
    return destination


def _apply_layout(section, layout):
    width, height = layout.size
    section.orientation = WD_ORIENT.LANDSCAPE if width > height else WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = Pt(width), Pt(height)
    section.left_margin, section.right_margin, section.top_margin, section.bottom_margin = map(Pt, layout.margins)
    section.header_distance = Pt(layout.header_distance)
    section.footer_distance = Pt(layout.footer_distance)
    for area, lines in ((section.header, layout.header), (section.footer, layout.footer)):
        if lines or area.is_linked_to_previous:
            area.is_linked_to_previous = False
            area.paragraphs[0].text = "\n".join(lines)


def _paragraph_fragments(block):
    for fragment in block.frags:
        if isinstance(fragment, list):
            yield from fragment[1:]
            if isinstance(fragment, _HSFrag) and fragment[1:]:
                yield fragment[-1][0], " "
        else:
            yield fragment, "\n" if getattr(fragment, "lineBreak", False) else getattr(fragment, "text", "")


def _add_paragraph(container, block):
    paragraph = container.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.alignment = {
        0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.CENTER,
        2: WD_ALIGN_PARAGRAPH.RIGHT, 4: WD_ALIGN_PARAGRAPH.JUSTIFY,
    }.get(block.style.alignment)
    fmt.space_before = Pt(max(0, block.style.spaceBefore))
    fmt.space_after = Pt(max(0, block.style.spaceAfter))
    fmt.left_indent = Pt(block.style.leftIndent)
    fmt.right_indent = Pt(block.style.rightIndent)
    fmt.first_line_indent = Pt(block.style.firstLineIndent)
    for fragment, content in _paragraph_fragments(block):
        if not content:
            continue
        run = paragraph.add_run(content)
        run.font.size = Pt(fragment.fontSize)
        family = fragment.fontName
        if family.startswith("MultiforaFont-"):
            family, variant = family.removeprefix("MultiforaFont-").rsplit("-", 1)
            run.font.name = family
        else:
            variant = family
        run.bold = bool(getattr(fragment, "bold", False) or "bold" in variant.lower())
        run.italic = bool(getattr(fragment, "italic", False) or "italic" in variant.lower())
        run.underline = any(line[1] == "underline" for line in getattr(fragment, "us_lines", ()))
        color = getattr(fragment, "textColor", None)
        if color is not None:
            run.font.color.rgb = RGBColor.from_string(color.hexval()[2:8])


def _add_table(container, block, should_cancel):
    widths = [Pt(width) for width in block._colWidths]
    if hasattr(container, "sections"):
        table = container.add_table(rows=block._nrows, cols=block._ncols)
        for column, width in zip(table.columns, widths, strict=True):
            column.width = width
    else:
        table = container.add_table(rows=block._nrows, cols=block._ncols)
    table.style = "Table Grid"
    table.autofit = False
    covered = set()
    for _, (left, top), (right, bottom) in block._spanCmds:
        if min(left, top, right, bottom) < 0:
            continue
        table.cell(top, left).merge(table.cell(bottom, right))
        covered.update((row, col) for row in range(top, bottom + 1)
                       for col in range(left, right + 1) if (row, col) != (top, left))
    for row, values in enumerate(block._cellvalues):
        for col, value in enumerate(values):
            _check_cancel(should_cancel)
            if (row, col) in covered or not value:
                continue
            cell = table.cell(row, col)
            original = cell.paragraphs[0]._p
            if isinstance(value, (tuple, list)):
                for item in value:
                    _add_block(cell, item, should_cancel)
                if len(cell.paragraphs) > 1:
                    cell._tc.remove(original)
            else:
                cell.paragraphs[0].text = str(value)


def _add_block(container, block, should_cancel):
    _check_cancel(should_cancel)
    if isinstance(block, Paragraph):
        _add_paragraph(container, block)
    elif isinstance(block, Table):
        _add_table(container, block, should_cancel)
    elif isinstance(block, Image):
        with PillowImage.open(block.source_data) as picture, BytesIO() as image:
            picture.convert("RGBA").save(image, format="PNG")
            image.seek(0)
            paragraph = container.add_paragraph()
            paragraph.alignment = getattr(WD_ALIGN_PARAGRAPH, block.hAlign, None)
            # Leave room for the paragraph's line box.
            scale = min(1, (block.drawHeight - 2) / block.drawHeight) if block.drawHeight > 2 else 1
            paragraph.add_run().add_picture(image, width=Pt(block.drawWidth * scale))
