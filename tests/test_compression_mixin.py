import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.compression.compression_mixin import CompressionMixin


class _DummyCompressionWorker(CompressionMixin):
    def __init__(self, method="auto", files=None):
        self.pdf_method = method
        self.files = files or []
        self._last_pdf_error = ""
        self.cancelled = False

    def _should_cancel(self):
        return self.cancelled

    @staticmethod
    def _get_unique_path(path):
        return path


class CompressionMixinTests(unittest.TestCase):
    def test_image_output_path_uses_selected_destination(self):
        worker = _DummyCompressionWorker()
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir, "source")
            output_dir = Path(tmp_dir, "output")
            source_dir.mkdir()
            source = source_dir / "photo.jpg"
            source.write_bytes(b"image")
            file_item = FileItem(str(source))

            worker.image_output_mode = "alongside"
            alongside = worker._image_compression_target_path(file_item, ".jpg")
            self.assertEqual(alongside, str(source_dir / "photo_compressed.jpg"))

            worker.image_output_mode = "custom"
            worker.image_output_dir = str(output_dir)
            custom = worker._image_compression_target_path(file_item, ".jpg")
            self.assertEqual(custom, str(output_dir / "photo_compressed.jpg"))
            self.assertTrue(output_dir.is_dir())

    def test_ghostscript_profiles_preserve_existing_settings(self):
        expected = {
            "max": ("/screen", 72, 40, "Максимальное сжатие"),
            "quality": ("/prepress", 300, 92, "Сохранить качество"),
            "optimize": ("/printer", 300, 90, "Только оптимизация"),
        }

        for method, (pdf_settings, resolution, quality, name) in expected.items():
            with self.subTest(method=method):
                settings = _DummyCompressionWorker(method)._get_ghostscript_settings()
                self.assertEqual(settings["pdf_settings"], pdf_settings)
                self.assertEqual(settings["color_resolution"], resolution)
                self.assertEqual(settings["jpeg_quality"], quality)
                self.assertEqual(settings["method_name"], name)
                self.assertTrue(settings["optimize"])
                self.assertEqual(settings["embed_fonts"], "true")
                self.assertEqual(settings["subset_fonts"], "true")

    def test_auto_profile_depends_on_original_file_size(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            standard_path = Path(tmp_dir, "standard.pdf")
            standard_path.write_bytes(b"pdf")
            large_path = Path(tmp_dir, "large.pdf")
            with large_path.open("wb") as stream:
                stream.truncate(11 * 1024 * 1024)

            standard = _DummyCompressionWorker(
                "auto", [FileItem(str(standard_path))]
            )._get_ghostscript_settings()
            large = _DummyCompressionWorker(
                "auto", [FileItem(str(large_path))]
            )._get_ghostscript_settings()

        self.assertEqual(standard["method_name"], "Авто (стандарт)")
        self.assertEqual(standard["color_resolution"], 300)
        self.assertEqual(large["method_name"], "Авто (для больших файлов)")
        self.assertEqual(large["color_resolution"], 150)

    def test_pymupdf_document_closes_when_save_fails(self):
        class _Document:
            def __init__(self):
                self.closed = False

            def save(self, *_args, **_kwargs):
                raise OSError("save failed")

            def close(self):
                self.closed = True

        document = _Document()

        class _Fitz:
            @staticmethod
            def open(_path):
                return document

        worker = _DummyCompressionWorker("max")
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir, "source.pdf")
            source.write_bytes(b"original")
            output = Path(tmp_dir, "output.pdf")
            with patch.dict(sys.modules, {"pymupdf": _Fitz}):
                result = worker._compress_pdf_with_pymupdf(
                    str(source),
                    str(output),
                )

        self.assertEqual(result, (False, "", 0.0))
        self.assertTrue(document.closed)
        self.assertEqual(worker._last_pdf_error, "PyMuPDF: save failed")


if __name__ == "__main__":
    unittest.main()
