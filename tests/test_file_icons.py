import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app.core.conversion_formats import KNOWN_FILE_EXTENSIONS
from app.ui.file_icons import file_icon
from app.core.app_icons import _find_bundled_icon
from PyQt6.QtGui import QIcon
from app.ui.ui_components import FileListModel


class FileIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_all_known_extensions_have_renderable_icons(self):
        for extension in KNOWN_FILE_EXTENSIONS:
            with self.subTest(extension=extension):
                icon = file_icon(SimpleNamespace(path="example" + extension, is_file=True))
                self.assertFalse(icon.pixmap(24, 24).isNull())

    def test_main_assets_and_all_categories_render(self):
        assets = ["file.svg", "folder.svg", "icon.svg", "three-dots.svg"]
        assets += [f"file_types/{category}.svg" for category in (
            "document", "image", "spreadsheet", "presentation", "audio", "video", "archive", "unknown"
        )]
        for asset in assets:
            with self.subTest(asset=asset):
                path = _find_bundled_icon(asset)
                self.assertIsNotNone(path)
                self.assertFalse(QIcon(path).pixmap(28, 28).isNull())
        self.assertFalse(file_icon(SimpleNamespace(path="folder", is_file=False)).pixmap(28, 28).isNull())

    def test_category_sharing_case_folder_and_unknown_fallback(self):
        def key(path, is_file=True):
            return file_icon(SimpleNamespace(path=path, is_file=is_file)).cacheKey()

        self.assertEqual(key("test.DOCX"), key("test.docx"))
        self.assertEqual(key("test.doc"), key("test.docx"))
        self.assertEqual(key("test.jpg"), key("test.png"))
        self.assertEqual(key("test.zip"), key("test.rar"))
        self.assertEqual(key("test.txt"), key("test.docx"))
        self.assertEqual(key("test.json"), key("test.txt"))
        self.assertNotEqual(key("test.txt"), key("test.png"))
        self.assertNotEqual(key("test.zip"), key("test.png"))
        self.assertEqual(key("folder.pdf", False), key("folder", False))
        self.assertNotEqual(key("folder.pdf", False), key("file.pdf"))
        for path in ("unknown.unregistered", "no_extension", "file.неизвестно"):
            self.assertFalse(file_icon(SimpleNamespace(path=path, is_file=True)).pixmap(24, 24).isNull())

    def test_model_uses_separate_icon_and_original_file_extension(self):
        item = SimpleNamespace(path="image.png", name="image.png", preview_name="image.pdf", is_file=True)
        model = FileListModel()
        model.set_files([item])
        index = model.index(0)
        self.assertEqual(index.data(Qt.ItemDataRole.DisplayRole), "image.png")
        self.assertEqual(index.data(Qt.ItemDataRole.ToolTipRole), "image.png -> image.pdf")
        self.assertEqual(index.data(Qt.ItemDataRole.DecorationRole).cacheKey(), file_icon(item).cacheKey())


if __name__ == "__main__":
    unittest.main()
