"""Подготовка кадров и запись изображений без управления очередью конвертации."""

import base64
from io import BytesIO

from app.core.app_utils import _debug_log
from app.core.deps import HAS_HEIF, HAS_PIL, HAS_PYMUPDF, Image

_IMAGE_SAVE_FORMATS: dict[str, str] = {
    "JPG": "JPEG",
    "JPEG": "JPEG",
    "PNG": "PNG",
    "WEBP": "WEBP",
    "BMP": "BMP",
    "TIFF": "TIFF",
    "GIF": "GIF",
    "ICO": "ICO",
    "TGA": "TGA",
    "PCX": "PCX",
    "JP2": "JPEG2000",
    "QOI": "QOI",
    "DDS": "DDS",
    "EPS": "EPS",
    "ICNS": "ICNS",
    "XBM": "XBM",
    "SGI": "SGI",
    "PPM": "PPM",
    "PGM": "PPM",
    "PBM": "PPM",
    "AVIF": "AVIF",
    "HEIC": "HEIF",
    "HEIF": "HEIF",
}


_IMAGE_RGB_TARGETS = frozenset(
    {"JPG", "JPEG", "BMP", "PCX", "PPM", "JP2", "EPS", "SGI"}
)

_IMAGE_ALPHA_TARGETS = frozenset(
    {"PNG", "WEBP", "TIFF", "TGA", "AVIF", "HEIC", "HEIF", "QOI", "DDS", "ICNS"}
)

_ANIMATED_IMAGE_TARGETS = frozenset({"GIF", "WEBP", "TIFF"})


class ImageEncodingMixin:
    # Сохраняет цвет, прозрачность и анимацию с учётом возможностей целевого формата.

    @staticmethod
    def _flatten_transparency(img):
        # Для форматов без альфа-канала возвращаем RGB-копию на белом фоне.
        has_palette_transparency = (
            img.mode == "P" and "transparency" in getattr(img, "info", {})
        )
        if img.mode not in {"RGBA", "LA"} and not has_palette_transparency:
            return img.convert("RGB")

        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    def _prepare_image_frame(self, frame, target_format: str):
        # Принимает кадр Pillow и формат, возвращает отдельный кадр для сохранения.
        # Исходное изображение остаётся доступным для обработки следующих кадров.
        target_format = str(target_format or "").upper()
        img = frame.copy()

        if target_format in _IMAGE_RGB_TARGETS:
            return self._flatten_transparency(img)
        if target_format == "PGM":
            return img.convert("L")
        if target_format in {"PBM", "XBM"}:
            return img.convert("1")
        if target_format == "GIF":
            if img.mode not in ("P", "L"):
                return img.convert("RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
            return img
        if target_format == "ICO":
            if img.mode not in ("RGBA", "RGB"):
                img = img.convert("RGBA")
            max_side = max(img.size) if img.size else 0
            if max_side > 256:
                img.thumbnail((256, 256), Image.Resampling.LANCZOS)
            return img
        if target_format in _IMAGE_ALPHA_TARGETS:
            if img.mode not in ("RGB", "RGBA", "L", "LA"):
                img = img.convert("RGBA")
            return img
        return img

    @staticmethod
    def _image_save_format(target_format: str) -> str:
        return _IMAGE_SAVE_FORMATS.get(str(target_format or "").upper(), "")

    def _load_svg_as_pillow_image(self, file_path: str):
        if not HAS_PYMUPDF or not HAS_PIL:
            raise Exception("Для SVG нужны PyMuPDF и Pillow")
        try:
            import pymupdf as fitz

            with fitz.open(file_path) as document:
                if document.page_count < 1:
                    raise Exception("SVG не содержит страницы")
                page = document.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=True)
                mode = "RGBA" if pix.alpha else "RGB"
                return Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        except Exception as error:
            raise Exception(f"Ошибка чтения SVG: {error}") from error

    @staticmethod
    def _image_save_options(target_format: str) -> dict[str, object]:
        """Возвращает параметры Pillow для выбранного формата."""
        options: dict[str, object] = {}
        if target_format in {"JPG", "JPEG"}:
            options.update(quality=92, optimize=True)
        elif target_format == "PNG":
            options["optimize"] = True
        elif target_format == "WEBP":
            options.update(quality=92, method=6)
        elif target_format == "TIFF":
            options["compression"] = "tiff_deflate"
        elif target_format == "GIF":
            options["optimize"] = True
        elif target_format in {"AVIF", "HEIC", "HEIF"}:
            options["quality"] = 90
        return options

    def _save_animated_pillow_image(
        self,
        source_image,
        output_path: str,
        target_format: str,
        save_format: str,
        save_options: dict[str, object],
        image_sequence,
    ) -> None:
        frames = [
            self._prepare_image_frame(frame, target_format)
            for frame in image_sequence.Iterator(source_image)
        ]
        if not frames:
            raise Exception("Изображение не содержит кадров")

        first, rest = frames[0], frames[1:]
        try:
            first.save(
                output_path,
                save_format,
                save_all=True,
                append_images=rest,
                duration=source_image.info.get("duration", 100),
                loop=source_image.info.get("loop", 0),
                **save_options,
            )
        finally:
            for frame in frames:
                try:
                    frame.close()
                except Exception as close_error:
                    _debug_log(f"Не удалось закрыть кадр изображения: {close_error}")

    @staticmethod
    def _ico_sizes(frame) -> list[tuple[int, int]]:
        width, height = frame.size
        max_side = max(width, height)
        sizes = [
            (size, size)
            for size in (16, 24, 32, 48, 64, 128, 256)
            if size <= max_side
        ]
        return sizes or [(width, height)]

    def _save_pillow_image(
        self,
        source_image,
        output_path: str,
        target_format: str,
    ) -> None:
        # Записывает изображение Pillow по заданному пути и формату, ничего не возвращает.
        # Для GIF, WEBP и TIFF сохраняет все кадры; временные кадры закрывает после записи.
        normalized_target = str(target_format or "").upper()
        if normalized_target == "SVG":
            self._save_embedded_svg(source_image, output_path)
            return
        save_format = self._image_save_format(normalized_target)
        if not save_format:
            raise Exception(f"Неизвестный формат изображения: {normalized_target}")
        if normalized_target in {"HEIC", "HEIF"} and not HAS_HEIF:
            raise Exception("Для HEIC/HEIF установите pillow-heif")

        try:
            from PIL import ImageSequence
        except ImportError:
            ImageSequence = None

        frame_count = int(getattr(source_image, "n_frames", 1) or 1)
        preserve_animation = (
            frame_count > 1 and normalized_target in _ANIMATED_IMAGE_TARGETS
        )
        save_options = self._image_save_options(normalized_target)

        if preserve_animation and ImageSequence is not None:
            self._save_animated_pillow_image(
                source_image,
                output_path,
                normalized_target,
                save_format,
                save_options,
                ImageSequence,
            )
            return

        frame = self._prepare_image_frame(source_image, normalized_target)
        try:
            if normalized_target == "ICO":
                save_options["sizes"] = self._ico_sizes(frame)
            frame.save(output_path, save_format, **save_options)
        finally:
            try:
                frame.close()
            except Exception as close_error:
                _debug_log(f"Не удалось закрыть подготовленное изображение: {close_error}")

    def _save_embedded_svg(self, source_image, output_path: str) -> None:
        """Встраивает статичный PNG в автономный SVG, сохраняя прозрачность."""
        from PIL import ImageOps

        with ImageOps.exif_transpose(source_image) as oriented:
            with self._prepare_image_frame(oriented, "PNG") as frame:
                width, height = frame.size
                with BytesIO() as buffer:
                    frame.save(buffer, "PNG")
                    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
            f'  <image width="{width}" height="{height}" '
            f'xlink:href="data:image/png;base64,{payload}"/>\n'
            '</svg>\n'
        )
        with open(output_path, "w", encoding="utf-8") as stream:
            stream.write(svg)
