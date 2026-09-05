import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app.core.conversion_formats import KNOWN_FILE_EXTENSIONS
from app.ui.file_icons import file_icon
from app.ui.ui_components import FileListModel


class FileIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_all_known_extensions_have_their_own_renderable_asset(self):
        asset_dir = Path("assets/files extension")
        for extension in KNOWN_FILE_EXTENSIONS:
            with self.subTest(extension=extension):
                self.assertTrue(any(
                    (asset_dir / f"{extension[1:]}.{suffix}").is_file()
                    for suffix in ("ico", "svg", "png")
                ))
                icon = file_icon(SimpleNamespace(path="example" + extension, is_file=True))
                self.assertFalse(icon.pixmap(24, 24).isNull())

    def test_exact_extension_case_folder_and_unknown_fallback(self):
        def key(path, is_file=True):
            return file_icon(SimpleNamespace(path=path, is_file=is_file)).cacheKey()

        self.assertEqual(key("test.DOCX"), key("test.docx"))
        self.assertNotEqual(key("test.doc"), key("test.docx"))
        self.assertNotEqual(key("test.jpg"), key("test.png"))
        self.assertNotEqual(key("test.zip"), key("test.rar"))
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
