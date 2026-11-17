from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.conversion_formats import DOCUMENT_CATEGORY, compatible_targets_for_source, source_formats_for_category
from app.core.models import FileItem
from core.workers.conversion_worker import ConversionWorker
from core.workers.pandoc_engine import PandocUnavailableError, find_pandoc, run_pandoc


@pytest.mark.skipif(find_pandoc() is None, reason="Pandoc is not installed")
def test_document_conversion_round_trip(tmp_path):
    source = tmp_path / "документ.md"
    source.write_text("# Заголовок\n\nТекст с **выделением**.\n", encoding="utf-8")
    worker = ConversionWorker()
    worker.conversion_output_mode = "alongside"
    output = Path(worker._convert_document_auto(FileItem(str(source)), "DOCX"))
    assert output.exists()
    html = Path(worker._convert_document_auto(FileItem(str(output)), "HTML"))
    result = html.read_text(encoding="utf-8")
    assert "Заголовок" in result
    assert "<strong>выделением</strong>" in result


def test_missing_pandoc_reports_error(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("text", encoding="utf-8")
    with patch("core.workers.pandoc_engine.find_pandoc", return_value=None):
        with pytest.raises(PandocUnavailableError):
            run_pandoc(str(source), str(tmp_path / "out.docx"), "markdown", "docx", lambda: False)


@pytest.mark.skipif(find_pandoc() is None, reason="Pandoc is not installed")
def test_cancelled_conversion_does_not_publish_file(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("text", encoding="utf-8")
    worker = ConversionWorker()
    worker.conversion_output_mode = "alongside"
    with patch.object(worker, "_should_cancel", return_value=True):
        with pytest.raises(InterruptedError):
            worker._convert_document_auto(FileItem(str(source)), "DOCX")
    assert not (tmp_path / "source.docx").exists()
    assert not list(tmp_path.glob(".__multifora_*"))


def test_visible_formats_exclude_unsupported_routes():
    assert "PDF" not in source_formats_for_category(DOCUMENT_CATEGORY)
    assert "PDF" not in compatible_targets_for_source(DOCUMENT_CATEGORY, "DOCX")
    assert "ODT" in compatible_targets_for_source(DOCUMENT_CATEGORY, "DOCX")
