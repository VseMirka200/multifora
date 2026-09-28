import unittest

from app.core.conversion_formats import (
    CONVERSION_CATEGORIES,
    DOCUMENT_CATEGORY,
    IMAGE_CATEGORY,
    category_for_file_type,
    compatible_targets_for_source,
    format_for_path,
    mixed_source_label_for_category,
    source_formats_for_category,
    target_formats_for_category,
    matches_format,
    suffix_for_format,
)


class ConversionFormatsTests(unittest.TestCase):
    def test_each_category_has_source_and_target_formats(self):
        self.assertIn("SVG", target_formats_for_category(IMAGE_CATEGORY))
        for category in CONVERSION_CATEGORIES:
            self.assertTrue(source_formats_for_category(category))
            self.assertTrue(target_formats_for_category(category))

    def test_known_extensions_resolve_to_expected_format(self):
        self.assertEqual(format_for_path("report.doc"), "DOC")
        self.assertEqual(format_for_path("report.docx"), "DOCX")
        self.assertEqual(format_for_path("photo.jpeg"), "JPEG")
        self.assertEqual(format_for_path("book.epub"), "EPUB")
        self.assertEqual(format_for_path("design.psd"), "PSD")
        self.assertEqual(format_for_path("vector.svg"), "SVG")

    def test_format_matching_and_output_suffix(self):
        self.assertTrue(matches_format("report.doc", "DOC"))
        self.assertFalse(matches_format("report.doc", "DOCX"))
        self.assertEqual(suffix_for_format("JPEG"), ".jpeg")
        self.assertEqual(suffix_for_format("HTML"), ".html")
        self.assertEqual(suffix_for_format("unknown"), "")

    def test_file_types_resolve_to_categories(self):
        self.assertEqual(category_for_file_type("document"), DOCUMENT_CATEGORY)
        self.assertEqual(category_for_file_type("image"), IMAGE_CATEGORY)

    def test_mixed_mode_offers_one_common_target(self):
        mixed_images = mixed_source_label_for_category(IMAGE_CATEGORY)
        image_targets = compatible_targets_for_source(IMAGE_CATEGORY, mixed_images)
        self.assertIn("WEBP", image_targets)
        self.assertIn("PNG", image_targets)
        self.assertIn("PDF", image_targets)

        mixed_docs = mixed_source_label_for_category(DOCUMENT_CATEGORY)
        doc_targets = compatible_targets_for_source(DOCUMENT_CATEGORY, mixed_docs)
        self.assertIn("PDF", doc_targets)
        self.assertIn("DOCX", doc_targets)

    def test_source_only_formats_are_not_offered_as_targets(self):
        self.assertIn("PSD", source_formats_for_category(IMAGE_CATEGORY))
        self.assertNotIn("PSD", target_formats_for_category(IMAGE_CATEGORY))
        self.assertIn("EPUB", source_formats_for_category(DOCUMENT_CATEGORY))
        self.assertNotIn("EPUB", target_formats_for_category(DOCUMENT_CATEGORY))


if __name__ == "__main__":
    unittest.main()
