from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from app.workers.common import (
    emit_progress,
    finish_if_cancelled,
    record_file_error,
)
from core import image_dependencies as deps
from core.compress_files import compress_image, compress_pdf, pdf_settings
from core.file_models import FileItem, OperationSource
from core.filesystem import compressed_name
from core.operation_result import CompressionSize

from .operation_worker import OperationWorker

logger = logging.getLogger(__name__)


class CompressionMixin:
    # Сжимает изображения и PDF, сохраняя исходник до успешного завершения записи.
    def _record_sizes(self, source, target, before):
        sizes = getattr(self, "compression_sizes", None)
        if sizes is not None:
            try:
                sizes.append(CompressionSize(source, before, os.path.getsize(target)))
            except OSError:
                logger.debug("Не удалось прочитать итоговый размер %s", target)

    def _image_compression_target_path(self, file, extension: str) -> str:
        mode = str(getattr(self, "image_output_mode", "alongside") or "alongside")
        output_folder = os.path.dirname(file.path)

        if mode == "custom":
            output_folder = str(getattr(self, "image_output_dir", "") or "").strip()
            if not output_folder:
                raise Exception("Не указана папка для сжатых изображений.")
            os.makedirs(output_folder, exist_ok=True)

        target_path = os.path.join(output_folder, compressed_name(file.name, extension))
        return self._get_unique_path(target_path)

    def _compress_image_files(self):
        results = []
        updated = []
        for index, file in enumerate(self.files):
            if finish_if_cancelled(self, results, updated):
                return
            try:
                if not file.is_file or file.file_type != "image":
                    raise ValueError(f"Файл {file.name} не является изображением или не поддерживается")
                if not deps.HAS_PIL:
                    raise RuntimeError("Для сжатия изображений установите Pillow: pip install Pillow")
                extension = os.path.splitext(file.name)[1].lower()
                destination = self._image_compression_target_path(file, extension)
                replace = getattr(self, "image_output_mode", "alongside") == "replace"
                before = os.path.getsize(file.path)
                ratio = compress_image(
                    file.path, destination, extension, self.compression_level,
                    replace=replace, should_cancel=self._should_cancel,
                )
                if ratio is None:
                    self._record_sizes(file.path, file.path, before)
                    self.status.emit(f"Изображение уже оптимизировано: {file.name}")
                else:
                    (updated if replace else results).append((file, file.path) if replace else FileItem(destination))
                    self._record_sizes(file.path, file.path if replace else destination, before)
                    action = "сжато и заменено" if replace else "сжато"
                    self.status.emit(f"Изображение {action}: {file.name} (-{ratio:.1f}%)")
            except InterruptedError:
                if finish_if_cancelled(self, results, updated):
                    return
                record_file_error(self, file, f"Ошибка сжатия {file.name}: операция прервана")
            except Exception as error:
                record_file_error(self, file, f"Ошибка сжатия {file.name}: {error}", cause=error)
            emit_progress(self, index, len(self.files))
            self.status.emit(f"Сжатие: {file.name}")
        self._emit_finished(results, updated)

    def _compress_pdf_files(self):
        logger.debug(f"Начало сжатия PDF: {len(self.files)} файлов")
        results = []
        updated = []
        for index, file in enumerate(self.files):
            if finish_if_cancelled(self, results, updated):
                return
            if not (file.is_file and file.path.lower().endswith(".pdf")):
                continue
            try:
                folder, name = os.path.split(file.path)
                destination = self._get_unique_path(os.path.join(folder, compressed_name(name, ".pdf")))
                replace = getattr(self, "replace_pdf", False)
                before = os.path.getsize(file.path)
                result = compress_pdf(
                    file.path, destination,
                    replace=replace, should_cancel=self._should_cancel,
                    optimize=self._compress_pdf_with_pdfcraft,
                )
                if result is None:
                    self._record_sizes(file.path, file.path, before)
                    self.status.emit(f"PDF уже оптимален: {file.name}")
                else:
                    method, ratio = result
                    (updated if replace else results).append((file, file.path) if replace else FileItem(destination))
                    self._record_sizes(file.path, file.path if replace else destination, before)
                    action = "сжат и заменен" if replace else "сжат"
                    self.status.emit(f"PDF {action} ({method}): {file.name} (-{ratio:.1f}%)")
            except InterruptedError:
                if finish_if_cancelled(self, results, updated):
                    return
                record_file_error(self, file, f"Ошибка сжатия PDF {file.name}: операция прервана")
            except Exception as error:
                message = f"Ошибка сжатия PDF {file.name}: {error}"
                self.status.emit(message)
                record_file_error(self, file, message, cause=error)
            emit_progress(self, index, len(self.files))
        self._emit_finished(results, updated)

    def _compress_pdf_with_pdfcraft(self, input_path: str, output_path: str | Path) -> tuple[bool, str, float]:
        from core.pdf_engine.operations import optimize_pdf

        original_size = os.path.getsize(input_path)
        settings = self._get_pdf_settings(original_size)
        optimize_pdf(input_path, output_path, settings, self._should_cancel)
        new_size = os.path.getsize(output_path)
        if new_size < original_size:
            ratio = (1 - new_size / original_size) * 100
            return True, self._get_compression_method_name(settings), ratio
        return False, "", 0.0

    def _get_pdf_settings(self, file_size):
        return pdf_settings(self.pdf_method, file_size)

    def _get_compression_method_name(self, settings):
        return settings.get("method_name", "Стандарт")


class CompressionWorker(CompressionMixin, OperationWorker):
    """Обработчик сжатия с общей инфраструктурой операций."""

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
        files: Sequence[OperationSource],
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
