"""GitFlic feedback templates: no Qt dependency or network requests."""

import unittest

from app.core.feedback import (
    GITFLIC_NEW_ISSUE_URL,
    ISSUE_TYPES,
    PROJECT_SUPPORT_URL,
    get_issue_type,
    issue_clipboard_text,
    issue_markdown,
)


class FeedbackTemplatesTests(unittest.TestCase):
    def test_categories_are_unique_and_have_emoji(self):
        self.assertGreaterEqual(len(ISSUE_TYPES), 4)
        self.assertEqual(len({kind.key for kind in ISSUE_TYPES}), len(ISSUE_TYPES))
        self.assertTrue(all(kind.caption and kind.subject and kind.sections for kind in ISSUE_TYPES))
        self.assertTrue(any(kind.key == "bug" for kind in ISSUE_TYPES))

    def test_render_every_template(self):
        for kind in ISSUE_TYPES:
            with self.subTest(kind=kind.key):
                output = issue_markdown(kind.key, version="1.2.3")
                self.assertIn("Мультифора: 1.2.3", output)
                self.assertIn("Windows", output)
                for header, _ in kind.sections:
                    self.assertIn("## " + header, output)
                self.assertIn("персональные данные", output)

    def test_unknown_kind_fails(self):
        with self.assertRaises(ValueError):
            get_issue_type("undefined")

    def test_clipboard_format_has_separate_title_and_description(self):
        text = issue_clipboard_text("  🐛 Ошибка  ", "  ## Шаги\n1. Нажать  ")
        self.assertEqual(text, "Название:\n🐛 Ошибка\n\nОписание (Markdown):\n## Шаги\n1. Нажать")

    def test_links_are_https_and_point_to_project(self):
        self.assertTrue(GITFLIC_NEW_ISSUE_URL.startswith(PROJECT_SUPPORT_URL + "/issue/"))
        self.assertTrue(PROJECT_SUPPORT_URL.startswith("https://gitflic.ru/"))


if __name__ == "__main__":
    unittest.main()
