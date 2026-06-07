import os
import json
import time
from PyQt6.QtCore import QObject, Qt

from app.core.app_utils import _debug_log
from app.core.app_utils import _get_app_data_dir
from app.core.deps import _detect_ghostscript


def _set_checkbox_state(checkbox, checked: bool) -> None:
    """Безопасно устанавливает состояние чекбокса без генерации сигналов."""
    if checkbox is None:
        return
    try:
        checkbox.blockSignals(True)
        checkbox.setChecked(bool(checked))
    except Exception:
        return
    finally:
        try:
            checkbox.blockSignals(False)
        except Exception:
            pass


def _set_combo_current_data(combo, value) -> None:
    """Безопасно выбирает элемент в комбобоксе по `itemData`."""
    if combo is None:
        return
    try:
        idx = combo.findData(value)
        if idx < 0:
            return
        combo.blockSignals(True)
        combo.setCurrentIndex(idx)
    except Exception:
        return
    finally:
        try:
            combo.blockSignals(False)
        except Exception:
            pass


def _collect_expandable_groups_state(window) -> dict:
    states = {}
    try:
        groups = window.findChildren(QObject)
    except Exception:
        return states

    for group in groups:
        try:
            if not callable(getattr(group, "isExpanded", None)):
                continue
            title = getattr(group, "_title", "")
            if not isinstance(title, str) or not title.strip():
                continue
            states[title] = bool(group.isExpanded())
        except Exception:
            continue
    return states


def _restore_expandable_groups_state(window, states: dict) -> None:
    if not isinstance(states, dict) or not states:
        return
    try:
        groups = window.findChildren(QObject)
    except Exception:
        return

    for group in groups:
        try:
            if not callable(getattr(group, "setChecked", None)):
                continue
            title = getattr(group, "_title", "")
            if title in states:
                group.setChecked(bool(states[title]))
        except Exception:
            continue


def _collect_template_session_state(window) -> dict:
    getter = getattr(window, "get_template_session_state", None)
    if callable(getter):
        try:
            state = getter()
            if isinstance(state, dict):
                return state
        except Exception:
            pass
    return {"selected_template": "", "template_data": {}}


def _normalize_rename_history_entry(entry, *, fallback_timestamp: float | None = None) -> dict | None:
    if not isinstance(entry, dict):
        return None

    normalized = dict(entry)
    pairs = normalized.get("pairs", [])
    if not isinstance(pairs, list):
        if isinstance(pairs, tuple):
            pairs = list(pairs)
        else:
            return None

    clean_pairs = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        left, right = pair
        clean_pairs.append([str(left), str(right)])

    normalized["pairs"] = clean_pairs
    if not clean_pairs:
        return None

    try:
        normalized["timestamp"] = float(normalized.get("timestamp", fallback_timestamp or time.time()))
    except Exception:
        normalized["timestamp"] = float(fallback_timestamp or time.time())

    try:
        normalized["count"] = int(normalized.get("count", len(clean_pairs)))
    except Exception:
        normalized["count"] = len(clean_pairs)

    if "label" in normalized and normalized["label"] is not None:
        normalized["label"] = str(normalized["label"])

    return normalized


def _collect_rename_history_state(window) -> dict:
    history = []
    redo_history = []
    max_items = int(getattr(window, "_max_rename_history", 20) or 20)

    raw_history = getattr(window, "_rename_history", [])
    if isinstance(raw_history, list):
        for entry in raw_history[-max_items:]:
            normalized = _normalize_rename_history_entry(entry)
            if normalized is not None:
                history.append(normalized)

    raw_redo_history = getattr(window, "_rename_redo_history", [])
    if isinstance(raw_redo_history, list):
        for entry in raw_redo_history[-max_items:]:
            normalized = _normalize_rename_history_entry(entry)
            if normalized is not None:
                redo_history.append(normalized)

    return {
        "history": history,
        "redo_history": redo_history,
    }


def _restore_rename_history_state(window, state: dict) -> None:
    if not isinstance(state, dict):
        return

    max_items = int(getattr(window, "_max_rename_history", 20) or 20)
    restored_history = []
    restored_redo_history = []

    history = state.get("history", [])
    if isinstance(history, list):
        for entry in history[-max_items:]:
            normalized = _normalize_rename_history_entry(entry)
            if normalized is not None:
                restored_history.append(normalized)

    redo_history = state.get("redo_history", [])
    if isinstance(redo_history, list):
        for entry in redo_history[-max_items:]:
            normalized = _normalize_rename_history_entry(entry)
            if normalized is not None:
                restored_redo_history.append(normalized)

    window._rename_history = restored_history
    window._rename_redo_history = restored_redo_history


def _restore_file_list_view_state(window, state: dict) -> None:
    if not isinstance(state, dict):
        return

    try:
        sort_mode = str(state.get("sort_mode") or "").strip()
        if sort_mode and callable(getattr(window, "set_sort_mode", None)):
            window.set_sort_mode(sort_mode, notify=False)
    except Exception:
        pass

    try:
        search_query = str(state.get("search_query") or "")
        if hasattr(window, "input_search") and window.input_search is not None:
            window.input_search.blockSignals(True)
            window.input_search.setText(search_query)
            window.input_search.blockSignals(False)
    except Exception:
        pass

    try:
        selected_types = state.get("type_filters")
        if isinstance(selected_types, list) and hasattr(window, "_type_filter_actions"):
            selected_types = {str(value) for value in selected_types}
            for value, action in window._type_filter_actions.items():
                action.blockSignals(True)
                action.setChecked(value in selected_types)
                action.blockSignals(False)
    except Exception:
        pass

    try:
        selected_ext = state.get("extension_filters")
        if isinstance(selected_ext, list) and hasattr(window, "_ext_filter_actions"):
            selected_ext = {str(value) for value in selected_ext}
            for value, action in window._ext_filter_actions.items():
                action.blockSignals(True)
                action.setChecked(value in selected_ext)
                action.blockSignals(False)
    except Exception:
        pass

    try:
        if hasattr(window, "_update_type_filter_button_text"):
            window._update_type_filter_button_text()
        if hasattr(window, "_update_ext_filter_button_text"):
            window._update_ext_filter_button_text()
        if callable(getattr(window, "on_sort_changed", None)):
            window.on_sort_changed()
        elif callable(getattr(window, "update_file_list", None)):
            window.update_file_list()
    except Exception:
        pass


def get_settings_file_path() -> str:
    """Возвращает полный путь к файлу настроек (в AppData пользователя)."""
    target_dir = _get_app_data_dir()
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "multifora_settings.json")

    roaming_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    candidate_files = [
        os.path.join(roaming_dir, "python", "Multifora", "multifora_settings.json"),
        os.path.join(roaming_dir, "multifora_settings.json"),
    ]

    existing_candidates = []
    for candidate in candidate_files:
        try:
            if os.path.exists(candidate):
                existing_candidates.append(candidate)
        except Exception:
            continue

    if existing_candidates:
        try:
            newest_candidate = max(existing_candidates, key=os.path.getmtime)
            should_migrate = (not os.path.exists(target_file)) or (os.path.getmtime(newest_candidate) > os.path.getmtime(target_file))
            if should_migrate and os.path.normcase(newest_candidate) != os.path.normcase(target_file):
                with open(newest_candidate, "r", encoding="utf-8") as src:
                    migrated_data = src.read()
                with open(target_file, "w", encoding="utf-8") as dst:
                    dst.write(migrated_data)
        except Exception as e:
            _debug_log(f"Ошибка миграции файла настроек: {e}")

    return target_file


def load_settings(window) -> None:
    """Загрузка настроек из файла БЕЗ уведомлений."""
    window.windows_context_menu_enabled = False
    window.desktop_shortcut_enabled = False
    window.start_menu_shortcut_enabled = False
    window.disable_warning_dialogs = False
    window.auto_update_check_enabled = True
    window.theme_mode = "system"
    window._pending_template_session_state = None
    window._pending_settings_dialog_geometry = None
    window._pending_settings_nav_row = 0
    window._rename_history = []
    window._rename_redo_history = []
    _set_checkbox_state(getattr(window, "auto_clear_checkbox", None), False)
    _set_checkbox_state(getattr(window, "context_menu_checkbox", None), False)
    _set_checkbox_state(getattr(window, "desktop_shortcut_checkbox", None), False)
    _set_checkbox_state(getattr(window, "start_menu_shortcut_checkbox", None), False)

    _set_checkbox_state(getattr(window, "disable_warning_dialogs_checkbox", None), False)
    _set_checkbox_state(getattr(window, "auto_update_check_checkbox", None), True)

    settings_file = get_settings_file_path()
    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "custom_templates" in data:
                window.custom_templates = data["custom_templates"]

            if "rename_history" in data:
                try:
                    _restore_rename_history_state(window, data.get("rename_history"))
                except Exception:
                    pass

            if "auto_clear" in data:
                _set_checkbox_state(getattr(window, "auto_clear_checkbox", None), data["auto_clear"])

            if "disable_warning_dialogs" in data:
                window.disable_warning_dialogs = bool(data["disable_warning_dialogs"])
                _set_checkbox_state(
                    getattr(window, "disable_warning_dialogs_checkbox", None),
                    window.disable_warning_dialogs,
                )

            if "windows_context_menu" in data:
                window.windows_context_menu_enabled = data["windows_context_menu"]
                _set_checkbox_state(
                    getattr(window, "context_menu_checkbox", None),
                    window.windows_context_menu_enabled,
                )

            if "desktop_shortcut" in data:
                window.desktop_shortcut_enabled = data["desktop_shortcut"]
                _set_checkbox_state(
                    getattr(window, "desktop_shortcut_checkbox", None),
                    window.desktop_shortcut_enabled,
                )

            if "start_menu_shortcut" in data:
                window.start_menu_shortcut_enabled = data["start_menu_shortcut"]
                _set_checkbox_state(
                    getattr(window, "start_menu_shortcut_checkbox", None),
                    window.start_menu_shortcut_enabled,
                )

            if "current_tab_index" in data and hasattr(window, "tabs"):
                try:
                    idx = int(data.get("current_tab_index"))
                    if 0 <= idx < window.tabs.count():
                        window.tabs.setCurrentIndex(idx)
                except Exception:
                    pass

            if "settings_nav_current_row" in data:
                try:
                    settings_row = int(data.get("settings_nav_current_row"))
                    if settings_row >= 0:
                        window._pending_settings_nav_row = settings_row
                        if hasattr(window, "settings_nav") and window.settings_nav is not None:
                            if settings_row < window.settings_nav.count():
                                window.settings_nav.setCurrentRow(settings_row)
                except Exception:
                    pass

            if "settings_dialog_geometry" in data:
                try:
                    settings_geom_hex = data.get("settings_dialog_geometry")
                    if isinstance(settings_geom_hex, str) and settings_geom_hex:
                        window._pending_settings_dialog_geometry = settings_geom_hex
                except Exception:
                    pass

            if "operations_tab_index" in data and hasattr(window, "operations_tab_bar"):
                try:
                    idx = int(data.get("operations_tab_index"))
                    settings_idx = getattr(window, "_settings_tab_index", -1)
                    if idx == settings_idx:
                        idx = 0
                    if 0 <= idx < window.operations_tab_bar.count():
                        window.operations_tab_bar.setCurrentIndex(idx)
                        if hasattr(window, "operations_stack") and idx < window.operations_stack.count():
                            window.operations_stack.setCurrentIndex(idx)
                        window._current_operations_tab_index = idx
                except Exception:
                    pass

            if "template_session" in data:
                template_session = data.get("template_session")
                if isinstance(template_session, dict):
                    window._pending_template_session_state = template_session

            if "file_list_view_state" in data:
                try:
                    _restore_file_list_view_state(window, data.get("file_list_view_state"))
                except Exception:
                    pass

            if "window_geometry" in data:
                try:
                    geom_hex = data.get("window_geometry")
                    if isinstance(geom_hex, str) and geom_hex:
                        window.restoreGeometry(bytes.fromhex(geom_hex))
                except Exception:
                    pass

            if "expandable_groups" in data:
                try:
                    _restore_expandable_groups_state(window, data.get("expandable_groups"))
                except Exception:
                    pass

            if "auto_check_updates" in data:
                window.auto_update_check_enabled = bool(data["auto_check_updates"])
                _set_checkbox_state(
                    getattr(window, "auto_update_check_checkbox", None),
                    window.auto_update_check_enabled,
                )

            if "theme_mode" in data:
                mode = str(data.get("theme_mode") or "system").strip().lower()
                if mode not in ("system", "dark", "light"):
                    mode = "system"
                window.theme_mode = mode
                if hasattr(window, "theme_mode_combo") and window.theme_mode_combo is not None:
                    _set_combo_current_data(window.theme_mode_combo, mode)

            if "ghostscript_path" in data:
                window.ghostscript_path_override = data.get("ghostscript_path") or None
                _detect_ghostscript(window.ghostscript_path_override)

            if data.get("window_maximized"):
                try:
                    window.setWindowState(window.windowState() | Qt.WindowState.WindowMaximized)
                except Exception:
                    pass
    except Exception as e:
        _debug_log(f"Ошибка загрузки настроек: {e}")

    try:
        window.apply_theme_mode(getattr(window, "theme_mode", "system"))
    except Exception:
        pass

    window.apply_shortcut_settings(silent=True)


def save_settings(window) -> None:
    """Сохранение настроек в файл."""
    settings_file = get_settings_file_path()
    try:
        data = {
            "custom_templates": window.custom_templates,
            "auto_clear": window.auto_clear_checkbox.isChecked(),
            "windows_context_menu": window.windows_context_menu_enabled,
            "ghostscript_path": window.ghostscript_path_override,
            "desktop_shortcut": window.desktop_shortcut_enabled,
            "start_menu_shortcut": window.start_menu_shortcut_enabled,
            "disable_warning_dialogs": getattr(window, "disable_warning_dialogs", False),
            "auto_check_updates": (
                window.auto_update_check_checkbox.isChecked()
                if hasattr(window, "auto_update_check_checkbox")
                else True
            ),
            "theme_mode": getattr(window, "theme_mode", "system"),
            "current_tab_index": window.tabs.currentIndex() if hasattr(window, "tabs") else 0,
            "settings_nav_current_row": (
                window.settings_nav.currentRow()
                if hasattr(window, "settings_nav") and window.settings_nav is not None
                else 0
            ),
            "operations_tab_index": (
                window.operations_tab_bar.currentIndex()
                if hasattr(window, "operations_tab_bar") and window.operations_tab_bar is not None
                else 0
            ),
            "settings_dialog_geometry": (
                window._settings_dialog.saveGeometry().toHex().data().decode("ascii")
                if hasattr(window, "_settings_dialog") and window._settings_dialog is not None
                else None
            ),
            "template_session": _collect_template_session_state(window),
            "rename_history": _collect_rename_history_state(window),
            "file_list_view_state": {
                "sort_mode": (
                    window.get_sort_mode()
                    if callable(getattr(window, "get_sort_mode", None))
                    else ""
                ),
                "search_query": (
                    window.input_search.text()
                    if hasattr(window, "input_search") and window.input_search is not None
                    else ""
                ),
                "type_filters": sorted(
                    key for key, action in getattr(window, "_type_filter_actions", {}).items() if action.isChecked()
                ),
                "extension_filters": sorted(
                    key for key, action in getattr(window, "_ext_filter_actions", {}).items() if action.isChecked()
                ),
            },
            "window_geometry": window.saveGeometry().toHex().data().decode("ascii") if hasattr(window, "saveGeometry") else None,
            "window_maximized": bool(window.isMaximized()) if hasattr(window, "isMaximized") else False,
            "expandable_groups": _collect_expandable_groups_state(window),
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _debug_log(f"Ошибка сохранения настроек: {e}")
