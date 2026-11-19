import subprocess
import sys
import textwrap
import unittest


class WorkerPackageImportTests(unittest.TestCase):
    def test_file_operations_import_without_app(self):
        script = textwrap.dedent("""
            import sys

            from core.compress_files import compress_image
            from core.document_engine.office import run_office
            from core.file_models import OperationFile
            from core.operation_result import OperationResult
            from core.pdf_docx_batch import run_parallel_batch
            from core.rename_plan import resolve_rename_targets
            from core.rename_transaction import rename_batch

            assert not any(name == "app" or name.startswith("app.") for name in sys.modules)
            assert "PySide6.QtCore" not in sys.modules
            assert "PIL.Image" not in sys.modules
        """)
        subprocess.run([sys.executable, "-c", script], check=True, timeout=30)

    def test_file_worker_defers_heavy_backends(self):
        script = textwrap.dedent("""
            import sys

            from app.workers.factory import create_operation_worker

            assert create_operation_worker(None)
            assert "cv2" not in sys.modules
            assert "numpy" not in sys.modules
            assert "PIL.Image" not in sys.modules
            assert "pillow_heif" not in sys.modules
            assert "odf" not in sys.modules
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script],
            text=True,
            encoding="utf-8",
            timeout=30,
        ).strip()
        self.assertEqual(output, "OK")

    def test_optional_image_backends_load_on_first_use(self):
        script = textwrap.dedent("""
            import sys

            from core import image_dependencies as deps

            assert deps.HAS_PIL
            assert deps.HAS_HEIF
            assert "PIL.Image" not in sys.modules
            assert "pillow_heif" not in sys.modules
            assert "odf" not in sys.modules

            with deps.Image.new("RGB", (1, 1)) as image:
                assert image.size == (1, 1)
            assert "PIL.Image" in sys.modules
            assert "pillow_heif" in sys.modules
            assert "odf" not in sys.modules

            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script],
            text=True,
            encoding="utf-8",
            timeout=30,
        ).strip()
        self.assertEqual(output, "OK")

    def test_rename_starts_and_completes_without_conversion_dependencies(self):
        script = textwrap.dedent("""
            import sys
            import tempfile
            from pathlib import Path
            from types import SimpleNamespace
            from unittest.mock import Mock

            class RejectConversionImports:
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.startswith((
                        "core.image_dependencies",
                        "app.workers.conversion", "app.workers.compression",
                    )):
                        raise AssertionError("Unexpected dependency: " + fullname)

            sys.meta_path.insert(0, RejectConversionImports())
            from app.ui.ui_main import MultiforaMainWindow
            from app.workers.rename_worker import RenameWorker

            window = SimpleNamespace(
                _ensure_operation_can_start=lambda: True,
                file_worker=None,
                progress_bar=SimpleNamespace(setValue=Mock()),
                on_worker_status=Mock(), on_operation_finished=Mock(),
                on_operation_error=Mock(),
            )
            assert MultiforaMainWindow.create_file_worker(window, operation="rename")
            worker = window.file_worker
            assert isinstance(worker, RenameWorker)
            with tempfile.TemporaryDirectory() as directory:
                sources = []
                names = []
                for index in range(15):
                    source = Path(directory, f"before{index}.txt")
                    source.write_text(str(index))
                    sources.append(SimpleNamespace(
                        path=str(source), folder=directory, name=source.name,
                    ))
                    names.append(f"after{index}.txt")
                results = []
                worker.finished.connect(results.append)
                worker.set_rename(sources, names)
                worker.run()
                assert len(results) == 1
                assert not results[0].errors
                assert len(results[0].updated_files) == 15
                for index, name in enumerate(names):
                    assert Path(directory, name).read_text() == str(index)
                    assert not Path(sources[index].path).exists()
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script], text=True, encoding="utf-8", timeout=30
        ).strip()
        self.assertEqual(output, "OK")

    def test_worker_package_import_is_qt_lazy(self):
        script = "import sys; import core; import app.workers; print('PySide6.QtCore' in sys.modules)"

        output = subprocess.check_output([sys.executable, "-c", script], text=True, encoding="utf-8").strip()

        self.assertEqual(output, "False")

    def test_generic_worker_factory_reuses_the_same_class(self):
        from app.workers.factory import create_operation_worker

        self.assertIs(type(create_operation_worker(None)), type(create_operation_worker(None)))

    def test_conversion_worker_does_not_import_compression_backend(self):
        script = textwrap.dedent("""
            import sys
            from app.workers.factory import create_operation_worker
            from app.workers.conversion_worker import ConversionWorker

            worker = create_operation_worker("convert")
            assert isinstance(worker, ConversionWorker)
            assert "app.workers.compression_worker" not in sys.modules
            assert "app.workers.compression" not in sys.modules
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script],
            text=True,
            encoding="utf-8",
            timeout=30,
        ).strip()
        self.assertEqual(output, "OK")

    def test_compression_worker_does_not_import_conversion_backend(self):
        script = textwrap.dedent("""
            import sys
            from app.workers.factory import create_operation_worker
            from app.workers.compression_worker import CompressionWorker

            worker = create_operation_worker("compress")
            assert isinstance(worker, CompressionWorker)
            assert "app.workers.conversion_worker" not in sys.modules
            assert "app.workers.conversion" not in sys.modules
            print("OK")
        """)
        output = subprocess.check_output(
            [sys.executable, "-c", script],
            text=True,
            encoding="utf-8",
            timeout=30,
        ).strip()
        self.assertEqual(output, "OK")

    def test_conversion_factory_selects_image_and_document_workers(self):
        from app.workers.conversion_worker import DocumentWorker, ImageWorker
        from app.workers.factory import create_operation_worker

        self.assertIsInstance(create_operation_worker("convert_image"), ImageWorker)
        self.assertIsInstance(create_operation_worker("convert_document"), DocumentWorker)


if __name__ == "__main__":
    unittest.main()
