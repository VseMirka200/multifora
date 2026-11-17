"""Проверяет преобразование страниц PDF встроенным движком."""

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from tests.pdf_engine_fixtures import create_pdf


class PdfDocumentEngineTests(unittest.TestCase):
    def test_pdf_to_docx_keeps_text_in_page_order(self):
        from app.core.models import FileItem
        from tests.test_conversion_mixin import _DummyConversionWorker

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "pages.pdf"
            create_pdf(source, ["FIRST PAGE", "SECOND PAGE"])
            output = _DummyConversionWorker()._convert_pdf_to_docx(FileItem(str(source)))
            with ZipFile(output) as document:
                root = ElementTree.fromstring(document.read("word/document.xml"))
                text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
            self.assertIn("FIRST PAGE", text)
            self.assertIn("SECOND PAGE", text)
            self.assertLess(text.index("FIRST PAGE"), text.index("SECOND PAGE"))
