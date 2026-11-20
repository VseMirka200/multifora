from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton

from app.core.app_icons import _find_bundled_icon


def ui_icon(name, variant):
    path = _find_bundled_icon(f"ui-icons/{variant}/{name}.svg")
    return QIcon(path) if path else QIcon()


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
        (window.btn_save_template, "save"),
        (window.btn_manage_templates, "templates"),
        (window.btn_select_image_output_path, "choose-folder"),
        (window.btn_select_conversion_output_folder, "choose-folder"),
        (window.conversion_panel.btn_sample, "check-document"),
        (window.operation_result_panel.open_result, "open"),
        (window.operation_result_panel.open_folder, "choose-folder"),
        (window.operation_result_panel.details, "details"),
        (window.operation_result_panel.undo, "undo"),
    )
    for control, name in controls:
        control.setIcon(ui_icon(name, mode))

    for button, name in (
        (window.btn_convert, "convert"),
        (window.btn_merge, "merge"),
        (window.btn_compress, "compress"),
    ):
        button.setIcon(ui_icon(name, mode))

    for button in window.help_commands:
        button.setIcon(ui_icon(button.property("uiIcon"), mode))

    for button in window.template_params_widget.findChildren(QPushButton):
        if name := button.property("uiIcon"):
            button.setIcon(ui_icon(name, mode))
