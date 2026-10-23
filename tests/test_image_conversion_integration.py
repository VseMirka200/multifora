import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from PIL import Image

from app.core.conversion_formats import (
    DOCUMENT_CATEGORY,
    compatible_targets_for_source,
    mixed_source_label_for_category,
)
from app.core.models import FileItem
from tests.test_conversion_mixin import _DummyConversionWorker


class ImageConversionIntegrationTests(unittest.TestCase):
    def test_grayscale_images_can_be_saved_as_qoi(self):
        with tempfile.TemporaryDirectory() as folder:
            for mode, value in (("L", 120), ("LA", (120, 64))):
                source = Path(folder) / (mode + ".png")
                with Image.new(mode, (20, 10), value) as image:
                    image.save(source)
                worker = _DummyConversionWorker()
                output = worker._convert_image_auto(FileItem(str(source)), "QOI")
                with Image.open(output) as image:
                    self.assertEqual(image.convert("RGB").getpixel((0, 0)), (120, 120, 120))
                    if mode == "LA":
                        self.assertEqual(image.getpixel((0, 0))[3], 64)

    def test_photo_orientation_is_applied_to_image_and_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "rotated.jpg"
            with Image.new("RGB", (40, 20), "red") as image:
                exif = image.getexif()
                exif[274] = 6
                image.save(source, exif=exif)
            worker = _DummyConversionWorker()
            for target in ("PNG", "WEBP", "TIFF"):
                output = worker._convert_image_auto(FileItem(str(source)), target)
                with Image.open(output) as image:
                    self.assertEqual(image.size, (20, 40))
                    self.assertNotIn(image.getexif().get(274), (3, 6, 8))
            output = worker._convert_image_to_pdf(FileItem(str(source)))
            with pymupdf.open(output) as document:
                self.assertLess(document[0].rect.width, document[0].rect.height)

    def test_rgb_transparent_color_is_respected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "transparent.png"
            with Image.new("RGB", (20, 20), "red") as image:
                image.save(source, transparency=(255, 0, 0))
            worker = _DummyConversionWorker()
            for target in ("WEBP", "TIFF"):
                output = worker._convert_image_auto(FileItem(str(source)), target)
                with Image.open(output) as image:
                    self.assertEqual(image.convert("RGBA").getpixel((0, 0))[3], 0)
            output = worker._convert_image_auto(FileItem(str(source)), "BMP")
            with Image.open(output) as image:
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_file_created_during_conversion_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.png"
            with Image.new("RGB", (20, 20), "red") as image:
                image.save(source)
            for target in ("WEBP", "PDF"):
                destination = Path(folder) / ("existing." + target.lower())
                destination.write_bytes(b"existing content")
                worker = _DummyConversionWorker()
                with patch.object(worker, "_conversion_output_path", return_value=str(destination)):
                    with self.assertRaisesRegex(Exception, "Ошибка конвертации"):
                        worker._convert_image_auto(FileItem(str(source)), target)
                self.assertEqual(destination.read_bytes(), b"existing content")
                self.assertEqual(list(Path(folder).glob(".__multifora_*")), [])

    def test_pdf_export_removes_partial_results_after_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "pages.pdf"
            with pymupdf.open() as document:
                document.new_page(width=72, height=72)
                document.new_page(width=72, height=72)
                document.save(str(source))
            worker = _DummyConversionWorker()
            save = worker._save_pillow_image
            calls = 0

            def fail_second_page(*args):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("disk error")
                return save(*args)

            with patch.object(worker, "_save_pillow_image", side_effect=fail_second_page):
                with self.assertRaisesRegex(Exception, "disk error"):
                    worker._convert_pdf_to_image(FileItem(str(source)), "PNG")
            self.assertEqual(list(Path(folder).rglob("*.png")), [])
            self.assertEqual(worker._conversion_reserved_paths, set())

    def test_pdf_image_targets_are_only_offered_for_pdf(self):
        self.assertIn("WEBP", compatible_targets_for_source(DOCUMENT_CATEGORY, "PDF"))
        for source in ("DOCX", mixed_source_label_for_category(DOCUMENT_CATEGORY)):
            self.assertNotIn("WEBP", compatible_targets_for_source(DOCUMENT_CATEGORY, source))

    def test_pdf_exports_every_page_and_registers_results(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "pages.pdf"
            with pymupdf.open() as document:
                for color in ((1, 0, 0), (0, 1, 0)):
                    page = document.new_page(width=72, height=72)
                    page.draw_rect(page.rect, color=color, fill=color)
                document.save(str(source))
            for target in ("JPG", "PNG", "WEBP", "TIFF", "BMP"):
                worker = _DummyConversionWorker()
                worker.files = [FileItem(str(source))]
                worker.conversion_type = "auto_document"
                worker.conversion_format = target
                worker._convert_files()
                self.assertEqual(worker.errors, [])
                results = worker.finished.emitted[0]["new_files"]
                self.assertEqual(len(results), 2)
                for item in results:
                    with Image.open(item.path) as image:
                        image.load()
                        self.assertEqual(image.size, (200, 200))

    def test_webp_preserves_transparency_and_animation_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = _DummyConversionWorker()
            source = Path(folder) / "transparent.png"
            with Image.new("RGBA", (32, 24), (255, 0, 0, 0)) as image:
                image.save(source)
            output = worker._convert_image_auto(FileItem(str(source)), "WEBP")
            with Image.open(output) as image:
                self.assertEqual(image.format, "WEBP")
                self.assertEqual(image.convert("RGBA").getpixel((0, 0))[3], 0)
            source = Path(folder) / "animation.gif"
            with Image.new("RGB", (32, 24), "red") as first, Image.new("RGB", (32, 24), "blue") as second:
                first.save(source, save_all=True, append_images=[second], duration=[40, 180], loop=2)
            output = worker._convert_image_auto(FileItem(str(source)), "WEBP")
            with Image.open(output) as image:
                self.assertEqual(image.n_frames, 2)
                self.assertEqual(image.info["loop"], 2)
                durations = []
                for index in range(image.n_frames):
                    image.seek(index)
                    image.load()
                    durations.append(image.info["duration"])
                self.assertEqual(durations, [40, 180])
