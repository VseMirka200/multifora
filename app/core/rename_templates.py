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
_CUSTOM_NUM_TOKEN_RE = re.compile(r"\{num([^}]*)\}")
_WIDTH_FORMAT_RE = re.compile(r"0?(\d+)d")


def get_date_format(format_name: str) -> str:
    # Числовые примеры остаются стабильными даже для старых шаблонов с повреждённым текстом.
    for example, date_format in _DATE_FORMAT_PATTERNS:
        if example in format_name:
            return date_format
    return "%Y-%m-%d"


def _positive_int(value: str):
    value = value.strip()
    return max(1, int(value)) if value.isdigit() else None


def _format_width(value: str):
    match = _WIDTH_FORMAT_RE.search(value.strip())
    return max(1, int(match.group(1))) if match else None


def parse_custom_template_settings(template: str) -> dict[str, int | bool]:
    settings: dict[str, int | bool] = {
        "start": 1,
        "step": 1,
        "digits": 3,
        "use_numbering": False,
    }

    match = _CUSTOM_NUM_TOKEN_RE.search(str(template or ""))
    if not match:
        return settings

    settings["use_numbering"] = True
    specification = str(match.group(1) or "").strip()
    if not specification:
        return settings

    for part in (chunk.strip() for chunk in specification.split(",")):
        if not part:
            continue

        if part.startswith(":"):
            width = _format_width(part[1:])
            if width is not None:
                settings["digits"] = width
            continue

        if "=" in part:
            key, value = (segment.strip() for segment in part.split("=", 1))
            if key == "fmt":
                width = _format_width(value)
                if width is not None:
                    settings["digits"] = width
            elif key in {"digits", "width", "start", "step"}:
                parsed_value = _positive_int(value)
                if parsed_value is not None:
                    target_key = "digits" if key == "width" else key
                    settings[target_key] = parsed_value
            continue

        width_match = re.fullmatch(_WIDTH_FORMAT_RE, part)
        if width_match:
            settings["digits"] = max(1, int(width_match.group(1)))

    return settings


def apply_custom_template(
    template: str,
    name_without_ext: str,
    ext: str,
    current_num: int,
    date_str: str,
    step: int = 1,
    use_numbering: bool = True,
    num_digits: int = 3,
):
    new_name = template.replace("{name}", name_without_ext)
    new_name = new_name.replace("{date}", date_str)
    new_name = new_name.replace("{ext}", ext[1:] if ext.startswith(".") else ext)

    if use_numbering:
        num_token_match = _CUSTOM_NUM_TOKEN_RE.search(new_name)
        token_digits = num_digits
        if num_token_match:
            token_spec = str(num_token_match.group(1) or "").strip()
            has_explicit_digits = bool(
                re.search(r"(^|,)\s*(?::|fmt=|digits=|width=|\d+d)", token_spec)
            )
            if has_explicit_digits:
                token_settings = parse_custom_template_settings(num_token_match.group(0))
                token_digits = int(token_settings.get("digits", num_digits))

        number = f"{current_num:0{token_digits}d}"
        if num_token_match:
            new_name = _CUSTOM_NUM_TOKEN_RE.sub(number, new_name)
        else:
            new_name = f"{current_num:0{num_digits}d}_{new_name}"
        next_num = current_num + step
    else:
        new_name = _CUSTOM_NUM_TOKEN_RE.sub("", new_name)
        next_num = current_num

    return new_name + ext, next_num
