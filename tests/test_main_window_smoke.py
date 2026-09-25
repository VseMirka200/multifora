import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QListWidget, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt

from app.core.models import FileItem
from app.ui.ui_main import MultiforaMainWindow
from app.ui.ui_spacing import FIELD_HEIGHT
from app.ui.ui_styles import build_standard_button_style


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
                self.assertEqual(window.windowTitle(), "Мультифора")
                self.assertIsNotNone(window.tabs)
                self.assertIsNotNone(window.operations_stack)
                self.assertGreaterEqual(window.operations_stack.count(), 5)
                self.assertEqual(window.operations_tab_bar.count(), 5)
                self.assertEqual(len(window.combo_merge_format._items), 2)
                self.assertEqual(window.combo_merge_format.findData("auto"), -1)
                self.assertEqual(window.combo_merge_format._items[0], ("PDF (только PDF)", "pdf"))
                self.assertFalse(hasattr(window, "checkbox_replace_image"))
                self.assertTrue(hasattr(window, "btn_ext_filter"))
                self.assertTrue(hasattr(window, "btn_type_filter"))
                self.assertFalse(hasattr(window, "combo_sort"))
                self.assertTrue(hasattr(window, "input_search"))
                header_positions = [
                    window._list_header_layout.getItemPosition(
                        window._list_header_layout.indexOf(widget)
                    )
                    for widget in (
                        window.input_search,
                        window.btn_ext_filter,
                        window.btn_type_filter,
                    )
                ]
                self.assertEqual([position[0] for position in header_positions], [0, 0, 0])
                self.assertEqual([position[1] for position in header_positions], [2, 0, 1])
                self.assertEqual(
                    window._clear_ext_filter_action.text(),
                    "Снять все отметки",
                )
                self.assertEqual(
                    window._clear_type_filter_action.text(),
                    "Снять все отметки",
                )

                filter_path = os.path.join(tmp_dir, "filter.txt")
                with open(filter_path, "wb") as stream:
                    stream.write(b"test")
                window.files = [FileItem(filter_path)]
                window.update_file_list()

                window._clear_type_filter_action.trigger()
                self.assertTrue(all(
                    not action.isChecked()
                    for action in window._type_filter_actions.values()
                ))
                self.assertEqual(window.list_files.model().files(), [])
                self.assertEqual(window.btn_type_filter.text(), "Выбрано: 0")

                for action in window._type_filter_actions.values():
                    action.setChecked(True)
                window._clear_ext_filter_action.trigger()
                self.assertTrue(all(
                    not action.isChecked()
                    for action in window._ext_filter_actions.values()
                ))
                self.assertEqual(window.list_files.model().files(), [])
                self.assertEqual(window.btn_ext_filter.text(), "Выбрано: 0")

                for action in window._ext_filter_actions.values():
                    action.setChecked(True)
                window.files = []
                window.update_file_list()
                self.assertFalse(window.btn_compress.isEnabled())
                self.assertFalse(window.progress_dialog.isModal())
                self.assertEqual(
                    window.progress_dialog.windowModality(),
                    Qt.WindowModality.NonModal,
                )
                self.assertEqual(
                    window.btn_cancel_operation.sizePolicy().horizontalPolicy(),
                    QSizePolicy.Policy.Expanding,
                )
                self.assertEqual(
                    window.btn_cancel_operation.property("buttonVariant"),
                    "danger",
                )
                self.assertEqual(
                    window.btn_cancel_operation.styleSheet(),
                    build_standard_button_style(
                        window._effective_theme_mode,
                        "danger",
                    ),
                )
                tab_labels = [
                    window.operations_tab_bar.tabText(index)
                    for index in range(window.operations_tab_bar.count())
                ]
                self.assertEqual(
                    tab_labels,
                    [
                        "Переименование",
                        "Конвертация",
                        "Сжатие",
                        "Объединение",
                        "Удаление метаданных",
                    ],
                )
                self.assertIsNotNone(window.btn_remove_metadata)
                self.assertTrue(window.metadata_field_checkboxes)

                settings_widget = window._ensure_settings_panel_widget()
                self.assertIsNotNone(settings_widget)
                window._ensure_about_settings_page()
                about_page = window.settings_stack.widget(window._about_settings_row)
                about_texts = [label.text() for label in about_page.findChildren(QLabel)]
                self.assertIn("Версия: 0.9.0", about_texts)
                self.assertFalse(hasattr(window, "conversion_output_mode_combo"))
                self.assertFalse(hasattr(window, "conversion_output_path_row"))
                self.assertEqual(window.btn_download_logs.text(), "Скачать логи")
                self.assertEqual(window.btn_download_logs.property("buttonVariant"), "secondary")
                self.assertEqual(window.btn_check_updates.property("buttonVariant"), "primary")
                self.assertEqual(window.btn_open_repo.property("buttonVariant"), "secondary")
                for button in (window.btn_check_updates, window.btn_open_repo):
                    self.assertEqual(
                        button.sizePolicy().horizontalPolicy(),
                        QSizePolicy.Policy.Expanding,
                    )
                standard_buttons = [
                    button
                    for button in window.findChildren(QPushButton)
                    if button.property("buttonVariant")
                ]
                self.assertTrue(standard_buttons)
                self.assertEqual(
                    [
                        (button.objectName(), button.text(), button.height())
                        for button in standard_buttons
                        if button.height() != FIELD_HEIGHT
                    ],
                    [],
                )
                self.assertEqual(window.logs_search_input.height(), FIELD_HEIGHT)
                self.assertEqual(window.logs_level_filter.height(), FIELD_HEIGHT)
                self.assertGreaterEqual(window.settings_stack.count(), 4)
                self.assertEqual(
                    window.settings_nav.findItems(
                        "История переименований",
                        Qt.MatchFlag.MatchExactly,
                    ),
                    [],
                )
                self.assertFalse(hasattr(window, "rename_history_settings_page"))
                self.assertEqual(
                    window.btn_open_rename_history.text(),
                    "Открыть историю переименований",
                )
                self.assertEqual(
                    window.btn_open_rename_history.property("buttonVariant"),
                    "secondary",
                )
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

                running_worker = Mock()
                running_worker.isRunning.return_value = True
                window.file_worker = running_worker
                with patch("app.ui.ui_main.QMessageBox.warning") as warning:
                    self.assertFalse(window.create_file_worker())
                    for callback in (
                        window.apply_rename,
                        window.convert_files_dual_combo,
                        window.compress_files,
                        window.merge_files,
                        window.remove_document_metadata,
                    ):
                        callback()
                    self.assertEqual(warning.call_count, 6)
                self.assertIs(window.file_worker, running_worker)
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_rename_history_opens_as_modal_dialog(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            captured = {}
            window._rename_history = [
                {
                    "timestamp": 0,
                    "count": 1,
                    "label": "Переименован 1 файл",
                    "pairs": [("new.txt", "old.txt")],
                }
            ]

            def inspect_dialog(dialog):
                captured["dialog"] = dialog
                history_list = dialog.findChild(QListWidget, "rename_history_list")
                self.assertTrue(dialog.isModal())
                self.assertEqual(dialog.windowTitle(), "История переименований")
                self.assertIsNotNone(history_list)
                self.assertEqual(history_list.count(), 1)
                self.assertEqual(history_list.currentRow(), 0)

                buttons = dialog.findChildren(QPushButton)
                self.assertEqual(
                    {button.text() for button in buttons},
                    {"Откатить выбранное", "Закрыть"},
                )
                for button in buttons:
                    self.assertEqual(
                        button.sizePolicy().horizontalPolicy(),
                        QSizePolicy.Policy.Expanding,
                    )
                    self.assertEqual(button.height(), FIELD_HEIGHT)
                return int(QDialog.DialogCode.Rejected)

            try:
                with patch.object(QDialog, "exec", new=inspect_dialog):
                    window.btn_open_rename_history.click()
                self.assertIn("dialog", captured)
                self.assertIsNone(window.rename_history_list)
                self.assertIsNone(window.btn_history_undo)
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_file_columns_sort_in_both_directions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_dir = os.path.join(tmp_dir, "01")
            second_dir = os.path.join(tmp_dir, "02")
            os.makedirs(first_dir)
            os.makedirs(second_dir)
            first_path = os.path.join(second_dir, "zeta.txt")
            second_path = os.path.join(first_dir, "alpha.pdf")
            for path in (first_path, second_path):
                with open(path, "wb") as stream:
                    stream.write(b"test")

            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.files = [FileItem(first_path), FileItem(second_path)]
                window.update_file_list()
                column = window.list_files.model().COLUMN_OLD_NAME

                window.on_file_header_clicked(column)
                self.assertEqual([item.name for item in window.files], ["alpha.pdf", "zeta.txt"])
                self.assertTrue(window.list_files.horizontalHeader().isSortIndicatorShown())
                self.assertEqual(window._column_sort_order, Qt.SortOrder.AscendingOrder)
                self.assertTrue(window.list_files.dragEnabled())

                window.on_file_header_clicked(column)
                self.assertEqual([item.name for item in window.files], ["zeta.txt", "alpha.pdf"])
                self.assertEqual(window._column_sort_order, Qt.SortOrder.DescendingOrder)
                self.assertTrue(window.list_files.dragEnabled())

                window.on_file_header_clicked(column)
                self.assertIsNone(window._column_sort_section)
                self.assertFalse(window.list_files.horizontalHeader().isSortIndicatorShown())
                self.assertTrue(window.list_files.dragEnabled())

                folder_column = window.list_files.model().COLUMN_PATH
                window.on_file_header_clicked(folder_column)
                self.assertEqual([item.name for item in window.files], ["alpha.pdf", "zeta.txt"])
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_filtered_rows_can_be_reordered_without_losing_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = [
                os.path.join(tmp_dir, "first.txt"),
                os.path.join(tmp_dir, "hidden.pdf"),
                os.path.join(tmp_dir, "second.txt"),
            ]
            for path in paths:
                with open(path, "wb") as stream:
                    stream.write(b"test")

            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.files = [FileItem(path) for path in paths]
                window.update_file_list()
                window.input_search.setText(".txt")
                self.app.processEvents()

                self.assertTrue(window.list_files.dragEnabled())
                self.assertEqual(window.list_files.model().rowCount(), 2)
                self.assertTrue(window.list_files.model().moveRows(
                    window.list_files.rootIndex(),
                    0,
                    1,
                    window.list_files.rootIndex(),
                    2,
                ))
                window.on_list_order_changed()

                self.assertEqual(
                    [item.name for item in window.files],
                    ["second.txt", "hidden.pdf", "first.txt"],
                )
                self.assertEqual(len(window.files), 3)
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
                self.assertEqual(window.combo_conversion_output_mode.currentData(), "ask")
                self.assertTrue(window.conversion_output_path_section.isHidden())

                window.combo_conversion_output_mode.setCurrentIndex(
                    window.combo_conversion_output_mode.findData("custom")
                )
                self.assertFalse(window.conversion_output_path_section.isHidden())
                self.assertTrue(window.input_conversion_output_path.isEnabled())
                self.assertTrue(window.btn_select_conversion_output_folder.isEnabled())
                self.assertFalse(window.btn_convert.isEnabled())

                window.input_conversion_output_path.setText(tmp_dir)
                window.conversion_output_path = tmp_dir
                window.update_convert_button_state()
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
                self.assertTrue(window.image_output_path_section.isHidden())
                self.assertFalse(window.input_image_output_path.isEnabled())
                self.assertFalse(window.btn_select_image_output_path.isEnabled())
                self.assertTrue(window.btn_compress.isEnabled())
                compact_stack_height = window.compress_mode_stack.height()

                window.combo_image_output_mode.setCurrentIndex(
                    window.combo_image_output_mode.findData("custom")
                )
                self.assertTrue(window.input_image_output_path.isEnabled())
                self.assertTrue(window.btn_select_image_output_path.isEnabled())
                self.assertFalse(window.image_output_path_section.isHidden())
                self.assertFalse(window.btn_compress.isEnabled())
                self.assertGreater(
                    window.compress_mode_stack.height(),
                    compact_stack_height,
                )
                self.assertEqual(
                    window.compress_mode_stack.height(),
                    window.image_mode_widget.sizeHint().height(),
                )

                window.input_image_output_path.setText(tmp_dir)
                window.image_compression_output_path = tmp_dir
                window._update_compress_button()
                self.assertTrue(window.btn_compress.isEnabled())

                window.files = []
                window.update_file_list()
                self.assertFalse(window.btn_compress.isEnabled())
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
                        "{name}", "{num:03d,start=1,step=1}", "{date}", "{ext}",
                        "{created}", "{modified}", "{exif_date}", "{width}", "{height}",
                    },
                )

                number_token = "{num:03d,start=1,step=1}"
                number_button = window.template_quick_insert_buttons[number_token]
                self.assertEqual(number_button.text(), number_token)
                window.template_custom.clear()
                number_button.click()
                self.assertEqual(window.template_custom.text(), number_token)

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

    def test_custom_numbering_continues_across_folders(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            folders = [os.path.join(tmp_dir, name) for name in ("first", "second")]
            for folder in folders:
                os.makedirs(folder)
            paths = []
            for folder in folders:
                for name in ("a.docx", "b.docx"):
                    path = os.path.join(folder, name)
                    with open(path, "wb") as stream:
                        stream.write(b"test")
                    paths.append(path)

            settings_path = os.path.join(tmp_dir, "settings.json")
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()

            try:
                window.files = [FileItem(path) for path in paths]
                window.update_file_list()
                window.on_template_selected("Пользовательский шаблон")
                window.template_custom.setText("ПР {num:1d,start=1,step=1}")
                window.refresh_rename_preview()

                self.assertEqual(
                    [item.preview_name for item in window.files],
                    ["ПР 1.docx", "ПР 2.docx", "ПР 3.docx", "ПР 4.docx"],
                )
            finally:
                if hasattr(window, "queue_timer"):
                    window.queue_timer.stop()
                if hasattr(window, "_settings_save_timer"):
                    window._settings_save_timer.stop()
                window.deleteLater()

    def test_regex_and_case_controls_exist_without_advanced_rename_options(self):
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

                self.assertFalse(hasattr(window, "rename_conflict_policy"))
                self.assertFalse(hasattr(window, "rename_folder_mode_combo"))
                self.assertFalse(hasattr(window, "rename_numbering_scope_combo"))
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
                dialog_margins = dialog.layout().contentsMargins()
                self.assertEqual(
                    (
                        dialog_margins.left(),
                        dialog_margins.top(),
                        dialog_margins.right(),
                        dialog_margins.bottom(),
                    ),
                    (6, 6, 6, 6),
                )
                card_layout = window.templates_table.parentWidget().layout()
                self.assertEqual(card_layout.spacing(), 4)
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
                    window.file_worker.isRunning.return_value = False
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
