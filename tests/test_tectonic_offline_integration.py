"""Проверка готового автономного набора на реальном DOCX."""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import pytest

from app.core.models import FileItem
from core.workers.conversion.pdf_layout import PdfLayout
from core.workers.conversion.tectonic_pdf import render_pdf
from tests.pdf_engine_fixtures import read_pdf_text
from tests.test_conversion_mixin import _DummyConversionWorker


@pytest.mark.skipif(
    not os.environ.get("MULTIFORA_TECTONIC_TEST_CACHE"),
    reason="Готовый автономный кэш Tectonic не задан",
)
def test_docx_converts_with_bundled_cache_and_no_network(tmp_path):
    from docx import Document
    from PIL import Image

    root = Path(__file__).resolve().parents[1]
    engine = tmp_path / "install" / "bin" / "tectonic" / "tectonic.exe"
    engine.parent.mkdir(parents=True)
    shutil.copyfile(root / "bin" / "tectonic" / "tectonic.exe", engine)
    shutil.copytree(os.environ["MULTIFORA_TECTONIC_TEST_CACHE"], engine.parent / "cache")

    image = tmp_path / "image.png"
    with Image.new("RGB", (16, 16), "red") as picture:
        picture.save(image)
    source = tmp_path / "document.docx"
    document = Document()
    document.add_heading("Offline heading", level=1)
    document.add_paragraph("Offline conversion works")
    document.add_picture(str(image))
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Table content"
    document.save(source)

    with (
        patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path / "user"), "HTTPS_PROXY": "http://127.0.0.1:1"}),
        patch("core.workers.conversion.tectonic_pdf.find_tectonic", return_value=str(engine)),
    ):
        result = _DummyConversionWorker()._convert_docx_to_pdf(FileItem(str(source)))
    text = read_pdf_text(result, tmp_path / "pdf-text.txt")
    assert "Offline heading" in text
    assert "Offline conversion works" in text
    assert "Table content" in text
    assert list((tmp_path / "user" / "Multifora" / "tectonic").glob("*/.multifora-cache-id"))


@pytest.mark.skipif(
    not os.environ.get("MULTIFORA_TECTONIC_TEST_CACHE"),
    reason="Готовый автономный кэш Tectonic не задан",
)
def test_docx_preserves_font_bullet_spaces_and_page_break(tmp_path):
    from docx import Document
    from docx.shared import Pt

    root = Path(__file__).resolve().parents[1]
    engine = tmp_path / "install" / "bin" / "tectonic" / "tectonic.exe"
    engine.parent.mkdir(parents=True)
    shutil.copyfile(root / "bin" / "tectonic" / "tectonic.exe", engine)
    shutil.copytree(os.environ["MULTIFORA_TECTONIC_TEST_CACHE"], engine.parent / "cache")

    source = tmp_path / "document.docx"
    document = Document()
    first = document.add_paragraph(style="List Bullet")
    first.paragraph_format.space_after = Pt(0)
    run = first.add_run("Alpha bravo charlie delta")
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    second = document.add_paragraph("Second page begins here")
    second.paragraph_format.page_break_before = True
    second.runs[0].font.name = "Times New Roman"
    second.runs[0].font.size = Pt(14)
    document.save(source)

    worker = _DummyConversionWorker()
    worker.conversion_output_mode = "alongside"
    with (
        patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path / "user"), "HTTPS_PROXY": "http://127.0.0.1:1"}),
        patch("core.workers.conversion.tectonic_pdf.find_tectonic", return_value=str(engine)),
    ):
        result = worker._convert_docx_to_pdf(FileItem(str(source)))

    text = read_pdf_text(result, tmp_path / "text.txt")
    assert "Alpha bravo charlie delta" in text
    assert "Second page begins here" in text
    assert "\u2022" in text
    executable = root / "bin" / "gswin64" / "gswin64c.exe"
    response = subprocess.run(
        [
            str(executable),
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=txtwrite",
            "-dTextFormat=0",
            "-sOutputFile=-",
            result,
        ],
        capture_output=True,
        check=True,
    )
    pages = ElementTree.fromstring("<document>" + response.stdout.decode("utf-8") + "</document>")
    assert len(pages) == 2
    assert any("TimesNewRoman" in span.get("font", "") for span in pages.iter("span"))


@pytest.mark.skipif(
    not os.environ.get("MULTIFORA_TECTONIC_TEST_CACHE"),
    reason="Готовый автономный кэш Tectonic не задан",
)
def test_unavailable_source_font_is_reported(tmp_path):
    root = Path(__file__).resolve().parents[1]
    engine = tmp_path / "install" / "bin" / "tectonic" / "tectonic.exe"
    engine.parent.mkdir(parents=True)
    shutil.copyfile(root / "bin" / "tectonic" / "tectonic.exe", engine)
    shutil.copytree(os.environ["MULTIFORA_TECTONIC_TEST_CACHE"], engine.parent / "cache")
    layout = PdfLayout(markup='<p><span style="font-family:MultiforaMissingFontQZ">Text</span></p>')
    with (
        patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path / "user"), "HTTPS_PROXY": "http://127.0.0.1:1"}),
        patch("core.workers.conversion.tectonic_pdf.find_tectonic", return_value=str(engine)),
    ):
        render_pdf(layout, str(tmp_path / "output.pdf"), lambda: False)
    assert any("MultiforaMissingFontQZ" in warning for warning in layout.warnings)
