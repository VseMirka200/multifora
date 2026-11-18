"""Compare experimental Python PDF operations with the bundled engines."""

import subprocess
from os import environ
from pathlib import Path

import pytest
from docx import Document
from PIL import Image
from pypdf import PdfReader

from core.pdf_engine.merge import combine_pdfs as python_merge
from core.pdf_engine.render import render_pdf_pages as python_render
from core.workers.office_engine import run_office

_REFERENCE = Path(environ.get("MULTIFORA_REFERENCE_PDFCRAFT", "bin/pdfcraft/pdfcraft-cli.exe")).resolve()


@pytest.mark.skipif(not _REFERENCE.is_file(), reason="Optional reference PDFCraft executable unavailable")
def test_merge_and_render_against_bundled_engines(tmp_path):
    source = tmp_path / "документ.docx"
    doc = Document()
    doc.add_heading("Проверка документа", 0)
    doc.add_paragraph("Текст кириллицей и English text")
    doc.add_page_break()
    doc.add_paragraph("Вторая страница")
    doc.save(source)
    pdf = tmp_path / "исходник.pdf"
    run_office(source, pdf, "PDF", lambda: False)
    expected = tmp_path / "craft.pdf"
    actual = tmp_path / "python.pdf"
    executable = _REFERENCE
    subprocess.run([executable, "combine", pdf, pdf, "--out", expected], check=True, capture_output=True)
    python_merge([pdf, pdf], actual, lambda: False)
    expected_reader, actual_reader = PdfReader(expected), PdfReader(actual)
    assert len(expected_reader.pages) == len(actual_reader.pages) == 4
    assert [p.extract_text() for p in expected_reader.pages] == [p.extract_text() for p in actual_reader.pages]
    expected_dir, actual_dir = tmp_path / "craft", tmp_path / "python"
    expected_dir.mkdir()
    actual_dir.mkdir()
    expected_pages = []
    for number in range(1, 3):
        page = expected_dir / f"{number}.png"
        subprocess.run(
            [executable, "render", pdf, "--page", str(number), "--dpi", "200", "--out", page],
            check=True, capture_output=True,
        )
        expected_pages.append(page)
    actual_pages = python_render(pdf, actual_dir, lambda: False)
    assert len(expected_pages) == len(actual_pages) == 2
    for expected_page, actual_page in zip(expected_pages, actual_pages, strict=True):
        with Image.open(expected_page) as left, Image.open(actual_page) as right:
            assert abs(left.width - right.width) <= 1
            assert abs(left.height - right.height) <= 1
