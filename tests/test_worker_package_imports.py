import subprocess
import sys
import textwrap
import unittest


class WorkerPackageImportTests(unittest.TestCase):
    def test_workers_do_not_import_removed_python_conversion_engines(self):
        script = textwrap.dedent("""
            import sys
            from core.workers.conversion_worker import ConversionWorker
            from core.workers.compression_worker import CompressionWorker
            from core.workers.merge.merge_worker import MergeWorker
            assert ConversionWorker and CompressionWorker and MergeWorker
            removed = ("pymupdf", "fitz", "pdf2docx", "docx", "docxcompose",
                       "odf", "cv2", "numpy", "pillow_heif")
            assert not any(name in sys.modules for name in removed), [
                name for name in removed if name in sys.modules
            ]
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script], text=True, encoding="utf-8", timeout=30
        ).strip()
        self.assertEqual(output, "OK")

    def test_native_engine_module_does_not_load_cli_until_requested(self):
        script = textwrap.dedent("""
            import sys
            from core.workers import native_engines
            assert "subprocess" in sys.modules
            assert native_engines.ENGINE_FILES["pdf"] == "pdfcraft-cli.exe"
            assert native_engines.ENGINE_FILES["photo"] == "photocraft-cli.exe"
            assert native_engines.ENGINE_FILES["deck"] == "deckcraft-cli.exe"
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script], text=True, encoding="utf-8", timeout=30
        ).strip()
        self.assertEqual(output, "OK")

    def test_rename_worker_stays_independent_of_native_engines(self):
        script = textwrap.dedent("""
            import sys
            from core.workers.rename_worker import RenameWorker
            assert RenameWorker
            assert "core.workers.native_engines" not in sys.modules
            assert "core.workers.conversion_worker" not in sys.modules
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script], text=True, encoding="utf-8", timeout=30
        ).strip()
        self.assertEqual(output, "OK")


if __name__ == "__main__":
    unittest.main()
