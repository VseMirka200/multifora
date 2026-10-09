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
        self.assertEqual(model.columnCount(), 4)
        self.assertEqual(
            model.headerData(model.COLUMN_OLD_NAME, Qt.Orientation.Horizontal), "Старое имя"
        )
        self.assertEqual(
            model.headerData(model.COLUMN_NEW_NAME, Qt.Orientation.Horizontal), "Новое имя"
        )
        self.assertEqual(
            model.headerData(model.COLUMN_PATH, Qt.Orientation.Horizontal),
            "Исходная папка",
        )
        self.assertEqual(old_name_index.data(Qt.ItemDataRole.DisplayRole), "image.png")
        self.assertEqual(old_name_index.data(Qt.ItemDataRole.ToolTipRole), "image.png")
        self.assertEqual(new_name_index.data(Qt.ItemDataRole.DisplayRole), "image.pdf")
        self.assertEqual(new_name_index.data(Qt.ItemDataRole.ToolTipRole), "image.pdf")
        self.assertEqual(type_index.data(Qt.ItemDataRole.DisplayRole), "PNG")
        self.assertEqual(
            path_index.data(Qt.ItemDataRole.DisplayRole),
            os.path.dirname(item.path),
        )
        self.assertEqual(path_index.data(Qt.ItemDataRole.ToolTipRole), item.path)
        self.assertIsNone(old_name_index.data(Qt.ItemDataRole.DecorationRole))
        self.assertIsNone(new_name_index.data(Qt.ItemDataRole.DecorationRole))

    def test_file_type_handles_uppercase_extension_folder_and_extensionless_file(self):
        model = FileListModel()
        model.set_files(
            [
                SimpleNamespace(path="report.PDF", name="report.PDF", is_file=True),
                SimpleNamespace(path="documents", name="documents", is_file=False),
                SimpleNamespace(path="README", name="README", is_file=True),
            ]
        )
        self.assertEqual(model.index(0, model.COLUMN_TYPE).data(), "PDF")
        self.assertEqual(model.index(1, model.COLUMN_TYPE).data(), "Папка")
        self.assertEqual(model.index(2, model.COLUMN_TYPE).data(), "Файл")

    def test_source_folder_distinguishes_files_from_different_directories(self):
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

    def test_widget_uses_row_selection_and_elides_long_text_on_the_right(self):
        widget = FileListWidget()
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
        header.setSortIndicator(widget.model().COLUMN_OLD_NAME, Qt.SortOrder.AscendingOrder)
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

    def test_mouse_click_selects_complete_rows_and_ctrl_adds_rows(self):
        widget = FileListWidget()
        widget.resize(640, 240)
        widget.set_files(
            [
                SimpleNamespace(path="one.docx", name="one.docx", is_file=True),
                SimpleNamespace(path="two.docx", name="two.docx", is_file=True),
                SimpleNamespace(path="three.docx", name="three.docx", is_file=True),
            ]
        )
        widget.show()
        self.app.processEvents()

        second_row_cell = widget.model().index(1, widget.model().COLUMN_NEW_NAME)
        QTest.mouseClick(
            widget.viewport(),
            Qt.MouseButton.LeftButton,
            pos=widget.visualRect(second_row_cell).center(),
        )
        self.assertEqual(
            [index.row() for index in widget.selectionModel().selectedRows()],
            [1],
        )
        self.assertTrue(
            all(
                widget.selectionModel().isSelected(widget.model().index(1, column))
                for column in range(widget.model().columnCount())
            )
        )

        third_row_cell = widget.model().index(2, widget.model().COLUMN_OLD_NAME)
        QTest.mouseClick(
            widget.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            widget.visualRect(third_row_cell).center(),
        )
        self.assertEqual(
            [index.row() for index in widget.selectionModel().selectedRows()],
            [1, 2],
        )
        widget.close()

    def test_empty_area_click_clears_selection(self):
        widget = FileListWidget()
        widget.resize(640, 240)
        widget.set_files(
            [SimpleNamespace(path="one.pdf", name="one.pdf", is_file=True)]
        )
        widget.show()
        self.app.processEvents()

        row = widget.model().index(0, 0)
        QTest.mouseClick(
            widget.viewport(),
            Qt.MouseButton.LeftButton,
            pos=widget.visualRect(row).center(),
        )
        self.assertTrue(widget.selectionModel().hasSelection())

        empty_point = QPoint(20, widget.viewport().height() - 10)
        self.assertFalse(widget.indexAt(empty_point).isValid())
        QTest.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=empty_point)

        self.assertFalse(widget.selectionModel().hasSelection())
        widget.close()

    def test_system_mouse_drag_selects_row_range(self):
        widget = FileListWidget()
        widget.resize(640, 240)
        widget.set_files(
            [
                SimpleNamespace(path="one.pdf", name="one.pdf", is_file=True),
                SimpleNamespace(path="two.pdf", name="two.pdf", is_file=True),
                SimpleNamespace(path="three.pdf", name="three.pdf", is_file=True),
            ]
        )
        widget.show()
        self.app.processEvents()

        start = widget.visualRect(widget.model().index(0, 0)).center()
        end = widget.visualRect(widget.model().index(2, 0)).center()

        QTest.mousePress(widget.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(widget.viewport(), end, delay=10)
        QTest.mouseRelease(widget.viewport(), Qt.MouseButton.LeftButton, pos=end)

        self.assertEqual(
            [index.row() for index in widget.selectionModel().selectedRows()],
            [0, 1, 2],
        )
        widget.close()


if __name__ == "__main__":
    unittest.main()
