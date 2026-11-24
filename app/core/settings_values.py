"""Нормализация сохранённых настроек без обращения к виджетам и файлам."""

from dataclasses import dataclass

DEFAULT_THEME_MODE = "system"
CONVERSION_OUTPUT_MODES = frozenset({"ask", "alongside", "source_subfolder", "custom"})
IMAGE_OUTPUT_MODES = frozenset({"replace", "alongside", "custom"})
AUTO_CLEAR_OPERATIONS = ("rename", "convert", "merge", "compress")
_LEGACY_TAB_LABELS = {0: "Переименование", 1: "Конвертация", 2: "Объединение", 3: "Сжатие"}


@dataclass(frozen=True, slots=True)
class SavedSettings:
    auto_clear_enabled: bool
    auto_clear_by_operation: dict[str, bool]
    disable_warning_dialogs: bool
    windows_context_menu: bool
    desktop_shortcut: bool
    start_menu_shortcut: bool
    auto_check_updates: bool
    theme_mode: str
    conversion_output_mode: str
    conversion_output_path: str
    image_compression_output_mode: str
    image_compression_output_path: str
    operations_tab_label: str
    operations_tab_index: int | None
    main_splitter_sizes: tuple[int, int] | None
    template_session: dict | None
    sort_column: int | None
    sort_descending: bool
    window_geometry: str | None
    window_pos: tuple[int, int] | None
    window_size: tuple[int, int] | None
    window_maximized: bool


def _integer(value: object) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    # PySide принимает эти координаты и размеры как знаковые int.
    return number if -(2**31) <= number < 2**31 else None


def _integer_pair(value: object) -> tuple[int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    first, second = map(_integer, value)
    return (first, second) if first is not None and second is not None else None


def _mapping(value: object) -> dict | None:
    return value if isinstance(value, dict) else None


def normalize_settings(data: dict) -> SavedSettings:
    """Читает текущие и прежние ключи JSON, заменяя повреждённые поля значениями по умолчанию."""
    operation_values = _mapping(data.get("auto_clear_by_operation"))
    legacy_auto_clear = bool(data.get("auto_clear"))
    if operation_values is None:
        auto_clear_by_operation = dict.fromkeys(AUTO_CLEAR_OPERATIONS, legacy_auto_clear)
        auto_clear_enabled = legacy_auto_clear
    else:
        auto_clear_by_operation = {key: bool(operation_values.get(key)) for key in AUTO_CLEAR_OPERATIONS}
        auto_clear_enabled = any(operation_values.values())

    tab_id = data.get("operations_tab_id")
    tab_label = tab_id if tab_id in ("home", "rename", "convert", "compress", "merge") else (
        str(data.get("operations_tab_label") or "").strip()
    )
    tab_index = _integer(data.get("operations_tab_index")) if not tab_label else None
    if not tab_label:
        tab_label = _LEGACY_TAB_LABELS.get(tab_index, "")
        if tab_label or tab_index == 4 or (tab_index is None and "operations_tab_label" in data):
            tab_index = 0

    theme = str(data.get("theme_mode") or DEFAULT_THEME_MODE).strip().lower()
    conversion_mode = str(data.get("conversion_output_mode") or "").strip()
    compression_mode = str(data.get("image_compression_output_mode") or "").strip()
    splitter = _integer_pair(data.get("main_splitter_sizes"))
    size = _integer_pair(data.get("window_size"))
    encoded_geometry = data.get("window_geometry")
    sort = _mapping(data.get("file_list_view_state")) or {}
    return SavedSettings(
        auto_clear_enabled=bool(data.get("auto_clear_enabled", auto_clear_enabled)),
        auto_clear_by_operation=auto_clear_by_operation,
        disable_warning_dialogs=bool(data.get("disable_warning_dialogs")),
        windows_context_menu=bool(data.get("windows_context_menu")),
        desktop_shortcut=bool(data.get("desktop_shortcut")),
        start_menu_shortcut=bool(data.get("start_menu_shortcut")),
        auto_check_updates=bool(data.get("auto_check_updates")),
        theme_mode=theme if theme in {DEFAULT_THEME_MODE, "dark", "light"} else DEFAULT_THEME_MODE,
        conversion_output_mode=conversion_mode if conversion_mode in CONVERSION_OUTPUT_MODES else "ask",
        conversion_output_path=str(data.get("conversion_output_path") or "").strip(),
        image_compression_output_mode=compression_mode if compression_mode in IMAGE_OUTPUT_MODES else "alongside",
        image_compression_output_path=str(data.get("image_compression_output_path") or "").strip(),
        operations_tab_label=tab_label,
        operations_tab_index=tab_index,
        main_splitter_sizes=(max(1, splitter[0]), max(1, splitter[1])) if splitter is not None else None,
        template_session=_mapping(data.get("template_session")),
        sort_column=_integer(sort.get("sort_column")),
        sort_descending=sort.get("sort_order") == "descending",
        window_geometry=encoded_geometry if isinstance(encoded_geometry, str) and encoded_geometry else None,
        window_pos=_integer_pair(data.get("window_pos")),
        window_size=size if size is not None and min(size) > 0 else None,
        window_maximized=bool(data.get("window_maximized")),
    )
