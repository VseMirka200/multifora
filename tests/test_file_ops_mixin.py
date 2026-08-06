import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.operations.file_ops_mixin import FileOpsMixin


class _SignalStub:
    def __init__(self):
        self.emitted = []

    def emit(self, value):
        self.emitted.append(value)


class _DummyFileWorker(FileOpsMixin):
    def __init__(self, files, destination):
        self.files = files
        self.destination = destination
        self.new_names = []
        self.status = _SignalStub()
        self.progress = _SignalStub()
        self.error = _SignalStub()
        self.errors = []
        self.finished = []
        self.cancelled = False

    def _should_cancel(self):
        return self.cancelled

    def _record_error(self, file_item, message):
        self.errors.append({"file": file_item, "message": message})

    def _emit_finished(self, new_files=None, updated_files=None):
        self.finished.append((new_files or [], updated_files or []))


class FileOpsMixinTests(unittest.TestCase):
    def test_copy_file_preserves_source_and_reports_new_file(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as destination_dir:
            source_path = Path(source_dir, "document.txt")
            source_path.write_text("content", encoding="utf-8")
            worker = _DummyFileWorker([FileItem(str(source_path))], destination_dir)

            worker._copy_files()

            copied_path = Path(destination_dir, source_path.name)
            self.assertTrue(source_path.exists())
            self.assertEqual(copied_path.read_text(encoding="utf-8"), "content")
            self.assertEqual(worker.progress.emitted, [100])
            self.assertEqual(worker.status.emitted, ["Копирование: document.txt"])
            self.assertEqual(len(worker.finished), 1)
            new_files, updated_files = worker.finished[0]
            self.assertEqual([item.path for item in new_files], [str(copied_path)])
            self.assertEqual(updated_files, [])

    def test_move_file_reports_updated_path(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as destination_dir:
            source_path = Path(source_dir, "document.txt")
            source_path.write_text("content", encoding="utf-8")
            file_item = FileItem(str(source_path))
            worker = _DummyFileWorker([file_item], destination_dir)

            worker._move_files()

            moved_path = Path(destination_dir, source_path.name)
            self.assertFalse(source_path.exists())
            self.assertTrue(moved_path.exists())
            new_files, updated_files = worker.finished[0]
            self.assertEqual(new_files, [])
            self.assertEqual(updated_files, [(file_item, str(moved_path))])
            self.assertEqual(worker.status.emitted, ["Перемещение: document.txt"])

    def test_copy_uses_unique_name_when_destination_exists(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as destination_dir:
            source_path = Path(source_dir, "document.txt")
            source_path.write_text("new", encoding="utf-8")
            Path(destination_dir, "document.txt").write_text("existing", encoding="utf-8")
            worker = _DummyFileWorker([FileItem(str(source_path))], destination_dir)

            worker._copy_files()

            unique_path = Path(destination_dir, "document_1.txt")
            self.assertEqual(unique_path.read_text(encoding="utf-8"), "new")
            self.assertEqual(worker.finished[0][0][0].path, str(unique_path))

    def test_copy_error_keeps_original_public_message(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as destination_dir:
            source_path = Path(source_dir, "document.txt")
            source_path.write_text("content", encoding="utf-8")
            worker = _DummyFileWorker([FileItem(str(source_path))], destination_dir)

            with patch(
                "core.workers.operations.file_ops_mixin.shutil.copy2",
                side_effect=OSError("нет доступа"),
            ):
                worker._copy_files()

            expected = "Ошибка копирования document.txt: нет доступа"
            self.assertEqual(worker.error.emitted, [expected])
            self.assertEqual(worker.errors[0]["message"], expected)

    def test_cancel_finishes_without_touching_files(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as destination_dir:
            source_path = Path(source_dir, "document.txt")
            source_path.write_text("content", encoding="utf-8")
            worker = _DummyFileWorker([FileItem(str(source_path))], destination_dir)
            worker.cancelled = True

            worker._move_files()

            self.assertTrue(source_path.exists())
            self.assertEqual(worker.status.emitted, ["Операция отменена пользователем"])
            self.assertEqual(worker.finished, [([], [])])
            self.assertEqual(os.listdir(destination_dir), [])


if __name__ == "__main__":
    unittest.main()
