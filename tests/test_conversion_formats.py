import unittest

from app.core.conversion_formats import (
    CONVERSION_CATEGORIES,
    category_for_file_type,
    format_for_path,
    formats_for_category,
    matches_format,
    suffix_for_format,
)


class ConversionFormatsTests(unittest.TestCase):
    def test_each_category_has_formats(self):
        for category in CONVERSION_CATEGORIES:
            self.assertTrue(formats_for_category(category))

    def test_known_extensions_resolve_to_expected_format(self):
        self.assertEqual(format_for_path("report.doc"), "DOCX")
        self.assertEqual(format_for_path("photo.jpeg"), "JPEG")
        self.assertEqual(format_for_path("clip.mkv"), "MKV")
        self.assertEqual(format_for_path("sound.flac"), "FLAC")

    def test_format_matching_and_output_suffix(self):
        self.assertTrue(matches_format("report.doc", "DOCX"))
        self.assertFalse(matches_format("report.doc", "PDF"))
        self.assertEqual(suffix_for_format("JPEG"), ".jpeg")
        self.assertEqual(suffix_for_format("unknown"), "")

    def test_file_types_resolve_to_categories(self):
        self.assertEqual(category_for_file_type("document"), "Документы")
        self.assertEqual(category_for_file_type("image"), "Фотографии")
        self.assertEqual(category_for_file_type("video"), "Видео")
        self.assertEqual(category_for_file_type("audio"), "Звуки")


if __name__ == "__main__":
    unittest.main()
