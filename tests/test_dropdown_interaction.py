import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit, QWidget

from app.ui.theme_styles import APPLICATION_STYLES
from app.ui.ui_components import (
    MenuLikeComboBox,
    apply_standard_field_style,
    ScrollableFilterMenu,
    StandardPopupMenu,
    setup_standard_dropdown,
)
from app.ui.ui_icons import button_icon


@pytest.fixture(params=["light", "dark"])
def field(request):
    app = QApplication.instance() or QApplication([])
    old_style = app.styleSheet()
    app.setStyleSheet(APPLICATION_STYLES[request.param])
    root = QWidget()
    root._effective_theme_mode = request.param
    root.resize(400, 150)
    combo = MenuLikeComboBox(root)
    setup_standard_dropdown(combo)
    combo.setFixedWidth(140)
    combo.move(10, 10)
    combo.addItem("Первый & выбранный", "first", icon_name="document")
    combo.addItem("Второй вариант", "second", icon_name="convert")
    root.show()
    app.processEvents()
    yield combo
    combo.menu().close()
    root.close()
    root.deleteLater()
    app.processEvents()
    app.setStyleSheet(old_style)


@pytest.mark.parametrize("arrow", [False, True])
def test_left_click_selection_and_persistent_check(field, arrow):
    QTest.mouseClick(field, Qt.MouseButton.LeftButton,
                     pos=QPoint(field.width() - 12 if arrow else 12, field.height() // 2))
    QApplication.processEvents()
    menu = field.menu()
    assert menu.isVisible() and field.property("menuOpen")
    first, second = menu.actions()
    menu.setActiveAction(second)
    assert first.isChecked() and not second.isChecked()
    assert first.property("fullText") == "Первый & выбранный"
    assert "&&" in first.text()
    assert menu.actionGeometry(first).height() == 28
    assert not first.icon().isNull()
    QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(second).center())
    assert field.currentData() == "second"
    assert second.isChecked() and not first.isChecked()
    assert not menu.isVisible() and not field.property("menuOpen")


def test_cancel_outside_empty_and_disabled(field):
    menu = field.menu()
    for escape in (True, False):
        QTest.mouseClick(field, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        if escape:
            QTest.keyClick(menu, Qt.Key.Key_Escape)
        else:
            QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=QPoint(-10, -10))
        assert not menu.isVisible()
        assert field.currentIndex() == 0
    field.setEnabled(False)
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    assert not menu.isVisible()
    field.clear()
    assert field.toolTip() == "" and field.currentIndex() == -1
    assert not menu.actions()
    field.setEnabled(True)
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    assert not menu.isVisible()


def test_long_labels_and_popup_fit_screen_edges(field):
    field.addItem("Длинное название " * 100)
    available = field.screen().availableGeometry()
    root = field.window()
    root.move(available.right() - root.width(), available.bottom() - root.height())
    field.move(root.width() - field.width(), root.height() - field.height())
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    menu = field.menu()
    assert menu.width() > field.width()
    assert available.contains(menu.geometry())
    assert menu.geometry().bottom() <= field.mapToGlobal(QPoint()).y()
    assert menu.toolTipsVisible()
    assert menu.actions()[-1].toolTip() == "Длинное название " * 100


def test_long_menu_scrolls_to_last_option(field):
    for index in range(100):
        field.addItem(f"Пункт {index}")
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    menu = field.menu()
    QTest.keyClick(menu, Qt.Key.Key_End)
    QApplication.processEvents()
    last = menu.actions()[-1]
    assert menu.activeAction() is last
    assert menu.rect().contains(menu.actionGeometry(last).center())
    QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(last).center())
    assert field.currentText() == "Пункт 99"


def test_group_and_individual_filter_clicks_keep_menu_open(field):
    menu = ScrollableFilterMenu(field)
    commands = [menu.add_command("Снять все", icon_name="clear-selection"),
                menu.add_command("Вернуть все", icon_name="select-all")]
    action = QAction("PDF", menu)
    action.setCheckable(True)
    action.setChecked(True)
    menu.add_filter_action(action)
    for command, checked in zip(commands, (False, True), strict=True):
        command.setProperty("keepOpen", True)
        command.triggered.connect(lambda _checked=False, value=checked: action.setChecked(value))
    menu.popup(field.mapToGlobal(QPoint(0, field.height())))
    QApplication.processEvents()
    for command, checked in zip(commands, (False, True), strict=True):
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(command).center())
        assert menu.isVisible() and action.isChecked() is checked
        assert menu.actionGeometry(command).height() == 28
    view = menu.filter_list
    assert view.visualItemRect(view.item(0)).height() == 28
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.visualItemRect(view.item(0)).center())
    assert menu.isVisible() and not action.isChecked()
    QTest.keyClick(menu, Qt.Key.Key_Escape)
    assert not menu.isVisible()


def test_menu_icons_refresh_and_disabled_actions_do_not_trigger(field):
    menu = StandardPopupMenu(field)
    action = menu.add_command("Недоступно", icon_name="copy")
    action.setEnabled(False)
    triggered = []
    action.triggered.connect(lambda: triggered.append(True))
    for mode in ("dark", "light"):
        field.window()._effective_theme_mode = mode
        menu.popup(field.mapToGlobal(QPoint(0, field.height())))
        QApplication.processEvents()
        assert action.icon().pixmap(18, 18).toImage() == button_icon("copy", mode, "secondary").pixmap(18, 18).toImage()
        assert not action.icon().pixmap(18, 18, QIcon.Mode.Disabled).isNull()
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
        assert not triggered
        menu.close()


def test_standard_edit_context_menus_are_disabled():
    app = QApplication.instance() or QApplication([])
    for widget in (QLineEdit(), QTextEdit(), QPlainTextEdit()):
        apply_standard_field_style(widget)
        assert widget.contextMenuPolicy() == Qt.ContextMenuPolicy.NoContextMenu
        widget.deleteLater()
    app.processEvents()


def test_context_popup_uses_theme_widget_without_anchor_width(field):
    menu = StandardPopupMenu(theme_widget=field.window())
    action = menu.add_command("Открыть\tEnter", icon_name="open")
    menu.popup(field.mapToGlobal(QPoint(0, field.height())))
    QApplication.processEvents()
    assert not action.icon().isNull()
    assert menu.width() < field.window().width()
    menu.close()
