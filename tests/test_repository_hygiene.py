from pathlib import Path
import unittest


class RepositoryHygieneTests(unittest.TestCase):
    def test_gitattributes_has_no_global_text_disable(self):
        text = Path(".gitattributes").read_text(encoding="utf-8")

        self.assertNotIn("* -text", text)
        self.assertIn("*.py text eol=lf", text)

    def test_sources_do_not_contain_known_mojibake_markers(self):
        markers = (
            "????",
            "\u0420\u045f",
            "\u0420\u0402",
            "\u0420\u045a",
            "\u0420\u0458",
            "\u0420\u2018",
            "\u0420\u0408",
            "\u0420\u00a4",
            "\u0420\u201d",
            "\u0420\u2014",
            "\u0420\u0409",
            "\u0432\u0402",
        )
        paths = [Path(".gitattributes")]
        paths.extend(Path("app").rglob("*.py"))
        paths.extend(Path("core").rglob("*.py"))
        paths.append(Path("multifora_start.pyw"))

        offenders = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if any(marker in text for marker in markers):
                offenders.append(str(path))

        self.assertEqual(offenders, [])
