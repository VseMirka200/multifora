import os

from app.core.models import FileItem
from core.merge_documents import _requires_docx_composer as _requires_docx_composer
from core.merge_documents import merge_documents


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
