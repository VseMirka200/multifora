"""Конвертация графики: отдельная зона ответственности и зависимости."""

from __future__ import annotations

import os
import shutil
import tempfile

from app.core.app_utils import _debug_log
from app.core.conversion_formats import (
    IMAGE_CATEGORY,
    PDF_IMAGE_TARGETS,
    format_for_path,
    source_formats_for_category,
    suffix_for_format,
)
from app.core.deps import HAS_PIL, Image
from app.core.models import FileItem
from core.workers.atomic_output import atomic_output_path


class ImageConversionMixin:
    """Конвертация графики, изолированная от документных форматов."""

    def _convert_image_to_image(
        self, file: FileItem, target_format: str
    ) -> str:
        if not HAS_PIL:
            raise Exception("Установите Pillow для конвертации изображений")

        source_format = format_for_path(file.path)
        if source_format not in source_formats_for_category(IMAGE_CATEGORY):
            extension = os.path.splitext(file.path)[1]
            raise Exception(
                f"Неподдерживаемый формат изображения: {extension}"
            )
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
            image = (
                self._load_svg_as_pillow_image(file.path)
                if source_format == "SVG"
                else Image.open(file.path)
            )
            if getattr(image, "format", None) == "EPS":
                raise ValueError("EPS input is not supported")
            with atomic_output_path(output_path) as temporary:
                self._save_pillow_image(image, temporary, target_format)
            return output_path
        except Exception as error:
            self._release_conversion_output_path(output_path)
            raise Exception(
                f"Ошибка конвертации изображения {source_format} → {target_format}: {error}"
            ) from error
        finally:
            if image is not None:
                try:
                    image.close()
                except Exception as close_error:
                    _debug_log(
                        f"Не удалось закрыть изображение {file.path}: {close_error}"
                    )

    def _convert_image_auto(self, file: FileItem, target_format: str) -> str:
        source_format = format_for_path(file.path)
        if source_format not in source_formats_for_category(IMAGE_CATEGORY):
            raise Exception("Файл не является поддерживаемым изображением")
        if source_format == str(target_format or "").upper():
            self.status.emit(f"Пропущен {file.name}: уже {target_format}")
            return None
        return self._convert_image_to_image(file, target_format)

    def _convert_pdf_to_image(
        self, file: FileItem, target_format: str = "JPG"
    ) -> str | list[str] | None:
        if not file.path.lower().endswith(".pdf"):
            return None
        if not HAS_PIL:
            raise Exception("Для конвертации PDF в изображения нужна библиотека Pillow")
        target_format = str(target_format or "JPG").strip().upper()
        if target_format not in PDF_IMAGE_TARGETS:
            raise ValueError(f"Неподдерживаемый формат экспорта PDF: {target_format}")

        from core.workers.pdfcraft_engine import PdfCraftUnavailableError, render_pdf_pages

        paths = []
        try:
            with tempfile.TemporaryDirectory(prefix="multifora_pdf_images_") as directory:
                pages = render_pdf_pages(file.path, directory, self._should_cancel)
                if not pages:
                    raise ValueError("PDF не содержит страниц")
                for index, page in enumerate(pages):
                    if self._should_cancel():
                        raise InterruptedError("Конвертация отменена пользователем")
                    reference = file
                    if len(pages) > 1:
                        stem = os.path.splitext(file.path)[0]
                        reference = FileItem(f"{stem}_page_{index + 1}.pdf")
                    output_path = self._conversion_output_path(
                        file, suffix_for_format(target_format), reference_file=reference
                    )
                    try:
                        with atomic_output_path(output_path) as temporary:
                            if target_format == "PNG":
                                shutil.copyfile(page, temporary)
                            else:
                                with Image.open(str(page)) as image:
                                    self._save_pillow_image(image, temporary, target_format)
                    except Exception:
                        self._release_conversion_output_path(output_path)
                        raise
                    paths.append(output_path)
                if self._should_cancel():
                    raise InterruptedError("Конвертация отменена пользователем")
            return paths[0] if len(paths) == 1 else paths
        except (InterruptedError, PdfCraftUnavailableError):
            for path in paths:
                self._discard_conversion_output(path)
            raise
        except Exception as error:
            for path in paths:
                self._discard_conversion_output(path)
            raise Exception(f"Ошибка конвертации PDF в изображения: {error}") from error

    def _convert_image_to_pdf(self, file: FileItem) -> str:
        source_format = format_for_path(file.path)
        if source_format not in source_formats_for_category(IMAGE_CATEGORY):
            return None
        if not HAS_PIL:
            raise Exception(
                "Установите Pillow для конвертации изображения в PDF"
            )

        pdf_path = self._conversion_output_path(file, ".pdf")
        image = None
        frames = []
        try:
            image = (
                self._load_svg_as_pillow_image(file.path)
                if source_format == "SVG"
                else Image.open(file.path)
            )
            if getattr(image, "format", None) == "EPS":
                raise ValueError("EPS input is not supported")
            frame_count = int(getattr(image, "n_frames", 1) or 1)
            if frame_count > 1:
                from PIL import ImageSequence

                frames.extend(
                    self._prepare_image_frame(frame, "JPG")
                    for frame in ImageSequence.Iterator(image)
                )
                first, rest = frames[0], frames[1:]
                with atomic_output_path(pdf_path) as temporary:
                    first.save(
                        temporary,
                        "PDF",
                        resolution=100.0,
                        save_all=True,
                        append_images=rest,
                    )
            else:
                with (
                    self._prepare_image_frame(image, "JPG") as frame,
                    atomic_output_path(pdf_path) as temporary,
                ):
                    frame.save(temporary, "PDF", resolution=100.0)
            return pdf_path
        except Exception as error:
            self._release_conversion_output_path(pdf_path)
            raise Exception(
                f"Ошибка конвертации изображения в PDF: {error}"
            ) from error
        finally:
            for frame in frames:
                frame.close()
            if image is not None:
                try:
                    image.close()
                except Exception as close_error:
                    _debug_log(
                        f"Не удалось закрыть изображение {file.path}: {close_error}"
                    )
