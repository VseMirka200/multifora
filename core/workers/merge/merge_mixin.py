import os
import shutil
import tempfile
from copy import deepcopy

from app.core.deps import HAS_PYMUPDF
from app.core.models import FileItem


class MergeMixin:
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
        if output_format == "auto":
            output_format = self._detect_merge_output_format(files)

        if output_format == "docx":
            return self._merge_word_files_to_docx(files)
        if output_format == "pdf":
            return self._merge_files_to_pdf(files)

        raise Exception(f"Неподдерживаемый формат объединения: {output_format}")

    def _detect_merge_output_format(self, files: list) -> str:
        if all(file.path.lower().endswith(".docx") for file in files):
            return "docx"
        return "pdf"

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
        if not HAS_PYMUPDF:
            raise Exception("Установите PyMuPDF для объединения PDF-файлов.")

        try:
            import fitz
        except Exception:
            raise Exception("PyMuPDF недоступен для объединения PDF-файлов.")

        output_path = self._get_merge_output_path(files, "pdf")
        temp_dir = tempfile.mkdtemp(prefix="multifora_merge_")
        pdf_paths = []

        try:
            total = len(files)
            for index, file in enumerate(files):
                if self._should_cancel():
                    raise Exception("Операция отменена пользователем")
                self.status.emit(f"Подготовка: {file.name}")

                lower_path = file.path.lower()
                if lower_path.endswith(".pdf"):
                    pdf_paths.append(file.path)
                elif lower_path.endswith((".doc", ".docx")):
                    pdf_paths.append(self._convert_merge_word_to_pdf(file, temp_dir))
                else:
                    raise Exception(f"Нельзя объединить файл этого формата: {file.name}")

                self.progress.emit(int((index + 1) / total * 50))

            merged_pdf = fitz.open()
            try:
                for index, pdf_path in enumerate(pdf_paths):
                    if self._should_cancel():
                        raise Exception("Операция отменена пользователем")
                    self.status.emit(f"Объединение PDF: {os.path.basename(pdf_path)}")
                    with fitz.open(pdf_path) as source_pdf:
                        merged_pdf.insert_pdf(source_pdf)
                    self.progress.emit(50 + int((index + 1) / len(pdf_paths) * 50))

                merged_pdf.save(output_path)
            finally:
                merged_pdf.close()
            return output_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _convert_merge_word_to_pdf(self, file, temp_dir: str) -> str:
        converted_path = self._convert_word_to_pdf(file)
        if not converted_path or not os.path.exists(converted_path):
            raise Exception(f"Не удалось подготовить PDF из Word-файла: {file.name}")

        temp_path = os.path.join(temp_dir, os.path.basename(converted_path))
        temp_path = self._get_unique_path(temp_path)
        shutil.move(converted_path, temp_path)
        return temp_path
