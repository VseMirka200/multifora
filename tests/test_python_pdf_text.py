import pytest
from docx import Document
from pypdf import PdfWriter

from core.pdf_engine.text import export_text
from core.workers.office_engine import run_office


def test_extract_text_from_multipage_unicode_pdf(tmp_path):
    document = Document()
    document.add_paragraph("Первая страница")
    document.add_page_break()
    document.add_paragraph("Вторая страница")
    source = tmp_path / "документ.docx"
    document.save(source)
    pdf = tmp_path / "файл.pdf"
    run_office(source, pdf, "PDF", lambda: False)
    target = tmp_path / "текст.txt"
    export_text(pdf, target, lambda: False)
    text = target.read_text(encoding="utf-8")
    assert text.index("Первая страница") < text.index("Вторая страница")


def test_cancel_keeps_existing_output(tmp_path):
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as stream:
        writer.write(stream)
    writer.close()
    output = tmp_path / "output.txt"
    output.write_text("original", encoding="utf-8")
    with pytest.raises(InterruptedError):
        export_text(source, output, lambda: True)
    assert output.read_text(encoding="utf-8") == "original"
