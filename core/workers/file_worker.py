from __future__ import annotations

from collections.abc import Callable

from app.core.models import FileItem

from .compression import CompressionMixin
from .conversion import ConversionMixin
from .merge.merge_mixin import MergeMixin
from .rename_worker import RenameWorker
from .rename_worker import _format_rename_error as _format_rename_error


class FileWorker(
    ConversionMixin,
    CompressionMixin,
    MergeMixin,
    RenameWorker,
):
    """Выполняет файловые операции в отдельном потоке Qt."""

    def __init__(self) -> None:
        super().__init__()
        self.conversion_type = ""
        self.conversion_format = ""
        self.conversion_output_mode = "source_subfolder"
        self.conversion_output_dir = ""
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

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            "convert": self._convert_files,
            "rename": self._rename_files,
            "compress": self._compression_handler(),
            "merge": self._merge_files,
        }
