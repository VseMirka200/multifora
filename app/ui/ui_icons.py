from functools import lru_cache

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractButton

from app.core.app_icons import _find_bundled_icon

UI_ICON_SIZE = QSize(22, 22)


def ui_icon(name, variant):
    path = _find_bundled_icon(f"ui-icons/{variant}/{name}.svg")
    return QIcon(path) if path else QIcon()


@lru_cache(maxsize=256)
def button_icon(name, mode, role):
    """Подбирает обычный и отключённый варианты для фона кнопки."""
    variant = mode
    if role == "danger" or (role == "primary" and mode == "light"):
        variant = "on-color"
    elif role == "primary":
        variant = "light"
    icon = ui_icon(name, variant)
    disabled_source = ui_icon(name, mode)
    # Белый on-color Qt не затемняет. Берём отключённый вариант с обычной
    # поверхности и сохраняем размеры для распространённых масштабов экрана.
    for size in (22, 33, 44, 66):
        icon.addPixmap(disabled_source.pixmap(size, size, QIcon.Mode.Disabled), QIcon.Mode.Disabled)
    return icon


def apply_button_icon(button, mode):
    """Обновляет явно заданную иконку с учётом фона кнопки."""
    name = button.property("buttonIconName")
    if not name:
        return
    role = button.property("buttonVariant") or "secondary"
    button.setIcon(button_icon(str(name), mode, str(role)))
    button.setIconSize(UI_ICON_SIZE)


def apply_window_icons(window, mode):
    controls = (
        (window._clear_ext_filter_action, "clear-selection"),
        (window._clear_type_filter_action, "clear-selection"),
        (window._select_all_ext_filter_action, "select-all"),
        (window._select_all_type_filter_action, "select-all"),
        (window.btn_reset_queue_filters, "reset-filters"),
        (window.btn_clear_active_filters, "reset-filters"),
        (window.btn_show_all_queue_files, "queue"),
        (window.search_icon_action, "search"),
        (window.btn_locate_rename_issue, "locate-issue"),
        (window.btn_open_rename_history, "history"),
        (window.btn_insert_token, "substitutions"),
        (window.btn_save_template, "save"),
        (window.btn_manage_templates, "templates"),
        (window.btn_select_image_output_path, "choose-folder"),
        (window.btn_select_conversion_output_folder, "choose-folder"),
        (window.operation_result_panel.open_result, "open"),
        (window.operation_result_panel.open_folder, "choose-folder"),
        (window.operation_result_panel.details, "details"),
        (window.btn_add_files, "add-file"),
        (window.btn_add_folder, "add-folder"),
        (window.support_page.guide, "guide"),
        (window.btn_apply_rename, "rename"),
        (window.btn_convert, "convert"),
        (window.btn_merge, "merge"),
        (window.btn_compress, "compress"),
    )
    for control, name in controls:
        if isinstance(control, QAbstractButton):
            control.setProperty("buttonIconName", name)
            apply_button_icon(control, mode)
        else:
            control.setIcon(ui_icon(name, mode))

    for key, label in window.support_page.icons.items():
        label.setPixmap(ui_icon("document" if key == "save" else key, mode).pixmap(UI_ICON_SIZE))
