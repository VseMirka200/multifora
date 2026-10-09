"""Проверки прямого перехода в GitHub Issues без промежуточной формы."""

import unittest
from pathlib import Path

from app.core.github_links import GITHUB_NEW_ISSUE_URL, PROJECT_SUPPORT_URL
from app.core.update_checker import REPO_PAGE


class GitHubLinksTests(unittest.TestCase):
    def test_support_points_to_repository(self):
        self.assertEqual(PROJECT_SUPPORT_URL, REPO_PAGE)
        self.assertTrue(PROJECT_SUPPORT_URL.startswith("https://github.com/"))

    def test_reporting_opens_template_chooser(self):
        self.assertEqual(GITHUB_NEW_ISSUE_URL, REPO_PAGE + "/issues/new/choose")

    def test_five_russian_issue_templates_exist(self):
        directory = Path(__file__).resolve().parent.parent / ".github/ISSUE_TEMPLATE"
        names = ("bug.md", "file.md", "feature.md", "ui.md", "question.md")
        self.assertEqual({p.name for p in directory.glob("*.md")}, set(names))
        for name in names:
            template = (directory / name).read_text(encoding="utf-8")
            self.assertTrue(template.startswith("---\nname: "))
            self.assertIn("\nabout: ", template)
            self.assertIn("\ntitle: ", template)
            self.assertIn("\n## ", template)
            self.assertIn("персональные данные", template)

    def test_no_legacy_platform_mentions(self):
        root = Path(__file__).resolve().parent.parent
        paths = (root / "app", root / "core", root / "tests", root / "docs", root / ".github")
        candidates = [root / "README.md"]
        for folder in paths:
            if folder.exists():
                candidates.extend(p for p in folder.rglob("*") if p.is_file() and p.suffix in (".py", ".md", ".yml", ".yaml", ".txt"))
        # Собираем строку, чтобы сама проверка не содержала искомое имя.
        legacy_name = "Git" + "Flic"
        for file in candidates:
            with self.subTest(file=str(file.relative_to(root))):
                self.assertNotIn(legacy_name.casefold(), file.read_text(encoding="utf-8").casefold())


if __name__ == "__main__":
    unittest.main()
