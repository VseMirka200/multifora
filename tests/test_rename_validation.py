import os
import tempfile
import unittest
from pathlib import Path

from app.core.models import FileItem
from app.core.rename_validation import analyze_rename_plan, format_rename_plan_issues


class RenameValidationTests(unittest.TestCase):
    def test_duplicate_targets_are_reported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "one.txt")
            second = Path(tmpdir, "two.txt")
            first.write_text("1", encoding="utf-8")
            second.write_text("2", encoding="utf-8")
            issues = analyze_rename_plan(
                [FileItem(str(first)), FileItem(str(second))],
                ["same.txt", "SAME.txt"],
            )
        self.assertEqual([issue.kind for issue in issues], ["duplicate_target", "duplicate_target"])
        self.assertFalse(any(issue.blocking for issue in issues))

    def test_existing_target_and_invalid_windows_name_are_reported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir, "source.txt")
            target = Path(tmpdir, "target.txt")
            source.write_text("source", encoding="utf-8")
            target.write_text("target", encoding="utf-8")
            item = FileItem(str(source))

            existing = analyze_rename_plan([item], [target.name])
            invalid = analyze_rename_plan([item], ["CON.txt"])
            too_long = analyze_rename_plan([item], [f"{'a' * 252}.txt"])

        self.assertEqual(existing[0].kind, "existing_target")
        self.assertEqual(invalid[0].kind, "invalid_name")
        self.assertTrue(invalid[0].blocking)
        self.assertTrue(too_long[0].blocking)
        self.assertIn("CON.txt", format_rename_plan_issues(invalid))

    def test_unchanged_target_is_not_a_conflict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir, "source.txt")
            source.write_text("source", encoding="utf-8")
            item = FileItem(str(source))
            self.assertEqual(analyze_rename_plan([item], [source.name]), [])


if __name__ == "__main__":
    unittest.main()
