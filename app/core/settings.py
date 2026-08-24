import json
import os
import time

from PyQt6.QtCore import QObject

from app.core.app_utils import _debug_log


_DEFAULT_THEME_MODE = "system"
_VALID_THEME_MODES = {_DEFAULT_THEME_MODE, "dark", "light"}
_SETTINGS_FILENAME = "multifora_settings.json"


def _log_settings_error(context: str, error: Exception) -> None:
    _debug_log(f"Ошибка {context}: {error}")


def _set_widget_value_without_signals(widget, setter, context: str) -> None:
    if widget is None:
        return

    previous_state = False
    signals_blocked = False
    try:
        previous_state = bool(widget.blockSignals(True))
        signals_blocked = True
        setter()
    except Exception as error:
        _log_settings_error(context, error)
    finally:
        if signals_blocked:
            try:
                widget.blockSignals(previous_state)
            except Exception as error:
                _log_settings_error(f"восстановления сигналов после {context}", error)


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


def _collect_expandable_groups_state(window) -> dict:
    states = {}
    try:
        groups = window.findChildren(QObject)
    except Exception as error:
        _log_settings_error("получения сворачиваемых групп", error)
        return states

    for group in groups:
        try:
            if not callable(getattr(group, "isExpanded", None)):
                continue
            title = getattr(group, "_title", "")
            if isinstance(title, str) and title.strip():
                states[title] = bool(group.isExpanded())
        except Exception as error:
            _log_settings_error("чтения состояния сворачиваемой группы", error)
    return states


def _restore_expandable_groups_state(window, states: dict) -> None:
    if not isinstance(states, dict) or not states:
        return
    try:
        groups = window.findChildren(QObject)
    except Exception as error:
        _log_settings_error("получения сворачиваемых групп", error)
        return

    for group in groups:
        try:
            if not callable(getattr(group, "setChecked", None)):
                continue
            title = getattr(group, "_title", "")
            if title in states:
                group.setChecked(bool(states[title]))
        except Exception as error:
            _log_settings_error("восстановления сворачиваемой группы", error)


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


def _normalize_rename_history_entry(
    entry,
    *,
    fallback_timestamp: float | None = None,
) -> dict | None:
    if not isinstance(entry, dict):
        return None

    normalized = dict(entry)
    pairs = normalized.get("pairs", [])
    if isinstance(pairs, tuple):
        pairs = list(pairs)
    if not isinstance(pairs, list):
        return None

    clean_pairs = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        left, right = pair
        clean_pairs.append([str(left), str(right)])

    if not clean_pairs:
        return None
    normalized["pairs"] = clean_pairs

    default_timestamp = fallback_timestamp or time.time()
    try:
        normalized["timestamp"] = float(normalized.get("timestamp", default_timestamp))
    except (TypeError, ValueError):
        normalized["timestamp"] = float(default_timestamp)

    try:
        normalized["count"] = int(normalized.get("count", len(clean_pairs)))
    except (TypeError, ValueError):
        normalized["count"] = len(clean_pairs)

    if normalized.get("label") is not None:
        normalized["label"] = str(normalized["label"])

    return normalized


def _normalized_history(entries, max_items: int) -> list[dict]:
    if not isinstance(entries, list):
        return []
    return [
        normalized
        for entry in entries[-max_items:]
        if (normalized := _normalize_rename_history_entry(entry)) is not None
    ]


def _history_limit(window) -> int:
    try:
        return int(getattr(window, "_max_rename_history", 20) or 20)
    except (TypeError, ValueError):
        return 20


def _collect_rename_history_state(window) -> dict:
    max_items = _history_limit(window)
    return {
        "history": _normalized_history(getattr(window, "_rename_history", []), max_items),
        "redo_history": _normalized_history(
            getattr(window, "_rename_redo_history", []),
            max_items,
        ),
    }


def _restore_rename_history_state(window, state: dict) -> None:
    if not isinstance(state, dict):
        return

    max_items = _history_limit(window)
    window._rename_history = _normalized_history(state.get("history", []), max_items)
    window._rename_redo_history = _normalized_history(
        state.get("redo_history", []),
        max_items,
    )


def _restore_filter_actions(actions, selected_values) -> None:
    if not isinstance(selected_values, list) or not isinstance(actions, dict):
        return
    selected = {str(value) for value in selected_values}
    for value, action in actions.items():
        _set_widget_value_without_signals(
            action,
            lambda action=action, value=value: action.setChecked(value in selected),
            "восстановления фильтра списка файлов",
        )


def _restore_file_list_view_state(window, state: dict) -> None:
    if not isinstance(state, dict):
        return

    sort_mode = str(state.get("sort_mode") or "").strip()
    set_sort_mode = getattr(window, "set_sort_mode", None)
    if sort_mode and callable(set_sort_mode):
        try:
            set_sort_mode(sort_mode, notify=False)
        except Exception as error:
            _log_settings_error("восстановления сортировки", error)

    search_input = getattr(window, "input_search", None)
    if search_input is not None:
        search_query = str(state.get("search_query") or "")
        _set_widget_value_without_signals(
            search_input,
            lambda: search_input.setText(search_query),
            "восстановления поискового запроса",
        )

    _restore_filter_actions(
        getattr(window, "_type_filter_actions", None),
        state.get("type_filters"),
    )
    _restore_filter_actions(
        getattr(window, "_ext_filter_actions", None),
        state.get("extension_filters"),
    )

    try:
        update_type_filter = getattr(window, "_update_type_filter_button_text", None)
        if callable(update_type_filter):
            update_type_filter()
        update_extension_filter = getattr(window, "_update_ext_filter_button_text", None)
        if callable(update_extension_filter):
            update_extension_filter()

        refresh_sort = getattr(window, "on_sort_changed", None)
        refresh_list = getattr(window, "update_file_list", None)
        if callable(refresh_sort):
            refresh_sort()
        elif callable(refresh_list):
            refresh_list()
    except Exception as error:
        _log_settings_error("обновления списка после загрузки фильтров", error)


def _legacy_settings_candidates() -> tuple[str, ...]:
    roaming_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    return (
        os.path.join(roaming_dir, "Multifora", _SETTINGS_FILENAME),
        os.path.join(roaming_dir, "python", "Multifora", _SETTINGS_FILENAME),
        os.path.join(roaming_dir, _SETTINGS_FILENAME),
    )


def _migrate_legacy_settings(target_file: str) -> None:
    existing_candidates = []
    for candidate in _legacy_settings_candidates():
        try:
            if os.path.exists(candidate):
                existing_candidates.append(candidate)
        except OSError as error:
            _log_settings_error(f"проверки старого файла настроек {candidate}", error)

    if not existing_candidates:
        return

    try:
        newest_candidate = max(existing_candidates, key=os.path.getmtime)
        target_exists = os.path.exists(target_file)
        target_is_older = target_exists and os.path.getmtime(newest_candidate) > os.path.getmtime(
            target_file
        )
        should_migrate = not target_exists or target_is_older
        if not should_migrate or os.path.normcase(newest_candidate) == os.path.normcase(target_file):
            return

        with open(newest_candidate, "r", encoding="utf-8") as source:
            migrated_data = source.read()
        with open(target_file, "w", encoding="utf-8") as destination:
            destination.write(migrated_data)
    except Exception as error:
        _log_settings_error("миграции файла настроек", error)


def get_settings_file_path() -> str:
    """Возвращает полный путь к файлу настроек (в Documents пользователя)."""
    target_dir = os.path.join(os.path.expanduser("~"), "Documents", "Multifora")
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, _SETTINGS_FILENAME)
    _migrate_legacy_settings(target_file)
    return target_file


def _initialize_settings_defaults(window) -> None:
    window.windows_context_menu_enabled = False
    window.desktop_shortcut_enabled = False
    window.start_menu_shortcut_enabled = False
    window.disable_warning_dialogs = False
    window.auto_update_check_enabled = True
    window.theme_mode = _DEFAULT_THEME_MODE
    window.conversion_output_mode = "source_subfolder"
    window.conversion_output_path = ""
    window._pending_template_session_state = None
    window._pending_settings_dialog_geometry = None
    window._pending_settings_nav_row = 0
    window._rename_history = []
    window._rename_redo_history = []

    checkbox_defaults = {
        "auto_clear_checkbox": False,
        "context_menu_checkbox": False,
        "desktop_shortcut_checkbox": False,
        "start_menu_shortcut_checkbox": False,
        "disable_warning_dialogs_checkbox": False,
        "auto_update_check_checkbox": True,
    }
    for attribute_name, checked in checkbox_defaults.items():
        _set_checkbox_state(getattr(window, attribute_name, None), checked)


def _restore_boolean_option(
    window,
    data: dict,
    setting_name: str,
    attribute_name: str,
    checkbox_name: str,
) -> None:
    if setting_name not in data:
        return
    value = bool(data[setting_name])
    setattr(window, attribute_name, value)
    _set_checkbox_state(getattr(window, checkbox_name, None), value)


def _restore_widget_index(widget, raw_index, context: str) -> int | None:
    if widget is None:
        return None
    try:
        index = int(raw_index)
        if 0 <= index < widget.count():
            widget.setCurrentIndex(index)
            return index
    except Exception as error:
        _log_settings_error(context, error)
    return None


def _restore_navigation_state(window, data: dict) -> None:
    if "current_tab_index" in data:
        _restore_widget_index(
            getattr(window, "tabs", None),
            data.get("current_tab_index"),
            "восстановления основной вкладки",
        )

    if "settings_nav_current_row" in data:
        try:
            settings_row = int(data.get("settings_nav_current_row"))
        except (TypeError, ValueError) as error:
            _log_settings_error("восстановления раздела настроек", error)
        else:
            if settings_row >= 0:
                window._pending_settings_nav_row = settings_row
                settings_nav = getattr(window, "settings_nav", None)
                if settings_nav is not None and settings_row < settings_nav.count():
                    settings_nav.setCurrentRow(settings_row)

    if "operations_tab_index" not in data and "operations_tab_label" not in data:
        return
    operations_tab_bar = getattr(window, "operations_tab_bar", None)
    if operations_tab_bar is None:
        return

    try:
        settings_index = getattr(window, "_settings_tab_index", -1)
        saved_label = str(data.get("operations_tab_label") or "").strip()
        index = None

        if saved_label:
            for candidate in range(operations_tab_bar.count()):
                if operations_tab_bar.tabText(candidate) == saved_label:
                    index = candidate
                    break
            if index == settings_index:
                index = 0
        elif "operations_tab_index" in data:
            legacy_index = int(data.get("operations_tab_index"))
            # До появления вкладки «Метаданные» индексы были:
            # 0 Переименование, 1 Конвертация, 2 Объединение, 3 Сжатие, 4 Настройки.
            # Сохраняем поведение старых settings.json после вставки новой вкладки.
            has_metadata_tab = any(
                operations_tab_bar.tabText(candidate) == "Метаданные"
                for candidate in range(operations_tab_bar.count())
            )
            if has_metadata_tab and legacy_index == 3:
                index = next(
                    (candidate for candidate in range(operations_tab_bar.count())
                     if operations_tab_bar.tabText(candidate) == "Сжатие"),
                    0,
                )
            elif has_metadata_tab and legacy_index == 4:
                index = 0
            else:
                index = legacy_index

        if index is None or index == settings_index or not 0 <= index < operations_tab_bar.count():
            index = 0

        operations_tab_bar.setCurrentIndex(index)
        operations_stack = getattr(window, "operations_stack", None)
        if operations_stack is not None and index < operations_stack.count():
            operations_stack.setCurrentIndex(index)
        window._current_operations_tab_index = index
    except Exception as error:
        _log_settings_error("восстановления вкладки операций", error)


def _nonempty_string(value):
    return value if isinstance(value, str) and value else None


def _restore_main_splitter_sizes(window, data: dict) -> None:
    raw_sizes = data.get("main_splitter_sizes")
    splitter = getattr(window, "main_splitter", None)
    if splitter is None or not isinstance(raw_sizes, (list, tuple)) or len(raw_sizes) != 2:
        return
    try:
        sizes = [max(1, int(raw_sizes[0])), max(1, int(raw_sizes[1]))]
        splitter.setSizes(sizes)
    except (TypeError, ValueError) as error:
        _log_settings_error("восстановления ширины панелей", error)


def _restore_pending_state(window, data: dict) -> None:
    settings_geometry = _nonempty_string(data.get("settings_dialog_geometry"))
    if settings_geometry:
        window._pending_settings_dialog_geometry = settings_geometry

    template_session = data.get("template_session")
    if isinstance(template_session, dict):
        window._pending_template_session_state = template_session

    window_geometry = _nonempty_string(data.get("window_geometry"))
    if window_geometry:
        window._pending_window_geometry = window_geometry

    if "window_pos" in data:
        window._pending_window_pos = data.get("window_pos")
    if "window_size" in data:
        window._pending_window_size = data.get("window_size")
    if data.get("window_maximized"):
        window._pending_window_maximized = True


def _restore_theme(window, data: dict) -> None:
    if "theme_mode" not in data:
        return
    theme_mode = str(data.get("theme_mode") or _DEFAULT_THEME_MODE).strip().lower()
    if theme_mode not in _VALID_THEME_MODES:
        theme_mode = _DEFAULT_THEME_MODE
    window.theme_mode = theme_mode
    _set_combo_current_data(getattr(window, "theme_mode_combo", None), theme_mode)


def _restore_conversion_output_settings(window, data: dict) -> None:
    # Место сохранения выбирается перед конвертацией. Запоминаем только последнюю
    # пользовательскую папку, чтобы следующий диалог открывался в том же месте.
    path = str(data.get("conversion_output_path") or "").strip()
    window.conversion_output_mode = "source_subfolder"
    window.conversion_output_path = path


def _apply_settings_data(window, data: dict) -> None:
    if "custom_templates" in data:
        window.custom_templates = data["custom_templates"]
    if "rename_history" in data:
        _restore_rename_history_state(window, data.get("rename_history"))
    if "auto_clear" in data:
        _set_checkbox_state(getattr(window, "auto_clear_checkbox", None), data["auto_clear"])

    boolean_options = (
        (
            "disable_warning_dialogs",
            "disable_warning_dialogs",
            "disable_warning_dialogs_checkbox",
        ),
        ("windows_context_menu", "windows_context_menu_enabled", "context_menu_checkbox"),
        ("desktop_shortcut", "desktop_shortcut_enabled", "desktop_shortcut_checkbox"),
        ("start_menu_shortcut", "start_menu_shortcut_enabled", "start_menu_shortcut_checkbox"),
        ("auto_check_updates", "auto_update_check_enabled", "auto_update_check_checkbox"),
    )
    for setting_name, attribute_name, checkbox_name in boolean_options:
        _restore_boolean_option(
            window,
            data,
            setting_name,
            attribute_name,
            checkbox_name,
        )

    _restore_navigation_state(window, data)
    _restore_main_splitter_sizes(window, data)
    _restore_pending_state(window, data)

    if "file_list_view_state" in data:
        _restore_file_list_view_state(window, data.get("file_list_view_state"))
    if "expandable_groups" in data:
        _restore_expandable_groups_state(window, data.get("expandable_groups"))

    _restore_conversion_output_settings(window, data)
    _restore_theme(window, data)

    if "ghostscript_path" in data:
        # На старте только восстанавливаем настройку. Проверка Ghostscript
        # выполняется лениво непосредственно перед PDF-операцией.
        window.ghostscript_path_override = data.get("ghostscript_path") or None


def load_settings(window) -> None:
    """Загрузка настроек из файла БЕЗ уведомлений."""
    _initialize_settings_defaults(window)
    settings_file = get_settings_file_path()

    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r", encoding="utf-8") as settings_stream:
                data = json.load(settings_stream)
            if not isinstance(data, dict):
                raise ValueError("корневое значение файла настроек должно быть объектом")
            _apply_settings_data(window, data)
    except Exception as error:
        _log_settings_error("загрузки настроек", error)

    apply_theme = getattr(window, "apply_theme_mode", None)
    if callable(apply_theme):
        try:
            apply_theme(getattr(window, "theme_mode", _DEFAULT_THEME_MODE))
        except Exception as error:
            _log_settings_error("применения темы", error)

    window.apply_shortcut_settings(silent=True)


def _resolve_saved_geometry(window):
    is_maximized = bool(window.isMaximized()) if hasattr(window, "isMaximized") else False
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
        saved_size = [int(geometry_source.width()), int(geometry_source.height())]
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


def _current_widget_index(window, attribute_name: str, default: int = 0) -> int:
    widget = getattr(window, attribute_name, None)
    if widget is None:
        return default
    return int(widget.currentIndex())


def _collect_file_list_view_state(window) -> dict:
    get_sort_mode = getattr(window, "get_sort_mode", None)
    search_input = getattr(window, "input_search", None)
    return {
        "sort_mode": get_sort_mode() if callable(get_sort_mode) else "",
        "search_query": search_input.text() if search_input is not None else "",
        "type_filters": sorted(
            key
            for key, action in getattr(window, "_type_filter_actions", {}).items()
            if action.isChecked()
        ),
        "extension_filters": sorted(
            key
            for key, action in getattr(window, "_ext_filter_actions", {}).items()
            if action.isChecked()
        ),
    }


def _encoded_geometry(widget):
    if widget is None or not callable(getattr(widget, "saveGeometry", None)):
        return None
    return widget.saveGeometry().toHex().data().decode("ascii")


def _collect_settings_data(window) -> dict:
    is_maximized, saved_position, saved_size = _resolve_saved_geometry(window)
    settings_nav = getattr(window, "settings_nav", None)
    auto_update_checkbox = getattr(window, "auto_update_check_checkbox", None)

    return {
        "custom_templates": window.custom_templates,
        "auto_clear": window.auto_clear_checkbox.isChecked(),
        "windows_context_menu": window.windows_context_menu_enabled,
        "ghostscript_path": window.ghostscript_path_override,
        "desktop_shortcut": window.desktop_shortcut_enabled,
        "start_menu_shortcut": window.start_menu_shortcut_enabled,
        "disable_warning_dialogs": getattr(window, "disable_warning_dialogs", False),
        "auto_check_updates": (
            auto_update_checkbox.isChecked() if auto_update_checkbox is not None else True
        ),
        "theme_mode": getattr(window, "theme_mode", _DEFAULT_THEME_MODE),
        "conversion_output_mode": getattr(window, "conversion_output_mode", "source_subfolder"),
        "conversion_output_path": getattr(window, "conversion_output_path", ""),
        "current_tab_index": _current_widget_index(window, "tabs"),
        "settings_nav_current_row": settings_nav.currentRow() if settings_nav is not None else 0,
        "operations_tab_index": _current_widget_index(window, "operations_tab_bar"),
        "main_splitter_sizes": (
            [int(value) for value in window.main_splitter.sizes()]
            if getattr(window, "main_splitter", None) is not None
            else None
        ),
        "operations_tab_label": (
            window.operations_tab_bar.tabText(window.operations_tab_bar.currentIndex())
            if getattr(window, "operations_tab_bar", None) is not None
            and window.operations_tab_bar.currentIndex() >= 0
            else ""
        ),
        "settings_dialog_geometry": _encoded_geometry(getattr(window, "_settings_dialog", None)),
        "template_session": _collect_template_session_state(window),
        "rename_history": _collect_rename_history_state(window),
        "file_list_view_state": _collect_file_list_view_state(window),
        "window_geometry": _encoded_geometry(window),
        "window_pos": saved_position,
        "window_size": saved_size,
        "window_maximized": is_maximized,
        "expandable_groups": _collect_expandable_groups_state(window),
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
        data = _collect_settings_data(window)
        with open(settings_file, "w", encoding="utf-8") as settings_stream:
            json.dump(data, settings_stream, ensure_ascii=False, indent=2)
    except Exception as error:
        _log_settings_error("сохранения настроек", error)
