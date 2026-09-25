import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from app.core.message_boxes import show_app_choice, show_app_confirmation
from app.ui.ui_spacing import FIELD_HEIGHT


class MessageBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.parent = QWidget()
        self.parent._effective_theme_mode = "dark"
        self.parent.setStyleSheet(
            'QPushButton[buttonVariant="secondary"] { background: #333333; }'
        )

    def tearDown(self):
        self.parent.deleteLater()

    def test_choice_dialog_uses_shared_layout_and_button_style(self):
        captured = {}

        def click_second(dialog):
            captured["dialog"] = dialog
            dialog.findChild(QPushButton, "appMessageButton_second").click()
            return int(QDialog.DialogCode.Accepted)

        with patch.object(QDialog, "exec", new=click_second):
            result = show_app_choice(
                self.parent,
                "Проверка",
                "Единое оформление уведомления",
                (
                    ("first", "Первый", "secondary"),
                    ("second", "Второй", "secondary"),
                ),
                default_key="first",
                cancel_key="second",
            )

        self.assertEqual(result, "second")
        dialog = captured["dialog"]
        self.assertEqual(dialog.objectName(), "appMessageDialog")
        self.assertEqual(dialog.styleSheet(), self.parent.styleSheet())
        for button in dialog.findChildren(QPushButton):
            self.assertEqual(button.height(), FIELD_HEIGHT)
            self.assertEqual(
                button.sizePolicy().horizontalPolicy(),
                QSizePolicy.Policy.Expanding,
            )
        self.assertEqual(
            dialog.findChild(QPushButton, "appMessageButton_first").property("buttonVariant"),
            "secondary",
        )
        self.assertEqual(
            dialog.findChild(QPushButton, "appMessageButton_second").property("buttonVariant"),
            "danger",
        )
        self.assertEqual(
            dialog.findChild(QPushButton, "appMessageButton_first").styleSheet(),
            dialog.findChild(QPushButton, "appMessageButton_second").styleSheet(),
        )

    def test_confirmation_treats_window_close_as_no(self):
        with patch.object(
            QDialog,
            "exec",
            new=lambda _dialog: int(QDialog.DialogCode.Rejected),
        ):
            accepted = show_app_confirmation(
                self.parent,
                "Подтверждение",
                "Продолжить?",
                icon=QMessageBox.Icon.Question,
            )

        self.assertFalse(accepted)

    def test_choice_buttons_fit_long_labels(self):
        captured = {}

        def close_dialog(dialog):
            captured["dialog"] = dialog
            return int(QDialog.DialogCode.Rejected)

        with patch.object(QDialog, "exec", new=close_dialog):
            show_app_choice(
                self.parent,
                "Добавление папки",
                "Выберите способ добавления",
                (
                    ("folder", "Добавить папку", "secondary"),
                    ("contents", "Добавить содержимое", "secondary"),
                    ("cancel", "Отмена", "secondary"),
                ),
                cancel_key="cancel",
            )

        dialog = captured["dialog"]
        buttons = dialog.findChildren(QPushButton)
        for button in buttons:
            text_width = QFontMetrics(button.font()).horizontalAdvance(button.text())
            self.assertGreaterEqual(button.minimumWidth(), text_width + 24)

        required_width = sum(button.minimumWidth() for button in buttons) + 8 * (len(buttons) - 1) + 28
        self.assertGreaterEqual(dialog.minimumWidth(), required_width)


if __name__ == "__main__":
    unittest.main()
