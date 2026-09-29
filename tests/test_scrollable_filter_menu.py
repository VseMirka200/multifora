import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QToolButton

from app.ui.theme_styles import DARK_APPLICATION_STYLE
from app.ui.ui_components import (
    MenuLikeComboBox,
    ScrollableFilterMenu,
    sync_standard_menu_width,
)
from app.ui.ui_spacing import FIELD_HEIGHT


class ScrollableFilterMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_long_menu_is_compact_scrollable_and_keeps_actions_checkable(self):
        previous_style = self.app.styleSheet()
        self.app.setStyleSheet(DARK_APPLICATION_STYLE)
        menu = ScrollableFilterMenu(max_visible_items=8)
        self.assertTrue(menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(menu.windowFlags() & Qt.WindowType.FramelessWindowHint)
        menu.addAction("Снять все отметки")
        menu.addSeparator()
        actions = []
        for index in range(12):
            action = QAction(f"Формат {index + 1}", menu)
            action.setCheckable(True)
            action.setChecked(True)
            menu.add_filter_action(action)
            actions.append(action)

        filter_list = menu.filter_list
        self.assertIsNotNone(filter_list)
        self.assertEqual(filter_list.count(), 12)
        self.assertEqual(filter_list.height(), FIELD_HEIGHT * 8 + 2)
        self.assertEqual(
            filter_list.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn,
        )
        self.assertFalse(hasattr(menu, "_scroll_hint"))

        anchor = QToolButton()
        anchor.setFixedWidth(180)
        sync_standard_menu_width(menu, anchor)
        menu.show()
        self.app.processEvents()
        self.assertEqual(menu.styleSheet(), "")
        self.assertEqual(filter_list.width(), menu.width() - 2)
        self.assertTrue(filter_list.verticalScrollBar().isVisible())
        self.assertEqual(filter_list.verticalScrollBar().width(), 14)
        scroll_bar = filter_list.verticalScrollBar()
        scroll_bar_right = scroll_bar.mapTo(menu, QPoint(0, 0)).x() + scroll_bar.width()
        self.assertLessEqual(scroll_bar_right, menu.width())

        menu._update_filter_list_height(FIELD_HEIGHT * 5)
        self.assertEqual(filter_list.height(), FIELD_HEIGHT * 3 + 2)

        scroll_bar.setRange(0, 300)
        scroll_bar.setValue(150)
        initial_scroll_value = scroll_bar.value()
        filter_list._animate_scroll_steps(-1)
        self.assertEqual(filter_list._scroll_animation.duration(), 180)
        self.assertEqual(
            filter_list._scroll_animation.endValue(),
            initial_scroll_value + FIELD_HEIGHT,
        )
        filter_list._scroll_animation.stop()

        menu._toggle_filter_item(filter_list.item(0))
        self.assertFalse(actions[0].isChecked())
        self.assertTrue(filter_list.item(0).text().startswith(" "))

        menu.deleteLater()
        self.app.setStyleSheet(previous_style)

    def test_menu_like_combo_uses_transparent_popup_corners(self):
        combo = MenuLikeComboBox()
        self.assertTrue(combo.menu().testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(combo.menu().windowFlags() & Qt.WindowType.FramelessWindowHint)
        combo.deleteLater()


if __name__ == "__main__":
    unittest.main()
