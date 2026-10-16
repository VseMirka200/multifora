"""Regressions for the Help button's dropdown toggle."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMenu, QPushButton

from app.ui.mixins.operations_tab_layout_mixin import (
    OperationsTabLayoutMixin,
    _HelpMenuClickFilter,
)


class _HelpHarness(OperationsTabLayoutMixin):
    def __init__(self, app):
        self.btn_help = QPushButton("Справка")
        self.btn_help.setCheckable(True)
        self.btn_help.setFixedSize(75, 24)
        self.help_menu = QMenu(self.btn_help)
        self.help_menu.addAction("О программе")
        self.help_menu.aboutToHide.connect(self._sync_help_button_after_menu)
        self._click_filter = _HelpMenuClickFilter(
            self.btn_help, self.help_menu
        )
        app.installEventFilter(self._click_filter)
        self.btn_help.clicked.connect(self._show_help_menu)
        self.btn_help.show()

    def cleanup(self, app):
        self.help_menu.hide()
        app.removeEventFilter(self._click_filter)
        self.btn_help.close()
        self.btn_help.deleteLater()


class HelpMenuToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.ui = _HelpHarness(self.app)
        self.app.processEvents()

    def tearDown(self):
        self.ui.cleanup(self.app)
        self.app.processEvents()

    def test_repeated_click_toggles_help_menu(self):
        self.ui.btn_help.click()
        self.app.processEvents()
        self.assertTrue(self.ui.help_menu.isVisible())
        self.assertTrue(self.ui.btn_help.isChecked())

        self.ui.btn_help.click()
        self.app.processEvents()
        self.assertFalse(self.ui.help_menu.isVisible())
        self.assertFalse(self.ui.btn_help.isChecked())

        self.ui.btn_help.click()
        self.app.processEvents()
        self.assertTrue(self.ui.help_menu.isVisible())

    def test_mouse_click_does_not_reopen_visible_popup(self):
        QTest.mouseClick(self.ui.btn_help, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.ui.help_menu.isVisible())

        # В зависимости от платформы Qt передаёт щелчок popup или кнопке.
        QTest.mouseClick(self.ui.btn_help, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertFalse(self.ui.help_menu.isVisible())
        self.assertFalse(self.ui.btn_help.isChecked())

        QTest.mouseClick(self.ui.btn_help, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.ui.help_menu.isVisible())

    def test_hiding_popup_resets_button_state(self):
        self.ui.btn_help.click()
        self.app.processEvents()
        self.ui.help_menu.hide()
        self.app.processEvents()
        self.assertFalse(self.ui.btn_help.isChecked())
        self.ui.btn_help.click()
        self.app.processEvents()
        self.assertTrue(self.ui.help_menu.isVisible())

    def test_popup_animates_to_the_right_of_help_button(self):
        expected_position = self.ui.btn_help.mapToGlobal(
            self.ui.btn_help.rect().topRight()
        ) + QPoint(4, 0)

        self.ui.btn_help.click()
        self.app.processEvents()

        self.assertEqual(
            self.ui._help_menu_position_animation.endValue(), expected_position
        )
        self.assertEqual(self.ui._help_menu_position_animation.duration(), 150)
        self.assertEqual(self.ui._help_menu_opacity_animation.endValue(), 1.0)


if __name__ == "__main__":
    unittest.main()
