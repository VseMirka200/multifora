from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass


_INVALID_WINDOWS_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


@dataclass(frozen=True)
class RenamePlanIssue:
    kind: str
    source: str
    target: str
    message: str
    blocking: bool = False


def _windows_name_error(name: str) -> str:
    if not name or name in {".", ".."}:
        return "пустое или служебное имя"
    if _INVALID_WINDOWS_CHARS_RE.search(name):
        return "имя содержит запрещённые Windows символы"
    if name.endswith((" ", ".")):
        return "имя оканчивается пробелом или точкой"
    if len(name) > 255:
        return "имя длиннее 255 символов"
    stem = name.split(".", 1)[0].rstrip(" .").upper()
    if stem in _RESERVED_WINDOWS_NAMES:
        return "имя зарезервировано Windows"
    return ""


def analyze_rename_plan(file_items, new_names: list[str]) -> list[RenamePlanIssue]:
    """Проверяет пакетное переименование до изменения файлов на диске."""
    pairs = list(zip(file_items, new_names))
    normalized_targets = [
        os.path.normcase(os.path.abspath(os.path.join(item.folder, str(name))))
        for item, name in pairs
    ]
    target_counts = Counter(target.casefold() for target in normalized_targets)
    source_paths = {
        os.path.normcase(os.path.abspath(str(getattr(item, "path", "")))).casefold()
        for item, _name in pairs
    }

    issues: list[RenamePlanIssue] = []
    for (item, raw_name), normalized_target in zip(pairs, normalized_targets):
        name = str(raw_name or "")
        source = str(getattr(item, "path", ""))
        target = os.path.join(str(getattr(item, "folder", "")), name)
        name_error = _windows_name_error(name)
        if name_error:
            issues.append(RenamePlanIssue("invalid_name", source, target, name_error, True))
            continue

        target_key = normalized_target.casefold()
        if target_counts[target_key] > 1:
            issues.append(
                RenamePlanIssue(
                    "duplicate_target",
                    source,
                    target,
                    "несколько файлов получат одинаковое имя",
                )
            )
        if target_key != os.path.normcase(os.path.abspath(source)).casefold() and os.path.exists(target):
            message = (
                "целевое имя занято другим файлом из пакета"
                if target_key in source_paths
                else "целевой файл уже существует"
            )
            issues.append(RenamePlanIssue("existing_target", source, target, message))
    return issues


def format_rename_plan_issues(issues: list[RenamePlanIssue], limit: int = 5) -> str:
    if not issues:
        return "Конфликты не обнаружены."
    lines = [f"Обнаружено конфликтов: {len(issues)}."]
    for issue in issues[: max(0, limit)]:
        lines.append(f"• {os.path.basename(issue.target)} — {issue.message}")
    remaining = len(issues) - max(0, limit)
    if remaining > 0:
        lines.append(f"• …и ещё {remaining}")
    return "\n".join(lines)
