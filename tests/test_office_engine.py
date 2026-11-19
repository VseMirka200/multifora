from contextlib import closing
from os import environ

import pypdfium2 as pdfium
import pytest
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image
from pypdf import PdfReader
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from core.document_engine.office import run_office


def _native_font_application():
    application = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        message = f"System fonts unavailable on Qt platform {application.platformName()}"
        if environ.get("MULTIFORA_REQUIRE_NATIVE_QT") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return application


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "исходный документ.docx"
    document = Document()
    document.add_paragraph("Привет, Мультифора")
    document.save(path)
    return path


def test_converts_without_modifying_source(source, tmp_path):
    original = source.read_bytes()
    destination = tmp_path / "результат.pdf"
    messages = []
    assert run_office(source, destination, "PDF", lambda: False, status=messages.append) == ""
    assert "Привет, Мультифора" in PdfReader(destination).pages[0].extract_text()
    assert source.read_bytes() == original
    assert messages


def test_cancellation_does_not_publish_output(source, tmp_path):
    destination = tmp_path / "результат.pdf"
    states = iter([False, False, True])
    with pytest.raises(InterruptedError):
        run_office(source, destination, "PDF", lambda: next(states))
    assert not destination.exists()


def test_existing_destination_is_preserved(source, tmp_path):
    destination = tmp_path / "out.pdf"
    destination.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        run_office(source, destination, "PDF", lambda: False)
    assert destination.read_bytes() == b"existing"


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32", "cp1251"])
def test_unicode_input_is_decoded_and_newlines_normalized(tmp_path, encoding):
    source = tmp_path / "source.txt"
    source.write_bytes("Привет\r\n\r\nМир".encode(encoding))
    destination = tmp_path / "out.docx"
    run_office(source, destination, "DOCX", lambda: False)
    assert [paragraph.text for paragraph in Document(destination).paragraphs] == ["Привет", "", "Мир"]


def test_unsupported_document_is_rejected(tmp_path):
    source = tmp_path / "unsupported.doc"
    source.write_bytes(b"test")
    destination = tmp_path / "out.pdf"
    with pytest.raises(ValueError, match="DOC"):
        run_office(source, destination, "PDF", lambda: False)
    assert not destination.exists()


def test_docx_pdf_retains_page_size_and_repeated_header_footer(tmp_path):
    source = tmp_path / "document.docx"
    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.header.paragraphs[0].text = "Верхний колонтитул"
    section.footer.paragraphs[0].text = "Нижний колонтитул"
    document.add_paragraph("Первая страница")
    document.add_page_break()
    document.add_paragraph("Вторая страница")
    document.save(source)
    output = tmp_path / "document.pdf"
    run_office(source, output, "PDF", lambda: False)
    pages = PdfReader(output).pages
    assert len(pages) == 2
    for index, marker in enumerate(("Первая страница", "Вторая страница")):
        page = pages[index]
        assert (page.mediabox.width, page.mediabox.height) == (612, 792)
        text = page.extract_text()
        assert marker in text
        assert "Верхний колонтитул" in text
        assert "Нижний колонтитул" in text


@pytest.fixture
def formatted_docx(tmp_path):
    image = tmp_path / "source.png"
    Image.new("RGB", (640, 320), "blue").save(image)
    source = tmp_path / "source.docx"
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.style.font.name = "Arial"
    text = paragraph.add_run("Styled text")
    text.font.size = Pt(19)
    document.add_picture(str(image), width=Inches(1.5))
    document.save(source)
    return source


@pytest.mark.parametrize("intermediate", ["HTML", "ODT", "RTF"])
def test_editable_round_trip_retains_family_size_and_displayed_image_dimensions(tmp_path, formatted_docx, intermediate):
    middle = tmp_path / f"converted.{intermediate.lower()}"
    run_office(formatted_docx, middle, intermediate, lambda: False)
    output = tmp_path / "roundtrip.docx"
    run_office(middle, output, "DOCX", lambda: False)
    doc = Document(output)
    run = doc.paragraphs[0].runs[0]
    assert (run.text, run.font.name, run.font.size.pt) == ("Styled text", "Arial", 19)
    image = doc.inline_shapes[0]
    assert (image.width.pt, image.height.pt) == pytest.approx((108, 54), abs=0.02)


@pytest.mark.parametrize("source_format", ["DOCX", "HTML", "ODT", "RTF"])
def test_pdf_embeds_font_and_scales_image(tmp_path, formatted_docx, source_format):
    source = formatted_docx
    if source_format != "DOCX":
        source = tmp_path / f"source.{source_format.lower()}"
        run_office(formatted_docx, source, source_format, lambda: False)
    output = tmp_path / "result.pdf"
    run_office(source, output, "PDF", lambda: False)
    text_styles = []

    def read_style(text, _ctm, _matrix, font, size):
        if "Styled text" in text:
            text_styles.append((font["/BaseFont"], size))

    PdfReader(output).pages[0].extract_text(visitor_text=read_style)
    assert any("Arial" in family and size == 19 for family, size in text_styles)
    with pdfium.PdfDocument(str(output)) as rendered:
        page = rendered[0]
        image, = page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE])
        left, bottom, right, top = image.get_bounds()
        assert (right - left, top - bottom) == pytest.approx((108, 54), abs=0.05)


def test_html_pdf_keeps_text_after_nested_blocks_and_tables(tmp_path):
    source = tmp_path / "source.html"
    source.write_text("<div>one</div>two<table><tr><td>three</td></tr></table>four", encoding="utf-8")
    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    assert PdfReader(output).pages[0].extract_text().split() == ["one", "two", "three", "four"]


def test_docx_pdf_exports_narrow_columns_and_merged_cells(tmp_path):
    source = tmp_path / "table.docx"
    document = Document()
    table = document.add_table(rows=2, cols=4)
    for column, width in zip(table.columns, (7.1, 5, 5, 350), strict=True):
        column.width = Pt(width)
    table.cell(0, 0).text = "1"
    table.cell(0, 1).merge(table.cell(0, 2)).text = "2"
    table.cell(0, 3).text = "Заголовок"
    table.cell(1, 0).merge(table.cell(1, 3)).text = "Объединённая строка"
    document.save(source)

    output = tmp_path / "table.pdf"
    run_office(source, output, "PDF", lambda: False)

    page, = PdfReader(output).pages
    assert page.extract_text().splitlines() == ["1", "2", "Заголовок", "Объединённая строка"]


def test_docx_pdf_retains_explicit_cell_borders_and_highlighted_capitals(tmp_path):
    source = tmp_path / "form.docx"
    document = Document()
    table = document.add_table(rows=2, cols=1)
    table.style = "Table Grid"
    table.rows[0].height = Pt(32)
    margins = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        margin = OxmlElement(f"w:{side}")
        margin.set(qn("w:w"), "0")
        margin.set(qn("w:type"), "dxa")
        margins.append(margin)
    table._tbl.tblPr.append(margins)
    for index in range(2):
        cell = table.cell(index, 0)
        borders = OxmlElement("w:tcBorders")
        for side in ("top", "right", "bottom", "left"):
            border = OxmlElement(f"w:{side}")
            border.set(qn("w:val"), "nil")
            if index == 1 and side == "bottom":
                border.set(qn("w:val"), "single")
                border.set(qn("w:sz"), "4")
                border.set(qn("w:color"), "FF0000")
            borders.append(border)
        cell._tc.get_or_add_tcPr().append(borders)
    run = table.cell(0, 0).paragraphs[0].add_run("Heading")
    run.font.all_caps = True
    run.font.color.rgb = RGBColor.from_string("0000FF")
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    table.cell(1, 0).text = "Signature"
    document.save(source)

    output = tmp_path / "form.pdf"
    run_office(source, output, "PDF", lambda: False)
    page, = PdfReader(output).pages
    operations = page.get_contents().operations
    assert page.extract_text().split() == ["HEADING", "Signature"]
    assert sum(operator == b"S" for _, operator in operations) == 1
    assert ([1, 0, 0], b"RG") in operations
    assert ([0, 0, 1], b"rg") in operations
    assert ([1, 1, 0], b"rg") in operations
    with pdfium.PdfDocument(str(output)) as pdf:
        text = pdf[0].get_textpage()
        with closing(text.search("HEADING")) as search:
            heading = text.get_charbox(search.get_next()[0])
        with closing(text.search("Signature")) as search:
            signature = text.get_charbox(search.get_next()[0])
        assert heading[0] == pytest.approx(document.sections[0].left_margin.pt, abs=1.5)
        assert heading[1] - signature[1] == pytest.approx(32, abs=1.5)


def test_docx_pdf_fits_tall_image_to_custom_page(tmp_path):
    image = tmp_path / "source.png"
    Image.new("RGB", (400, 800), "blue").save(image)
    source = tmp_path / "source.docx"
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(5), Inches(4)
    document.add_picture(str(image), width=Inches(4))
    document.save(source)
    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    with pdfium.PdfDocument(str(output)) as rendered:
        assert len(rendered) == 1
        page = rendered[0]
        picture, = page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE])
        left, bottom, right, top = picture.get_bounds()
        assert bottom >= section.bottom_margin.pt
        assert top <= section.page_height.pt - section.top_margin.pt
        assert right - left == pytest.approx((top - bottom) / 2, abs=0.05)


def test_docx_pdf_keeps_text_on_correct_side_of_inline_page_break(tmp_path):
    source = tmp_path / "source.docx"
    document = Document()
    run = document.add_paragraph().add_run("Before")
    run.font.size = Pt(16)
    run.add_break(WD_BREAK.PAGE)
    run.add_text("After")
    document.save(source)
    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    assert [page.extract_text().strip() for page in PdfReader(output).pages] == ["Before", "After"]


@pytest.mark.parametrize("landscape_text", ["Landscape", "Landscape مرحبا"])
def test_docx_pdf_respects_landscape_section_between_portrait_sections(tmp_path, landscape_text):
    _application = _native_font_application() if not landscape_text.isascii() else None
    source = tmp_path / "source.docx"
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.header.paragraphs[0].text = "Inherited header"
    document.add_paragraph("First")
    landscape = document.add_section()
    landscape.orientation = WD_ORIENT.LANDSCAPE
    landscape.page_width, landscape.page_height = Inches(11), Inches(8.5)
    document.add_paragraph(landscape_text)
    portrait = document.add_section()
    portrait.orientation = WD_ORIENT.PORTRAIT
    portrait.page_width, portrait.page_height = Inches(8.5), Inches(11)
    document.add_paragraph("Last")
    document.save(source)

    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    pages = PdfReader(output).pages
    assert [(page.mediabox.width, page.mediabox.height) for page in pages] == [(612, 792), (792, 612), (612, 792)]
    for page, text in zip(pages, ("First", "Landscape", "Last"), strict=True):
        extracted = page.extract_text()
        assert "Inherited header" in extracted
        assert text in extracted


def test_docx_pdf_preserves_continuous_section_without_forcing_page_break(tmp_path):
    source = tmp_path / "source.docx"
    document = Document()
    document.add_paragraph("Before")
    document.add_section(WD_SECTION_START.CONTINUOUS)
    document.add_paragraph("After")
    document.save(source)

    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    pages = PdfReader(output).pages
    assert len(pages) == 1
    assert pages[0].extract_text().split() == ["Before", "After"]


def test_docx_pdf_preserves_inherited_indents_alignment_and_line_spacing(tmp_path):
    source = tmp_path / "source.docx"
    document = Document()
    section = document.sections[0]
    section.left_margin = Inches(1)
    formatting = document.styles["Normal"].paragraph_format
    formatting.left_indent = Pt(18)
    formatting.first_line_indent = Pt(24)
    formatting.line_spacing = Pt(22)
    formatting.space_after = Pt(12)
    paragraph = document.add_paragraph("Indented")
    paragraph.add_run().add_break()
    paragraph.add_run("Next line")
    right = document.add_paragraph("Right aligned")
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    document.save(source)

    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    with pdfium.PdfDocument(str(output)) as rendered:
        text_page = rendered[0].get_textpage()

        def box(text, index=0):
            with closing(text_page.search(text)) as search:
                start, count = search.get_next()
            return text_page.get_charbox(start + (count - 1 if index < 0 else index))

        first = box("Indented")
        second = box("Next line")
        aligned_right = box("Right aligned", -1)
        assert (first[0], second[0]) == pytest.approx((114, 90), abs=1.5)
        assert first[1] - second[1] == pytest.approx(22, abs=1.5)
        assert aligned_right[2] == pytest.approx(section.page_width.pt - section.right_margin.pt, abs=1.5)
        assert second[1] - aligned_right[1] == pytest.approx(34, abs=2)


def test_qt_pdf_preserves_page_geometry_header_footer_and_inline_break(tmp_path):
    _application = _native_font_application()
    source = tmp_path / "source.docx"
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.header.paragraphs[0].text = "Header"
    section.footer.paragraphs[0].text = "Footer"
    run = document.add_paragraph().add_run("Before")
    run.add_break(WD_BREAK.PAGE)
    run.add_text("After office file مرحبا")
    image = tmp_path / "source.png"
    Image.new("RGB", (640, 320), "blue").save(image)
    document.add_picture(str(image), width=Inches(1.5))
    document.save(source)
    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    pages = PdfReader(output).pages
    assert len(pages) == 2
    for page, marker in zip(pages, ("Before", "After office file"), strict=True):
        assert (page.mediabox.width, page.mediabox.height) == (612, 792)
        assert all(text in page.extract_text() for text in (marker, "Header", "Footer"))
    with pdfium.PdfDocument(str(output)) as rendered:
        page = rendered[1]
        picture, = page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE])
        left, bottom, right, top = picture.get_bounds()
        assert (right - left, top - bottom) == pytest.approx((108, 54), abs=0.05)


def test_html_docx_preserves_link_and_table_cell_paragraphs(tmp_path):
    source = tmp_path / "source.html"
    source.write_text(
        '<p><a href="https://example.com">Link</a></p><table><tr><td><p>one</p><p>two</p></td></tr></table>',
        encoding="utf-8",
    )
    output = tmp_path / "out.docx"
    run_office(source, output, "DOCX", lambda: False)
    doc = Document(output)
    assert doc.paragraphs[0].hyperlinks[0].url == "https://example.com"
    assert doc.tables[0].cell(0, 0).text == "one\ntwo"


def test_docx_html_keeps_numbered_list_and_horizontal_merge(tmp_path):
    source = tmp_path / "source.docx"
    document = Document()
    document.add_paragraph("First", "List Number")
    document.add_paragraph("Second", "List Number")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Merged cell"
    document.save(source)
    output = tmp_path / "out.html"
    run_office(source, output, "HTML", lambda: False)
    result = output.read_text(encoding="utf-8")
    assert result.count("<ol>") == 1
    assert result.count("<li>") == 2
    assert '<td colspan="2"' in result
    assert result.count("Merged cell") == 1


@pytest.mark.parametrize("requires_qt", [False, True])
def test_docx_pdf_preserves_merged_table_and_cell_content(tmp_path, requires_qt):
    _application = _native_font_application() if requires_qt else None
    source = tmp_path / "table.docx"
    image = tmp_path / "picture.png"
    Image.new("RGB", (400, 200), "blue").save(image)
    document = Document()
    table = document.add_table(rows=3, cols=2)
    table.columns[0].width = Pt(90)
    table.columns[1].width = Pt(240)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Merged title" + (" مرحبا" if requires_qt else "")
    vertical = table.cell(1, 0).merge(table.cell(2, 0))
    vertical.text = "Vertical top"
    vertical.add_paragraph("Vertical lower")
    table.cell(1, 1).text = "Right first"
    cell = table.cell(2, 1)
    cell.text = "Right last"
    cell.add_paragraph().add_run().add_picture(str(image), width=Pt(180))
    document.save(source)

    output = tmp_path / "out.pdf"
    run_office(source, output, "PDF", lambda: False)
    with pdfium.PdfDocument(str(output)) as rendered:
        assert len(rendered) == 1
        page = rendered[0]
        text_page = page.get_textpage()
        text = text_page.get_text_range()
        assert all(text.count(phrase) == 1 for phrase in (
            "Merged title", "Vertical top", "Vertical lower", "Right first", "Right last",
        )), repr(text)
        with closing(text_page.search("Vertical lower")) as search:
            lower = text_page.get_charbox(search.get_next()[0])
        with closing(text_page.search("Vertical top")) as search:
            upper = text_page.get_charbox(search.get_next()[0])
        with closing(text_page.search("Right first")) as search:
            right = text_page.get_charbox(search.get_next()[0])
        assert upper[1] - lower[1] >= 10
        assert right[0] - upper[0] == pytest.approx(90, abs=3)
        picture, = page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE])
        left, bottom, right, top = picture.get_bounds()
        assert (right - left, top - bottom) == pytest.approx((180, 90), abs=1)
