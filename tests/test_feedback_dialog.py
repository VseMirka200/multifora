"""Компактная форма обращения: выбор категории, копирование и внешний браузер."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.core.feedback import ISSUE_TYPES
from app.ui.feedback_dialog import FeedbackDialog


class FeedbackDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = FeedbackDialog()

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()

    def test_compact_and_non_resizable(self):
        self.assertEqual(self.dialog.minimumSize(), self.dialog.maximumSize())
        self.assertFalse(self.dialog.isSizeGripEnabled())
        self.assertLessEqual(self.dialog.width(), 530)
        self.assertEqual(self.dialog.issue_type.count(), len(ISSUE_TYPES))

    def test_changing_type_populates_correct_template(self):
        new_index = next(i for i, kind in enumerate(ISSUE_TYPES) if kind.key == "feature")
        self.dialog.issue_type.setCurrentIndex(new_index)
        self.assertIn("💡", self.dialog.subject.text())
        self.assertIn("Что предлагаете", self.dialog.details.toPlainText())

    def test_copy_then_open_url(self):
        self.dialog.subject.setText("🐛 Ошибка тестирования")
        with patch("app.ui.feedback_dialog.QDesktopServices.openUrl", return_value=True) as opener:
            self.dialog.copy_and_open()
        opener.assert_called_once()
        self.assertIn("Шаги воспроизведения", self.app.clipboard().text())
        self.dialog.copy_title()
        self.assertEqual(self.app.clipboard().text(), "🐛 Ошибка тестирования")
        self.dialog.copy_description()
        self.assertIn("Шаги воспроизведения", self.app.clipboard().text())


if __name__ == "__main__":
    unittest.main()
