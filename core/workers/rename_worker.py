"""Lightweight rename worker without conversion or compression dependencies."""

from __future__ import annotations

import os
from collections.abc import Callable

from app.core.models import FileItem
from app.core.rename_plan import resolve_rename_targets

from .common import emit_progress, record_file_error
from .operation_worker import OperationWorker
from .rename_transaction import rename_batch


def _format_rename_error(error: Exception) -> str:
    """Возвращает понятное пользователю описание ошибки переименования."""
    if isinstance(error, OSError) and (
        getattr(error, "winerror", None) == 87 or error.errno in {22, 87}
    ):
        return (
            "Не удалось создать новое имя: путь или имя содержит "
            "недопустимый символ. Проверьте шаблон: в имени нельзя "
            "использовать \\ / : * ? \" < > |."
        )
    return f"Ошибка переименования: {error}"


class RenameWorker(OperationWorker):
    def __init__(self) -> None:
        super().__init__()
        self.operation: str | None = None
        self.files: list[FileItem] = []
        self.new_names: list[str] = []
        self.strict_rename = False

    def _prepare_operation(
        self, operation: str, files: list[FileItem]
    ) -> None:
        with self._cancel_lock:
            self._cancel_requested = False
            self._active_cancel_action = None
        self.operation = operation
        self.files = files
        self.errors = []
        self.warnings = []

    def set_rename(
        self,
        files: list[FileItem],
        new_names: list[str],
        *,
        strict: bool = False,
    ) -> None:
        self._prepare_operation("rename", files)
        self.new_names = new_names
        self.strict_rename = strict

    def _rename_files(self) -> None:
        """Сначала рассчитывает всю пачку, затем безопасно меняет имена."""
        try:
            targets = resolve_rename_targets(self.files, self.new_names)
            if self.strict_rename:
                requested = [
                    os.path.join(file.folder, name)
                    for file, name in zip(
                        self.files, self.new_names, strict=True
                    )
                ]
                if any(
                    os.path.normcase(actual).casefold()
                    != os.path.normcase(desired).casefold()
                    for actual, desired in zip(targets, requested, strict=True)
                ):
                    raise ValueError(
                        "Откат невозможен: исходные имена заняты другими файлами"
                    )
        except ValueError as error:
            record_file_error(
                self, None, f"Ошибка плана переименования: {error}"
            )
            self._emit_finished([], [])
            return

        total = len(self.files)
        successes, errors = rename_batch(
            [file.path for file in self.files],
            targets,
            cancelled=self._should_cancel,
            on_done=lambda index: (
                self.status.emit(f"Переименование: {self.files[index].name}"),
                emit_progress(self, index, total),
            ),
        )
        for index, error in errors:
            record_file_error(
                self,
                self.files[index] if 0 <= index < total else None,
                _format_rename_error(error),
            )
        if self._should_cancel():
            self.status.emit("Операция отменена пользователем")
        self._emit_finished(
            [], [(self.files[index], target) for index, target in successes]
        )

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {"rename": self._rename_files}

    def run(self) -> None:
        """Запускает выбранную операцию и завершает её даже при аварийной ошибке."""
        try:
            handler = self._operation_handlers().get(self.operation or "")
            if handler is None:
                return
            handler()
        except Exception as error:
            message = str(error)
            self._record_error(None, message)
            self.error.emit(message)
            # Верхнеуровневая ошибка не должна оставлять UI в состоянии
            # бесконечной операции без итогового результата.
            self._emit_finished([], [])
