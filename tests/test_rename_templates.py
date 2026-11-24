import unittest

import app.core.rename_templates as rt


class RenameTemplateTests(unittest.TestCase):
    def test_regex_replace_supports_groups_and_ignore_case(self):
        self.assertEqual(
            rt.regex_replace(
                "IMG_0042", r"^img_(\d+)$", r"Фото_\1", ignore_case=True
            ),
            "Фото_0042",
        )

    def test_case_modes(self):
        self.assertEqual(rt.apply_case_mode("my FILE", "lower"), "my file")
        self.assertEqual(rt.apply_case_mode("my FILE", "upper"), "MY FILE")
        self.assertEqual(rt.apply_case_mode("my FILE", "title"), "My File")
        self.assertEqual(rt.apply_case_mode("my FILE", "sentence"), "My file")
        self.assertEqual(rt.apply_case_mode("my FILE", "swap"), "MY file")

    def test_sentence_case_skips_symbols_before_the_first_letter(self):
        self.assertEqual(rt.apply_case_mode("__01_ёЛКА и ДОГОВОР", "sentence"), "__01_Ёлка и договор")
        self.assertEqual(rt.apply_case_mode("__01_+-", "sentence"), "__01_+-")

    def test_get_date_format_known(self):
        self.assertEqual(rt.get_date_format("ГГГГММДД (20240115)"), "%Y%m%d")

    def test_get_date_format_default(self):
        self.assertEqual(rt.get_date_format("UNKNOWN"), "%Y-%m-%d")

if __name__ == "__main__":
    unittest.main()
