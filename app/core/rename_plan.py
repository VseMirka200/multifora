"""Единый расчёт реальных имён для предпросмотра и рабочего потока.

Никогда не заменяет существующие файлы. Зависимые переименования (A↔B)
выполняются рабочим потоком через временные имена.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Sequence

from app.core.rename_validation import _windows_name_error


def path_key(path: str) -> str:
    # NTFS обрабатывает имена без учёта регистра; такая же проверка нужна в тестах на Unix.
    return os.path.normcase(os.path.abspath(path)).casefold()


def resolve_rename_targets(
    files: Sequence[object],
    new_names: Sequence[str],
    *,
    exists: Callable[[str], bool] = os.path.exists,
) -> list[str]:
    """Возвращает полные конечные пути, учитывая всю пачку, а не только первый файл."""
    if len(files) != len(new_names):
        raise ValueError("Количество файлов и новых имён не совпадает")
    originals = [str(item.path) for item in files]
    keys = [path_key(path) for path in originals]
    if len(set(keys)) != len(keys):
        raise ValueError("Один файл добавлен в переименование несколько раз")

    requested = []
    for item, name in zip(files, new_names, strict=True):
        name = str(name)
        error = _windows_name_error(name)
        if error:
            raise ValueError(f"Недопустимое имя «{name}»: {error}")
        requested.append(os.path.join(str(item.folder), name))

    # Только действительно освобождаемые исходные пути можно использовать как цели.
    vacated = {
        source_key
        for source_key, target in zip(keys, requested, strict=True)
        if source_key != path_key(target)
    }
    reserved: set[str] = set()
    result: list[str] = []
    for old_path, target in zip(originals, requested, strict=True):
        own_key = path_key(old_path)
        stem, extension = os.path.splitext(target)
        candidate = target
        number = 0
        while True:
            key = path_key(candidate)
            unavailable = key in reserved or (
                key != own_key and key not in vacated and exists(candidate)
            )
            if not unavailable:
                break
            number += 1
            if number > 10000:
                raise ValueError(f"Не удалось найти свободное имя для {target}")
            candidate = f"{stem}_{number}{extension}"
            if _windows_name_error(os.path.basename(candidate)):
                raise ValueError(f"Невозможно подобрать свободное имя для {target}")
        result.append(candidate)
        reserved.add(path_key(candidate))
    return result
