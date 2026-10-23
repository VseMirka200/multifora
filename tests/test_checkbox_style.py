import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QCheckBox, QMenu, QStyle

from app.ui.checkbox_style import install_checkbox_style, paint_checkbox
from app.ui.theme_styles import APPLICATION_STYLES
from app.ui.ui_components import ScrollableFilterMenu


class CheckboxStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        install_checkbox_style(cls.app)

    def setUp(self):
        previous = self.app.styleSheet()
        self.addCleanup(self.app.setStyleSheet, previous)

    def test_widget_states_use_shared_renderer_in_both_themes(self):
        for theme in ("light", "dark"):
            self.app.setStyleSheet(APPLICATION_STYLES[theme])
            checkbox = QCheckBox("Флажок")
            checkbox.resize(180, 32)
            self.addCleanup(checkbox.deleteLater)
            for state in (Qt.CheckState.Unchecked, Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                for enabled in (True, False):
                    with self.subTest(theme=theme, state=state, enabled=enabled):
                        checkbox.setEnabled(enabled)
                        checkbox.setCheckState(state)
                        with patch("app.ui.checkbox_style.paint_checkbox", wraps=paint_checkbox) as paint:
                            checkbox.grab()
                        self.assertTrue(paint.called)
                        flags = paint.call_args.args[1].state
                        self.assertEqual(bool(flags & QStyle.StateFlag.State_Enabled), enabled)
                        self.assertEqual(bool(flags & QStyle.StateFlag.State_On), state == Qt.CheckState.Checked)
                        self.assertEqual(
                            bool(flags & QStyle.StateFlag.State_NoChange), state == Qt.CheckState.PartiallyChecked
                        )

    def test_filter_list_uses_shared_renderer_and_keeps_action_state(self):
        self.app.setStyleSheet(APPLICATION_STYLES["dark"])
        menu = ScrollableFilterMenu()
        self.addCleanup(menu.deleteLater)
        action = QAction("PDF", menu)
        action.setCheckable(True)
        action.setChecked(True)
        menu.add_filter_action(action)
        menu.filter_list.resize(180, 40)
        with patch("app.ui.checkbox_style.paint_checkbox", wraps=paint_checkbox) as paint:
            menu.filter_list.grab()
        self.assertTrue(paint.called)
        self.assertEqual(menu.filter_list.item(0).text(), "PDF")
        self.assertEqual(menu.filter_list.item(0).checkState(), Qt.CheckState.Checked)
        menu._toggle_filter_item(menu.filter_list.item(0))
        self.assertFalse(action.isChecked())
        self.assertEqual(menu.filter_list.item(0).checkState(), Qt.CheckState.Unchecked)

    def test_installation_can_repeat_without_replacing_style(self):
        self.app.setStyleSheet("")
        style = self.app.style()
        install_checkbox_style(self.app)
        self.assertIs(self.app.style(), style)

    def test_regular_menu_uses_shared_renderer(self):
        self.app.setStyleSheet(APPLICATION_STYLES["light"])
        menu = QMenu()
        self.addCleanup(menu.deleteLater)
        action = menu.addAction("Включено")
        action.setCheckable(True)
        action.setChecked(True)
        menu.adjustSize()
        with patch("app.ui.checkbox_style.paint_checkbox", wraps=paint_checkbox) as paint:
            menu.grab()
        self.assertTrue(paint.called)
