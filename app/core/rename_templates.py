import re


def get_date_format(format_name: str) -> str:
    # Опираемся на числовые примеры в тексте, чтобы корректно работать
    # с уже сохраненными шаблонами независимо от возможной порчи кодировки.
    if "2024-01-15_" in format_name:
        return "%Y-%m-%d_"
    if "15-01-2024_" in format_name:
        return "%d-%m-%Y_"
    if "[2024-01-15]_" in format_name:
        return "[%Y-%m-%d]_"
    if "20240115_" in format_name:
        return "%Y%m%d_"
    if "20240115" in format_name:
        return "%Y%m%d"
    if "15_01_2024" in format_name:
        return "%d_%m_%Y"
    if "15-01-2024" in format_name:
        return "%d-%m-%Y"
    return "%Y-%m-%d"


_CUSTOM_NUM_TOKEN_RE = re.compile(r"\{num([^}]*)\}")


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
    spec = str(match.group(1) or "").strip()
    if not spec:
        return settings

    for part in (chunk.strip() for chunk in spec.split(",")):
        if not part:
            continue
        if part.startswith(":"):
            width_match = re.search(r"0?(\d+)d", part[1:])
            if width_match:
                settings["digits"] = max(1, int(width_match.group(1)))
            continue
        if part.startswith("fmt="):
            fmt_value = part.split("=", 1)[1].strip()
            width_match = re.search(r"0?(\d+)d", fmt_value)
            if width_match:
                settings["digits"] = max(1, int(width_match.group(1)))
            continue
        if part.startswith("digits=") or part.startswith("width="):
            value = part.split("=", 1)[1].strip()
            if value.isdigit():
                settings["digits"] = max(1, int(value))
            continue
        if part.startswith("start="):
            value = part.split("=", 1)[1].strip()
            if value.isdigit():
                settings["start"] = max(1, int(value))
            continue
        if part.startswith("step="):
            value = part.split("=", 1)[1].strip()
            if value.isdigit():
                settings["step"] = max(1, int(value))
            continue
        width_match = re.fullmatch(r"0?(\d+)d", part)
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

    used_num = False
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
        num_str = f"{current_num:0{token_digits}d}"
        if num_token_match:
            new_name = _CUSTOM_NUM_TOKEN_RE.sub(num_str, new_name)
            used_num = True

        if not used_num:
            num_str = f"{current_num:0{num_digits}d}"
            new_name = f"{num_str}_{new_name}"

        next_num = current_num + step
    else:
        new_name = _CUSTOM_NUM_TOKEN_RE.sub("", new_name)
        next_num = current_num

    new_name += ext
    return new_name, next_num
