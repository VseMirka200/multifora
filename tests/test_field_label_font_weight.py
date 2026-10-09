"""Field captions use regular weight; section headers and buttons are unchanged."""

import unittest

from app.ui.ui_styles import STANDARD_FORM_LABEL_STYLE, build_tab_content_style_block


class FieldLabelFontWeightTests(unittest.TestCase):
    def test_shared_form_labels_are_regular(self):
        self.assertIn("font-weight: 400;", STANDARD_FORM_LABEL_STYLE)

    def test_operation_field_captions_are_regular_in_both_themes(self):
        for theme in ("light", "dark"):
            style = build_tab_content_style_block(theme)
            caption = style.split("QLabel#tab_section_label {", 1)[1].split("}", 1)[0]
            self.assertIn("font-weight: 400;", caption)
            self.assertNotIn("font-weight: 700;", caption)


if __name__ == "__main__":
    unittest.main()
