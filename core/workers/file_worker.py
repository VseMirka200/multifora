from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import FileItem

from .compression import CompressionMixin
from .conversion import ConversionMixin
from .merge import MergeMixin
from .metadata import MetadataMixin
from .operations import FileOpsMixin
from .result import OperationResult


class FileWorker(
    FileOpsMixin,
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

    def __init__(self) -> None:
        super().__init__()
        self.operation: str | None = None
        self.files: list[FileItem] = []
        self.destination = ""
        self.conversion_type = ""
        self.conversion_format = ""
        self.conversion_output_dir = ""
        self.new_names: list[str] = []
        self.compression_level = 85
        self.compression_type = "image"
        self.pdf_method = "auto"
        self.replace_pdf = False
        self.replace_image = False
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

    def set_copy_move(
        self,
        files: list[FileItem],
        destination: str,
        move: bool = False,
    ) -> None:
        self._prepare_operation("move" if move else "copy", files)
        self.destination = destination

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
    ) -> None:
        self._prepare_operation("rename", files)
        self.new_names = new_names

    def set_compression(
        self,
        files: list[FileItem],
        compression_level: int,
        compression_type: str = "image",
        pdf_method: str = "auto",
        replace_pdf: bool = False,
        replace_image: bool = False,
    ) -> None:
        self._prepare_operation("compress", files)
        self.compression_level = compression_level
        self.compression_type = compression_type
        self.pdf_method = pdf_method
        self.replace_pdf = replace_pdf
        self.replace_image = replace_image

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

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            "copy": self._copy_files,
            "move": self._move_files,
            "convert": self._convert_files,
            "rename": self._rename_files,
            "compress": self._compression_handler(),
            "merge": self._merge_files,
            "metadata": self._remove_metadata_files,
        }

    def run(self) -> None:
        """Запускает выбранную операцию и завершает её даже при аварийной ошибке."""
        handler = self._operation_handlers().get(self.operation or "")
        if handler is None:
            return

        try:
            handler()
        except Exception as error:
            message = str(error)
            self._record_error(None, message)
            self.error.emit(message)
            # Верхнеуровневая ошибка не должна оставлять UI в состоянии
            # бесконечной операции без итогового результата.
            self._emit_finished([], [])
