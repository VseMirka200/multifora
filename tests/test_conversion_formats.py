import unittest

from app.core.conversion_formats import (
    DOCUMENT_CATEGORY,
    IMAGE_CATEGORY,
    IMAGE_WRITABLE_FORMATS,
    build_file_dialog_filter,
    category_for_file_type,
    compatible_targets_for_source,
    format_for_path,
    matches_format,
    mixed_source_label_for_category,
    source_formats_for_category,
    suffix_for_format,
    target_formats_for_category,
)


class ConversionFormatsTests(unittest.TestCase):
    def test_only_artcraft_supported_document_sources_are_exposed(self):
        self.assertEqual(source_formats_for_category(DOCUMENT_CATEGORY), ["PDF", "TXT", "PPTX", "DECKCRAFT"])
        self.assertEqual(compatible_targets_for_source(DOCUMENT_CATEGORY, "TXT"), ["PDF"])
        self.assertIn("DOCX", compatible_targets_for_source(DOCUMENT_CATEGORY, "PDF"))
        self.assertIn("PPTX", compatible_targets_for_source(DOCUMENT_CATEGORY, "PDF"))
        self.assertNotIn("DECKCRAFT", compatible_targets_for_source(DOCUMENT_CATEGORY, "PDF"))

    def test_deckcraft_sources_offer_only_deckcraft_writable_outputs(self):
        targets = compatible_targets_for_source(DOCUMENT_CATEGORY, "PPTX")
        for supported in ("PDF", "PPTX", "DECKCRAFT", "DOCX", "HTML", "RTF", "MD", "TXT", "PNG", "JPG", "GIF"):
            self.assertIn(supported, targets)
        self.assertNotIn("EPUB", targets)
        self.assertNotIn("ODT", targets)
        self.assertNotIn("TIFF", targets)

    def test_image_read_only_formats_are_not_offered_as_targets(self):
        sources = source_formats_for_category(IMAGE_CATEGORY)
        targets = target_formats_for_category(IMAGE_CATEGORY)
        self.assertIn("HEIC", sources)
        self.assertIn("SVG", sources)
        self.assertIn("KRA", sources)
        self.assertNotIn("HEIC", targets)
        self.assertNotIn("SVG", targets)
        self.assertNotIn("KRA", targets)
        self.assertIn("PSD", IMAGE_WRITABLE_FORMATS)
        self.assertIn("PDF", targets)

    def test_known_extensions_resolve_only_when_supported(self):
        self.assertEqual(format_for_path("report.pdf"), "PDF")
        self.assertEqual(format_for_path("presentation.pptx"), "PPTX")
        self.assertEqual(format_for_path("presentation.deckcraft"), "DECKCRAFT")
        self.assertEqual(format_for_path("photo.jpeg"), "JPEG")
        self.assertEqual(format_for_path("design.psd"), "PSD")
        self.assertIsNone(format_for_path("book.epub"))
        self.assertIsNone(format_for_path("report.odt"))
        self.assertIsNone(format_for_path("document.docx"))

    def test_format_matching_and_output_suffix(self):
        self.assertTrue(matches_format("photo.jpeg", "JPEG"))
        self.assertFalse(matches_format("photo.jpeg", "PNG"))
        self.assertEqual(suffix_for_format("JPEG"), ".jpeg")
        self.assertEqual(suffix_for_format("HTML"), ".html")
        self.assertEqual(suffix_for_format("unknown"), "")

    def test_mixed_mode_offers_only_common_safe_targets(self):
        docs = compatible_targets_for_source(
            DOCUMENT_CATEGORY, mixed_source_label_for_category(DOCUMENT_CATEGORY)
        )
        self.assertEqual(docs, ["PDF"])
        images = compatible_targets_for_source(
            IMAGE_CATEGORY, mixed_source_label_for_category(IMAGE_CATEGORY)
        )
        self.assertEqual(images, ["PDF"])

    def test_file_types_resolve_to_categories(self):
        self.assertEqual(category_for_file_type("document"), DOCUMENT_CATEGORY)
        self.assertEqual(category_for_file_type("image"), IMAGE_CATEGORY)

    def test_dialog_filter_omits_removed_formats(self):
        dialog_filter = build_file_dialog_filter()
        self.assertIn("*.pdf", dialog_filter)
        self.assertIn("*.pptx", dialog_filter)
        self.assertIn("*.png", dialog_filter)
        self.assertNotIn("*.epub", dialog_filter)
        self.assertNotIn("*.odt", dialog_filter)
        self.assertNotIn("*.docx", dialog_filter)


if __name__ == "__main__":
    unittest.main()
