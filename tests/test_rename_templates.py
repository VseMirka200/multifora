import unittest

import app.core.rename_templates as rt


class RenameTemplateTests(unittest.TestCase):
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
