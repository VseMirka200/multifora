import subprocess
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

    def test_tracked_text_files_are_utf8_without_bom(self):
        tracked_files = subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8").splitlines()
        binary_suffixes = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".zip",
            ".tar.gz",
            ".7z",
            ".rar",
        )

        offenders = []
        for file_name in tracked_files:
            path = Path(file_name)
            if path.suffix.lower() in binary_suffixes or path.name.endswith(".tar.gz"):
                continue

            data = path.read_bytes()
            if b"\x00" in data[:4096]:
                continue

            if data.startswith(b"\xef\xbb\xbf"):
                offenders.append(f"{file_name} (BOM)")
                continue

            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                offenders.append(f"{file_name} (non-utf8)")

        self.assertEqual(offenders, [])
