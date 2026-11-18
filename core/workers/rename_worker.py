"""Обработчик переименования без зависимостей конвертации и сжатия."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.core.models import OperationSource
from app.core.rename_plan import resolve_rename_targets
from core.rename_transaction import rename_batch

from .common import emit_progress, record_file_error
from .operation_worker import OperationWorker


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
        self.new_names: list[str] = []
        self.strict_rename = False

    def set_rename(
        self,
        files: Sequence[OperationSource],
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
            targets = resolve_rename_targets(self.files, self.new_names, strict=self.strict_rename)
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
        return {**super()._operation_handlers(), "rename": self._rename_files}
