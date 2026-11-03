import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QThread, QTimer
from PySide6.QtWidgets import QApplication

from app.ui.mixins.file_list_actions_mixin import FileListActionsMixin
from app.ui.mixins.lifecycle_mixin import LifecycleMixin
from app.ui.ui_main import MultiforaMainWindow
from core.workers.file_metadata_worker import (
    FileMetadataWorker,
    FolderMetadataWorker,
)


class _AsyncAddHost(QObject, FileListActionsMixin):
    def __init__(self):
        super().__init__()
        self.files = []
        self.status_bar = Mock()
        self.update_file_list = Mock()
        self.update_file_info = Mock()
        self.refresh_active_file_preview = Mock()
        self.log_event = Mock()
        self._column_sort_section = None

    @staticmethod
    def _ru_files_label(count):
        return f"{count} файлов"

    @staticmethod
    def _ask_folder_add_mode():
        return "contents"


class FileMetadataWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_worker_preserves_order_and_emits_bounded_batches(self):
        paths = [f"C:/queue/{index}.pdf" for index in range(600)]
        batches = []
        worker_threads = []
        loop = QEventLoop()

        def build_item(path):
            worker_threads.append(QThread.currentThread())
            return SimpleNamespace(path=path, size=1)

        worker = FileMetadataWorker(paths, batch_size=128)
        worker.batch_ready.connect(batches.append)
        worker.finished.connect(loop.quit)
        with patch(
            "core.workers.file_metadata_worker.FileItem",
            side_effect=build_item,
        ):
            worker.start()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()

        self.assertFalse(worker.isRunning())
        self.assertEqual(
            [item.path for batch in batches for item in batch], paths
        )
        self.assertEqual([len(batch) for batch in batches], [128, 128, 128, 128, 88])
        self.assertTrue(worker_threads)
        self.assertTrue(
            all(thread is not self.app.thread() for thread in worker_threads)
        )

    def test_large_addition_uses_worker_and_applies_every_batch(self):
        host = _AsyncAddHost()
        paths = [f"C:/queue/{index}.pdf" for index in range(600)]
        loop = QEventLoop()

        with (
            patch(
                "app.ui.mixins.file_list_actions_mixin.os.path.isdir",
                return_value=False,
            ),
            patch(
                "core.workers.file_metadata_worker.FileItem",
                side_effect=lambda path: SimpleNamespace(path=path, size=1),
            ),
        ):
            host.add_files(paths)
            worker = host._file_metadata_worker
            worker.finished.connect(loop.quit)
            QTimer.singleShot(5000, loop.quit)
            loop.exec()

        self.assertEqual([item.path for item in host.files], paths)
        self.assertIsNone(host._file_metadata_worker)
        self.assertGreaterEqual(host.update_file_list.call_count, 3)
        host.refresh_active_file_preview.assert_called_once_with()

    def test_folder_worker_expands_filters_and_preserves_mixed_order(self):
        entries = [
            ("C:/first.pdf", False),
            ("C:/folder", True),
            ("C:/last.docx", False),
        ]
        batches = []
        loop = QEventLoop()
        walk_result = [
            ("C:/folder", [], ["inside.png", "ignored.xyz"]),
            ("C:/folder/sub", [], ["nested.pdf"]),
        ]
        worker = FolderMetadataWorker(entries, set(), batch_size=2)
        worker.batch_ready.connect(batches.append)
        worker.finished.connect(loop.quit)

        with (
            patch(
                "core.workers.file_metadata_worker.os.walk",
                return_value=walk_result,
            ),
            patch(
                "core.workers.file_metadata_worker.FileItem",
                side_effect=lambda path: SimpleNamespace(path=path, size=1),
            ),
        ):
            worker.start()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()

        self.assertEqual(
            [item.path for batch in batches for item in batch],
            [
                "C:/first.pdf",
                os.path.join("C:/folder", "inside.png"),
                os.path.join("C:/folder/sub", "nested.pdf"),
                "C:/last.docx",
            ],
        )
        self.assertEqual(
            worker.unsupported_paths,
            [os.path.join("C:/folder", "ignored.xyz")],
        )

    def test_folder_contents_are_walked_outside_ui_thread(self):
        host = _AsyncAddHost()
        root = "C:/selected-folder"
        paths = ["C:/first.pdf", root, "C:/last.docx"]
        walk_threads = []
        loop = QEventLoop()

        def walk(_root):
            walk_threads.append(QThread.currentThread())
            return [(root, [], ["inside.png"])]

        with (
            patch(
                "app.ui.mixins.file_list_actions_mixin.os.path.isdir",
                side_effect=lambda path: path == root,
            ),
            patch(
                "core.workers.file_metadata_worker.os.walk",
                side_effect=walk,
            ),
            patch(
                "core.workers.file_metadata_worker.FileItem",
                side_effect=lambda path: SimpleNamespace(path=path, size=1),
            ),
        ):
            host.add_files(paths)
            worker = host._file_metadata_worker
            worker.finished.connect(loop.quit)
            QTimer.singleShot(5000, loop.quit)
            loop.exec()

        self.assertEqual(
            [item.path for item in host.files],
            [
                "C:/first.pdf",
                os.path.join(root, "inside.png"),
                "C:/last.docx",
            ],
        )
        self.assertEqual(len(walk_threads), 1)
        self.assertIsNot(walk_threads[0], self.app.thread())

    def test_close_requests_metadata_interruption_before_accepting(self):
        worker = Mock()
        worker.isRunning.return_value = True
        host = SimpleNamespace(
            _file_metadata_worker=worker,
            status_bar=Mock(),
        )
        event = Mock()

        LifecycleMixin.closeEvent(host, event)

        worker.requestInterruption.assert_called_once_with()
        self.assertTrue(host._pending_metadata_close)
        event.ignore.assert_called_once_with()
        event.accept.assert_not_called()

    def test_file_operation_waits_for_metadata_scan(self):
        worker = Mock()
        worker.isRunning.return_value = True
        host = SimpleNamespace(
            _file_metadata_worker=worker,
            _operation_is_running=Mock(return_value=False),
        )

        with patch("app.ui.ui_main.QMessageBox.warning") as warning:
            allowed = MultiforaMainWindow._ensure_operation_can_start(host)

        self.assertFalse(allowed)
        warning.assert_called_once()
        host._operation_is_running.assert_not_called()


if __name__ == "__main__":
    unittest.main()
