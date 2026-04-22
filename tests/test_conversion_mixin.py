import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.conversion.conversion_mixin import ConversionMixin
import core.workers.conversion.conversion_mixin as conv_module


class _SignalStub:
    def __init__(self):
        self.emitted = []

    def emit(self, value):
        self.emitted.append(value)


class _DummyConversionWorker(ConversionMixin):
    def __init__(self):
        self.files = []
        self.errors = []
        self.conversion_type = ""
        self.status = _SignalStub()
        self.progress = _SignalStub()
        self.finished = _SignalStub()
        self.error = _SignalStub()
        self._word_warmup_done = False
        self._cancel_requested = False

    def _should_cancel(self):
        return self._cancel_requested

    def _record_error(self, file_item, message):
        self.errors.append({"file": file_item, "message": message})

    def _get_unique_path(self, path):
        return path


class ConversionMixinTests(unittest.TestCase):
    def test_convert_files_accepts_pdf_to_images_alias(self):
        worker = _DummyConversionWorker()

        class _SimpleFile:
            is_file = True
            name = "input.pdf"
            path = r"C:\temp\input.pdf"

        worker.files = [_SimpleFile()]
        worker.conversion_type = "pdf_to_images"

        with patch.object(worker, "_convert_pdf_to_image", return_value=r"C:\temp\output.jpg") as convert_mock:
            with patch("core.workers.conversion.conversion_mixin.os.path.exists", return_value=True):
                worker._convert_files()

        self.assertEqual(convert_mock.call_count, 1)
        self.assertEqual(len(worker.finished.emitted), 1)
        result = worker.finished.emitted[0]
        self.assertIn("new_files", result)
        self.assertEqual(len(result["new_files"]), 1)

    def test_word_to_pdf_fallback_without_python_executable(self):
        worker = _DummyConversionWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_docx = os.path.join(tmpdir, "source.docx")
            with open(source_docx, "wb") as f:
                f.write(b"x")

            source_item = FileItem(source_docx)

            def fake_word_to_pdf(src, dst):
                with open(dst, "wb") as f:
                    f.write(b"%PDF-1.4")

            with patch.object(worker, "_warmup_word", return_value=None):
                with patch.object(worker, "_resolve_python_for_docx2pdf", return_value=None):
                    with patch.object(conv_module, "HAS_WORD_TO_PDF", True):
                        with patch.object(conv_module, "word_to_pdf", side_effect=fake_word_to_pdf) as convert_mock:
                            result_path = worker._convert_word_to_pdf(source_item)

            self.assertTrue(os.path.exists(result_path))
            self.assertEqual(convert_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()

