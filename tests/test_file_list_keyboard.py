import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from app.ui.ui_components import FileListWidget


class FileListKeyboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_file_action_keys_emit_requests(self):
        widget = FileListWidget()
        callbacks = {
            Qt.Key.Key_Delete: (widget.deleteRequested, Mock()),
            Qt.Key.Key_Return: (widget.openRequested, Mock()),
            Qt.Key.Key_F2: (widget.renameRequested, Mock()),
        }

        for key, (signal, callback) in callbacks.items():
            signal.connect(callback)
            widget.keyPressEvent(
                QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
            )
            callback.assert_called_once_with()

        copy_callback = Mock()
        widget.copyRequested.connect(copy_callback)
        widget.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_C,
                Qt.KeyboardModifier.ControlModifier,
            )
        )
        copy_callback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
