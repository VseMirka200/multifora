import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QSizePolicy

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
                self.assertEqual(len(window.combo_merge_format._items), 2)
                self.assertEqual(window.combo_merge_format.findData("auto"), -1)
                self.assertEqual(window.combo_merge_format._items[0], ("PDF (только PDF)", "pdf"))
                self.assertFalse(hasattr(window, "checkbox_replace_image"))
                tab_labels = [
                    window.operations_tab_bar.tabText(index)
                    for index in range(window.operations_tab_bar.count())
                ]
                self.assertIn("Метаданные", tab_labels)
                self.assertIsNotNone(window.btn_remove_metadata)
                self.assertTrue(window.metadata_field_checkboxes)

                settings_widget = window._ensure_settings_panel_widget()
                self.assertIsNotNone(settings_widget)
                self.assertEqual(window.conversion_output_mode_combo.currentData(), "ask")
                self.assertFalse(window.conversion_output_path_input.isEnabled())
                window.conversion_output_mode_combo.setCurrentIndex(
                    window.conversion_output_mode_combo.findData("custom")
                )
                self.assertTrue(window.conversion_output_path_input.isEnabled())
                self.assertTrue(window.btn_select_conversion_output_path.isEnabled())
                self.assertEqual(window.btn_download_logs.text(), "Скачать логи")
                self.assertEqual(window.btn_download_logs.property("buttonVariant"), "secondary")
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

    def test_download_logs_saves_current_filtered_view(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            export_path = os.path.join(tmp_dir, "filtered_logs.txt")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window._ensure_settings_panel_widget()
                window._log_lines = [
                    "[2026-01-01 10:00:00] [INFO] Запуск",
                    "[2026-01-01 10:00:01] [ERROR] Тестовая ошибка",
                ]
                window.logs_search_input.setText("ошибка")
                window._apply_logs_filters()

                with patch(
                    "app.ui.mixins.logging_mixin.QFileDialog.getSaveFileName",
                    return_value=(export_path, "Текстовые файлы (*.txt)"),
                ):
                    window.download_visible_logs()

                with open(export_path, "r", encoding="utf-8") as exported:
                    content = exported.read()
                self.assertIn("Тестовая ошибка", content)
                self.assertNotIn("Запуск", content)
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

    def test_merge_button_follows_format_and_output_selection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_paths = [os.path.join(tmp_dir, name) for name in ("first.pdf", "second.pdf")]
            for path in pdf_paths:
                with open(path, "wb") as stream:
                    stream.write(b"pdf")

            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                self.assertEqual(window.btn_merge.property("buttonVariant"), "primary")
                self.assertFalse(window.btn_merge.isEnabled())

                window.files = [FileItem(path) for path in pdf_paths]
                window.update_file_list()
                self.assertFalse(window.btn_merge.isEnabled())

                window.input_merge_output_path.setText(os.path.join(tmp_dir, "merged.pdf"))
                self.assertTrue(window.btn_merge.isEnabled())

                window.combo_merge_format.setCurrentIndex(
                    window.combo_merge_format.findData("docx")
                )
                self.assertFalse(window.btn_merge.isEnabled())
                self.assertTrue(window.input_merge_output_path.text().endswith(".docx"))
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_compression_type_follows_selected_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = os.path.join(tmp_dir, "photo.png")
            pdf_path = os.path.join(tmp_dir, "document.pdf")
            for path in (image_path, pdf_path):
                with open(path, "wb") as stream:
                    stream.write(b"test")

            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.files = [FileItem(image_path), FileItem(pdf_path)]
                window.update_file_list()

                window.list_files.select_paths([pdf_path])
                window.on_file_selection_changed()
                self.assertEqual(window.combo_compress_type.currentText(), "PDF документы")

                window.list_files.clearSelection()
                window.list_files.select_paths([image_path])
                window.on_file_selection_changed()
                self.assertEqual(window.combo_compress_type.currentText(), "Изображения")
                self.assertEqual(window.combo_image_output_mode.currentData(), "alongside")
                self.assertFalse(window.input_image_output_path.isEnabled())
                self.assertFalse(window.btn_select_image_output_path.isEnabled())
                self.assertTrue(window.btn_compress.isEnabled())

                window.combo_image_output_mode.setCurrentIndex(
                    window.combo_image_output_mode.findData("custom")
                )
                self.assertTrue(window.input_image_output_path.isEnabled())
                self.assertTrue(window.btn_select_image_output_path.isEnabled())
                self.assertFalse(window.btn_compress.isEnabled())

                window.input_image_output_path.setText(tmp_dir)
                window.image_compression_output_path = tmp_dir
                window._update_compress_button()
                self.assertTrue(window.btn_compress.isEnabled())
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

    def test_regex_case_and_conflict_controls_exist(self):
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
                self.assertFalse(hasattr(window, "operation_profile_combo"))
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_template_manager_actions_are_full_width_and_apply_selection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            dialog = None
            try:
                window.custom_templates["Тест"] = {
                    "type": "Изменить регистр",
                    "data": {"case_mode": "upper"},
                }
                with patch.object(QDialog, "exec", return_value=0):
                    window.show_template_manager()

                dialog = window.templates_table.window()
                card_layout = window.templates_table.parentWidget().layout()
                actions_row = window.btn_apply_template.parentWidget()
                self.assertGreater(card_layout.indexOf(actions_row), card_layout.indexOf(window.templates_table))

                for button in (
                    window.btn_export_templates,
                    window.btn_import_templates,
                    window.btn_apply_template,
                ):
                    self.assertEqual(
                        button.sizePolicy().horizontalPolicy(),
                        QSizePolicy.Policy.Expanding,
                    )
                    self.assertTrue(button.property("buttonVariant"))

                self.assertFalse(window.btn_apply_template.isEnabled())
                window.templates_table.selectRow(0)
                self.app.processEvents()
                self.assertTrue(window.btn_apply_template.isEnabled())

                with patch.object(window, "load_selected_template") as apply_template:
                    window.btn_apply_template.click()
                    apply_template.assert_called_once_with(dialog)
            finally:
                if dialog is not None:
                    dialog.deleteLater()
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
