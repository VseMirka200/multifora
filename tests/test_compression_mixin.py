import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.compression.compression_mixin import CompressionMixin


class _Signal:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class _Worker(CompressionMixin):
    def __init__(self, files, kind="pdf"):
        self.files = files
        self.compression_level = 75
        self.compression_type = kind
        self.pdf_method = "auto"
        self.replace_pdf = False
        self.image_output_mode = "alongside"
        self.image_output_dir = ""
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

    def _get_unique_path(self, path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        index = 1
        while os.path.exists(f"{base}_{index}{ext}"):
            index += 1
        return f"{base}_{index}{ext}"


class CompressionMixinTests(unittest.TestCase):
    def test_pdf_compression_delegates_to_pdfcraft(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source.pdf")
            with open(source, "wb") as stream:
                stream.write(b"x" * 1000)
            worker = _Worker([FileItem(source)], "pdf")

            def compress(_owner, _source, output, ppi, quality):
                self.assertEqual((ppi, quality), (300, 85))
                with open(output, "wb") as stream:
                    stream.write(b"small pdf")
                return output

            with patch("core.workers.compression.compression_mixin.native_engines.compress_pdf", side_effect=compress) as engine:
                worker._compress_pdf_files()
            engine.assert_called_once()
            results, updated = worker.finished.values[-1]
            self.assertEqual(len(results), 1)
            self.assertEqual(updated, [])
            self.assertTrue(results[0].path.endswith("_compressed.pdf"))

    def test_image_compression_delegates_to_photocraft(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source.png")
            with open(source, "wb") as stream:
                stream.write(b"x" * 1000)
            worker = _Worker([FileItem(source)], "image")

            def compress(_owner, _source, output, quality):
                self.assertEqual(quality, 75)
                with open(output, "wb") as stream:
                    stream.write(b"small")
                return output

            with patch("core.workers.compression.compression_mixin.native_engines.compress_image", side_effect=compress) as engine:
                worker._compress_image_files()
            engine.assert_called_once()
            results, updated = worker.finished.values[-1]
            self.assertEqual(len(results), 1)
            self.assertEqual(updated, [])
            self.assertTrue(results[0].path.endswith("_compressed.png"))

    def test_read_only_photo_formats_are_rejected_for_in_place_compression(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "vector.svg")
            with open(source, "wb") as stream:
                stream.write(b"<svg/>")
            worker = _Worker([FileItem(source)], "image")
            with patch("core.workers.compression.compression_mixin.native_engines.compress_image") as engine:
                worker._compress_image_files()
            engine.assert_not_called()
            self.assertTrue(worker.errors)
            self.assertIn("не может сохранить", worker.errors[0][1])

    def test_pdf_replace_mode_updates_original_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source.pdf")
            with open(source, "wb") as stream:
                stream.write(b"x" * 1000)
            worker = _Worker([FileItem(source)], "pdf")
            worker.replace_pdf = True

            def compress(_owner, _source, output, _ppi, _quality):
                with open(output, "wb") as stream:
                    stream.write(b"small")
                return output

            with patch("core.workers.compression.compression_mixin.native_engines.compress_pdf", side_effect=compress):
                worker._compress_pdf_files()
            results, updated = worker.finished.values[-1]
            self.assertEqual(results, [])
            self.assertEqual(updated[0][1], source)
            self.assertEqual(os.path.getsize(source), 5)

    def test_pdf_profiles_map_to_pdfcraft_options(self):
        self.assertEqual(_Worker._pdf_profile("unused", "max"), (72, 40))
        self.assertEqual(_Worker._pdf_profile("unused", "quality"), (300, 92))
        self.assertEqual(_Worker._pdf_profile("unused", "optimize"), (300, 90))


if __name__ == "__main__":
    unittest.main()
