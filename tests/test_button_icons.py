import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QPushButton, QWidget

from app.ui.ui_components import (
    refresh_standard_button_styles,
    setup_standard_action_button,
)
from app.ui.ui_icons import UI_ICON_SIZE, ui_icon


@pytest.fixture
def icon_host():
    app = QApplication.instance() or QApplication([])
    root = QWidget()
    root._effective_theme_mode = "dark"
    yield root
    root.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("role", ["primary", "secondary", "danger"])
def test_explicit_icon_uses_button_background_and_survives_caption_change(icon_host, theme, role):
    icon_host._effective_theme_mode = theme
    button = QPushButton("Первое название", icon_host)
    setup_standard_action_button(button, variant=role, icon_name="save")
    variant = "on-color" if role == "danger" or (role == "primary" and theme == "light") else (
        "light" if role == "primary" else theme
    )
    expected = ui_icon("save", variant).pixmap(UI_ICON_SIZE).toImage()
    assert not expected.isNull()
    assert button.iconSize() == UI_ICON_SIZE
    assert button.icon().pixmap(UI_ICON_SIZE).toImage() == expected
    button.setText("Другая подпись")
    refresh_standard_button_styles(icon_host)
    assert button.icon().pixmap(UI_ICON_SIZE).toImage() == expected
    disabled = button.icon().pixmap(UI_ICON_SIZE, QIcon.Mode.Disabled).toImage()
    assert not disabled.isNull()
    assert disabled != expected


def test_dialog_icon_follows_root_theme_even_with_cached_dialog_theme(icon_host):
    dialog = QDialog(icon_host)
    dialog._effective_theme_mode = "dark"
    button = QPushButton("Применить", dialog)
    setup_standard_action_button(button, variant="primary", icon_name="check-document")
    for theme, variant in (("light", "on-color"), ("dark", "light")):
        icon_host._effective_theme_mode = theme
        refresh_standard_button_styles(icon_host)
        assert button.icon().pixmap(UI_ICON_SIZE).toImage() == ui_icon(
            "check-document", variant
        ).pixmap(UI_ICON_SIZE).toImage()


@pytest.mark.parametrize("name", ["add-file", "check-document", "retry", "guide", "undo"])
def test_new_colored_button_assets_render_at_both_scales(icon_host, name):
    icon = ui_icon(name, "on-color")
    for size in (22, 44):
        pixmap = icon.pixmap(size, size)
        assert not pixmap.isNull()
        image = pixmap.toImage()
        visible = [image.pixelColor(x, y) for y in range(image.height()) for x in range(image.width())
                   if image.pixelColor(x, y).alpha() > 128]
        assert visible
        assert all(color.red() == color.green() == color.blue() == 255 for color in visible)
