"""Safety regressions for file operations and native-engine migration."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.rename_plan import resolve_rename_targets
from core.workers.atomic_output import atomic_output_path
from core.workers.rename_transaction import rename_batch


class RenameSafetyTests(unittest.TestCase):
    def test_swap_names_preserves_both_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = [Path(directory, name) for name in ("a.txt", "b.txt")]
            first.write_text("FIRST", encoding="utf8")
            second.write_text("SECOND", encoding="utf8")
            items = [SimpleNamespace(path=str(path), folder=directory) for path in (first, second)]
            targets = resolve_rename_targets(items, ["b.txt", "a.txt"])
            successes, errors = rename_batch([item.path for item in items], targets)
            self.assertEqual(errors, [])
            self.assertEqual(len(successes), 2)
            self.assertEqual(first.read_text(), "SECOND")
            self.assertEqual(second.read_text(), "FIRST")

    def test_external_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            first, existing = [Path(directory, name) for name in ("a.txt", "b.txt")]
            first.write_text("FIRST")
            existing.write_text("EXISTING")
            item = SimpleNamespace(path=str(first), folder=directory)
            [target] = resolve_rename_targets([item], ["b.txt"])
            self.assertEqual(os.path.basename(target), "b_1.txt")
            successes, errors = rename_batch([str(first)], [target])
            self.assertFalse(errors)
            self.assertEqual(existing.read_text(), "EXISTING")
            self.assertEqual(Path(successes[0][1]).read_text(), "FIRST")

    def test_duplicate_targets_get_distinct_names(self):
        with tempfile.TemporaryDirectory() as directory:
            items = [
                SimpleNamespace(path=str(Path(directory, name)), folder=directory)
                for name in ("a.txt", "b.txt")
            ]
            result = resolve_rename_targets(items, ["x.txt", "X.txt"])
            self.assertEqual(len({path.casefold() for path in result}), 2)

    def test_staging_failure_rolls_back_files(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory, name) for name in ("a.txt", "b.txt")]
            for idx, path in enumerate(paths):
                path.write_text(str(idx))
            true_rename = os.rename
            calls = 0

            def fail_second_move(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise PermissionError("mock staging failure")
                return true_rename(source, target)

            with patch("core.workers.rename_transaction.os.rename", side_effect=fail_second_move):
                successes, errors = rename_batch(
                    [str(path) for path in paths], [str(paths[1]), str(paths[0])]
                )
            self.assertFalse(successes)
            self.assertTrue(errors)
            self.assertEqual(paths[0].read_text(), "0")
            self.assertEqual(paths[1].read_text(), "1")
            self.assertFalse(list(Path(directory).glob(".__multifora_*")))

    def test_invalid_windows_names_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            item = SimpleNamespace(path=str(Path(directory, "a.txt")), folder=directory)
            for invalid in ("CON.txt", "../outside.txt", "bad?.txt", "end. "):
                with self.subTest(name=invalid), self.assertRaises(ValueError):
                    resolve_rename_targets([item], [invalid])


class AtomicSaveTests(unittest.TestCase):
    def test_fail_does_not_publish_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "merged.pdf")
            with self.assertRaises(RuntimeError):
                with atomic_output_path(str(output)) as temporary:
                    Path(temporary).write_bytes(b"part")
                    raise RuntimeError("failed")
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(directory).glob(".__multifora_*")))

    def test_success_is_published(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "merged.pdf")
            with atomic_output_path(str(output)) as temporary:
                Path(temporary).write_bytes(b"%PDF content")
            self.assertEqual(output.read_bytes(), b"%PDF content")

    def test_does_not_replace_preexisting_target(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "merged.pdf")
            output.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                with atomic_output_path(str(output)) as temporary:
                    Path(temporary).write_bytes(b"new")
            self.assertEqual(output.read_bytes(), b"original")


class NativeEngineMigrationTests(unittest.TestCase):
    def test_legacy_conversion_backend_sources_are_removed(self):
        root = Path(__file__).resolve().parents[1]
        removed = (
            "app/core/deps.py",
            "app/core/pdf_compat.py",
            "core/workers/conversion/image_conversion_mixin.py",
            "core/workers/conversion/image_encoding_mixin.py",
            "core/workers/compression/image_optimizer.py",
            "scripts/install_pandoc.ps1",
            "scripts/install_tectonic.ps1",
        )
        for relative in removed:
            with self.subTest(path=relative):
                self.assertFalse((root / relative).exists())

    def test_runtime_lock_does_not_include_removed_engines(self):
        requirements = Path("requirements-runtime.txt").read_text(encoding="utf-8").lower()
        for package in ("pymupdf", "pdf2docx", "python-docx", "docxcompose", "odfpy", "pillow_heif", "opencv-python", "numpy"):
            with self.subTest(package=package):
                self.assertNotIn(package, requirements)

    def test_native_cli_build_pins_three_upstream_projects(self):
        script = Path("scripts/build_native_engines.ps1").read_text(encoding="utf-8")
        for marker in ("storytold/pdfcraft.git", "storytold/photocraft.git", "storytold/deckcraft.git"):
            self.assertIn(marker, script)
        for tag in ("v0.22.0", "v0.23.1", "v0.19.1"):
            self.assertIn(tag, script)
        self.assertIn("LICENSE-APACHE", script)
        self.assertIn("LICENSE-MIT", script)


if __name__ == "__main__":
    unittest.main()
