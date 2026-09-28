from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Protocol

CANCELLED_STATUS = "Операция отменена пользователем"


class _SignalLike(Protocol):
    def emit(self, value: object) -> None: ...


class WorkerLike(Protocol):
    # Общим функциям нужны только сигналы и результат, а не зависимость от QThread.
    progress: _SignalLike
    status: _SignalLike
    error: _SignalLike

    def _should_cancel(self) -> bool: ...

    def _emit_finished(
        self,
        new_files: Iterable[object] | None = None,
        updated_files: Iterable[object] | None = None,
    ) -> None: ...

    def _record_error(self, file_item: object | None, message: str) -> None: ...


def get_unique_path(path: str) -> str:
    """Возвращает незанятый путь, добавляя числовой суффикс при необходимости."""
    if not os.path.exists(path):
        return path

    base, extension = os.path.splitext(path)
    counter = 1
    candidate = path
    while os.path.exists(candidate):
        candidate = f"{base}_{counter}{extension}"
        counter += 1
    return candidate


def emit_progress(worker: WorkerLike, index: int, total: int) -> None:
    """Публикует прогресс по индексу текущего элемента."""
    if total <= 0:
        return
    worker.progress.emit(int((index + 1) / total * 100))


def finish_if_cancelled(
    worker: WorkerLike,
    new_files: Iterable[object] | None = None,
    updated_files: Iterable[object] | None = None,
) -> bool:
    """Завершает операцию стандартным результатом, если запрошена отмена."""
    if not worker._should_cancel():
        return False
    worker.status.emit(CANCELLED_STATUS)
    worker._emit_finished(new_files or [], updated_files or [])
    return True


def record_file_error(
    worker: WorkerLike,
    file_item: object | None,
    message: str,
) -> None:
    """Сохраняет ошибку файла и отправляет её в UI."""
    worker._record_error(file_item, message)
    worker.error.emit(message)
