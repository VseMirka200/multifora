import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QAbstractItemView, QApplication, QHeaderView

from app.ui.ui_components import FileListModel, FileListWidget
from app.ui.ui_styles import build_standard_field_style


class FileTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_model_exposes_names_type_and_source_folder_without_icons(self):
        item = SimpleNamespace(
            path=r"C:\Users\User\Pictures\image.png",
            name="image.png",
            preview_name="image.pdf",
            is_file=True,
        )
        model = FileListModel()
        model.set_files([item])
        old_name_index = model.index(0, model.COLUMN_OLD_NAME)
        new_name_index = model.index(0, model.COLUMN_NEW_NAME)
        type_index = model.index(0, model.COLUMN_TYPE)
        path_index = model.index(0, model.COLUMN_PATH)
        self.assertEqual(model.columnCount(), 5)
        self.assertEqual(
            model.headerData(model.COLUMN_OLD_NAME, Qt.Orientation.Horizontal),
            "Старое имя",
        )
        self.assertEqual(
            model.headerData(model.COLUMN_NEW_NAME, Qt.Orientation.Horizontal),
            "Новое имя",
        )
        self.assertEqual(
            model.headerData(model.COLUMN_PATH, Qt.Orientation.Horizontal),
            "Исходная папка",
        )
        self.assertEqual(
            old_name_index.data(Qt.ItemDataRole.DisplayRole), "image.png"
        )
        self.assertEqual(
            old_name_index.data(Qt.ItemDataRole.ToolTipRole), "image.png"
        )
        self.assertEqual(
            new_name_index.data(Qt.ItemDataRole.DisplayRole), "image.pdf"
        )
        self.assertEqual(
            new_name_index.data(Qt.ItemDataRole.ToolTipRole), "image.pdf"
        )
        self.assertEqual(type_index.data(Qt.ItemDataRole.DisplayRole), "PNG")
        self.assertEqual(
            path_index.data(Qt.ItemDataRole.DisplayRole),
            os.path.dirname(item.path),
        )
        self.assertEqual(
            path_index.data(Qt.ItemDataRole.ToolTipRole), item.path
        )
        self.assertIsNone(old_name_index.data(Qt.ItemDataRole.DecorationRole))
        self.assertIsNone(new_name_index.data(Qt.ItemDataRole.DecorationRole))

    def test_file_type_handles_uppercase_extension_folder_and_extensionless_file(
        self,
    ):
        model = FileListModel()
        model.set_files(
            [
                SimpleNamespace(
                    path="report.PDF", name="report.PDF", is_file=True
                ),
                SimpleNamespace(
                    path="documents", name="documents", is_file=False
                ),
                SimpleNamespace(path="README", name="README", is_file=True),
            ]
        )
        self.assertEqual(model.index(0, model.COLUMN_TYPE).data(), "PDF")
        self.assertEqual(model.index(1, model.COLUMN_TYPE).data(), "Папка")
        self.assertEqual(model.index(2, model.COLUMN_TYPE).data(), "Файл")

    def test_source_folder_distinguishes_files_from_different_directories(
        self,
    ):
        model = FileListModel()
        model.set_files(
            [
                SimpleNamespace(
                    path=r"C:\One\report.pdf",
                    folder=r"C:\One",
                    name="report.pdf",
                    is_file=True,
                ),
                SimpleNamespace(
                    path=r"D:\Two\report.pdf",
                    folder=r"D:\Two",
                    name="report.pdf",
                    is_file=True,
                ),
            ]
        )

        self.assertEqual(model.index(0, model.COLUMN_PATH).data(), r"C:\One")
        self.assertEqual(model.index(1, model.COLUMN_PATH).data(), r"D:\Two")

    def test_model_can_show_result_folder_in_preview(self):
        item = SimpleNamespace(
            path=r"C:\One\report.docx",
            folder=r"C:\One",
            preview_folder=r"C:\One\Конвертированные",
            name="report.docx",
            preview_name="report.pdf",
            is_file=True,
        )
        model = FileListModel()
        model.set_files([item])
        model.set_folder_header("Папка результата")

        path_index = model.index(0, model.COLUMN_PATH)
        self.assertEqual(
            model.headerData(model.COLUMN_PATH, Qt.Orientation.Horizontal),
            "Папка результата",
        )
        self.assertEqual(
            path_index.data(Qt.ItemDataRole.DisplayRole),
            r"C:\One\Конвертированные",
        )
        self.assertEqual(
            path_index.data(Qt.ItemDataRole.ToolTipRole),
            r"C:\One\Конвертированные",
        )

    def test_widget_uses_row_selection_and_elides_long_text_on_the_right(self):
        widget = FileListWidget()
        widget.set_files([SimpleNamespace(path="one.pdf", name="one.pdf", is_file=True)])
        self.assertEqual(
            widget.selectionBehavior(),
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self.assertEqual(widget.textElideMode(), Qt.TextElideMode.ElideRight)
        self.assertTrue(widget.horizontalHeader().stretchLastSection())
        header = widget.horizontalHeader()
        self.assertTrue(header.sectionsClickable())
        self.assertFalse(header.isSortIndicatorShown())
        unsorted_width = header.sectionSize(widget.model().COLUMN_OLD_NAME)
        header.setSortIndicator(
            widget.model().COLUMN_OLD_NAME, Qt.SortOrder.AscendingOrder
        )
        header.setSortIndicatorShown(True)
        widget._resize_columns_to_contents()
        self.assertGreaterEqual(
            header.sectionSize(widget.model().COLUMN_OLD_NAME),
            unsorted_width + 6,
        )
        header.setSortIndicatorShown(False)
        widget._resize_columns_to_contents()
        self.assertEqual(
            header.sectionResizeMode(widget.model().COLUMN_OLD_NAME),
            QHeaderView.ResizeMode.Interactive,
        )
        self.assertEqual(
            header.sectionResizeMode(widget.model().COLUMN_NEW_NAME),
            QHeaderView.ResizeMode.Interactive,
        )
        self.assertEqual(
            header.sectionResizeMode(widget.model().COLUMN_TYPE),
            QHeaderView.ResizeMode.Interactive,
        )
        self.assertEqual(
            header.sectionResizeMode(widget.model().COLUMN_PATH),
            QHeaderView.ResizeMode.Interactive,
        )
        self.assertEqual(header.resizeContentsPrecision(), 100)
        self.assertIn(
            "padding: 0px 6px;",
            build_standard_field_style("dark", "surface"),
        )

    def test_preview_refresh_does_not_remeasure_column_widths(self):
        widget = FileListWidget()
        widget.set_files(
            [SimpleNamespace(path="one.pdf", name="one.pdf", is_file=True)]
        )

        with patch.object(widget, "resizeColumnToContents") as resize_column:
            widget.refresh()

        resize_column.assert_not_called()

    def test_clearing_wide_table_removes_scrollbars_even_after_resizing_and_refilling(self):
        widget = FileListWidget()
        self.addCleanup(widget.deleteLater)
        widget.resize(800, 300)
        widget.show()
        files = [SimpleNamespace(
            path=f"{index}.pdf", name="long_name_" * 40 + f"{index}.pdf",
            preview_name="new_name_" * 40 + f"{index}.pdf", is_file=True,
        ) for index in range(40)]
        widget.set_files(files)
        self.app.processEvents()
        self.assertGreater(widget.horizontalScrollBar().maximum(), 0)
        widget.horizontalScrollBar().setValue(100)
        widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())

        widget.clear()
        for width in (800, 600, 1000):
            widget.resize(width, 300)
            self.app.processEvents()
            self.app.processEvents()
            self.assertLessEqual(widget.horizontalHeader().length(), widget.viewport().width())
            self.assertFalse(widget.horizontalScrollBar().isVisible())
            self.assertFalse(widget.verticalScrollBar().isVisible())
            self.assertEqual(widget.horizontalScrollBar().value(), 0)
            self.assertEqual(widget.verticalScrollBar().value(), 0)

        widget.set_files(files)
        self.app.processEvents()
        self.assertTrue(widget.horizontalHeader().stretchLastSection())
        self.assertEqual(
            widget.horizontalHeader().sectionResizeMode(widget.model().COLUMN_OLD_NAME),
            QHeaderView.ResizeMode.Interactive,
        )
        widget.horizontalHeader().resizeSection(widget.model().COLUMN_OLD_NAME, widget.width() * 2)
        self.app.processEvents()
        self.assertGreater(widget.horizontalScrollBar().maximum(), 0)

    def _file_widget(self):
        widget = FileListWidget()
        widget.resize(700, 240)
        widget.set_files(
            [SimpleNamespace(path=f"{number}.pdf", name=f"{number}.pdf", is_file=True) for number in range(3)]
        )
        widget.show()
        self.app.processEvents()
        self.addCleanup(widget.close)
        return widget

    def _click(self, widget, row, column):
        QTest.mouseClick(
            widget.viewport(),
            Qt.MouseButton.LeftButton,
            pos=widget.visualRect(widget.model().index(row, column)).center(),
        )

    def test_name_clicks_do_not_select_or_check_files(self):
        widget = self._file_widget()
        self._click(widget, 1, widget.model().COLUMN_OLD_NAME)
        self.assertFalse(widget.selectionModel().hasSelection())
        self.assertEqual(widget.selected_file_items(), [])
        self.assertEqual(widget.selectionMode(), QAbstractItemView.SelectionMode.NoSelection)

    def test_checkbox_clicks_toggle_multiple_files_without_row_selection(self):
        widget = self._file_widget()
        for row in (0, 2):
            self._click(widget, row, widget.model().COLUMN_CHECK)
        self.assertEqual([item.path for item in widget.selected_file_items()], ["0.pdf", "2.pdf"])
        self.assertFalse(widget.selectionModel().hasSelection())
        self._click(widget, 0, widget.model().COLUMN_CHECK)
        self.assertEqual([item.path for item in widget.selected_file_items()], ["2.pdf"])

    def test_empty_area_click_keeps_explicit_checks(self):
        widget = self._file_widget()
        self._click(widget, 0, widget.model().COLUMN_CHECK)
        QTest.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(20, widget.viewport().height() - 10))
        self.assertEqual([item.path for item in widget.selected_file_items()], ["0.pdf"])

    def test_holding_mouse_checks_every_row_even_when_pointer_skips_rows(self):
        widget = self._file_widget()
        column = widget.model().COLUMN_CHECK
        start = widget.visualRect(widget.model().index(0, column)).center()
        end = widget.visualRect(widget.model().index(2, column)).center()
        QTest.mousePress(widget.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(widget.viewport(), end)
        QTest.mouseMove(widget.viewport(), start)
        QTest.mouseRelease(widget.viewport(), Qt.MouseButton.LeftButton, pos=start)
        self.assertEqual(len(widget.selected_file_items()), 3)
        self.assertFalse(widget.selectionModel().hasSelection())
        self.assertFalse(widget._check_drag_timer.isActive())

    def test_drag_from_checked_box_clears_rows_and_stops_after_release(self):
        widget = self._file_widget()
        widget.selectAll()
        column = widget.model().COLUMN_CHECK
        start = widget.visualRect(widget.model().index(0, column)).center()
        end = widget.visualRect(widget.model().index(1, column)).center()
        QTest.mousePress(widget.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(widget.viewport(), end)
        # Отпускание за пределами колонки тоже завершает протягивание.
        release = widget.visualRect(widget.model().index(1, widget.model().COLUMN_OLD_NAME)).center()
        QTest.mouseRelease(widget.viewport(), Qt.MouseButton.LeftButton, pos=release)
        QTest.mouseMove(widget.viewport(), widget.visualRect(widget.model().index(2, column)).center())
        self.assertEqual([item.path for item in widget.selected_file_items()], ["2.pdf"])
        self.assertFalse(widget._check_drag_timer.isActive())

    def test_check_drag_scrolls_to_continue_marking_files(self):
        widget = self._file_widget()
        widget.set_files([
            SimpleNamespace(path=f"{number}.pdf", name=f"{number}.pdf", is_file=True)
            for number in range(60)
        ])
        self.app.processEvents()
        start = widget.visualRect(widget.model().index(0, widget.model().COLUMN_CHECK)).center()
        QTest.mousePress(widget.viewport(), Qt.MouseButton.LeftButton, pos=start)
        edge = QPoint(start.x(), widget.viewport().height() - 1)
        for _ in range(20):
            widget._move_check_drag(edge)
        QTest.mouseRelease(widget.viewport(), Qt.MouseButton.LeftButton, pos=edge)
        self.assertGreater(widget.verticalScrollBar().value(), 0)
        self.assertGreater(len(widget.selected_file_items()), 8)

    def test_checks_survive_model_reset_filtering_and_reordering(self):
        widget = self._file_widget()
        files = widget.model().files()
        widget.select_paths(["2.pdf"])
        widget.set_files(files[:1])
        widget.set_files(list(reversed(files)))
        self.assertEqual([item.path for item in widget.selected_file_items()], ["2.pdf"])
        index = widget.model().index(0, widget.model().COLUMN_CHECK)
        self.assertEqual(index.data(Qt.ItemDataRole.CheckStateRole), Qt.CheckState.Checked)

    def test_select_all_and_space_manage_checks(self):
        widget = self._file_widget()
        widget.selectAll()
        self.assertEqual(len(widget.selected_file_items()), 3)
        widget.setCurrentIndex(widget.model().index(1, widget.model().COLUMN_OLD_NAME))
        QTest.keyClick(widget, Qt.Key.Key_Space)
        self.assertEqual([item.path for item in widget.selected_file_items()], ["0.pdf", "2.pdf"])
        widget.clearSelection()
        self.assertEqual(widget.selected_file_items(), [])

    def test_header_checkbox_toggles_visible_files_and_follows_individual_checks(self):
        widget = self._file_widget()
        files = widget.model().files()
        checkbox = widget.check_all_checkbox
        self.assertTrue(checkbox.isEnabled())
        self.assertFalse(checkbox.isChecked())
        QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
        self.assertTrue(all(item.checked for item in files))
        self.assertTrue(checkbox.isChecked())
        index = widget.model().index(0, widget.model().COLUMN_CHECK)
        widget.model().setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.assertFalse(checkbox.isChecked())
        QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
        self.assertTrue(all(item.checked for item in files))
        QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
        self.assertFalse(any(item.checked for item in files))

        widget.set_files(files[:2])
        QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
        self.assertTrue(all(item.checked for item in files[:2]))
        self.assertFalse(files[2].checked)
        widget.set_files(files)
        self.assertFalse(checkbox.isChecked())
        widget.selectAll()
        self.assertTrue(checkbox.isChecked())
        widget.clear()
        self.assertFalse(checkbox.isChecked())
        self.assertFalse(checkbox.isEnabled())

    def test_check_column_is_first_visually_and_empty_queue_cannot_be_checked(self):
        widget = self._file_widget()
        self.assertEqual(widget.horizontalHeader().visualIndex(widget.model().COLUMN_CHECK), 0)
        widget.clear()
        self._click(widget, 0, widget.model().COLUMN_CHECK)
        self.assertEqual(widget.selected_file_items(), [])


if __name__ == "__main__":
    unittest.main()
