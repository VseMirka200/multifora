"""Лёгкий воркер, предназначенный для объединения документов.

Он намеренно не импортирует универсальный файловый воркер: зависимости
конвертации и сжатия не должны задерживать старт объединения PDF/DOCX.
"""

from __future__ import annotations

from app.core.models import FileItem
from core.workers.operation_worker import OperationWorker

from .merge_mixin import MergeMixin


class MergeWorker(MergeMixin, OperationWorker):
    """Объединяет упорядоченный набор документов в фоновом потоке Qt."""

    def __init__(
        self,
        files: list[FileItem],
        output_format: str,
        output_path: str,
    ) -> None:
        super().__init__()
        self.files = files
        self.merge_output_format = output_format
        self.merge_output_path = output_path

    def run(self) -> None:
        self._merge_files()
