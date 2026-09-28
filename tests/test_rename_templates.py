import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import app.core.rename_templates as rt


class RenameTemplateTests(unittest.TestCase):
    def test_regex_replace_supports_groups_and_ignore_case(self):
        self.assertEqual(
            rt.regex_replace("IMG_0042", r"^img_(\d+)$", r"Фото_\1", ignore_case=True),
            "Фото_0042",
        )

    def test_case_modes(self):
        self.assertEqual(rt.apply_case_mode("my FILE", "lower"), "my file")
        self.assertEqual(rt.apply_case_mode("my FILE", "upper"), "MY FILE")
        self.assertEqual(rt.apply_case_mode("my FILE", "sentence"), "My file")
        self.assertEqual(rt.apply_case_mode("my FILE", "swap"), "MY file")

    def test_custom_template_supports_file_and_exif_tokens(self):
        name, nxt = rt.apply_custom_template(
            "{created}_{modified}_{exif_date}_{width}x{height}_{name}",
            "photo",
            ".jpg",
            1,
            "2026-09-09",
            use_numbering=False,
            token_values={
                "created": "2026-01-02",
                "modified": "2026-03-04",
                "exif_date": "2025-05-06",
                "width": 1920,
                "height": 1080,
            },
        )
        self.assertEqual(name, "2026-01-02_2026-03-04_2025-05-06_1920x1080_photo.jpg")
        self.assertEqual(nxt, 1)

    def test_build_file_tokens_uses_file_timestamps(self):
        with patch("app.core.rename_templates.os.path.isfile", return_value=False), \
            patch("app.core.rename_templates.os.path.getctime", return_value=0), \
            patch("app.core.rename_templates.os.path.getmtime", return_value=86400):
            values = rt.build_file_token_values("sample.txt")
        self.assertTrue(values["created"])
        self.assertTrue(values["modified"])
        self.assertEqual(values["file_date"], values["modified"])

    def test_build_file_tokens_reads_exif_date_and_dimensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "photo.jpg")
            exif = Image.Exif()
            exif[36867] = "2024:02:03 10:20:30"
            Image.new("RGB", (16, 9), "white").save(path, exif=exif)

            values = rt.build_file_token_values(str(path))

        self.assertEqual(values["exif_date"], "2024-02-03")
        self.assertEqual(values["width"], "16")
        self.assertEqual(values["height"], "9")

    def test_get_date_format_known(self):
        self.assertEqual(rt.get_date_format("ГГГГММДД (20240115)"), "%Y%m%d")

    def test_get_date_format_default(self):
        self.assertEqual(rt.get_date_format("UNKNOWN"), "%Y-%m-%d")

    def test_custom_template_with_num(self):
        name, nxt = rt.apply_custom_template(
            "{name}_{num}",
            "report",
            ".txt",
            3,
            "2024-01-15",
        )
        self.assertEqual(name, "report_003.txt")
        self.assertEqual(nxt, 4)

    def test_custom_template_with_custom_num_digits(self):
        name, nxt = rt.apply_custom_template(
            "{name}_{num}",
            "report",
            ".txt",
            3,
            "2024-01-15",
            num_digits=5,
        )
        self.assertEqual(name, "report_00003.txt")
        self.assertEqual(nxt, 4)

    def test_custom_template_with_num_format(self):
        name, nxt = rt.apply_custom_template(
            "{name}_{num:04d}",
            "img",
            ".jpg",
            7,
            "2024-01-15",
        )
        self.assertEqual(name, "img_0007.jpg")
        self.assertEqual(nxt, 8)

    def test_custom_template_with_inline_settings(self):
        template = "фото_{num:04d,start=10,step=2}_{date}_{name}"
        settings = rt.parse_custom_template_settings(template)
        name, nxt = rt.apply_custom_template(
            template,
            "scene",
            ".jpg",
            settings["start"],
            "2024-01-15",
            step=settings["step"],
            use_numbering=settings["use_numbering"],
            num_digits=settings["digits"],
        )
        self.assertEqual(name, "фото_0010_2024-01-15_scene.jpg")
        self.assertEqual(nxt, 12)

    def test_parse_custom_template_settings(self):
        settings = rt.parse_custom_template_settings(
            "фото_{num:04d,start=10,step=2}_{date}_{name}"
        )
        self.assertEqual(settings["start"], 10)
        self.assertEqual(settings["step"], 2)
        self.assertEqual(settings["digits"], 4)
        self.assertTrue(settings["use_numbering"])

    def test_custom_template_without_num(self):
        name, nxt = rt.apply_custom_template(
            "{name}_{date}",
            "doc",
            ".pdf",
            12,
            "2024-01-15",
        )
        self.assertEqual(name, "012_doc_2024-01-15.pdf")
        self.assertEqual(nxt, 13)

    def test_custom_template_without_numbering(self):
        name, nxt = rt.apply_custom_template(
            "{name}_{date}",
            "doc",
            ".pdf",
            12,
            "2024-01-15",
            step=5,
            use_numbering=False,
        )
        self.assertEqual(name, "doc_2024-01-15.pdf")
        self.assertEqual(nxt, 12)


if __name__ == "__main__":
    unittest.main()
