import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.ui.mixins.file_list_context_mixin import FileListContextMixin
from app.ui.mixins.worker_ops_mixin import WorkerOpsMixin


class _Host(FileListContextMixin):
    def __init__(self, files, selected):
        self.files = files
        self._selected = selected
        self.list_files = Mock()
        self.status_bar = Mock()
        self.update_file_info = Mock()

    def _get_selected_file_items(self):
        return list(self._selected)


class FileListContextTests(unittest.TestCase):
    def test_remove_from_list_keeps_file_on_disk_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "document.txt")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("data")
            item = SimpleNamespace(path=path, is_file=True)
            host = _Host([item], [item])

            with patch(
                "app.ui.mixins.file_list_context_mixin."
                "show_app_confirmation_with_checkbox",
                return_value=(True, False),
            ):
                host.remove_selected_files_from_list()

            self.assertTrue(os.path.exists(path))
            self.assertEqual(host.files, [])
            host.list_files.set_files.assert_called_once_with([])

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
                    "app.ui.mixins.file_list_context_mixin."
                    "show_app_confirmation_with_checkbox",
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
                "app.ui.mixins.file_list_context_mixin."
                "show_app_confirmation_with_checkbox",
                return_value=(True, True),
            ),
            patch("app.ui.mixins.file_list_context_mixin.os.path.exists", return_value=True),
            patch(
                "app.ui.mixins.file_list_context_mixin.QFile.moveToTrash",
                return_value=False,
            ),
            patch("app.ui.mixins.file_list_context_mixin.QMessageBox.warning") as warning,
        ):
            host.remove_selected_files_from_list()

        self.assertEqual(host.files, [item])
        warning.assert_called_once()

    def test_folder_is_removed_from_list_but_never_moved_to_trash(self):
        folder = SimpleNamespace(path=r"C:\Documents", is_file=False)
        host = _Host([folder], [folder])

        with (
            patch(
                "app.ui.mixins.file_list_context_mixin."
                "show_app_confirmation_with_checkbox",
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
        host.list_files.set_files.assert_not_called()


class AutoClearBehaviorTests(unittest.TestCase):
    def test_auto_clear_requires_master_switch_and_matching_operation(self):
        host = SimpleNamespace(
            _last_operation={"op": "convert"},
            auto_clear_enabled_checkbox=Mock(),
            auto_clear_convert_checkbox=Mock(),
        )
        host.auto_clear_enabled_checkbox.isChecked.return_value = False
        host.auto_clear_convert_checkbox.isChecked.return_value = True

        self.assertFalse(WorkerOpsMixin._should_auto_clear_after_operation(host))

        host.auto_clear_enabled_checkbox.isChecked.return_value = True
        self.assertTrue(WorkerOpsMixin._should_auto_clear_after_operation(host))

        host._last_operation = {"op": "rename"}
        self.assertFalse(WorkerOpsMixin._should_auto_clear_after_operation(host))


if __name__ == "__main__":
    unittest.main()
