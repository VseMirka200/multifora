"""Safety and packaging contract for SignPath Foundation onboarding artifacts."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.prepare_signpath_payloads import prepare_payloads

ROOT = Path(__file__).resolve().parents[1]


class SignPathStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.app = root / "Multifora.exe"
        self.installer = root / "Multifora-Setup-1.0.4.exe"
        self.output = root / "signpath-staging"
        self.app.write_bytes(b"MZ" + b"application")
        self.installer.write_bytes(b"MZ" + b"installer")

    def test_archives_contain_exactly_one_expected_unsigned_binary(self):
        manifest = prepare_payloads(self.app, self.installer, self.output)
        self.assertFalse(manifest["signed"])
        self.assertEqual(
            [file["kind"] for file in manifest["files"]],
            ["application", "installer"],
        )
        for entry, source in zip(manifest["files"], (self.app, self.installer)):
            with zipfile.ZipFile(self.output / entry["archive"]) as archive:
                self.assertEqual(archive.namelist(), [source.name])
                self.assertEqual(archive.read(source.name), source.read_bytes())
            self.assertEqual(entry["member"], source.name)
            self.assertEqual(entry["size"], source.stat().st_size)
            self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(
            json.loads((self.output / "manifest.json").read_text("utf-8")),
            manifest,
        )

    def test_refuses_to_overwrite_existing_unsigned_artifacts(self):
        self.output.mkdir()
        (self.output / "marker").write_text("untouched", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            prepare_payloads(self.app, self.installer, self.output)
        self.assertEqual(
            (self.output / "marker").read_text(encoding="utf-8"),
            "untouched",
        )

    def test_rejects_invalid_or_path_like_executable_names(self):
        for name in (
            "Multifora-Setup-1.0.4.exe.extra",
            "Multifora-Setup-v1.0.4.exe",
            "Other-Setup-1.0.4.exe",
        ):
            with self.subTest(name=name):
                renamed = self.installer.with_name(name)
                renamed.write_bytes(b"MZtest")
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    prepare_payloads(self.app, renamed, self.output)
                self.assertFalse(self.output.exists())

    def test_rejects_empty_executable(self):
        self.app.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "Invalid size"):
            prepare_payloads(self.app, self.installer, self.output)
        self.assertFalse(self.output.exists())

    def test_workflow_only_stages_artifacts_without_provider_secrets(self):
        workflow = (ROOT / ".github/workflows/windows-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertLess(
            workflow.index("      - name: Собрать установщик"),
            workflow.index("Подготовить пакеты для SignPath Foundation"),
        )
        self.assertIn("scripts/prepare_signpath_payloads.py", workflow)
        self.assertIn("dist/signpath-staging/", workflow)
        self.assertNotIn("SIGNPATH_API_TOKEN", workflow)
        self.assertNotIn("SignPath/github-action", workflow)

    def test_release_fails_closed_if_signpath_is_enabled_prematurely(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("vars.MULTIFORA_SIGN_PROVIDER", workflow)
        self.assertIn("if ($env:SIGN_PROVIDER -eq 'signpath')", workflow)
        self.assertIn("SignPath Foundation is not connected", workflow)
        self.assertIn("verify_release_commit.py", workflow)


if __name__ == "__main__":
    unittest.main()
