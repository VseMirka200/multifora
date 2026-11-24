import re

_DATE_FORMAT_PATTERNS = (
    ("2024-01-15_", "%Y-%m-%d_"),
    ("15-01-2024_", "%d-%m-%Y_"),
    ("[2024-01-15]_", "[%Y-%m-%d]_"),
    ("20240115_", "%Y%m%d_"),
    ("20240115", "%Y%m%d"),
    ("15_01_2024", "%d_%m_%Y"),
    ("15-01-2024", "%d-%m-%Y"),
)


def apply_case_mode(value: str, mode: str) -> str:
    """Преобразует регистр имени без привязки к UI."""
    text = str(value or "")
    if mode == "lower":
        return text.lower()
    if mode == "upper":
        return text.upper()
    if mode == "title":
        return text.title()
    if mode == "sentence":
        return text[:1].upper() + text[1:].lower()
    if mode == "swap":
        return text.swapcase()
    return text


def regex_replace(
    value: str, pattern: str, replacement: str, *, ignore_case: bool = False
) -> str:
    """Выполняет regex-замену и оставляет сообщения об ошибках вызывающему коду."""
    flags = re.IGNORECASE if ignore_case else 0
    return re.sub(pattern, replacement, value, flags=flags)


def get_date_format(format_name: str) -> str:
    # Распознаём формат по числовому примеру в подписи.
    for example, date_format in _DATE_FORMAT_PATTERNS:
        if example in format_name:
            return date_format
    return "%Y-%m-%d"
