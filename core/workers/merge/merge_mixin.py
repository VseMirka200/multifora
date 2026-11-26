"""PDF merge delegated to PdfCraft. Unsupported DOCX merge is deliberately removed."""
from __future__ import annotations

import os

from app.core.models import FileItem
from core.workers import native_engines


class MergeMixin:
    def _merge_files(self):
        try:
            result = self._merge_files_to_target()
        except InterruptedError:
            self.status.emit("Операция отменена пользователем")
            self._emit_finished([], [])
            return
        except Exception as error:
            self._record_error(None, str(error))
            self.error.emit(str(error))
            self._emit_finished([], [])
            return
        new_files = [FileItem(result)] if result and os.path.exists(result) else []
        self._emit_finished(new_files, [])

    def _merge_files_to_target(self) -> str:
        files = [file for file in self.files if getattr(file, "is_file", False)]
        if len(files) < 2:
            raise ValueError("Для объединения нужно выбрать минимум два PDF-файла.")
        if any(not file.path.lower().endswith(".pdf") for file in files):
            raise ValueError("PdfCraft объединяет PDF с PDF. Объединение DOCX удалено.")
        missing = [file.path for file in files if not os.path.isfile(file.path)]
        if missing:
            raise FileNotFoundError("Не найдены исходные PDF:\n" + "\n".join(missing))
        output_path = self._get_merge_output_path(files, "pdf")
        for index, file in enumerate(files):
            if self._should_cancel():
                raise InterruptedError("Операция отменена пользователем")
            self.status.emit(f"Подготовка PDF: {file.name}")
            self.progress.emit(int(index / len(files) * 100))
        result = native_engines.merge_pdfs(self, files, output_path)
        self.progress.emit(100)
        return result

    def _get_merge_output_path(self, files: list, extension: str) -> str:
        requested = str(getattr(self, "merge_output_path", "") or "").strip()
        if requested:
            base, ext = os.path.splitext(requested)
            if ext.lower() != f".{extension}":
                requested = f"{base}.{extension}" if base else f"{requested}.{extension}"
            return self._get_unique_path(requested)
        folder = os.path.dirname(files[0].path)
        return self._get_unique_path(os.path.join(folder, f"Объединенный_документ.{extension}"))
