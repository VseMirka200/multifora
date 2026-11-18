"""Exercise PDFCraft against a real PDF and verify its output."""

import json
import random
import subprocess

import pytest
from docx import Document
from PIL import Image

from core.workers.office_engine import find_wordcraft, run_office
from core.workers.pdfcraft_engine import combine_pdfs, export_pdf, find_pdfcraft, optimize_pdf, render_pdf_pages


@pytest.mark.skipif(not find_pdfcraft() or not find_wordcraft(), reason="Bundled engines unavailable")
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
    result = subprocess.run([find_pdfcraft(), "info", str(merged)], capture_output=True, check=True)
    assert json.loads(result.stdout)["pages"] == 2
    images = tmp_path / "images"
    images.mkdir()
    pages = render_pdf_pages(merged, images, lambda: False)
    assert len(pages) == 2
    assert all(page.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for page in pages)
    optimized = tmp_path / "optimized.pdf"
    optimize_pdf(pdf, optimized, {"color_resolution": 150, "gray_resolution": 150, "jpeg_quality": 75}, lambda: False)
    result = subprocess.run([find_pdfcraft(), "info", str(optimized)], capture_output=True, check=True)
    assert json.loads(result.stdout)["pages"] == 1


@pytest.mark.skipif(not find_pdfcraft(), reason="Bundled PDFCraft unavailable")
def test_pdfcraft_compresses_image_pdf(tmp_path):
    rng = random.Random(42)
    source = tmp_path / "scan.pdf"
    Image.frombytes("RGB", (600, 600), rng.randbytes(600 * 600 * 3)).save(source, "PDF", resolution=300)
    result = tmp_path / "compressed.pdf"
    optimize_pdf(source, result, {"color_resolution": 72, "gray_resolution": 72, "jpeg_quality": 40}, lambda: False)
    assert result.stat().st_size < source.stat().st_size
    info = subprocess.run([find_pdfcraft(), "info", str(result)], capture_output=True, check=True)
    assert json.loads(info.stdout)["pages"] == 1
