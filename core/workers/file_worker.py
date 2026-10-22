from __future__ import annotations

import os
from collections.abc import Callable

from app.core.models import FileItem
from app.core.rename_plan import resolve_rename_targets

from .common import emit_progress, record_file_error
from .compression import CompressionMixin
from .conversion import ConversionMixin
from .merge.merge_mixin import MergeMixin
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


class FileWorker(
    ConversionMixin,
    CompressionMixin,
    MergeMixin,
    OperationWorker,
):
    """Выполняет файловые операции в отдельном потоке Qt."""

    def __init__(self) -> None:
        super().__init__()
        self.operation: str | None = None
        self.files: list[FileItem] = []
        self.conversion_type = ""
        self.conversion_format = ""
        self.conversion_output_mode = "source_subfolder"
        self.conversion_output_dir = ""
        self.new_names: list[str] = []
        self.strict_rename = False
        self.compression_level = 85
        self.compression_type = "image"
        self.pdf_method = "auto"
        self.replace_pdf = False
        self.image_output_mode = "alongside"
        self.image_output_dir = ""
        self.merge_output_format = "pdf"
        self.merge_output_path = ""
        self._last_pdf_error = ""
        self._word_warmup_done = False
        self._word_pdf_unavailable = False
        self._conversion_reserved_paths: set[str] = set()

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

    def set_conversion(
        self,
        files: list[FileItem],
        conversion_type: str,
        conversion_format: str = "",
        output_dir: str = "",
        output_mode: str | None = None,
    ) -> None:
        self._prepare_operation("convert", files)
        self.conversion_type = conversion_type
        self.conversion_format = conversion_format
        self.conversion_output_dir = str(output_dir or "").strip()
        if output_mode is None:
            output_mode = (
                "custom" if self.conversion_output_dir else "source_subfolder"
            )
        self.conversion_output_mode = (
            output_mode
            if output_mode in {"alongside", "source_subfolder", "custom"}
            else "source_subfolder"
        )
        self._conversion_reserved_paths = set()
        self._word_warmup_done = False
        self._word_pdf_unavailable = False

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

    def set_compression(
        self,
        files: list[FileItem],
        compression_level: int,
        compression_type: str = "image",
        pdf_method: str = "auto",
        replace_pdf: bool = False,
        image_output_mode: str = "alongside",
        image_output_dir: str = "",
    ) -> None:
        self._prepare_operation("compress", files)
        self.compression_level = compression_level
        self.compression_type = compression_type
        self.pdf_method = pdf_method
        self.replace_pdf = replace_pdf
        self.image_output_mode = (
            image_output_mode
            if image_output_mode in {"replace", "alongside", "custom"}
            else "alongside"
        )
        self.image_output_dir = str(image_output_dir or "").strip()

    def set_merge(
        self,
        files: list[FileItem],
        output_format: str = "pdf",
        output_path: str = "",
    ) -> None:
        self._prepare_operation("merge", files)
        self.merge_output_format = output_format
        self.merge_output_path = output_path

    def _compression_handler(self) -> Callable[[], None]:
        if self.compression_type == "pdf":
            return self._compress_pdf_files
        return self._compress_image_files

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
        return {
            "convert": self._convert_files,
            "rename": self._rename_files,
            "compress": self._compression_handler(),
            "merge": self._merge_files,
        }

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
