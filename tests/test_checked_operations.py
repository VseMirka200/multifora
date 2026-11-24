import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDeadlineTimer, QEventLoop
from PySide6.QtWidgets import QApplication, QLabel

from app.ui.file_table import operation_file_items
from app.ui.ui_main import MultiforaMainWindow
from app.ui.ui_styles import PAGE_SECTION_SPACING
from core.file_models import FileItem, OperationFile


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
        self.addCleanup(self.window.merge_pages_panel.stop)
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

    def test_numbering_fields_fit_at_minimum_window_width(self):
        window = self.window
        self.tab("rename")
        window.resize(window.minimumWidth(), window.minimumHeight())
        window.show()
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, QDeadlineTimer(100))
        window.combo_templates.setCurrentText("Нумерация")
        modes = (
            (window.template_num_sep, window.template_num_simple_widget),
            (window.template_prefix_text, window.template_num_prefix_widget),
            (window.template_date_format, window.template_num_date_widget),
        )
        for index, (mode_field, fields) in enumerate(modes):
            with self.subTest(mode=index):
                window.template_numbering_mode.setCurrentIndex(index)
                QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, QDeadlineTimer(100))
                self.assertTrue(fields.isVisible())
                selector = window.template_numbering_mode
                for field, _ in modes:
                    self.assertEqual(field.isVisible(), field is mode_field)
                mode_position = mode_field.mapTo(window, mode_field.rect().topLeft())
                selector_position = selector.mapTo(window, selector.rect().topLeft())
                self.assertEqual(mode_position.y(), selector_position.y())
                self.assertEqual(mode_field.visibleRegion().boundingRect().height(), mode_field.height())
                self.assertEqual(mode_position.x() - selector_position.x() - selector.width(), PAGE_SECTION_SPACING)
                self.assertGreater(fields.mapTo(window, fields.rect().topLeft()).y(), mode_position.y())
                field_tops = set()
                field_gaps = []
                previous_field = None
                for label in fields.findChildren(QLabel):
                    self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()), label.text())
                    field = label.buddy()
                    self.assertEqual(field.visibleRegion().boundingRect().height(), field.height())
                    field_tops.add(field.y())
                    if previous_field is not None:
                        field_gaps.append(field.x() - previous_field.x() - previous_field.width())
                    previous_field = field
                self.assertEqual(len(field_tops), 1)
                self.assertEqual(field_gaps, [PAGE_SECTION_SPACING, PAGE_SECTION_SPACING])

    def test_remove_chars_combines_directions_and_restores_old_settings(self):
        window = self.window
        self.tab("rename")
        window.combo_templates.setCurrentText("Удалить символы")
        self.assertEqual(window.template_remove_position.currentText(), "С начала")
        self.assertEqual(window.template_remove_count.value(), 1)
        preview = window.list_files.model().preview_for(self.items[0])

        for old_rule, key, position, name in (
            ("Удалить символы с начала", "remove_start", "start", "rst.pdf"),
            ("Удалить символы с конца", "remove_end", "end", "fir.pdf"),
        ):
            with self.subTest(rule=old_rule):
                self.assertEqual(window.combo_templates.findText(old_rule), -1)
                window.restore_template_session_state({
                    "selected_template": old_rule,
                    "template_data": {key: 2},
                })
                self.assertEqual(window.get_template_session_state(), {
                    "selected_template": "Удалить символы",
                    "template_data": {"position": position, "count": 2},
                })
                self.assertEqual(preview.preview_name, name)

        window.template_remove_position.setCurrentText("С начала")
        self.assertEqual(preview.preview_name, "rst.pdf")
        window.template_remove_count.setValue(5)
        self.assertEqual(preview.preview_name, "first.pdf")

    def test_case_modes_update_preview_without_changing_extension(self):
        window = self.window
        self.tab("rename")
        path = Path(self.tmp.name, "__оФОРМЛЕНИЕ ПР и ЁлКА.DOCX")
        path.write_bytes(b"test")
        item = FileItem(str(path))
        window.files = [item]
        window.update_file_list()
        window.combo_templates.setCurrentText("Изменить регистр")

        for mode, preview in (
            ("upper", "__ОФОРМЛЕНИЕ ПР И ЁЛКА.DOCX"),
            ("title", "__Оформление Пр И Ёлка.DOCX"),
            ("sentence", "__Оформление пр и ёлка.DOCX"),
            ("swap", "__Оформление пр И ёЛка.DOCX"),
            ("lower", "__оформление пр и ёлка.DOCX"),
        ):
            with self.subTest(mode=mode):
                window.template_case_mode.setCurrentIndex(window.template_case_mode.findData(mode))
                self.assertEqual(window.list_files.model().preview_for(item).preview_name, preview)
                self.assertTrue(window.btn_apply_rename.isEnabled())

    def test_rename_numbers_and_dispatches_only_checked_files(self):
        window = self.window
        self.tab("rename")
        window.list_files.select_paths([self.items[1].path, self.items[3].path])
        window.on_template_selected("Нумерация")
        window.template_num_start.setValue(1)
        self.assertEqual(self.window.list_files.model().preview_for(self.items[0]).preview_name, self.items[0].name)
        self.assertTrue(self.window.list_files.model().preview_for(self.items[1]).preview_name.startswith("001"))
        self.assertTrue(self.window.list_files.model().preview_for(self.items[3]).preview_name.startswith("002"))
        worker = Mock()
        with (
            patch.object(window, "_ensure_operation_can_start", return_value=True),
            patch("app.workers.factory.create_operation_worker", return_value=worker),
            patch.object(window, "show_russian_message_box", return_value=True),
            patch.object(window, "_show_operation_starting"),
            patch.object(window, "_show_progress_dialog"),
        ):
            window.apply_rename()
        sources = window.file_worker.set_rename.call_args.args[0]
        self.assertEqual(sources, [OperationFile.from_item(self.items[index]) for index in (1, 3)])
        self.assertTrue(all(not hasattr(source, "preview_name") for source in sources))

    def test_path_swap_updates_original_rows_and_preserves_marks(self):
        first, second = self.items[:2]
        self.window.list_files.model().set_checked(first, True)
        first_source, second_source = OperationFile.from_item(first), OperationFile.from_item(second)

        self.window._apply_operation_updates([(first_source, second_source.path), (second_source, first_source.path)])

        self.assertEqual((first.path, second.path), (second_source.path, first_source.path))
        self.assertTrue(self.window.list_files.model().is_checked(first))
        self.assertFalse(self.window.list_files.model().is_checked(second))

    def test_filters_update_merge_buttons_and_previews_without_fallback(self):
        window = self.window
        # Проверяем область операции независимо от фонового рендеринга страниц.
        def set_files(files):
            window.merge_pages_panel.files = list(files)
            window.merge_pages_panel.ready = bool(files)
            window.merge_pages_panel.pages.clear()
            for file in files:
                window.merge_pages_panel.pages.addItem(file.name)

        render = patch.object(window.merge_pages_panel, "set_files", side_effect=set_files)
        render.start()
        self.addCleanup(render.stop)
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
        window.combo_templates.setCurrentText("Добавить текст")
        window.template_add_text.setText("prefix_")
        preview_for = self.window.list_files.model().preview_for
        self.assertTrue(all(preview_for(item).preview_name == item.name for item in self.items))
        self.assertFalse(window.btn_apply_rename.isEnabled())
        window.input_search.clear()
        self.assertEqual(self.window.list_files.model().preview_for(self.items[0]).preview_name, "prefix_first.pdf")

    def test_merge_reordering_preserves_files_hidden_by_the_tab(self):
        window = self.window
        self.tab("merge")
        window.list_files.set_files(list(reversed(self.items[:4])))
        window.on_list_order_changed()
        self.assertEqual(window.files, [*reversed(self.items[:4]), self.items[4]])

    def test_compression_column_shows_current_sizes(self):
        from PySide6.QtCore import Qt

        window = self.window
        self.items[0].size = 10 * 1024 * 1024
        self.items[1].size = 2 * 1024 * 1024
        self.tab("compress")
        window.combo_compress_type.setCurrentText("PDF документы")
        window.combo_pdf_method.setCurrentText("Авто")
        window.refresh_compression_preview()
        model = window.list_files.model()
        column = model.COLUMN_TYPE
        self.assertEqual(model.headerData(column, Qt.Orientation.Horizontal), "Размер")
        self.assertEqual(model.index(0, column).data(), "10,0 МБ")
        window.combo_pdf_method.setCurrentText("Максимальное сжатие")
        self.assertEqual(model.index(0, column).data(), "10,0 МБ")
        window.list_files.select_paths([self.items[1].path])
        self.assertEqual(model.index(0, column).data(), "10,0 МБ")
        self.assertEqual(model.index(1, column).data(), "2,0 МБ")
        window.sort_files_by_column(column)
        self.assertLessEqual(window.files[0].size, window.files[-1].size)
        self.tab("rename")
        self.assertEqual(model.headerData(column, Qt.Orientation.Horizontal), "Тип файла")

    def test_png_compression_shows_size_and_hides_quality(self):
        window = self.window
        self.items[4].size = 8 * 1024 * 1024
        self.tab("compress")
        window.combo_compress_type.setCurrentText("PDF документы")
        window.refresh_compression_preview()
        window.list_files.select_paths([self.items[4].path])
        window.combo_compress_type.setCurrentText("Изображения")
        model = window.list_files.model()
        self.assertEqual(model.index(4, model.COLUMN_TYPE).data(), "8,0 МБ")
        self.assertTrue(window.compression_level_widget.isHidden())
        jpeg = Path(self.tmp.name) / "photo.jpg"
        jpeg.write_bytes(b"test")
        window.files.append(FileItem(str(jpeg)))
        window.update_file_list()
        window.list_files.select_paths([str(jpeg)])
        self.assertFalse(window.compression_level_widget.isHidden())

    def test_conversion_shows_pdf_and_presentation_requirements(self):
        window = self.window
        self.tab("convert")
        window.convert_file_type_combo.setCurrentText("Документы")
        window.from_convert_combo.setCurrentText("PDF")
        window.to_convert_combo.setCurrentText("DOCX")
        hint = window.conversion_panel.format_hint
        self.assertIn("без текстового слоя", hint.text())
        self.assertFalse(hint.isHidden())
        window.convert_file_type_combo.setCurrentText("Презентации")
        self.assertIn("LibreOffice Impress", hint.text())
        window.convert_file_type_combo.setCurrentText("Изображения")
        self.assertTrue(hint.isHidden())

    def test_conversion_column_shows_current_and_target_formats(self):
        from PySide6.QtCore import Qt

        window = self.window
        self.tab("convert")
        window.convert_file_type_combo.setCurrentText("Документы")
        window.from_convert_combo.setCurrentText("DOCX")
        window.to_convert_combo.setCurrentText("PDF")
        model = window.list_files.model()
        column = model.COLUMN_TYPE
        self.assertEqual(model.headerData(column, Qt.Orientation.Horizontal), "Формат → результат")
        self.assertEqual(model.index(2, column).data(), "DOCX → PDF")
        self.assertEqual(model.index(0, column).data(), "PDF → —")
        window.to_convert_combo.setCurrentText("TXT")
        self.assertEqual(model.index(2, column).data(), "DOCX → TXT")
        window.list_files.select_paths([self.items[3].path])
        self.assertEqual(model.index(2, column).data(), "DOCX → —")
        window.to_convert_combo.setCurrentText("TXT")
        self.assertEqual(model.index(3, column).data(), "DOCX → TXT")
        self.tab("rename")
        self.assertEqual(model.headerData(column, Qt.Orientation.Horizontal), "Тип файла")
        self.assertEqual(model.index(3, column).data(), "DOCX")

    def test_removed_files_can_be_changed_without_closing_window(self):
        window = self.window
        paths = [Path(item.path) for item in self.items]
        window.files = []
        window.update_file_list()
        window.add_files([str(path) for path in paths])
        for path in paths:
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
