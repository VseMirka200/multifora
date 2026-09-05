import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.core.models import FileItem
from app.ui.ui_main import MultiforaMainWindow


class MainWindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_builds_core_ui(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                self.assertIsNotNone(window.tabs)
                self.assertIsNotNone(window.operations_stack)
                self.assertGreaterEqual(window.operations_stack.count(), 5)
                self.assertEqual(window.operations_tab_bar.count(), 5)
                tab_labels = [
                    window.operations_tab_bar.tabText(index)
                    for index in range(window.operations_tab_bar.count())
                ]
                self.assertIn("Метаданные", tab_labels)
                self.assertIsNotNone(window.btn_remove_metadata)
                self.assertTrue(window.metadata_field_checkboxes)

                settings_widget = window._ensure_settings_panel_widget()
                self.assertIsNotNone(settings_widget)
                self.assertGreaterEqual(window.settings_stack.count(), 4)
                original_index = window.operations_tab_bar.currentIndex()
                window.btn_settings.click()
                self.assertFalse(window.settings_panel_host.isHidden())
                self.assertEqual(window.operations_tab_bar.currentIndex(), original_index)
                self.assertTrue(all(
                    window.operations_tab_bar.isTabVisible(index)
                    for index in range(window.operations_tab_bar.count())
                ))
                window.operations_tab_bar.tabBarClicked.emit(original_index)
                self.assertTrue(window.settings_panel_host.isHidden())
                self.assertFalse(window.btn_settings.isChecked())
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_conversion_button_enables_after_target_format_selection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_docx = os.path.join(tmp_dir, "source.docx")
            with open(source_docx, "wb") as f:
                f.write(b"x")

            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.files = [FileItem(source_docx)]
                window.update_file_list()
                window.list_files.select_paths([source_docx])
                window.on_file_selection_changed()

                window.convert_file_type_combo.setCurrentText("Документы")
                window.from_convert_combo.setCurrentText("DOCX")
                window.to_convert_combo.setCurrentText("PDF")

                self.assertTrue(window.btn_convert.isEnabled())
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_metadata_buttons_dispatch_selected_and_all_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("app.core.settings.get_settings_file_path", return_value=os.path.join(tmp_dir, "settings.json")), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings"), \
                patch.object(MultiforaMainWindow, "create_ipc_server"), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()
                try:
                    self.assertFalse(window.btn_remove_metadata.isEnabled())
                    self.assertFalse(window.btn_remove_all_metadata.isEnabled())
                    document = Mock(path=os.path.join(tmp_dir, "document.pdf"))
                    window.file_worker = Mock()
                    with patch.object(window, "_get_selected_or_all_file_items", return_value=[document]), \
                        patch.object(window, "show_russian_message_box", return_value=True), \
                        patch.object(window, "_show_progress_dialog"):
                        window._update_metadata_controls()
                        self.assertFalse(window.btn_remove_metadata.isEnabled())
                        self.assertTrue(window.btn_remove_all_metadata.isEnabled())
                        window.metadata_field_checkboxes["author"].setChecked(True)
                        window.btn_remove_metadata.click()
                        window.file_worker.set_metadata_cleanup.assert_called_with(
                            [document], remove_all=False, fields=["author"]
                        )
                        window.btn_remove_all_metadata.click()
                        window.file_worker.set_metadata_cleanup.assert_called_with(
                            [document], remove_all=True, fields=[]
                        )
                        window.metadata_field_checkboxes["author"].setChecked(False)
                        self.assertFalse(window.btn_remove_metadata.isEnabled())
                        window.btn_remove_all_metadata.click()
                        self.assertEqual(window.file_worker.start.call_count, 3)
                    for name in ("document.pdf", "image.png"):
                        with open(os.path.join(tmp_dir, name), "wb") as source:
                            source.write(b"test")
                    document_item = FileItem(os.path.join(tmp_dir, "document.pdf"))
                    image_item = FileItem(os.path.join(tmp_dir, "image.png"))
                    window.files = [document_item, image_item]
                    window.update_file_list()
                    self.assertTrue(window.btn_remove_all_metadata.isEnabled())
                    window.metadata_field_checkboxes["author"].setChecked(True)
                    self.assertTrue(window.btn_remove_metadata.isEnabled())
                    window.list_files.select_paths([image_item.path])
                    self.assertFalse(window.btn_remove_all_metadata.isEnabled())
                    self.assertFalse(window.btn_remove_metadata.isEnabled())
                    window.list_files.clearSelection()
                    self.assertTrue(window.btn_remove_all_metadata.isEnabled())
                    window.files = []
                    window.update_file_list()
                    self.assertFalse(window.btn_remove_all_metadata.isEnabled())
                    self.assertFalse(window.btn_remove_metadata.isEnabled())
                finally:
                    window.queue_timer.stop()
                    window._settings_save_timer.stop()
                    window.deleteLater()


if __name__ == "__main__":
    unittest.main()
