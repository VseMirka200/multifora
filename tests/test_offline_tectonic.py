import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.workers.conversion.tectonic_pdf import FONT_CHOICE, TectonicUnavailableError, _bundled_cache_environment
from scripts.prepare_tectonic_cache import prepare


class OfflineTectonicTests(unittest.TestCase):
    def test_bundled_cache_is_copied_to_user_directory_and_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "installation" / "bin" / "tectonic" / "tectonic.exe"
            seed = executable.parent / "cache"
            seed.mkdir(parents=True)
            executable.write_bytes(b"engine")
            cache_id = "a" * 64
            (seed / ".multifora-cache-id").write_text(cache_id, encoding="ascii")
            (seed / "resource").write_bytes(b"tex-resource")
            with (
                patch.dict(os.environ, {"LOCALAPPDATA": str(root / "user")}),
                patch.dict(os.environ, {"TECTONIC_CACHE_DIR": "wrong"}),
            ):
                environment = _bundled_cache_environment(str(executable))
                target = Path(environment["TECTONIC_CACHE_DIR"])
                self.assertEqual((target / "resource").read_bytes(), b"tex-resource")
                (target / "resource").write_bytes(b"already-used")
                self.assertEqual(_bundled_cache_environment(str(executable))["TECTONIC_CACHE_DIR"], str(target))
                self.assertEqual((target / "resource").read_bytes(), b"already-used")

    def test_missing_marker_reports_incomplete_install(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "tectonic.exe"
            executable.touch()
            (executable.parent / "cache").mkdir()
            with self.assertRaises(TectonicUnavailableError):
                _bundled_cache_environment(str(executable))

    def test_installed_app_reports_missing_cache_without_network_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "tectonic.exe"
            executable.touch()
            with patch("core.workers.conversion.tectonic_pdf.sys.frozen", True, create=True):
                with self.assertRaisesRegex(TectonicUnavailableError, "отсутствуют ресурсы"):
                    _bundled_cache_environment(str(executable))

    def test_cache_copy_can_be_cancelled_without_publishing_partial_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "install" / "tectonic.exe"
            seed = executable.parent / "cache"
            seed.mkdir(parents=True)
            executable.touch()
            cache_id = "b" * 64
            (seed / ".multifora-cache-id").write_text(cache_id, encoding="ascii")
            (seed / "resource").write_bytes(b"data")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(root / "user")}):
                with self.assertRaises(InterruptedError):
                    _bundled_cache_environment(str(executable), Mock(side_effect=[False] + [True] * 10))
            self.assertFalse((root / "user" / "Multifora" / "tectonic" / cache_id).exists())

    def test_invalid_seed_marker_reports_engine_problem(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "tectonic.exe"
            executable.touch()
            seed = executable.parent / "cache"
            seed.mkdir()
            (seed / ".multifora-cache-id").write_bytes(b"\xff")
            with self.assertRaises(TectonicUnavailableError):
                _bundled_cache_environment(str(executable))

    def test_corrupt_user_cache_is_reported_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "install" / "tectonic.exe"
            seed = executable.parent / "cache"
            seed.mkdir(parents=True)
            executable.touch()
            cache_id = "a" * 64
            (seed / ".multifora-cache-id").write_text(cache_id, encoding="ascii")
            destination = root / "user" / "Multifora" / "tectonic" / cache_id
            destination.mkdir(parents=True)
            (destination / ".multifora-cache-id").write_text("damaged", encoding="ascii")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(root / "user")}):
                with self.assertRaisesRegex(TectonicUnavailableError, "повреждено"):
                    _bundled_cache_environment(str(executable))

    def test_build_creates_cache_only_after_offline_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "tectonic.exe"
            executable.write_bytes(b"engine")
            destination = root / "prepared-cache"
            calls = []

            def compile_stub(_executable, _work, cache, *, offline):
                calls.append(offline)
                if not offline:
                    (cache / "format-data").write_bytes(b"resource")

            with (
                patch("scripts.prepare_tectonic_cache._sample", return_value=(FONT_CHOICE, {})),
                patch("scripts.prepare_tectonic_cache._compile", side_effect=compile_stub),
            ):
                # The real compiler creates the PDF before the offline check.
                def create_output(*args, **kwargs):
                    compile_stub(*args, **kwargs)
                    (args[1] / "document.pdf").write_bytes(b"%PDF")

                with patch("scripts.prepare_tectonic_cache._compile", side_effect=create_output):
                    prepare(executable, destination)
            self.assertEqual(calls, [False, False, True, True])
            self.assertEqual((destination / "format-data").read_bytes(), b"resource")
            self.assertEqual(len((destination / ".multifora-cache-id").read_text(encoding="ascii")), 64)

    def test_build_does_not_publish_cache_if_offline_verification_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "tectonic.exe"
            executable.write_bytes(b"engine")
            destination = root / "prepared-cache"

            def compile_stub(_executable, work, cache, *, offline):
                if offline:
                    raise RuntimeError("offline resources missing")
                (cache / "resource").write_bytes(b"data")
                (work / "document.pdf").write_bytes(b"%PDF")

            with (
                patch("scripts.prepare_tectonic_cache._sample", return_value=(FONT_CHOICE, {})),
                patch("scripts.prepare_tectonic_cache._compile", side_effect=compile_stub),
            ):
                with self.assertRaisesRegex(RuntimeError, "offline resources missing"):
                    prepare(executable, destination)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
