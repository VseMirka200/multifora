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


def apply_custom_template(
    template: str,
    name_without_ext: str,
    ext: str,
    current_num: int,
    date_str: str,
    step: int = 1,
    use_numbering: bool = True,
):
    new_name = template.replace("{name}", name_without_ext)
    new_name = new_name.replace("{date}", date_str)
    new_name = new_name.replace("{ext}", ext[1:] if ext.startswith(".") else ext)

    used_num = False
    if use_numbering:
        if "{num}" in new_name:
            num_str = f"{current_num:03d}"
            new_name = new_name.replace("{num}", num_str)
            used_num = True

        pattern = r"\{num:0?(\d+)d\}"
        match = re.search(pattern, new_name)
        if match:
            digits = int(match.group(1))
            num_str = f"{current_num:0{digits}d}"
            new_name = new_name.replace(match.group(0), num_str)
            used_num = True

        if not used_num:
            num_str = f"{current_num:03d}"
            new_name = f"{num_str}_{new_name}"

        next_num = current_num + step
    else:
        new_name = new_name.replace("{num}", "")
        new_name = re.sub(r"\{num:0?\d+d\}", "", new_name)
        next_num = current_num

    new_name += ext
    return new_name, next_num
