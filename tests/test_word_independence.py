"""Интеграционные проверки обработки документов без Microsoft Word."""

import ast
import tempfile
import unittest
from pathlib import Path

from docx import Document
from odf import teletype, text
from odf.opendocument import load

from app.core.deps import ensure_pandoc_detected
from app.core.models import FileItem
from core.workers.conversion.conversion_mixin import ConversionMixin


class ConversionWorker(ConversionMixin):
    conversion_output_mode = "source_subfolder"
    conversion_output_dir = ""

    def _should_cancel(self):
        return False


def test_application_does_not_use_word_automation():
    for root in (Path("app"), Path("core")):
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                else:
                    modules = []
                assert not any(
                    name == "pythoncom" or name.startswith("win32com")
                    for name in modules
                ), str(path)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    assert "word.application" not in node.value.lower(), str(path)


class DocumentIntegrationTests(unittest.TestCase):
    def test_plain_text_to_odt_does_not_use_pandoc(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("Первая строка\n\nВторая строка", encoding="utf-8")
            worker = ConversionWorker()
            with patch.object(worker, "_convert_with_pandoc", side_effect=AssertionError):
                result = worker._convert_document_auto(FileItem(str(source)), "ODT")
            converted = load(result)
            paragraphs = [
                teletype.extractText(p) for p in converted.getElementsByType(text.P)
            ]
            self.assertEqual(paragraphs, ["Первая строка", "", "Вторая строка"])

    def test_real_docx_to_odt_without_word(self):
        if not ensure_pandoc_detected()[0]:
            self.skipTest("Pandoc is not installed")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.docx"
            document = Document()
            document.add_paragraph("Привет, мир!")
            document.save(source)
            result = ConversionWorker()._convert_docx_to_odt(FileItem(str(source)))
            converted = load(result)
            paragraphs = [
                teletype.extractText(p) for p in converted.getElementsByType(text.P)
            ]
            self.assertIn("Привет, мир!", paragraphs)

    def test_no_word_automation(self):
        test_application_does_not_use_word_automation()
