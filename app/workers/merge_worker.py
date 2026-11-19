"""Лёгкий воркер, предназначенный для объединения документов.

Он намеренно не импортирует универсальный файловый воркер: зависимости
конвертации и сжатия не должны задерживать старт объединения PDF/DOCX.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from core.file_models import FileItem, OperationSource
from core.merge_documents import merge_documents

from .operation_worker import OperationWorker


class MergeMixin:
    # Объединяет документы в порядке очереди и публикует итоговый файл для интерфейса.
    def _merge_files(self):
        try:
            result = self._merge_files_to_target()
        except InterruptedError:
            self.status.emit("Операция отменена пользователем")
            self._emit_finished([], [])
            return
        except Exception as e:
            self._record_error(None, str(e))
            self.error.emit(
                str(e)
            )  # Критическая ошибка всей операции объединения
            self._emit_finished([], [])
            return

        new_files = (
            [FileItem(result)] if result and os.path.exists(result) else []
        )
        self._emit_finished(new_files, [])

    def _merge_files_to_target(self) -> str:
        return merge_documents(
            self.files,
            getattr(self, "merge_output_format", "pdf"),
            getattr(self, "merge_output_path", ""),
            should_cancel=self._should_cancel,
            status=self.status.emit,
            progress=self.progress.emit,
            unique_path=self._get_unique_path,
        )


class MergeWorker(MergeMixin, OperationWorker):
    """Объединяет упорядоченный набор документов в фоновом потоке Qt."""

    def __init__(
        self,
        files: Sequence[OperationSource],
        output_format: str,
        output_path: str,
    ) -> None:
        super().__init__()
        self.files = list(files)
        self.merge_output_format = output_format
        self.merge_output_path = output_path

    def run(self) -> None:
        self._merge_files()
