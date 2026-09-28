import os
from copy import deepcopy

from app.core.deps import HAS_PYMUPDF
from app.core.models import FileItem


class MergeMixin:
    # Объединяет документы в порядке очереди и публикует итоговый файл для интерфейса.
    def _merge_files(self):
        try:
            result = self._merge_files_to_target()
        except Exception as e:
            self._record_error(None, str(e))
            self.error.emit(str(e))
            self._emit_finished([], [])
            return

        new_files = [FileItem(result)] if result and os.path.exists(result) else []
        self._emit_finished(new_files, [])

    def _merge_files_to_target(self) -> str | None:
        files = [file for file in self.files if getattr(file, "is_file", False)]
        if len(files) < 2:
            raise Exception("Для объединения нужно выбрать минимум два файла.")

        output_format = str(getattr(self, "merge_output_format", "pdf") or "pdf").lower()
        if output_format == "docx":
            return self._merge_word_files_to_docx(files)
        if output_format == "pdf":
            return self._merge_files_to_pdf(files)

        raise Exception(f"Неподдерживаемый формат объединения: {output_format}")

    def _get_merge_output_path(self, files: list, extension: str) -> str:
        requested_path = str(getattr(self, "merge_output_path", "") or "").strip()
        if requested_path:
            base, ext = os.path.splitext(requested_path)
            if ext.lower() != f".{extension}":
                requested_path = f"{base}.{extension}" if base else f"{requested_path}.{extension}"
            return self._get_unique_path(requested_path)

        folder = os.path.dirname(files[0].path)
        path = os.path.join(folder, f"Объединенный_документ.{extension}")
        return self._get_unique_path(path)

    def _merge_word_files_to_docx(self, files: list) -> str:
        if not all(file.path.lower().endswith(".docx") for file in files):
            raise Exception(
                "Объединение в DOCX поддерживает только файлы DOCX. "
                "Для DOC и смешанных файлов выберите PDF."
            )

        try:
            from docx import Document
        except Exception:
            raise Exception("Установите python-docx для объединения Word-файлов.")

        output_path = self._get_merge_output_path(files, "docx")
        merged = Document(files[0].path)
        body = merged.element.body
        total = len(files)

        for index, file in enumerate(files):
            if self._should_cancel():
                raise Exception("Операция отменена пользователем")
            self.status.emit(f"Объединение: {file.name}")

            if index > 0:
                source = Document(file.path)
                merged.add_page_break()
                for element in source.element.body:
                    if element.tag.endswith("sectPr"):
                        continue
                    body.append(deepcopy(element))

            self.progress.emit(int((index + 1) / total * 100))

        merged.save(output_path)
        return output_path

    def _merge_files_to_pdf(self, files: list) -> str:
        if not all(file.path.lower().endswith(".pdf") for file in files):
            raise Exception("Объединение в PDF поддерживает только файлы PDF.")

        if not HAS_PYMUPDF:
            raise Exception("Установите PyMuPDF для объединения PDF-файлов.")

        try:
            import pymupdf as fitz
        except Exception:
            raise Exception("PyMuPDF недоступен для объединения PDF-файлов.")

        output_path = self._get_merge_output_path(files, "pdf")
        merged_pdf = fitz.open()
        try:
            for index, file in enumerate(files):
                if self._should_cancel():
                    raise Exception("Операция отменена пользователем")
                self.status.emit(f"Объединение PDF: {file.name}")
                with fitz.open(file.path) as source_pdf:
                    merged_pdf.insert_pdf(source_pdf)
                self.progress.emit(int((index + 1) / len(files) * 100))

            merged_pdf.save(output_path)
            return output_path
        finally:
            merged_pdf.close()
