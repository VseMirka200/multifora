"""Общий жизненный цикл Qt-воркеров файловых операций."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Sequence

from PySide6.QtCore import QThread, Signal

from core.file_models import FileItem, OperationSource
from core.filesystem import get_unique_path
from core.operation_result import CompressionSize, OperationIssue, OperationResult


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
        self.errors: list[OperationIssue] = []
        self.warnings: list[OperationIssue] = []
        self.compression_sizes: list[CompressionSize] = []
        self._cancel_requested = False
        self._cancel_lock = threading.Lock()
        self._active_cancel_action: Callable[[], None] | None = None
        self.operation: str | None = None
        self.files: list[OperationSource] = []

    def _prepare_operation(self, operation: str, files: Sequence[OperationSource]) -> None:
        with self._cancel_lock:
            self._cancel_requested = False
            self._active_cancel_action = None
        self.operation = operation
        self.files = list(files)
        self.errors = []
        self.warnings = []
        self.compression_sizes = []

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {}

    def run(self) -> None:
        """Выполняет операцию и отправляет результат при аварийной ошибке."""
        try:
            handler = self._operation_handlers().get(self.operation or "")
            if handler is not None:
                handler()
        except Exception as error:
            message = str(error)
            self._record_error(None, message)
            self.error.emit(message)
            self._emit_finished([], [])

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

    def _record_error(
        self, file_item: OperationSource | None, message: str, *, cause: Exception | None = None
    ) -> None:
        entry: OperationIssue = {"message": message}
        if file_item is not None:
            entry["path"] = file_item.path
            entry["name"] = file_item.name
        if isinstance(cause, PermissionError):
            entry["explanation"] = "Нет доступа к файлу или папке. Проверьте права и закройте открытый файл."
            entry["retryable"] = True
        elif isinstance(cause, FileNotFoundError):
            entry["explanation"] = "Файл или папка недоступны по указанному пути."
        elif isinstance(cause, TimeoutError):
            entry["explanation"] = "Истекло время ожидания обработки файла."
            entry["retryable"] = True
        elif cause is not None and "negative availWidth" in str(cause):
            entry["explanation"] = "Не удалось разместить таблицу в PDF. Проверьте ширину её ячеек."
        self.errors.append(entry)

    def _record_warning(
        self, file_item: OperationSource | None, message: str
    ) -> None:
        self.warnings.append(
            {"path": getattr(file_item, "path", None), "message": message}
        )

    def _emit_finished(
        self,
        new_files: Iterable[FileItem] | None = None,
        updated_files: Iterable[tuple[OperationSource, str]] | None = None,
    ) -> None:
        self.finished.emit(
            OperationResult(
                new_files=list(new_files or []),
                updated_files=list(updated_files or []),
                errors=list(self.errors),
                warnings=list(self.warnings),
                cancelled=self._should_cancel(),
                compression_sizes=list(self.compression_sizes),
            )
        )
