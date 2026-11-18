import os

import app.core.deps as deps
from app.core.app_utils import _debug_log
from app.core.models import FileItem
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
        "color_resolution": 300,
        "gray_resolution": 300,
        "jpeg_quality": 90,
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


def _remove_file_safely(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    try:
        os.remove(path)
    except OSError as error:
        _debug_log(f"Не удалось удалить временный файл {path}: {error}")


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

    def _compress_image_files(self):
        total = len(self.files)
        results = []
        updated = []

        for i, file in enumerate(self.files):
            if finish_if_cancelled(self, results, updated):
                return
            try:
                if file.is_file and file.file_type == "image":
                    ext = os.path.splitext(file.name)[1].lower()
                    compressed_path = self._image_compression_target_path(file, ext)

                    if deps.HAS_PIL:
                        try:
                            with deps.Image.open(file.path) as img:
                                save_optimized_image(
                                    img,
                                    compressed_path,
                                    ext,
                                    self.compression_level,
                                )

                                original_size = os.path.getsize(file.path)
                                compressed_size = os.path.getsize(compressed_path)

                                if compressed_size < original_size:
                                    ratio = (1 - compressed_size / original_size) * 100
                                    if (
                                        getattr(
                                            self,
                                            "image_output_mode",
                                            "alongside",
                                        )
                                        == "replace"
                                    ):
                                        try:
                                            os.replace(compressed_path, file.path)
                                            updated.append((file, file.path))
                                            self.status.emit(
                                                f"Изображение сжато и заменено: {file.name} (-{ratio:.1f}%)"
                                            )
                                        except Exception as replace_error:
                                            msg = f"Ошибка замены {file.name}: {replace_error}"
                                            record_file_error(self, file, msg)
                                            _remove_file_safely(compressed_path)
                                    else:
                                        results.append(FileItem(compressed_path))
                                        self.status.emit(f"Изображение сжато: {file.name} (-{ratio:.1f}%)")
                                else:
                                    os.remove(compressed_path)
                                    self.status.emit(f"Изображение уже оптимизировано: {file.name}")

                        except Exception as img_error:
                            _remove_file_safely(compressed_path)
                            msg = f"Ошибка сжатия {file.name}: {img_error}"
                            record_file_error(self, file, msg)
                    else:
                        msg = "Для сжатия изображений установите Pillow: pip install Pillow"
                        record_file_error(self, file, msg)
                else:
                    msg = f"Файл {file.name} не является изображением или не поддерживается"
                    record_file_error(self, file, msg)

            except Exception as e:
                msg = f"Ошибка сжатия {file.name}: {e!s}"
                record_file_error(self, file, msg)

            emit_progress(self, i, total)
            self.status.emit(f"Сжатие: {file.name}")

        self._emit_finished(results, updated)

    def _compress_pdf_files(self):
        _debug_log(f"Начало сжатия PDF: {len(self.files)} файлов")
        total = len(self.files)
        results = []
        updated = []
        self._last_pdf_error = ""

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self._emit_finished(results, updated)
                return
            try:
                if not (file.is_file and file.path.lower().endswith(".pdf")):
                    continue

                original_size = os.path.getsize(file.path)
                compressed_path = self._get_unique_path(file.path.rsplit(".", 1)[0] + "_compressed.pdf")

                success = False
                compression_method = ""
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    _remove_file_safely(compressed_path)
                    self._emit_finished(results, updated)
                    return

                if not success:
                    success, compression_method, _ = self._compress_pdf_with_pdfcraft(file.path, compressed_path)
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    _remove_file_safely(compressed_path)
                    self._emit_finished(results, updated)
                    return

                if success and os.path.exists(compressed_path):
                    new_size = os.path.getsize(compressed_path)

                    if new_size < original_size:
                        if getattr(self, "replace_pdf", False):
                            try:
                                os.replace(compressed_path, file.path)
                                updated.append((file, file.path))
                                ratio = (1 - new_size / original_size) * 100
                                self.status.emit(
                                    f"PDF сжат и заменен ({compression_method}): {file.name} (-{ratio:.1f}%)"
                                )
                            except Exception as e:
                                msg = f"Ошибка замены PDF {file.name}: {e!s}"
                                record_file_error(self, file, msg)
                                _remove_file_safely(compressed_path)
                        else:
                            results.append(FileItem(compressed_path))
                            ratio = (1 - new_size / original_size) * 100
                            self.status.emit(f"PDF сжат ({compression_method}): {file.name} (-{ratio:.1f}%)")
                    else:
                        _remove_file_safely(compressed_path)
                        self.status.emit(f"PDF уже оптимизирован: {file.name}")

                else:
                    if not self._last_pdf_error:
                        if os.path.exists(compressed_path):
                            try:
                                out_size = os.path.getsize(compressed_path)
                                if out_size == 0:
                                    self._last_pdf_error = "сжатый файл пустой"
                                elif out_size >= original_size:
                                    self._last_pdf_error = "уже оптимизирован"
                            except OSError as error:
                                _debug_log(f"Не удалось проверить результат сжатия PDF: {error}")
                                self._last_pdf_error = "не удалось проверить результат"
                        else:
                            self._last_pdf_error = "выходной файл не создан"
                    if self._last_pdf_error == "уже оптимизирован":
                        self.status.emit(f"PDF уже оптимален: {file.name}")
                    else:
                        reason = f" ({self._last_pdf_error})" if self._last_pdf_error else ""
                        message = f"Не удалось сжать PDF: {file.name}{reason}"
                        self.status.emit(message)
                        record_file_error(self, file, message)
                    _remove_file_safely(compressed_path)
                    self._last_pdf_error = ""

            except Exception as e:
                msg = f"Ошибка PDF: {str(e)[:100]}"
                record_file_error(self, file, msg)

            self.progress.emit(int((i + 1) / total * 100))

        self._emit_finished(results, updated)

    def _compress_pdf_with_pdfcraft(self, input_path: str, output_path: str) -> tuple[bool, str, float]:
        from core.workers.pdfcraft_engine import optimize_pdf

        try:
            original_size = os.path.getsize(input_path)
            settings = self._get_pdf_settings()
            optimize_pdf(input_path, output_path, settings, self._should_cancel)
            new_size = os.path.getsize(output_path)
            if new_size < original_size:
                ratio = (1 - new_size / original_size) * 100
                return True, f"PDFCraft ({self._get_compression_method_name(settings)})", ratio
            return False, "", 0.0
        except InterruptedError:
            self._last_pdf_error = "отменено"
            return False, "", 0.0
        except Exception as error:
            self._last_pdf_error = f"PDFCraft: {error}"
            return False, "", 0.0

    def _get_pdf_settings(self):
        profile_name = self.pdf_method
        if profile_name not in {"max", "quality", "optimize"}:
            if self.files:
                file_size = os.path.getsize(self.files[0].path)
                profile_name = "auto_large" if file_size > _LARGE_PDF_THRESHOLD_BYTES else "auto_standard"
            else:
                profile_name = "standard"
        return {
            **_PDF_PROFILES[profile_name],
        }

    def _get_compression_method_name(self, settings):
        return settings.get("method_name", "Стандарт")
