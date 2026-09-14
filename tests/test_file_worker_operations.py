import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.workers.file_worker import FileWorker


class FileWorkerOperationTests(unittest.TestCase):
    def test_operation_handlers_can_be_built_for_every_operation(self):
        worker = FileWorker()

        self.assertEqual(
            set(worker._operation_handlers()),
            {"convert", "rename", "compress", "merge", "metadata"},
        )

    @patch("core.workers.file_worker.os.rename")
    @patch("core.workers.file_worker.os.path.exists", return_value=False)
    def test_rename_operation_moves_file_and_emits_result(self, _exists, rename):
        source = SimpleNamespace(
            path="C:/files/source.txt",
            folder="C:/files",
            name="source.txt",
        )
        worker = FileWorker()
        results = []
        worker.finished.connect(results.append)
        worker.set_rename([source], ["renamed.txt"])

        worker.run()

        expected_target = os.path.join("C:/files", "renamed.txt")
        rename.assert_called_once_with("C:/files/source.txt", expected_target)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].updated_files[0][1], expected_target)
        self.assertEqual(results[0].errors, [])

    def test_rename_operation_renames_real_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source.txt")
            target_path = os.path.join(tmp_dir, "renamed.txt")
            with open(source_path, "w", encoding="utf-8") as stream:
                stream.write("test")

            source = SimpleNamespace(
                path=source_path,
                folder=tmp_dir,
                name="source.txt",
            )
            worker = FileWorker()
            results = []
            worker.finished.connect(results.append)
            worker.set_rename([source], ["renamed.txt"])

            worker.run()

            self.assertFalse(os.path.exists(source_path))
            self.assertTrue(os.path.exists(target_path))
            self.assertEqual(results[0].updated_files, [(source, target_path)])
            self.assertEqual(results[0].errors, [])


if __name__ == "__main__":
    unittest.main()
