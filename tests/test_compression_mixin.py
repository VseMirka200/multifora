import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.models import FileItem
from core.workers.compression.compression_mixin import CompressionMixin


class _DummyCompressionWorker(CompressionMixin):
    def __init__(self, method="auto", files=None):
        self.pdf_method = method
        self.files = files or []
        self.cancelled = False

    def _should_cancel(self):
        return self.cancelled

    @staticmethod
    def _get_unique_path(path):
        return path


class CompressionMixinTests(unittest.TestCase):
    def test_cancelled_pdf_compression_emits_result(self):
        worker = _DummyCompressionWorker()
        worker.cancelled = True
        worker.status = Mock()
        worker._emit_finished = Mock()
        worker._compress_pdf_files()
        worker._emit_finished.assert_called_once_with([], [])

    def test_invalid_pdf_is_reported_as_file_error(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder, "source.pdf")
            source.write_bytes(b"pdf")
            worker = _DummyCompressionWorker(files=[FileItem(str(source))])
            worker.status = Mock()
            worker.progress = Mock()
            worker._record_error = Mock()
            worker._emit_finished = Mock()
            worker._compress_pdf_files()
            self.assertIn("Ошибка сжатия PDF", worker._record_error.call_args.args[1])
            worker._emit_finished.assert_called_once_with([], [])

    def test_pdf_batch_keeps_completed_output_and_competing_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            sources = [directory / f"{name}.pdf" for name in ("first", "conflict", "broken")]
            for source in sources:
                source.write_bytes(b"source bytes")
            competitor = directory / "conflict_compressed.pdf"
            worker = _DummyCompressionWorker(files=[FileItem(str(path)) for path in sources])
            worker.status = Mock()
            worker.progress = Mock()
            worker._record_error = Mock()
            worker._emit_finished = Mock()

            def compress(source, stage, _settings, _cancel):
                if Path(source).stem == "broken":
                    raise ValueError("bad input")
                if Path(source).stem == "conflict":
                    competitor.write_bytes(b"external")
                Path(stage).write_bytes(b"small")

            with patch("core.workers.pdfcraft_engine.optimize_pdf", side_effect=compress):
                worker._compress_pdf_files()

            results, updated = worker._emit_finished.call_args.args
            first = directory / "first_compressed.pdf"
            self.assertEqual([Path(item.path) for item in results], [first])
            self.assertEqual(first.read_bytes(), b"small")
            self.assertEqual(competitor.read_bytes(), b"external")
            self.assertEqual(worker._record_error.call_count, 2)
            self.assertFalse(updated)
            self.assertTrue(all(source.read_bytes() == b"source bytes" for source in sources))
            self.assertEqual(set(directory.iterdir()), {*sources, first, competitor})

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

    def test_pdf_profiles_preserve_existing_settings(self):
        expected = {
            "max": (72, 40, "Максимальное сжатие"),
            "quality": (300, 92, "Сохранить качество"),
        }

        for method, (
            resolution,
            quality,
            name,
        ) in expected.items():
            with self.subTest(method=method):
                settings = _DummyCompressionWorker(method)._get_pdf_settings(0)
                self.assertEqual(settings["color_resolution"], resolution)
                self.assertEqual(settings["jpeg_quality"], quality)
                self.assertEqual(settings["method_name"], name)
        self.assertEqual(_DummyCompressionWorker("optimize")._get_pdf_settings(0), {
            "lossless": True, "method_name": "Только оптимизация",
        })

    def test_auto_profile_depends_on_original_file_size(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            standard_path = Path(tmp_dir, "standard.pdf")
            standard_path.write_bytes(b"pdf")
            large_path = Path(tmp_dir, "large.pdf")
            with large_path.open("wb") as stream:
                stream.truncate(11 * 1024 * 1024)

            worker = _DummyCompressionWorker("auto", [FileItem(str(standard_path)), FileItem(str(large_path))])
            with patch("core.workers.pdfcraft_engine.optimize_pdf") as optimize:
                for source in (standard_path, large_path):
                    output = source.with_stem("out-" + source.stem)
                    output.write_bytes(b"ok")
                    worker._compress_pdf_with_pdfcraft(str(source), str(output))
                standard, large = [call.args[2] for call in optimize.call_args_list]

        self.assertEqual(standard["method_name"], "Авто (стандарт)")
        self.assertEqual(standard["color_resolution"], 300)
        self.assertEqual(large["method_name"], "Авто (для больших файлов)")
        self.assertEqual(large["color_resolution"], 150)


if __name__ == "__main__":
    unittest.main()
