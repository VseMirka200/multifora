import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.conversion.conversion_mixin import ConversionMixin


class _Signal:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class _Worker(ConversionMixin):
    def __init__(self, mode="source_subfolder", output_dir=""):
        self.files = []
        self.conversion_format = "WEBP"
        self.conversion_output_mode = mode
        self.conversion_output_dir = output_dir
        self._conversion_reserved_paths = set()
        self.status = _Signal()
        self.progress = _Signal()
        self.error = _Signal()
        self.finished = _Signal()
        self.errors = []

    def _should_cancel(self):
        return False

    def _emit_finished(self, new_files=None, updated_files=None):
        self.finished.emit((new_files or [], updated_files or []))

    def _record_error(self, file_item, message):
        self.errors.append((file_item, message))


class ConversionMixinTests(unittest.TestCase):
    def test_custom_output_uses_selected_folder(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as output:
            item_path = os.path.join(source, "photo.png")
            with open(item_path, "wb") as stream:
                stream.write(b"source")
            worker = _Worker("custom", output)
            self.assertEqual(worker._conversion_output_path(FileItem(item_path), ".webp"), os.path.join(output, "photo.webp"))

    def test_alongside_output_uses_source_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            item_path = os.path.join(directory, "photo.png")
            with open(item_path, "wb") as stream:
                stream.write(b"source")
            worker = _Worker("alongside")
            self.assertEqual(worker._conversion_output_path(FileItem(item_path), ".jpg"), os.path.join(directory, "photo.jpg"))

    def test_source_subfolder_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            item_path = os.path.join(directory, "photo.png")
            with open(item_path, "wb") as stream:
                stream.write(b"source")
            worker = _Worker()
            output = worker._conversion_output_path(FileItem(item_path), ".webp")
            self.assertEqual(os.path.dirname(output), os.path.join(directory, "Конвертированные"))
            self.assertTrue(os.path.isdir(os.path.dirname(output)))

    def test_output_names_are_reserved_before_files_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = _Worker("alongside")
            first = os.path.join(directory, "first", "same.png")
            second = os.path.join(directory, "second", "same.png")
            os.makedirs(os.path.dirname(first))
            os.makedirs(os.path.dirname(second))
            for source in (first, second):
                with open(source, "wb") as stream:
                    stream.write(b"x")
            self.assertEqual(worker._conversion_output_path(FileItem(first), ".webp"), os.path.join(directory, "first", "same.webp"))
            self.assertEqual(worker._conversion_output_path(FileItem(second), ".webp"), os.path.join(directory, "second", "same.webp"))

    def test_handler_delegates_to_native_engine_router(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "image.png")
            with open(source, "wb") as stream:
                stream.write(b"input")
            worker = _Worker("alongside")
            item = FileItem(source)
            expected = os.path.join(directory, "image.webp")
            with patch("core.workers.conversion.conversion_mixin.native_engines.convert_file", return_value=expected) as convert:
                result = worker._get_conversion_handler()(item)
            self.assertEqual(result, expected)
            convert.assert_called_once_with(worker, item, "WEBP", expected)

    def test_failed_native_conversion_removes_partial_output_and_releases_name(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "image.png")
            with open(source, "wb") as stream:
                stream.write(b"input")
            worker = _Worker("alongside")
            item = FileItem(source)
            expected = os.path.join(directory, "image.webp")

            def partial_failure(_worker, _file, _target, output):
                with open(output, "wb") as stream:
                    stream.write(b"partial")
                raise RuntimeError("native conversion failed")

            with patch("core.workers.conversion.conversion_mixin.native_engines.convert_file", side_effect=partial_failure):
                with self.assertRaisesRegex(RuntimeError, "native conversion failed"):
                    worker._get_conversion_handler()(item)
            self.assertFalse(os.path.exists(expected))
            self.assertNotIn(os.path.normcase(expected), worker._conversion_reserved_paths)

    def test_conversion_mixin_has_no_legacy_engine_imports(self):
        source = open("core/workers/conversion/conversion_mixin.py", encoding="utf-8").read().lower()
        for legacy in ("pdf2docx", "pymupdf", "pandoc", "tectonic", "odfpy", "pillow"):
            self.assertNotIn(legacy, source)


if __name__ == "__main__":
    unittest.main()
