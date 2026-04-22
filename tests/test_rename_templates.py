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
