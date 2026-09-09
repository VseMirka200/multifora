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

    def test_custom_template_quick_commands_insert_at_cursor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.on_template_selected("Пользовательский шаблон")
                self.assertEqual(
                    set(window.template_quick_insert_buttons),
                    {
                        "{name}", "{num}", "{date}", "{ext}",
                        "{created}", "{modified}", "{exif_date}", "{width}", "{height}",
                    },
                )

                window.template_custom.setText("AB")
                cursor = window.template_custom.textCursor()
                cursor.setPosition(1)
                window.template_custom.setTextCursor(cursor)
                window.template_quick_insert_buttons["{name}"].click()

                self.assertEqual(window.template_custom.text(), "A{name}B")
                self.assertEqual(window.template_custom.textCursor().position(), 7)
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_regex_case_conflict_controls_and_profiles_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                source = os.path.join(tmp_dir, "IMG_0042.JPG")
                with open(source, "wb") as stream:
                    stream.write(b"not-an-image")
                window.files = [FileItem(source)]
                window.update_file_list()

                window.on_template_selected("Регулярное выражение")
                window.template_regex_pattern.setText(r"^img_(\d+)$")
                window.template_regex_replace.setText(r"Фото_\1")
                window.template_regex_ignore_case.setChecked(True)
                window.refresh_rename_preview()
                self.assertEqual(window.files[0].preview_name, "Фото_0042.JPG")

                window.template_regex_pattern.setText("[")
                window.refresh_rename_preview()
                self.assertFalse(window.btn_apply_rename.isEnabled())
                self.assertIn("Ошибка регулярного выражения", window.rename_validation_label.text())

                window.on_template_selected("Изменить регистр")
                window.template_case_mode.setCurrentIndex(
                    window.template_case_mode.findData("lower")
                )
                window.refresh_rename_preview()
                self.assertEqual(window.files[0].preview_name, "img_0042.JPG")

                self.assertEqual(window.rename_conflict_policy.currentData(), "unique")
                self.assertIsNotNone(window.rename_validation_label)
                self.assertIsNotNone(window.operation_profile_combo)
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_operation_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.on_template_selected("Изменить регистр")
                window.template_case_mode.setCurrentIndex(
                    window.template_case_mode.findData("upper")
                )
                window.rename_conflict_policy.setCurrentIndex(
                    window.rename_conflict_policy.findData("skip")
                )
                window.operation_profiles["Верхний регистр"] = window._collect_operation_profile()
                window._refresh_operation_profiles_combo("Верхний регистр")

                window.template_case_mode.setCurrentIndex(
                    window.template_case_mode.findData("lower")
                )
                window.rename_conflict_policy.setCurrentIndex(0)
                window.apply_selected_operation_profile()

                self.assertEqual(window.template_case_mode.currentData(), "upper")
                self.assertEqual(window.rename_conflict_policy.currentData(), "skip")
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
