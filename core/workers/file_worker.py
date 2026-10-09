from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterable

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import FileItem

from .common import emit_progress, get_unique_path, record_file_error
from .compression import CompressionMixin
from .conversion import ConversionMixin
from .merge import MergeMixin
from .result import OperationResult
from .rename_transaction import rename_batch
from app.core.rename_plan import resolve_rename_targets


class FileWorker(
    ConversionMixin,
    CompressionMixin,
    MergeMixin,
    QThread,
):
    """Выполняет файловые операции в отдельном потоке Qt."""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)  # Только критическая ошибка всей операции
    file_error = pyqtSignal(str)  # Ошибка отдельного файла, обработка продолжается
    _get_unique_path = staticmethod(get_unique_path)

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
        self._cancel_requested = False
        self._cancel_lock = threading.Lock()
        self._active_cancel_action: Callable[[], None] | None = None
        self.errors: list[dict[str, object]] = []
        self.warnings: list[dict[str, object]] = []
        self._word_warmup_done = False
        self._word_pdf_unavailable = False
        self._conversion_reserved_paths: set[str] = set()

    def request_cancel(self) -> None:
        with self._cancel_lock:
            self._cancel_requested = True
            cancel_action = self._active_cancel_action
        if cancel_action is not None:
            try:
                cancel_action()
            except Exception:
                pass

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def _set_active_cancel_action(self, action: Callable[[], None]) -> None:
        with self._cancel_lock:
            self._active_cancel_action = action
            cancel_requested = self._cancel_requested
        if cancel_requested:
            try:
                action()
            except Exception:
                pass

    def _clear_active_cancel_action(self, action: Callable[[], None]) -> None:
        with self._cancel_lock:
            if self._active_cancel_action is action:
                self._active_cancel_action = None

    def _record_error(self, file_item: FileItem | None, message: str) -> None:
        entry: dict[str, object] = {"message": message}
        if file_item is not None:
            entry["path"] = getattr(file_item, "path", None)
            entry["name"] = getattr(file_item, "name", None)
        self.errors.append(entry)

    def _record_warning(self, file_item: FileItem | None, message: str) -> None:
        self.warnings.append({"path": getattr(file_item, "path", None), "message": message})

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

    def _prepare_operation(self, operation: str, files: list[FileItem]) -> None:
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
            output_mode = "custom" if self.conversion_output_dir else "source_subfolder"
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
                    for file, name in zip(self.files, self.new_names, strict=True)
                ]
                if any(
                    os.path.normcase(actual).casefold() != os.path.normcase(desired).casefold()
                    for actual, desired in zip(targets, requested, strict=True)
                ):
                    raise ValueError("Откат невозможен: исходные имена заняты другими файлами")
        except ValueError as error:
            record_file_error(self, None, f"Ошибка плана переименования: {error}")
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
                f"Ошибка переименования: {error}",
            )
        if self._should_cancel():
            self.status.emit("Операция отменена пользователем")
        self._emit_finished([], [(self.files[index], target) for index, target in successes])

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
