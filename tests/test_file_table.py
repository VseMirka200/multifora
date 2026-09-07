import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QApplication, QHeaderView

from app.ui.ui_components import FileListModel, FileListWidget


class FileTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_model_exposes_name_type_and_path_without_icons(self):
        item = SimpleNamespace(
            path=r"C:\Users\User\Pictures\image.png",
            name="image.png",
            preview_name="image.pdf",
            is_file=True,
        )
        model = FileListModel()
        model.set_files([item])
        name_index = model.index(0, model.COLUMN_NAME)
        type_index = model.index(0, model.COLUMN_TYPE)
        path_index = model.index(0, model.COLUMN_PATH)
        self.assertEqual(model.columnCount(), 3)
        self.assertEqual(name_index.data(Qt.ItemDataRole.DisplayRole), "image.pdf")
        self.assertEqual(name_index.data(Qt.ItemDataRole.ToolTipRole), "image.png -> image.pdf")
        self.assertEqual(type_index.data(Qt.ItemDataRole.DisplayRole), "PNG")
        self.assertEqual(path_index.data(Qt.ItemDataRole.DisplayRole), item.path)
        self.assertEqual(path_index.data(Qt.ItemDataRole.ToolTipRole), item.path)
        self.assertIsNone(name_index.data(Qt.ItemDataRole.DecorationRole))

    def test_file_type_handles_uppercase_extension_folder_and_extensionless_file(self):
        model = FileListModel()
        model.set_files([
            SimpleNamespace(path="report.PDF", name="report.PDF", is_file=True),
            SimpleNamespace(path="documents", name="documents", is_file=False),
            SimpleNamespace(path="README", name="README", is_file=True),
        ])
        self.assertEqual(model.index(0, model.COLUMN_TYPE).data(), "PDF")
        self.assertEqual(model.index(1, model.COLUMN_TYPE).data(), "Папка")
        self.assertEqual(model.index(2, model.COLUMN_TYPE).data(), "Файл")

    def test_widget_uses_row_selection_and_elides_long_text_on_the_right(self):
        widget = FileListWidget()
        self.assertEqual(
            widget.selectionBehavior(),
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self.assertEqual(widget.textElideMode(), Qt.TextElideMode.ElideRight)
        self.assertTrue(widget.horizontalHeader().stretchLastSection())
        header = widget.horizontalHeader()
        self.assertEqual(
            header.sectionResizeMode(widget.model().COLUMN_NAME),
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


if __name__ == "__main__":
    unittest.main()
