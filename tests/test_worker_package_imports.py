import subprocess
import sys
import textwrap
import unittest


class WorkerPackageImportTests(unittest.TestCase):
    def test_rename_starts_and_completes_without_conversion_dependencies(self):
        script = textwrap.dedent('''
            import sys
            import tempfile
            from pathlib import Path
            from types import SimpleNamespace
            from unittest.mock import Mock

            class RejectConversionImports:
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.startswith((
                        "app.core.deps", "core.workers.file_worker",
                        "core.workers.conversion", "core.workers.compression",
                    )):
                        raise AssertionError("Unexpected dependency: " + fullname)

            sys.meta_path.insert(0, RejectConversionImports())
            from app.ui.ui_main import MultiforaMainWindow
            from core.workers.rename_worker import RenameWorker

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
        ''')
        output = subprocess.check_output(
            [sys.executable, "-c", script], text=True, encoding="utf-8", timeout=30
        ).strip()
        self.assertEqual(output, "OK")

    def test_core_workers_package_import_is_qt_lazy(self):
        script = (
            "import sys; import core.workers; "
            "print('core.workers.file_worker' in sys.modules)"
        )

        output = subprocess.check_output(
            [sys.executable, "-c", script], text=True, encoding="utf-8"
        ).strip()

        self.assertEqual(output, "False")


if __name__ == "__main__":
    unittest.main()
