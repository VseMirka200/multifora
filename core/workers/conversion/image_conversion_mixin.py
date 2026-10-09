"""Конвертация графики: отдельная зона ответственности и зависимости."""
from __future__ import annotations

import os

from app.core.app_utils import _debug_log
from app.core.conversion_formats import (
    IMAGE_CATEGORY,
    format_for_path,
    source_formats_for_category,
    suffix_for_format,
)
from app.core.deps import HAS_PIL, HAS_PYMUPDF, Image
from app.core.models import FileItem
from core.workers.atomic_output import atomic_output_path


class ImageConversionMixin:
    """Конвертация графики, изолированная от Word/RTF/ODT логики."""

    def _convert_image_to_image(self, file: FileItem, target_format: str) -> str:
        if not HAS_PIL:
            raise Exception("Установите Pillow для конвертации изображений")

        source_format = format_for_path(file.path)
        if source_format not in source_formats_for_category(IMAGE_CATEGORY):
            extension = os.path.splitext(file.path)[1]
            raise Exception(f"Неподдерживаемый формат изображения: {extension}")
        target_format = str(target_format or "").upper()
        target_ext = suffix_for_format(target_format)
        if not target_ext:
            raise Exception(f"Неизвестный формат изображения: {target_format}")
        if source_format == target_format:
            return None
        if target_format == "PDF":
            return self._convert_image_to_pdf(file)

        output_path = self._conversion_output_path(file, target_ext)
        image = None
        try:
            if source_format == "SVG":
                image = self._load_svg_as_pillow_image(file.path)
            else:
                image = Image.open(file.path)
            with atomic_output_path(output_path) as temporary:
                self._save_pillow_image(image, temporary, target_format)
            return output_path
        except Exception as error:
            self._discard_conversion_output(output_path)
            raise Exception(
                f"Ошибка конвертации изображения {source_format} → {target_format}: {error}"
            ) from error
        finally:
            if image is not None:
                try:
                    image.close()
                except Exception as close_error:
                    _debug_log(f"Не удалось закрыть изображение {file.path}: {close_error}")

    def _convert_image_auto(self, file: FileItem, target_format: str) -> str:
        source_format = format_for_path(file.path)
        if source_format not in source_formats_for_category(IMAGE_CATEGORY):
            raise Exception("Файл не является поддерживаемым изображением")
        if source_format == str(target_format or "").upper():
            self.status.emit(f"Пропущен {file.name}: уже {target_format}")
            return None
        return self._convert_image_to_image(file, target_format)

    def _convert_pdf_to_image(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".pdf"):
            return None
        if not HAS_PYMUPDF:
            raise Exception("Установите PyMuPDF для конвертации PDF в изображение")

        image_path = self._conversion_output_path(file, ".jpg")
        try:
            import pymupdf as fitz

            with fitz.open(file.path) as pdf_document:
                if pdf_document.page_count < 1:
                    raise Exception("PDF не содержит страниц")
                page = pdf_document.load_page(0)
                # ~200 DPI при стандартных 72 DPI PDF.
                pix = page.get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72), alpha=False)
                with atomic_output_path(image_path) as temporary:
                    pix.save(temporary)
            return image_path
        except Exception as error:
            raise Exception(f"Ошибка конвертации PDF в изображение: {error}") from error

    def _convert_image_to_pdf(self, file: FileItem) -> str:
        source_format = format_for_path(file.path)
        if source_format not in source_formats_for_category(IMAGE_CATEGORY):
            return None
        if not HAS_PIL:
            raise Exception("Установите Pillow для конвертации изображения в PDF")

        pdf_path = self._conversion_output_path(file, ".pdf")
        image = None
        try:
            if source_format == "SVG":
                image = self._load_svg_as_pillow_image(file.path)
            else:
                image = Image.open(file.path)
            frame_count = int(getattr(image, "n_frames", 1) or 1)
            if frame_count > 1:
                from PIL import ImageSequence

                frames = [
                    self._flatten_transparency(frame.copy())
                    for frame in ImageSequence.Iterator(image)
                ]
                first, rest = frames[0], frames[1:]
                with atomic_output_path(pdf_path) as temporary:
                    first.save(temporary, "PDF", resolution=100.0, save_all=True, append_images=rest)
            else:
                frame = self._flatten_transparency(image)
                with atomic_output_path(pdf_path) as temporary:
                    frame.save(temporary, "PDF", resolution=100.0)
            return pdf_path
        except Exception as error:
            self._discard_conversion_output(pdf_path)
            raise Exception(f"Ошибка конвертации изображения в PDF: {error}") from error
        finally:
            if image is not None:
                try:
                    image.close()
                except Exception as close_error:
                    _debug_log(f"Не удалось закрыть изображение {file.path}: {close_error}")
