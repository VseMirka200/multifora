import os
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core.models import FileItem
from app.ui.mixins.file_list_actions_mixin import FileListActionsMixin
from app.ui.mixins.file_list_context_mixin import FileListContextMixin
from app.ui.mixins.file_list_preview_mixin import FileListPreviewMixin
from app.ui.mixins.worker_ops_mixin import WorkerOpsMixin


class _Host(FileListContextMixin):
    def __init__(self, files, selected):
        self.files = files
        self._selected = selected
        self.list_files = Mock()
        self.status_bar = Mock()
        self.update_file_info = Mock()
        self.update_file_list = Mock()

    def _get_selected_file_items(self):
        return list(self._selected)


class _QueueRefreshHost(FileListPreviewMixin):
    def __init__(self, files):
        self.files = files
        self.update_file_list = Mock()
        self.update_file_info = Mock()

    def _operation_is_running(self):
        return False


class _QueueUpdateHost(FileListPreviewMixin):
    def __init__(self, files):
        self.files = files
        self.list_files = Mock()
        self.on_file_selection_changed = Mock()


class FileListContextTests(unittest.TestCase):
    def test_refresh_queue_removes_only_missing_files(self):
        existing = SimpleNamespace(path=r"C:\\available.docx", is_file=True)
        missing = SimpleNamespace(path=r"C:\\missing.docx", is_file=True)
        folder = SimpleNamespace(path=r"C:\\folder", is_file=False)
        host = _QueueRefreshHost([existing, missing, folder])

        with patch(
            "app.ui.mixins.file_list_preview_mixin.os.path.isfile",
            side_effect=lambda path: path == existing.path,
        ) as isfile:
            host.refresh_queue_paths()

        self.assertEqual(host.files, [existing, folder])
        self.assertEqual(isfile.call_count, 2)
        host.update_file_list.assert_called_once_with()
        host.update_file_info.assert_called_once_with()

    def test_visual_list_update_does_not_rescan_every_file_path(self):
        files = [
            SimpleNamespace(path=rf"C:\queue\{index}.pdf", is_file=True)
            for index in range(10_000)
        ]
        host = _QueueUpdateHost(files)

        with patch(
            "app.ui.mixins.file_list_preview_mixin.os.path.isfile"
        ) as isfile:
            host.update_file_list()

        isfile.assert_not_called()
        host.list_files.set_files.assert_called_once_with(files)

    def test_remove_from_list_keeps_file_on_disk_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "document.txt")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("data")
            item = SimpleNamespace(path=path, is_file=True)
            host = _Host([item], [item])

            with patch(
                "app.ui.mixins.file_list_context_mixin.show_app_confirmation_with_checkbox",
                return_value=(True, False),
            ):
                host.remove_selected_files_from_list()

            self.assertTrue(os.path.exists(path))
            self.assertEqual(host.files, [])
            host.update_file_list.assert_called_once_with()

    def test_checked_option_moves_file_to_trash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "document.txt")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("data")
            item = SimpleNamespace(path=path, is_file=True)
            host = _Host([item], [item])

            def move_to_trash(target):
                os.remove(target)
                return True

            with (
                patch(
                    "app.ui.mixins.file_list_context_mixin.show_app_confirmation_with_checkbox",
                    return_value=(True, True),
                ),
                patch(
                    "app.ui.mixins.file_list_context_mixin.QFile.moveToTrash",
                    side_effect=move_to_trash,
                ),
            ):
                host.remove_selected_files_from_list()

            self.assertFalse(os.path.exists(path))
            self.assertEqual(host.files, [])
            host.status_bar.showMessage.assert_called_once_with(
                "Убрано из списка: 1; перемещено в корзину: 1."
            )

    def test_failed_trash_move_keeps_file_in_list(self):
        item = SimpleNamespace(path=r"C:\locked.txt", is_file=True)
        host = _Host([item], [item])

        with (
            patch(
                "app.ui.mixins.file_list_context_mixin.show_app_confirmation_with_checkbox",
                return_value=(True, True),
            ),
            patch(
                "app.ui.mixins.file_list_context_mixin.os.path.exists",
                return_value=True,
            ),
            patch(
                "app.ui.mixins.file_list_context_mixin.QFile.moveToTrash",
                return_value=False,
            ),
            patch(
                "app.ui.mixins.file_list_context_mixin.QMessageBox.warning"
            ) as warning,
        ):
            host.remove_selected_files_from_list()

        self.assertEqual(host.files, [item])
        warning.assert_called_once()

    def test_folder_is_removed_from_list_but_never_moved_to_trash(self):
        folder = SimpleNamespace(path=r"C:\Documents", is_file=False)
        host = _Host([folder], [folder])

        with (
            patch(
                "app.ui.mixins.file_list_context_mixin.show_app_confirmation_with_checkbox",
                return_value=(True, True),
            ),
            patch(
                "app.ui.mixins.file_list_context_mixin.QFile.moveToTrash"
            ) as move_to_trash,
        ):
            host.remove_selected_files_from_list()

        self.assertEqual(host.files, [])
        move_to_trash.assert_not_called()

    def test_cancel_keeps_selection_and_files_unchanged(self):
        item = SimpleNamespace(path=r"C:\document.txt", is_file=True)
        host = _Host([item], [item])

        with patch(
            "app.ui.mixins.file_list_context_mixin.show_app_confirmation_with_checkbox",
            return_value=(False, True),
        ):
            host.remove_selected_files_from_list()

        self.assertEqual(host.files, [item])
        host.update_file_list.assert_not_called()


class FileMetadataTests(unittest.TestCase):
    def test_file_item_reads_type_and_size_with_one_stat_call(self):
        path_stat = SimpleNamespace(st_mode=stat.S_IFREG, st_size=4096)
        with patch("app.core.models.os.stat", return_value=path_stat) as os_stat:
            item = FileItem(r"C:\queue\report.pdf")

        os_stat.assert_called_once_with(r"C:\queue\report.pdf")
        self.assertTrue(item.is_file)
        self.assertEqual(item.size, 4096)
        self.assertEqual(item.file_type, "document")

    def test_known_extension_does_not_repeat_directory_stat(self):
        with patch(
            "app.ui.mixins.file_list_actions_mixin.os.path.isdir"
        ) as isdir:
            self.assertTrue(
                FileListActionsMixin._is_supported_queue_path(
                    r"C:\queue\report.PDF"
                )
            )

        isdir.assert_not_called()

    def test_unknown_extension_still_checks_for_directory(self):
        with patch(
            "app.ui.mixins.file_list_actions_mixin.os.path.isdir",
            return_value=True,
        ) as isdir:
            self.assertTrue(
                FileListActionsMixin._is_supported_queue_path(
                    r"C:\queue\project.folder"
                )
            )

        isdir.assert_called_once_with(r"C:\queue\project.folder")


class AutoClearBehaviorTests(unittest.TestCase):
    def test_auto_clear_requires_master_switch_and_matching_operation(self):
        host = SimpleNamespace(
            _last_operation={"op": "convert"},
            auto_clear_enabled_checkbox=Mock(),
            auto_clear_convert_checkbox=Mock(),
        )
        host.auto_clear_enabled_checkbox.isChecked.return_value = False
        host.auto_clear_convert_checkbox.isChecked.return_value = True

        self.assertFalse(
            WorkerOpsMixin._should_auto_clear_after_operation(host)
        )

        host.auto_clear_enabled_checkbox.isChecked.return_value = True
        self.assertTrue(
            WorkerOpsMixin._should_auto_clear_after_operation(host)
        )

        host._last_operation = {"op": "rename"}
        self.assertFalse(
            WorkerOpsMixin._should_auto_clear_after_operation(host)
        )


if __name__ == "__main__":
    unittest.main()
