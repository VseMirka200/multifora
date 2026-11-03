"""Общий жизненный цикл Qt-воркеров файловых операций."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable

from PySide6.QtCore import QThread, Signal

from app.core.models import FileItem

from .common import get_unique_path
from .result import OperationResult


class OperationWorker(QThread):
    """Предоставляет отмену, сбор результата и уведомления Qt."""

    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)
    error = Signal(str)
    file_error = Signal(str)
    _get_unique_path = staticmethod(get_unique_path)

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[dict[str, object]] = []
        self.warnings: list[dict[str, object]] = []
        self._cancel_requested = False
        self._cancel_lock = threading.Lock()
        self._active_cancel_action: Callable[[], None] | None = None

    def request_cancel(self) -> None:
        with self._cancel_lock:
            self._cancel_requested = True
            cancel_action = self._active_cancel_action
        self._run_cancel_action(cancel_action)

    def _should_cancel(self) -> bool:
        with self._cancel_lock:
            return self._cancel_requested

    def _set_active_cancel_action(self, action: Callable[[], None]) -> None:
        with self._cancel_lock:
            self._active_cancel_action = action
            cancel_requested = self._cancel_requested
        if cancel_requested:
            self._run_cancel_action(action)

    @staticmethod
    def _run_cancel_action(action: Callable[[], None] | None) -> None:
        if action is None:
            return
        try:
            action()
        except Exception:
            # Отмена является best-effort: рабочий поток сам завершит очистку.
            pass

    def _clear_active_cancel_action(self, action: Callable[[], None]) -> None:
        with self._cancel_lock:
            if self._active_cancel_action is action:
                self._active_cancel_action = None

    def _record_error(self, file_item: FileItem | None, message: str) -> None:
        entry: dict[str, object] = {"message": message}
        if file_item is not None:
            entry["path"] = file_item.path
            entry["name"] = file_item.name
        self.errors.append(entry)

    def _record_warning(
        self, file_item: FileItem | None, message: str
    ) -> None:
        self.warnings.append(
            {"path": getattr(file_item, "path", None), "message": message}
        )

    def _emit_finished(
        self,
        new_files: Iterable[object] | None = None,
        updated_files: Iterable[object] | None = None,
    ) -> None:
        self.finished.emit(
            OperationResult(
                new_files=list(new_files or []),
                updated_files=list(updated_files or []),
                errors=list(self.errors),
                warnings=list(self.warnings),
            )
        )
