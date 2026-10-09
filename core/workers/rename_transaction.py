"""Пакетное переименование с поддержкой циклов и откатом временных перемещений."""
from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Sequence

from app.core.rename_plan import path_key


def _move_without_overwriting(source: str, target: str) -> None:
    if path_key(source) != path_key(target) and os.path.exists(target):
        raise FileExistsError(f"Целевой путь уже занят: {target}")
    os.rename(source, target)


def _temp_path(source: str) -> str:
    folder = os.path.dirname(source)
    while True:
        candidate = os.path.join(folder, f".__multifora_{uuid.uuid4().hex}.tmp")
        if not os.path.lexists(candidate):
            return candidate


def rename_batch(
    sources: Sequence[str],
    targets: Sequence[str],
    *,
    cancelled: Callable[[], bool] = lambda: False,
    on_done: Callable[[int], None] = lambda _index: None,
) -> tuple[list[tuple[int, str]], list[tuple[int, Exception]]]:
    """Возвращает успехи и ошибки по индексам, без потери существующих путей.

    При зависимостях между именами сначала освобождаются исходные пути всей пачки.
    В случае ошибки выполняется откат всей пачки с записью ошибок отката.
    """
    if len(sources) != len(targets):
        raise ValueError("Размеры списков файлов и целевых имён различаются")
    vacated_sources = {
        path_key(source)
        for source, target in zip(sources, targets, strict=True)
        if path_key(source) != path_key(target)
    }
    dependencies = any(
        path_key(target) in vacated_sources and path_key(source) != path_key(target)
        for source, target in zip(sources, targets, strict=True)
    )
    successes: list[tuple[int, str]] = []
    errors: list[tuple[int, Exception]] = []
    if not dependencies:
        for index, (source, target) in enumerate(zip(sources, targets, strict=True)):
            if cancelled():
                break
            try:
                _move_without_overwriting(source, target)
                successes.append((index, target))
            except OSError as exc:
                errors.append((index, exc))
            on_done(index)
        return successes, errors

    temporary: dict[int, str] = {}
    placed: list[int] = []
    failure: tuple[int, Exception] | None = None
    current_index = 0
    try:
        for index, source in enumerate(sources):
            current_index = index
            if cancelled():
                raise InterruptedError("Операция отменена пользователем")
            if path_key(source) == path_key(targets[index]):
                continue
            temp = _temp_path(source)
            _move_without_overwriting(source, temp)
            temporary[index] = temp

        for index, (source, target) in enumerate(zip(sources, targets, strict=True)):
            current_index = index
            if cancelled():
                raise InterruptedError("Операция отменена пользователем")
            if index in temporary:
                _move_without_overwriting(temporary[index], target)
                placed.append(index)
            successes.append((index, target))
            on_done(index)
        return successes, []
    except (OSError, InterruptedError) as exc:
        if not (isinstance(exc, InterruptedError) and cancelled()):
            failure = (current_index, exc)

    # Сначала возвращаем готовые цели на временные пути, затем временные — на исходные.
    # Ни один из откатов не должен затереть появившийся за это время внешний файл.
    rollback_errors: list[tuple[int, Exception]] = []
    for index in reversed(placed):
        try:
            _move_without_overwriting(targets[index], temporary[index])
        except OSError as exc:
            rollback_errors.append((index, exc))
    for index, temp in reversed(list(temporary.items())):
        if not os.path.exists(temp):
            continue
        try:
            _move_without_overwriting(temp, sources[index])
        except OSError as exc:
            rollback_errors.append((index, exc))
    if failure is not None:
        errors.append(failure)
    errors.extend(rollback_errors)
    # Если откат не удался, сообщаем UI о фактическом расположении файлов.
    for index, target in enumerate(targets):
        if index in placed and os.path.exists(target):
            successes.append((index, target))
        elif index in temporary and os.path.exists(temporary[index]):
            successes.append((index, temporary[index]))
    return successes, errors
