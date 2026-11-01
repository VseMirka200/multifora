from __future__ import annotations

from collections.abc import Callable

from app.core.models import FileItem

from .compression import CompressionMixin
from .rename_worker import RenameWorker


class CompressionWorker(CompressionMixin, RenameWorker):
    """Worker containing only compression and shared operation infrastructure."""

    def __init__(self) -> None:
        super().__init__()
        self.compression_level = 85
        self.compression_type = "image"
        self.pdf_method = "auto"
        self.replace_pdf = False
        self.image_output_mode = "alongside"
        self.image_output_dir = ""
        self._last_pdf_error = ""

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

    def _compression_handler(self) -> Callable[[], None]:
        if self.compression_type == "pdf":
            return self._compress_pdf_files
        return self._compress_image_files

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            **super()._operation_handlers(),
            "compress": self._compression_handler(),
        }
