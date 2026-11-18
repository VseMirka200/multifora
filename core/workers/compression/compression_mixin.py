import os
from pathlib import Path
from tempfile import TemporaryDirectory

import app.core.deps as deps
from app.core.app_utils import _debug_log
from app.core.models import FileItem
from core.workers.atomic_output import publish_new_file
from core.workers.common import (
    emit_progress,
    finish_if_cancelled,
    record_file_error,
)

from .image_optimizer import save_optimized_image

_LARGE_PDF_THRESHOLD_BYTES = 10 * 1024 * 1024

_PDF_PROFILES = {
    "max": {
        "color_resolution": 72,
        "gray_resolution": 72,
        "jpeg_quality": 40,
        "method_name": "Максимальное сжатие",
    },
    "quality": {
        "color_resolution": 300,
        "gray_resolution": 300,
        "jpeg_quality": 92,
        "method_name": "Сохранить качество",
    },
    "optimize": {
        "lossless": True,
        "method_name": "Только оптимизация",
    },
    "auto_large": {
        "color_resolution": 150,
        "gray_resolution": 150,
        "jpeg_quality": 75,
        "method_name": "Авто (для больших файлов)",
    },
    "auto_standard": {
        "color_resolution": 300,
        "gray_resolution": 300,
        "jpeg_quality": 85,
        "method_name": "Авто (стандарт)",
    },
    "standard": {
        "color_resolution": 300,
        "gray_resolution": 300,
        "jpeg_quality": 85,
        "method_name": "Стандарт",
    },
}


class CompressionMixin:
    # Сжимает изображения и PDF, сохраняя исходник до успешного завершения записи.
    def _image_compression_target_path(self, file, extension: str) -> str:
        mode = str(getattr(self, "image_output_mode", "alongside") or "alongside")
        source_stem = os.path.splitext(file.name)[0]
        output_folder = os.path.dirname(file.path)

        if mode == "custom":
            output_folder = str(getattr(self, "image_output_dir", "") or "").strip()
            if not output_folder:
                raise Exception("Не указана папка для сжатых изображений.")
            os.makedirs(output_folder, exist_ok=True)

        target_path = os.path.join(output_folder, f"{source_stem}_compressed{extension}")
        return self._get_unique_path(target_path)

    def _publish_compressed(self, file, staged, destination, replace, results, updated):
        if replace:
            os.replace(staged, file.path)
            updated.append((file, file.path))
        else:
            publish_new_file(staged, destination)
            results.append(FileItem(destination))

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
                original_size = os.path.getsize(file.path)
                replace = getattr(self, "image_output_mode", "alongside") == "replace"
                with TemporaryDirectory(dir=os.path.dirname(os.path.abspath(destination))) as folder:
                    staged = Path(folder, "image" + extension)
                    with deps.Image.open(file.path) as image:
                        save_optimized_image(image, staged, extension, self.compression_level)
                    if finish_if_cancelled(self, results, updated):
                        return
                    size = staged.stat().st_size
                    if 0 < size < original_size:
                        self._publish_compressed(file, staged, destination, replace, results, updated)
                        action = "сжато и заменено" if replace else "сжато"
                        ratio = (1 - size / original_size) * 100
                        self.status.emit(f"Изображение {action}: {file.name} (-{ratio:.1f}%)")
                    elif size == 0:
                        raise OSError("сжатый файл пустой")
                    else:
                        self.status.emit(f"Изображение уже оптимизировано: {file.name}")
            except Exception as error:
                record_file_error(self, file, f"Ошибка сжатия {file.name}: {error}")
            emit_progress(self, index, len(self.files))
            self.status.emit(f"Сжатие: {file.name}")
        self._emit_finished(results, updated)

    def _compress_pdf_files(self):
        _debug_log(f"Начало сжатия PDF: {len(self.files)} файлов")
        results = []
        updated = []
        for index, file in enumerate(self.files):
            if finish_if_cancelled(self, results, updated):
                return
            if not (file.is_file and file.path.lower().endswith(".pdf")):
                continue
            try:
                destination = self._get_unique_path(file.path.rsplit(".", 1)[0] + "_compressed.pdf")
                replace = getattr(self, "replace_pdf", False)
                with TemporaryDirectory(dir=os.path.dirname(os.path.abspath(destination))) as folder:
                    staged = Path(folder, "document.pdf")
                    success, method, ratio = self._compress_pdf_with_pdfcraft(file.path, staged)
                    if finish_if_cancelled(self, results, updated):
                        return
                    if success:
                        self._publish_compressed(file, staged, destination, replace, results, updated)
                        action = "сжат и заменен" if replace else "сжат"
                        self.status.emit(f"PDF {action} ({method}): {file.name} (-{ratio:.1f}%)")
                    else:
                        self.status.emit(f"PDF уже оптимален: {file.name}")
            except InterruptedError:
                if finish_if_cancelled(self, results, updated):
                    return
                record_file_error(self, file, f"Ошибка сжатия PDF {file.name}: операция прервана")
            except Exception as error:
                message = f"Ошибка сжатия PDF {file.name}: {error}"
                self.status.emit(message)
                record_file_error(self, file, message)
            emit_progress(self, index, len(self.files))
        self._emit_finished(results, updated)

    def _compress_pdf_with_pdfcraft(self, input_path: str, output_path: str | Path) -> tuple[bool, str, float]:
        from core.workers.pdfcraft_engine import optimize_pdf

        original_size = os.path.getsize(input_path)
        settings = self._get_pdf_settings(original_size)
        optimize_pdf(input_path, output_path, settings, self._should_cancel)
        new_size = os.path.getsize(output_path)
        if new_size < original_size:
            ratio = (1 - new_size / original_size) * 100
            return True, self._get_compression_method_name(settings), ratio
        return False, "", 0.0

    def _get_pdf_settings(self, file_size):
        profile_name = self.pdf_method
        if profile_name not in {"max", "quality", "optimize"}:
            profile_name = "auto_large" if file_size > _LARGE_PDF_THRESHOLD_BYTES else "auto_standard"
        return {
            **_PDF_PROFILES[profile_name],
        }

    def _get_compression_method_name(self, settings):
        return settings.get("method_name", "Стандарт")
