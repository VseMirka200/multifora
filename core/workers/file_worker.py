from __future__ import annotations

import os
from collections.abc import Callable, Iterable

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import FileItem

from .compression import CompressionMixin
from .common import emit_progress, finish_if_cancelled, get_unique_path, record_file_error
from .conversion import ConversionMixin
from .merge import MergeMixin
from .metadata import MetadataMixin
from .result import OperationResult


class FileWorker(
    ConversionMixin,
    CompressionMixin,
    MergeMixin,
    MetadataMixin,
    QThread,
):
    """Выполняет файловые операции в отдельном потоке Qt."""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    _get_unique_path = staticmethod(get_unique_path)

    def __init__(self) -> None:
        super().__init__()
        self.operation: str | None = None
        self.files: list[FileItem] = []
        self.conversion_type = ""
        self.conversion_format = ""
        self.conversion_output_dir = ""
        self.new_names: list[str] = []
        self.rename_conflict_policy = "unique"
        self.compression_level = 85
        self.compression_type = "image"
        self.pdf_method = "auto"
        self.replace_pdf = False
        self.image_output_mode = "alongside"
        self.image_output_dir = ""
        self.merge_output_format = "pdf"
        self.merge_output_path = ""
        self.metadata_remove_all = True
        self.metadata_fields: set[str] = set()
        self._last_pdf_error = ""
        self._cancel_requested = False
        self.errors: list[dict[str, object]] = []
        self._word_warmup_done = False
        self._conversion_reserved_paths: set[str] = set()

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def _record_error(self, file_item: FileItem | None, message: str) -> None:
        entry: dict[str, object] = {"message": message}
        if file_item is not None:
            entry["path"] = getattr(file_item, "path", None)
            entry["name"] = getattr(file_item, "name", None)
        self.errors.append(entry)

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
            )
        )

    def _prepare_operation(self, operation: str, files: list[FileItem]) -> None:
        self.operation = operation
        self.files = files
        self._cancel_requested = False
        self.errors = []

    def set_conversion(
        self,
        files: list[FileItem],
        conversion_type: str,
        conversion_format: str = "",
        output_dir: str = "",
    ) -> None:
        self._prepare_operation("convert", files)
        self.conversion_type = conversion_type
        self.conversion_format = conversion_format
        self.conversion_output_dir = str(output_dir or "").strip()
        self._conversion_reserved_paths = set()
        self._word_warmup_done = False

    def set_rename(
        self,
        files: list[FileItem],
        new_names: list[str],
        conflict_policy: str = "unique",
    ) -> None:
        self._prepare_operation("rename", files)
        self.new_names = new_names
        self.rename_conflict_policy = conflict_policy if conflict_policy in {"unique", "skip"} else "unique"

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

    def set_metadata_cleanup(
        self,
        files: list[FileItem],
        remove_all: bool = True,
        fields: Iterable[str] | None = None,
    ) -> None:
        self._prepare_operation("metadata", files)
        self.metadata_remove_all = bool(remove_all)
        self.metadata_fields = set(fields or [])

    def _compression_handler(self) -> Callable[[], None]:
        if self.compression_type == "pdf":
            return self._compress_pdf_files
        return self._compress_image_files

    def _rename_files(self) -> None:
        if len(self.files) != len(self.new_names):
            message = "Ошибка переименования: несоответствие количества файлов и новых имён"
            record_file_error(self, None, message)
            self._emit_finished([], [])
            return

        total = len(self.files)
        updated_files = []

        for index, (file_item, new_name) in enumerate(zip(self.files, self.new_names)):
            if finish_if_cancelled(self, [], updated_files):
                return

            old_path = file_item.path
            new_path = os.path.join(file_item.folder, new_name)

            try:
                same_path = (
                    os.path.normcase(os.path.abspath(old_path)).casefold()
                    == os.path.normcase(os.path.abspath(new_path)).casefold()
                )
                if os.path.exists(new_path) and not same_path:
                    if self.rename_conflict_policy == "skip":
                        self.status.emit(f"Пропущен конфликт имён: {file_item.name}")
                        emit_progress(self, index, total)
                        continue
                    new_path = self._get_unique_path(new_path)

                os.rename(old_path, new_path)
                updated_files.append((file_item, new_path))
            except Exception as error:
                message = f"Ошибка переименования {file_item.name}: {error}"
                record_file_error(self, file_item, message)

            emit_progress(self, index, total)
            self.status.emit(f"Переименование: {file_item.name}")

        self._emit_finished([], updated_files)

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            "convert": self._convert_files,
            "rename": self._rename_files,
            "compress": self._compression_handler(),
            "merge": self._merge_files,
            "metadata": self._remove_metadata_files,
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
