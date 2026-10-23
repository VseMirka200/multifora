import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.core.models import FileItem
from app.ui.ui_components import operation_file_items
from app.ui.ui_main import MultiforaMainWindow


class OperationScopeTests(unittest.TestCase):
    def test_marked_folder_does_not_fall_back_to_unmarked_files(self):
        folder = SimpleNamespace(is_file=False, checked=True)
        file = SimpleNamespace(is_file=True, checked=False)
        self.assertEqual(operation_file_items([folder, file]), [folder])
        self.assertEqual(operation_file_items([folder, file], files_only=True), [])

    def test_hidden_marks_do_not_fall_back_to_unmarked_visible_files(self):
        first = SimpleNamespace(is_file=True, checked=True)
        second = SimpleNamespace(is_file=True, checked=False)
        self.assertEqual(operation_file_items([first, second], visible_files=[second]), [])
        first.checked = False
        self.assertEqual(operation_file_items([first, second], visible_files=[second]), [second])


class CheckedOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        with (
            patch("app.core.settings.get_settings_file_path", return_value=str(folder / "settings.json")),
            patch.object(MultiforaMainWindow, "apply_shortcut_settings"),
            patch.object(MultiforaMainWindow, "create_ipc_server"),
            patch.object(MultiforaMainWindow, "check_updates_on_startup"),
        ):
            self.window = MultiforaMainWindow()
        self.window.queue_timer.stop()
        self.window._settings_save_timer.stop()
        self.addCleanup(self.window.deleteLater)
        self.items = []
        for name in ("first.pdf", "second.pdf", "third.docx", "fourth.docx", "image.png"):
            path = folder / name
            path.write_bytes(b"test")
            self.items.append(FileItem(str(path)))
        self.window.files = self.items
        self.window.update_file_list()

    def tab(self, operation):
        bar = self.window.operations_tab_bar
        for index in range(bar.count()):
            if bar.tabData(index) == operation:
                bar.setCurrentIndex(index)
                return
        self.fail(f"Missing operation tab: {operation}")

    def test_all_tabs_use_marks_and_keep_them_when_switching(self):
        for operation in ("rename", "convert", "compress", "merge"):
            with self.subTest(operation=operation):
                self.tab(operation)
                visible = self.items[:4] if operation == "merge" else self.items
                self.assertEqual(self.window._get_selected_or_all_file_items(), visible)
                self.window.list_files.select_paths([self.items[0].path, self.items[1].path])
                self.assertEqual(self.window._get_selected_or_all_file_items(), self.items[:2])
                self.tab("convert" if operation == "merge" else "merge")
                self.assertEqual(self.window._get_selected_or_all_file_items(), self.items[:2])
                self.tab(operation)
                self.assertFalse(self.window.list_files.selectionModel().hasSelection())
                self.window.list_files.clearSelection()

    def test_rename_numbers_and_dispatches_only_checked_files(self):
        window = self.window
        self.tab("rename")
        window.list_files.select_paths([self.items[1].path, self.items[3].path])
        window.on_template_selected("Нумерация")
        window.template_num_start.setValue(1)
        self.assertEqual(self.items[0].preview_name, self.items[0].name)
        self.assertTrue(self.items[1].preview_name.startswith("001"))
        self.assertTrue(self.items[3].preview_name.startswith("002"))
        window.file_worker = Mock()
        with (
            patch.object(window, "_ensure_operation_can_start", return_value=True),
            patch.object(window, "create_file_worker", return_value=True),
            patch.object(window, "show_russian_message_box", return_value=True),
            patch.object(window, "_show_operation_starting"),
            patch.object(window, "_show_progress_dialog"),
        ):
            window.apply_rename()
        self.assertEqual(window.file_worker.set_rename.call_args.args[0], [self.items[1], self.items[3]])

    def test_filters_update_merge_buttons_and_previews_without_fallback(self):
        window = self.window
        self.tab("merge")
        window.input_search.setText(".pdf")
        self.assertEqual(window._get_selected_or_all_file_items(), self.items[:2])
        self.assertTrue(window.btn_merge.isEnabled())
        window.list_files.select_paths([self.items[0].path])
        self.assertFalse(window.btn_merge.isEnabled())
        window.input_search.setText(".docx")
        self.assertEqual(window._get_selected_or_all_file_items(), [])
        self.assertFalse(window.btn_merge.isEnabled())
        self.tab("rename")
        window.on_template_selected("Добавить текст в начало")
        window.template_prefix.setText("prefix_")
        self.assertTrue(all(item.preview_name == item.name for item in self.items))
        self.assertFalse(window.btn_apply_rename.isEnabled())
        window.input_search.clear()
        self.assertEqual(self.items[0].preview_name, "prefix_first.pdf")

    def test_merge_reordering_preserves_files_hidden_by_the_tab(self):
        window = self.window
        self.tab("merge")
        window.list_files.set_files(list(reversed(self.items[:4])))
        window.on_list_order_changed()
        self.assertEqual(window.files, [*reversed(self.items[:4]), self.items[4]])

    def test_removed_files_can_be_changed_without_closing_window(self):
        from app.core.rename_templates import build_file_token_values

        window = self.window
        paths = [Path(item.path) for item in self.items]
        window.files = []
        window.update_file_list()
        window.add_files([str(path) for path in paths])
        for path in paths:
            build_file_token_values(str(path))
            moved = path.with_name("check_" + path.name)
            path.rename(moved)
            moved.rename(path)
        window.list_files.selectAll()
        with patch(
            "app.ui.mixins.file_list_context_mixin.show_app_confirmation_with_checkbox",
            return_value=(True, False),
        ):
            window.remove_selected_files_from_list()
        self.assertEqual(window.files, [])
        self.assertEqual(window.list_files.model().files(), [])
        for path in paths:
            self.assertEqual(path.read_bytes(), b"test")
            moved = path.with_name("after_" + path.name)
            path.rename(moved)
            moved.write_bytes(b"updated")
            moved.unlink()


if __name__ == "__main__":
    unittest.main()
