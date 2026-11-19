from PySide6.QtCore import Qt

from app.core.app_utils import signals_blocked
from app.core.settings_storage import get_settings_file_path as get_settings_file_path
from app.core.settings_storage import log_settings_error as _log_settings_error
from app.core.settings_storage import read_settings, write_settings
from app.core.settings_values import DEFAULT_THEME_MODE, SavedSettings, normalize_settings

_AUTO_CLEAR_CHECKBOXES = {
    "rename": "auto_clear_rename_checkbox",
    "convert": "auto_clear_convert_checkbox",
    "merge": "auto_clear_merge_checkbox",
    "compress": "auto_clear_compress_checkbox",
}


def _set_widget_value_without_signals(widget, setter, context: str) -> None:
    if widget is None:
        return

    try:
        with signals_blocked(widget):
            try:
                setter()
            except Exception as error:
                _log_settings_error(context, error)
    except Exception as error:
        _log_settings_error(
            f"блокировки или восстановления сигналов при {context}", error
        )


def _set_checkbox_state(checkbox, checked: bool) -> None:
    """Безопасно устанавливает состояние чекбокса без генерации сигналов."""
    _set_widget_value_without_signals(
        checkbox,
        lambda: checkbox.setChecked(bool(checked)),
        "установки состояния флажка",
    )


def _set_combo_current_data(combo, value) -> None:
    """Безопасно выбирает элемент в комбобоксе по `itemData`."""
    if combo is None:
        return
    try:
        index = combo.findData(value)
    except Exception as error:
        _log_settings_error("поиска значения в списке", error)
        return
    if index < 0:
        return

    _set_widget_value_without_signals(
        combo,
        lambda: combo.setCurrentIndex(index),
        "выбора значения в списке",
    )


def _collect_template_session_state(window) -> dict:
    getter = getattr(window, "get_template_session_state", None)
    if callable(getter):
        try:
            state = getter()
            if isinstance(state, dict):
                return state
        except Exception as error:
            _log_settings_error("сохранения состояния шаблона", error)
    return {"selected_template": "", "template_data": {}}


def _restore_file_list_view_state(window, section: int | None, descending: bool) -> None:
    if section is None:
        return
    try:
        order = (
            Qt.SortOrder.DescendingOrder
            if descending
            else Qt.SortOrder.AscendingOrder
        )
        window._column_sort_section = section
        window._column_sort_order = order
        file_list = getattr(window, "list_files", None)
        if (
            file_list is not None
            and 0 <= section < file_list.model().columnCount()
        ):
            header = file_list.horizontalHeader()
            header.setSortIndicator(section, order)
            header.setSortIndicatorShown(True)
            file_list.set_manual_sorting(True)
    except Exception as error:
        _log_settings_error("восстановления сортировки таблицы", error)


def _initialize_settings_defaults(window) -> None:
    window.windows_context_menu_enabled = False
    window.desktop_shortcut_enabled = False
    window.start_menu_shortcut_enabled = False
    window.disable_warning_dialogs = False
    window.theme_mode = DEFAULT_THEME_MODE
    window.conversion_output_mode = "ask"
    window.conversion_output_path = ""
    window.image_compression_output_mode = "alongside"
    window.image_compression_output_path = ""
    window._pending_template_session_state = None
    window._rename_history = []

    checkbox_defaults = {
        "context_menu_checkbox": False,
        "desktop_shortcut_checkbox": False,
        "start_menu_shortcut_checkbox": False,
        "disable_warning_dialogs_checkbox": False,
        "auto_update_check_checkbox": False,
        "auto_clear_enabled_checkbox": False,
    }
    for attribute_name, checked in checkbox_defaults.items():
        _set_checkbox_state(getattr(window, attribute_name, None), checked)
    for attribute_name in _AUTO_CLEAR_CHECKBOXES.values():
        _set_checkbox_state(
            getattr(window, attribute_name, None),
            False,
        )


def _find_tab_index(tab_bar, label: str) -> int | None:
    normalized_label = label.casefold()
    return next(
        (
            index
            for index in range(tab_bar.count())
            if normalized_label in {tab_bar.tabText(index).casefold(), str(tab_bar.tabData(index) or "").casefold()}
        ),
        None,
    )


def _restore_operations_tab_state(window, label: str, index: int | None) -> None:
    if not label and index is None:
        return
    operations_tab_bar = getattr(window, "operations_tab_bar", None)
    if operations_tab_bar is None:
        return

    try:
        settings_index = getattr(window, "_settings_tab_index", -1)
        if label:
            index = _find_tab_index(operations_tab_bar, label)

        if (
            index is None
            or index == settings_index
            or not 0 <= index < operations_tab_bar.count()
        ):
            index = 0

        operations_tab_bar.setCurrentIndex(index)
        operations_stack = getattr(window, "operations_stack", None)
        if operations_stack is not None and index < operations_stack.count():
            operations_stack.setCurrentIndex(index)
    except Exception as error:
        _log_settings_error("восстановления вкладки операций", error)


def _restore_window_state(window, values: SavedSettings) -> None:
    splitter = getattr(window, "main_splitter", None)
    if splitter is not None and values.main_splitter_sizes is not None:
        splitter.setSizes(list(values.main_splitter_sizes))
    window._pending_template_session_state = values.template_session
    window._pending_window_geometry = values.window_geometry
    window._pending_window_pos = values.window_pos
    window._pending_window_size = values.window_size
    window._pending_window_maximized = values.window_maximized


def _restore_conversion_output_settings(window, mode: str, path: str) -> None:
    window.conversion_output_mode = mode
    window.conversion_output_path = path

    combo = getattr(window, "combo_conversion_output_mode", None)
    if combo is not None:
        _set_combo_current_data(combo, mode)
    path_field = getattr(window, "input_conversion_output_path", None)
    if path_field is not None:
        _set_widget_value_without_signals(
            path_field,
            lambda: path_field.setText(path),
            "восстановления папки конвертации",
        )
    inline_updater = getattr(
        window, "_update_inline_conversion_output_controls", None
    )
    if callable(inline_updater):
        inline_updater()


def _restore_image_compression_output_settings(window, mode: str, path: str) -> None:
    window.image_compression_output_mode = mode
    window.image_compression_output_path = path

    combo = getattr(window, "combo_image_output_mode", None)
    if combo is not None:
        index = combo.findData(mode)
        if index >= 0:
            with signals_blocked(combo):
                combo.setCurrentIndex(index)
    path_field = getattr(window, "input_image_output_path", None)
    if path_field is not None:
        path_field.setText(path)
    updater = getattr(window, "on_image_output_mode_changed", None)
    if callable(updater):
        updater()


def _apply_settings_data(window, data: dict) -> None:
    _apply_settings(window, normalize_settings(data))


def _apply_settings(window, values: SavedSettings) -> None:
    if values.custom_templates is not None:
        window.custom_templates = values.custom_templates

    for operation, checkbox_name in _AUTO_CLEAR_CHECKBOXES.items():
        _set_checkbox_state(getattr(window, checkbox_name, None), values.auto_clear_by_operation[operation])
    _set_checkbox_state(getattr(window, "auto_clear_enabled_checkbox", None), values.auto_clear_enabled)
    for value, attribute, checkbox in (
        (values.disable_warning_dialogs, "disable_warning_dialogs", "disable_warning_dialogs_checkbox"),
        (values.windows_context_menu, "windows_context_menu_enabled", "context_menu_checkbox"),
        (values.desktop_shortcut, "desktop_shortcut_enabled", "desktop_shortcut_checkbox"),
        (values.start_menu_shortcut, "start_menu_shortcut_enabled", "start_menu_shortcut_checkbox"),
    ):
        setattr(window, attribute, value)
        _set_checkbox_state(getattr(window, checkbox, None), value)
    _set_checkbox_state(getattr(window, "auto_update_check_checkbox", None), values.auto_check_updates)

    sync_auto_clear_controls = getattr(window, "_sync_auto_clear_controls", None)
    if callable(sync_auto_clear_controls):
        sync_auto_clear_controls()

    _restore_operations_tab_state(window, values.operations_tab_label, values.operations_tab_index)
    _restore_window_state(window, values)
    _restore_file_list_view_state(window, values.sort_column, values.sort_descending)
    _restore_conversion_output_settings(window, values.conversion_output_mode, values.conversion_output_path)
    _restore_image_compression_output_settings(
        window, values.image_compression_output_mode, values.image_compression_output_path
    )
    window.theme_mode = values.theme_mode
    _set_combo_current_data(getattr(window, "theme_mode_combo", None), values.theme_mode)


def load_settings(window) -> None:
    """Загрузка настроек из файла БЕЗ уведомлений."""
    _initialize_settings_defaults(window)
    settings_file = get_settings_file_path()

    try:
        data = read_settings(settings_file)
        if data is not None:
            _apply_settings_data(window, data)
    except Exception as error:
        _log_settings_error("загрузки настроек", error)

    apply_theme = getattr(window, "apply_theme_mode", None)
    if callable(apply_theme):
        try:
            apply_theme(getattr(window, "theme_mode", DEFAULT_THEME_MODE))
        except Exception as error:
            _log_settings_error("применения темы", error)



def _resolve_saved_geometry(window):
    is_maximized = (
        bool(window.isMaximized()) if hasattr(window, "isMaximized") else False
    )
    geometry_source = None

    geometry_getters = []
    if is_maximized:
        geometry_getters.append(getattr(window, "normalGeometry", None))
    geometry_getters.append(getattr(window, "geometry", None))

    for getter in geometry_getters:
        if not callable(getter):
            continue
        try:
            geometry_source = getter()
        except Exception as error:
            _log_settings_error("получения геометрии окна", error)
        if geometry_source is not None:
            break

    if geometry_source is not None:
        saved_position = [int(geometry_source.x()), int(geometry_source.y())]
        saved_size = [
            int(geometry_source.width()),
            int(geometry_source.height()),
        ]
        return is_maximized, saved_position, saved_size

    saved_position = None
    saved_size = None
    position_getter = getattr(window, "pos", None)
    size_getter = getattr(window, "size", None)
    if callable(position_getter):
        position = position_getter()
        saved_position = [position.x(), position.y()]
    if callable(size_getter):
        size = size_getter()
        saved_size = [size.width(), size.height()]
    return is_maximized, saved_position, saved_size


def _current_widget_index(
    window, attribute_name: str, default: int = 0
) -> int:
    widget = getattr(window, attribute_name, None)
    if widget is None:
        return default
    return int(widget.currentIndex())


def _collect_file_list_view_state(window) -> dict:
    order = getattr(window, "_column_sort_order", Qt.SortOrder.AscendingOrder)
    return {
        "sort_column": getattr(window, "_column_sort_section", None),
        "sort_order": (
            "descending"
            if order == Qt.SortOrder.DescendingOrder
            else "ascending"
        ),
    }


def _encoded_geometry(widget):
    if widget is None or not callable(getattr(widget, "saveGeometry", None)):
        return None
    return widget.saveGeometry().toHex().data().decode("ascii")


def _collect_settings_data(window) -> dict:
    is_maximized, saved_position, saved_size = _resolve_saved_geometry(window)
    auto_update_checkbox = getattr(window, "auto_update_check_checkbox", None)
    tab_bar = getattr(window, "operations_tab_bar", None)
    tab_index = _current_widget_index(window, "operations_tab_bar")
    if tab_index is not None and tab_index == getattr(window, "_settings_tab_index", None):
        tab_index = _current_widget_index(window, "operations_stack")
    valid_tab = tab_bar is not None and tab_index is not None and tab_index >= 0

    return {
        "custom_templates": window.custom_templates,
        "auto_clear_enabled": bool(
            getattr(window, "auto_clear_enabled_checkbox", None)
            and window.auto_clear_enabled_checkbox.isChecked()
        ),
        "auto_clear_by_operation": {
            operation: bool(
                getattr(window, attribute_name, None)
                and getattr(window, attribute_name).isChecked()
            )
            for operation, attribute_name in _AUTO_CLEAR_CHECKBOXES.items()
        },
        "windows_context_menu": window.windows_context_menu_enabled,
        "desktop_shortcut": window.desktop_shortcut_enabled,
        "start_menu_shortcut": window.start_menu_shortcut_enabled,
        "disable_warning_dialogs": getattr(
            window, "disable_warning_dialogs", False
        ),
        "auto_check_updates": (
            auto_update_checkbox.isChecked()
            if auto_update_checkbox is not None
            else False
        ),
        "theme_mode": getattr(window, "theme_mode", DEFAULT_THEME_MODE),
        "conversion_output_mode": getattr(
            window, "conversion_output_mode", "ask"
        ),
        "conversion_output_path": getattr(
            window, "conversion_output_path", ""
        ),
        "image_compression_output_mode": getattr(
            window, "image_compression_output_mode", "alongside"
        ),
        "image_compression_output_path": getattr(
            window, "image_compression_output_path", ""
        ),
        "operations_tab_index": tab_index,
        "main_splitter_sizes": (
            [int(value) for value in window.main_splitter.sizes()]
            if getattr(window, "main_splitter", None) is not None
            else None
        ),
        "operations_tab_label": tab_bar.tabText(tab_index) if valid_tab else "",
        "operations_tab_id": tab_bar.tabData(tab_index) if valid_tab else None,
        "template_session": _collect_template_session_state(window),
        "file_list_view_state": _collect_file_list_view_state(window),
        "window_geometry": _encoded_geometry(window),
        "window_pos": saved_position,
        "window_size": saved_size,
        "window_maximized": is_maximized,
    }


def save_settings(window) -> None:
    """Сохранение настроек в файл."""
    if not getattr(window, "initial_load_complete", False) and not getattr(
        window,
        "_force_settings_save",
        False,
    ):
        return

    settings_file = get_settings_file_path()
    try:
        write_settings(settings_file, _collect_settings_data(window))
    except Exception as error:
        _log_settings_error("сохранения настроек", error)
