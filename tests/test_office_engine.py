import pytest
from docx import Document
from docx.shared import Inches
from pypdf import PdfReader

from core.workers.office_engine import run_office


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
