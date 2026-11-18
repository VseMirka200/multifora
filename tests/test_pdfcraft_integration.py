"""Exercise the production PDF entry points and verify their output."""

import random

from docx import Document
from PIL import Image
from pypdf import PdfReader, PdfWriter

from core.workers.office_engine import run_office
from core.workers.pdfcraft_engine import combine_pdfs, export_pdf, optimize_pdf, render_pdf_pages


def test_pdfcraft_export_and_combine(tmp_path):
    source = tmp_path / "input.docx"
    document = Document()
    document.add_paragraph("Multifora test document")
    document.save(source)
    pdf = tmp_path / "input.pdf"
    run_office(source, pdf, "PDF", lambda: False)
    text = tmp_path / "out.txt"
    output = tmp_path / "out.docx"
    export_pdf(pdf, text, "TXT", lambda: False)
    export_pdf(pdf, output, "DOCX", lambda: False)
    assert "Multifora test document" in text.read_text(encoding="utf-8")
    assert "Multifora test document" in "\n".join(p.text for p in Document(output).paragraphs)
    merged = tmp_path / "merged.pdf"
    combine_pdfs([pdf, pdf], merged, lambda: False)
    assert len(PdfReader(merged).pages) == 2
    images = tmp_path / "images"
    images.mkdir()
    pages = render_pdf_pages(merged, images, lambda: False)
    assert len(pages) == 2
    assert all(page.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for page in pages)
    optimized = tmp_path / "optimized.pdf"
    optimize_pdf(pdf, optimized, {"color_resolution": 150, "gray_resolution": 150, "jpeg_quality": 75}, lambda: False)
    assert len(PdfReader(optimized).pages) == 1


def test_pdfcraft_compresses_image_pdf(tmp_path):
    rng = random.Random(42)
    source = tmp_path / "scan.pdf"
    Image.frombytes("RGB", (600, 600), rng.randbytes(600 * 600 * 3)).save(source, "PDF", resolution=300)
    result = tmp_path / "compressed.pdf"
    optimize_pdf(source, result, {"color_resolution": 72, "gray_resolution": 72, "jpeg_quality": 40}, lambda: False)
    assert result.stat().st_size < source.stat().st_size
    assert len(PdfReader(result).pages) == 1


def test_export_scan_through_production_entry_point(tmp_path):
    source = tmp_path / "scan.pdf"
    Image.new("RGB", (200, 300), "blue").save(source, "PDF")
    docx = tmp_path / "out.docx"
    export_pdf(source, docx, "DOCX", lambda: False)
    assert len(Document(docx).inline_shapes) == 1
    text = tmp_path / "out.txt"
    export_pdf(source, text, "TXT", lambda: False)
    assert text.read_bytes() == b""


def test_merge_preserves_outlines(tmp_path):
    source = tmp_path / "links.pdf"
    with PdfWriter() as writer:
        writer.add_blank_page(width=72, height=72)
        writer.add_outline_item(title="Раздел", page_number=0)
        writer.write(source)
    output = tmp_path / "merged.pdf"
    combine_pdfs([source, source], output, lambda: False)
    reader = PdfReader(output)
    assert [(item.title, reader.get_destination_page_number(item)) for item in reader.outline] == [
        ("Раздел", 0), ("Раздел", 1),
    ]
