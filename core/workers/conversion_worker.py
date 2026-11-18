from __future__ import annotations

from collections.abc import Callable, Sequence

from app.core.models import OperationSource

from .conversion import ConversionMixin
from .operation_worker import OperationWorker


class ConversionWorker(ConversionMixin, OperationWorker):
    """Обработчик конвертации с общей инфраструктурой операций."""

    def __init__(self) -> None:
        super().__init__()
        self.conversion_type = ""
        self.conversion_format = ""
        self.conversion_output_mode = "source_subfolder"
        self.conversion_output_dir = ""
        self._conversion_reserved_paths: set[str] = set()

    def set_conversion(
        self,
        files: Sequence[OperationSource],
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

    def _operation_handlers(self) -> dict[str, Callable[[], None]]:
        return {**super()._operation_handlers(), "convert": self._convert_files}
