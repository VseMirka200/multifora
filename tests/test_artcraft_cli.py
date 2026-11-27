import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.core.artcraft import resolve_artcraft_cli, run_artcraft_cli
from app.core.models import FileItem
from core.workers.conversion.conversion_mixin import ConversionMixin


class _Worker(ConversionMixin):
    def __init__(self):
        self.conversion_output_mode = "source_subfolder"
        self.conversion_output_dir = ""
        self._conversion_reserved_paths = set()
        self.cancelled = False
        self.active_cancel = None

    def _should_cancel(self):
        return self.cancelled

    def _set_active_cancel_action(self, action):
        self.active_cancel = action

    def _clear_active_cancel_action(self, action):
        if self.active_cancel is action:
            self.active_cancel = None


class ArtCraftCliTests(unittest.TestCase):
    def test_resolver_prefers_explicit_environment_path(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = os.path.join(directory, "wordcraft-cli.exe")
            with open(executable, "wb") as stream:
                stream.write(b"test")
            with (
                patch.dict(os.environ, {"MULTIFORA_WORDCRAFT_CLI": executable}),
                patch("app.core.artcraft.shutil.which", return_value=None),
            ):
                self.assertEqual(resolve_artcraft_cli("wordcraft"), executable)

    def test_unknown_engine_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_artcraft_cli("unknown")

    def test_missing_engine_has_configuration_hint(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.core.artcraft.shutil.which", return_value=None),
            patch("app.core.artcraft._application_roots", return_value=()),
        ):
            with self.assertRaisesRegex(FileNotFoundError, "MULTIFORA_PDFCRAFT_CLI"):
                run_artcraft_cli("pdfcraft", ["--help"])

    def test_wordcraft_is_used_for_supported_document_conversion(self):
        worker = _Worker()
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source.docx")
            with open(source, "wb") as stream:
                stream.write(b"input")
            process = Mock(returncode=0)

            def finish():
                output = popen.call_args.args[0][-1]
                with open(output, "wb") as stream:
                    stream.write(b"converted")
                return "", ""

            process.communicate.side_effect = finish
            with (
                patch("core.workers.conversion.conversion_mixin.resolve_artcraft_cli", return_value="wordcraft-cli"),
                patch("app.core.artcraft.resolve_artcraft_cli", return_value="wordcraft-cli"),
                patch("app.core.artcraft.subprocess.Popen", return_value=process) as popen,
                patch("core.workers.conversion.conversion_mixin.ensure_pandoc_detected") as pandoc,
            ):
                result = worker._convert_with_pandoc(FileItem(source), "PDF")

            self.assertTrue(os.path.isfile(result))
            self.assertEqual(popen.call_args.args[0][1:3], ["convert", source])
            pandoc.assert_not_called()

    def test_photocraft_is_used_for_image_conversion(self):
        worker = _Worker()
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source.png")
            with open(source, "wb") as stream:
                stream.write(b"input")
            process = Mock(returncode=0)

            def finish():
                output = popen.call_args.args[0][-1]
                with open(output, "wb") as stream:
                    stream.write(b"converted")
                return "", ""

            process.communicate.side_effect = finish
            with (
                patch("core.workers.conversion.image_conversion_mixin.resolve_artcraft_cli", return_value="photocraft-cli"),
                patch("app.core.artcraft.resolve_artcraft_cli", return_value="photocraft-cli"),
                patch("app.core.artcraft.subprocess.Popen", return_value=process) as popen,
            ):
                result = worker._convert_image_to_image(FileItem(source), "WEBP")

            self.assertTrue(os.path.isfile(result))
            self.assertEqual(popen.call_args.args[0][1:3], ["convert", source])


if __name__ == "__main__":
    unittest.main()
