"""Интеграционные проверки установленных офисных приложений (по явному флагу)."""

import os
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from docx import Document

from app.core.models import FileItem
from core.workers.conversion.conversion_mixin import ConversionMixin


class ConversionWorker(ConversionMixin):
    conversion_output_mode = "source_subfolder"
    conversion_output_dir = ""

    def _should_cancel(self):
        return False


def body_paragraphs(path):
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    ns = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    }
    body = root.find("office:body/office:text", ns)
    return ["".join(p.itertext()).strip() for p in body.findall(".//text:p", ns)]


@unittest.skipUnless(os.environ.get("MULTIFORA_TEST_OFFICE"), "Installed office integration is opt-in")
class DocumentIntegrationTests(unittest.TestCase):
    def test_plain_text_to_odt_uses_installed_office(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("Первая строка\n\nВторая строка", encoding="utf-8")
            worker = ConversionWorker()
            with patch.object(worker, "_convert_text_document", side_effect=AssertionError):
                result = worker._convert_document_auto(FileItem(str(source)), "ODT")
            self.assertEqual(body_paragraphs(result), ["Первая строка", "", "Вторая строка"])

    def test_real_docx_to_odt_uses_installed_office(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.docx"
            document = Document()
            document.add_paragraph("Привет, мир!")
            document.save(source)
            result = ConversionWorker()._convert_docx_to_odt(FileItem(str(source)))
            self.assertIn("Привет, мир!", body_paragraphs(result))

    def test_real_html_and_text_exports_keep_cyrillic_and_inline_image(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.docx"
            picture = Path(directory) / "picture.png"
            Image.new("RGB", (24, 24), "red").save(picture)
            document = Document()
            document.add_paragraph("Привет, мир!")
            document.add_picture(str(picture))
            document.save(source)
            worker = ConversionWorker()
            html = worker._convert_document_auto(FileItem(str(source)), "HTML")
            result = Path(html).read_text(encoding="utf-8")
            self.assertIn("Привет, мир!", result)
            self.assertIn("data:image/", result)
            text = worker._convert_document_auto(FileItem(str(source)), "TXT")
            self.assertIn("Привет, мир!", Path(text).read_text(encoding="utf-8"))
