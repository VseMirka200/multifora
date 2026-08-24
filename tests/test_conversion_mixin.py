import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.conversion.conversion_mixin import ConversionMixin
from core.workers.result import OperationResult
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
        self.conversion_format = ""
        self.conversion_output_dir = ""
        self._conversion_reserved_paths = set()
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

    def _emit_finished(self, new_files=None, updated_files=None):
        self.finished.emit(OperationResult(new_files or [], updated_files or [], list(self.errors)))

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

    def test_convert_files_emits_result_when_cancelled(self):
        worker = _DummyConversionWorker()

        class _SimpleFile:
            is_file = True
            name = "input.pdf"
            path = r"C:\temp\input.pdf"

        worker.files = [_SimpleFile()]
        worker.conversion_type = "pdf_to_images"
        worker._cancel_requested = True

        worker._convert_files()

        self.assertEqual(len(worker.finished.emitted), 1)
        self.assertEqual(worker.finished.emitted[0].get("new_files"), [])

    def test_word_to_pdf_reports_error_when_hidden_com_is_unavailable(self):
        worker = _DummyConversionWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_docx = os.path.join(tmpdir, "source.docx")
            with open(source_docx, "wb") as f:
                f.write(b"x")

            source_item = FileItem(source_docx)

            with patch.object(worker, "_warmup_word", return_value=None):
                with patch.object(worker, "_convert_word_to_pdf_hidden_com", return_value=False):
                    with patch.object(conv_module, "HAS_WORD_TO_PDF", True):
                        with self.assertRaisesRegex(Exception, "Microsoft Word не создал"):
                            worker._convert_word_to_pdf(source_item)

    def test_default_conversion_output_goes_to_sibling_converted_folder(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "clip.png")
            with open(source_path, "wb") as stream:
                stream.write(b"x")
            source_item = FileItem(source_path)

            output_path = worker._conversion_output_path(source_item, ".webp")

            self.assertEqual(
                output_path,
                os.path.join(tmpdir, "Конвертированные", "clip.webp"),
            )
            self.assertTrue(os.path.isdir(os.path.join(tmpdir, "Конвертированные")))

    def test_custom_conversion_output_uses_selected_folder(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            worker.conversion_output_dir = output_dir
            source_path = os.path.join(source_dir, "photo.png")
            with open(source_path, "wb") as stream:
                stream.write(b"x")
            source_item = FileItem(source_path)

            output_path = worker._conversion_output_path(source_item, ".jpg")

            self.assertEqual(output_path, os.path.join(output_dir, "photo.jpg"))

    def test_conversion_output_reserves_unique_names_before_files_exist(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            worker.conversion_output_dir = output_dir
            first_source = os.path.join(source_dir, "a", "same.png")
            second_source = os.path.join(source_dir, "b", "same.png")
            os.makedirs(os.path.dirname(first_source), exist_ok=True)
            os.makedirs(os.path.dirname(second_source), exist_ok=True)
            for source_path in (first_source, second_source):
                with open(source_path, "wb") as stream:
                    stream.write(b"x")

            first = worker._conversion_output_path(FileItem(first_source), ".webp")
            second = worker._conversion_output_path(FileItem(second_source), ".webp")

            self.assertEqual(first, os.path.join(output_dir, "same.webp"))
            self.assertEqual(second, os.path.join(output_dir, "same_1.webp"))

    def test_reference_file_keeps_chained_conversion_in_original_output_folder(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.odt")
            with open(source_path, "wb") as stream:
                stream.write(b"x")
            source_item = FileItem(source_path)
            intermediate_dir = os.path.join(tmpdir, "Конвертированные")
            os.makedirs(intermediate_dir, exist_ok=True)
            intermediate_path = os.path.join(intermediate_dir, "source.docx")
            with open(intermediate_path, "wb") as stream:
                stream.write(b"x")

            output_path = worker._conversion_output_path(
                FileItem(intermediate_path),
                ".pdf",
                reference_file=source_item,
            )

            self.assertEqual(output_path, os.path.join(intermediate_dir, "source.pdf"))
            self.assertNotIn(
                os.path.join("Конвертированные", "Конвертированные"),
                output_path,
            )

    @unittest.skipUnless(conv_module.HAS_PIL, "Pillow is required")
    def test_auto_image_converts_mixed_inputs_to_one_target(self):
        from PIL import Image as PILImage

        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            worker.conversion_output_dir = output_dir
            png_path = os.path.join(source_dir, "first.png")
            jpg_path = os.path.join(source_dir, "second.jpg")
            PILImage.new("RGBA", (12, 12), (255, 0, 0, 128)).save(png_path)
            PILImage.new("RGB", (12, 12), (0, 255, 0)).save(jpg_path)

            first = worker._convert_image_auto(FileItem(png_path), "WEBP")
            second = worker._convert_image_auto(FileItem(jpg_path), "WEBP")

            self.assertTrue(first.endswith(".webp"))
            self.assertTrue(second.endswith(".webp"))
            self.assertTrue(os.path.exists(first))
            self.assertTrue(os.path.exists(second))

    def test_auto_document_converts_txt_to_docx(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            worker.conversion_output_dir = output_dir
            source_path = os.path.join(source_dir, "note.txt")
            with open(source_path, "w", encoding="utf-8") as stream:
                stream.write("Пример документа\nВторая строка")

            output_path = worker._convert_document_auto(FileItem(source_path), "DOCX")

            self.assertTrue(output_path.endswith(".docx"))
            self.assertTrue(os.path.exists(output_path))

    def test_auto_conversion_skips_file_already_in_target_format(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as source_dir:
            source_path = os.path.join(source_dir, "already.txt")
            with open(source_path, "w", encoding="utf-8") as stream:
                stream.write("ok")
            self.assertIsNone(worker._convert_document_auto(FileItem(source_path), "TXT"))

    @unittest.skipUnless(conv_module.HAS_PYMUPDF, "PyMuPDF is required")
    def test_text_to_pdf_reserves_output_name_only_once(self):
        worker = _DummyConversionWorker()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            worker.conversion_output_dir = output_dir
            source_path = os.path.join(source_dir, "note.txt")
            with open(source_path, "w", encoding="utf-8") as stream:
                stream.write("Тест")

            output_path = worker._write_text_output(
                FileItem(source_path),
                "PDF",
                "Тест",
            )

            self.assertEqual(output_path, os.path.join(output_dir, "note.pdf"))
            self.assertNotIn("note_1.pdf", output_path)


if __name__ == "__main__":
    unittest.main()
