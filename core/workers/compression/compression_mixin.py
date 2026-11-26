"""Compression delegated to PdfCraft and PhotoCraft native engines."""
from __future__ import annotations

import os

from app.core.conversion_formats import IMAGE_WRITABLE_FORMATS, format_for_path
from app.core.models import FileItem
from core.workers import native_engines
from core.workers.common import emit_progress, finish_if_cancelled, record_file_error


class CompressionMixin:
    def _image_compression_target_path(self, file, extension: str) -> str:
        mode = str(getattr(self, "image_output_mode", "alongside") or "alongside")
        output_folder = os.path.dirname(file.path)
        if mode == "custom":
            output_folder = str(getattr(self, "image_output_dir", "") or "").strip()
            if not output_folder:
                raise ValueError("Не указана папка для сжатых изображений.")
            os.makedirs(output_folder, exist_ok=True)
        return self._get_unique_path(
            os.path.join(output_folder, f"{os.path.splitext(file.name)[0]}_compressed{extension}")
        )

    @staticmethod
    def _pdf_profile(file_path: str, method: str) -> tuple[int, int]:
        profiles = {
            "max": (72, 40),
            "quality": (300, 92),
            "optimize": (300, 90),
            "standard": (300, 85),
            "auto": (150, 75) if os.path.getsize(file_path) > 10 * 1024 * 1024 else (300, 85),
        }
        return profiles.get(method, profiles["auto"])

    def _compress_image_files(self):
        total = len(self.files)
        results = []
        updated = []
        for index, file in enumerate(self.files):
            if finish_if_cancelled(self, results, updated):
                return
            try:
                if not file.is_file or file.file_type != "image":
                    raise ValueError(f"{file.name} не является изображением")
                image_format = format_for_path(file.path)
                if image_format not in IMAGE_WRITABLE_FORMATS:
                    raise ValueError(
                        f"PhotoCraft может прочитать {image_format or 'этот формат'}, "
                        "но не может сохранить его в исходный формат для сжатия."
                    )
                extension = os.path.splitext(file.name)[1].lower()
                compressed_path = self._image_compression_target_path(file, extension)
                original_size = os.path.getsize(file.path)
                native_engines.compress_image(
                    self, file.path, compressed_path, self.compression_level
                )
                compressed_size = os.path.getsize(compressed_path)
                if compressed_size >= original_size:
                    os.remove(compressed_path)
                    self.status.emit(f"Изображение уже оптимизировано: {file.name}")
                else:
                    ratio = (1 - compressed_size / original_size) * 100
                    if getattr(self, "image_output_mode", "alongside") == "replace":
                        os.replace(compressed_path, file.path)
                        updated.append((file, file.path))
                        self.status.emit(f"Изображение сжато и заменено: {file.name} (-{ratio:.1f}%)")
                    else:
                        results.append(FileItem(compressed_path))
                        self.status.emit(f"Изображение сжато: {file.name} (-{ratio:.1f}%)")
            except InterruptedError:
                self.status.emit("Операция отменена пользователем")
                break
            except Exception as error:
                record_file_error(self, file, f"Ошибка сжатия {file.name}: {error}")
            emit_progress(self, index, total)
        self._emit_finished(results, updated)

    def _compress_pdf_files(self):
        total = len(self.files)
        results = []
        updated = []
        method = str(getattr(self, "pdf_method", "auto") or "auto")
        for index, file in enumerate(self.files):
            if finish_if_cancelled(self, results, updated):
                return
            try:
                if not file.is_file or not file.path.lower().endswith(".pdf"):
                    raise ValueError(f"{file.name} не является PDF")
                original_size = os.path.getsize(file.path)
                output_path = self._get_unique_path(
                    os.path.splitext(file.path)[0] + "_compressed.pdf"
                )
                ppi, quality = self._pdf_profile(file.path, method)
                native_engines.compress_pdf(self, file.path, output_path, ppi, quality)
                compressed_size = os.path.getsize(output_path)
                if compressed_size >= original_size:
                    os.remove(output_path)
                    self.status.emit(f"PDF уже оптимален: {file.name}")
                else:
                    ratio = (1 - compressed_size / original_size) * 100
                    if getattr(self, "replace_pdf", False):
                        os.replace(output_path, file.path)
                        updated.append((file, file.path))
                        self.status.emit(f"PDF сжат и заменен (PdfCraft): {file.name} (-{ratio:.1f}%)")
                    else:
                        results.append(FileItem(output_path))
                        self.status.emit(f"PDF сжат (PdfCraft): {file.name} (-{ratio:.1f}%)")
            except InterruptedError:
                self.status.emit("Операция отменена пользователем")
                break
            except Exception as error:
                record_file_error(self, file, f"Ошибка сжатия PDF {file.name}: {error}")
            self.progress.emit(int((index + 1) / max(total, 1) * 100))
        self._emit_finished(results, updated)
