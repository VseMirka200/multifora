import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from app.workers.compression_worker import CompressionMixin, CompressionWorker
from core.file_models import FileItem


@pytest.mark.parametrize("extension", [".gif", ".webp", ".png", ".tiff"])
@pytest.mark.parametrize("mode", ["alongside", "replace"])
def test_compression_worker_preserves_multiframe_images(tmp_path, extension, mode):
    source = tmp_path / f"source{extension}"
    with Image.new("RGBA", (96, 96)) as first, Image.new("RGBA", (96, 96)) as second:
        first.paste("red", (15, 15, 65, 65))
        second.paste("blue", (20, 20, 70, 70))
        options = {"disposal": 2} if extension == ".gif" else {}
        first.save(source, save_all=True, append_images=[second], duration=[80, 120], loop=2, **options)
    with source.open("ab") as stream:
        stream.write(bytes(100_000))
    original = source.read_bytes()

    worker = CompressionWorker()
    worker.set_compression([FileItem(str(source))], 65, image_output_mode=mode)
    results = []
    worker.finished.connect(results.append)
    worker.run()

    result = results[0]
    assert not result.errors
    assert not result.warnings
    destination = source if mode == "replace" else Path(result.new_files[0].path)
    if mode == "alongside":
        assert source.read_bytes() == original
    assert destination.read_bytes() != original
    with Image.open(destination) as image:
        assert image.n_frames == 2
        if extension != ".tiff":
            assert image.info["loop"] == 2
        for index, duration in enumerate((80, 120)):
            image.seek(index)
            with image.convert("RGBA") as frame:
                red, _, blue, alpha = frame.getpixel((40, 40))
                assert (red > blue) == (index == 0)
                assert alpha == 255
                assert frame.getpixel((0, 0))[3] == 0
            if extension != ".tiff":
                assert image.info["duration"] == duration


def test_compression_worker_preserves_apng_default_image(tmp_path):
    source = tmp_path / "source.png"
    with (
        Image.new("RGBA", (32, 32), "red") as poster,
        Image.new("RGBA", (32, 32), "blue") as first,
        Image.new("RGBA", (32, 32), "green") as second,
    ):
        poster.save(source, save_all=True, default_image=True, append_images=[first, second], duration=[80, 120])
    with source.open("ab") as stream:
        stream.write(bytes(100_000))
    worker = CompressionWorker()
    worker.set_compression([FileItem(str(source))], 65)
    results = []
    worker.finished.connect(results.append)
    worker.run()
    with Image.open(results[0].new_files[0].path) as result:
        assert result.info["default_image"]
        assert result.n_frames == 3
        assert result.getpixel((0, 0)) == (255, 0, 0, 255)
        result.seek(1)
        assert result.info["duration"] == 80


def test_compression_worker_rejects_single_frame_output_in_replace_mode(tmp_path):
    source = tmp_path / "source.tiff"
    with Image.new("RGB", (96, 96), "red") as first, Image.new("RGB", (96, 96), "blue") as second:
        first.save(source, save_all=True, append_images=[second])
    original = source.read_bytes()

    def omit_pages(image, path, *_args, **_kwargs):
        image.save(path, format="TIFF")

    worker = CompressionWorker()
    worker.set_compression([FileItem(str(source))], 65, image_output_mode="replace")
    results = []
    worker.finished.connect(results.append)
    with patch("core.compress_files.save_optimized_image", side_effect=omit_pages):
        worker.run()
    assert source.read_bytes() == original
    assert results[0].warnings
    assert not results[0].updated_files
    assert list(tmp_path.iterdir()) == [source]


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

            with patch("core.pdf_engine.operations.optimize_pdf", side_effect=compress):
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
            with patch("core.pdf_engine.operations.optimize_pdf") as optimize:
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
