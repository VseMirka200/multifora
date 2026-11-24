"""Запись изображений без неявного удаления прозрачности и цветовых профилей."""

from __future__ import annotations

from contextlib import ExitStack
from hashlib import blake2s

JPEG_EXTENSIONS = frozenset({".jpg", ".jpe", ".jpeg", ".jfif"})
QUALITY_EXTENSIONS = JPEG_EXTENSIONS | {".webp"}


class ImageCompressionSkipped(ValueError):
    """Изображение нельзя безопасно опубликовать после сжатия."""


def image_structure(image, should_cancel):
    frames = []
    count = getattr(image, "n_frames", 1)
    animated = count > 1 and image.format in {"GIF", "PNG", "WEBP"}
    loop = image.info.get("loop") if animated else None
    default_image = bool(image.info.get("default_image"))
    for index in range(count):
        if should_cancel():
            raise InterruptedError
        image.seek(index)
        image.load()
        duration = image.info.get("duration", 0) if animated else None
        pixels = None
        if count > 1:
            if image.format in {"GIF", "PNG"}:
                with image.convert("RGBA") as rgba, rgba.convert("RGBa") as frame:
                    pixels = blake2s(frame.tobytes()).digest()
            elif image.format == "WEBP":
                with image.convert("RGBA") as frame, frame.getchannel("A") as alpha:
                    pixels = blake2s(alpha.tobytes()).digest()
            elif image.format == "TIFF":
                pixels = (image.mode, blake2s(image.tobytes()).digest(), image.getpalette())
        frames.append((image.size, duration, pixels))
    image.seek(0)
    return loop, default_image, frames


def _save_multiframe(image, destination, quality, metadata, should_cancel):
    from PIL import ImageSequence

    image_format = image.format
    if image_format == "TIFF":
        image.save(destination, format="TIFF", save_all=True, compression="tiff_deflate", **metadata)
        return
    if image_format not in {"GIF", "PNG", "WEBP"}:
        raise ImageCompressionSkipped("сжатие с сохранением всех кадров этого формата недоступно")

    with ExitStack() as resources:
        frames, durations = [], []
        for frame in ImageSequence.Iterator(image):
            if should_cancel():
                raise InterruptedError
            frames.append(resources.enter_context(frame.convert("RGBA")))
            durations.append(frame.info.get("duration", 0))
        image.seek(0)
        options = {**metadata, "save_all": True, "append_images": frames[1:], "duration": durations}
        if "loop" in image.info:
            options["loop"] = image.info["loop"]
        if image_format == "GIF":
            options.update(optimize=True, disposal=2)
        elif image_format == "PNG":
            default_image = bool(image.info.get("default_image"))
            options.update(optimize=True, default_image=default_image, disposal=0, blend=0)
            if default_image:
                options["duration"] = durations[1:]
        else:
            options.update(quality=quality, method=6, background=image.info.get("background", (0, 0, 0, 0)))
        frames[0].save(destination, format=image_format, **options)


def save_optimized_image(
    image, destination: str, extension: str, quality: int, *, should_cancel=lambda: False
) -> None:
    """Сохраняет формат и режим изображения, кроме JPEG, не поддерживающего alpha."""
    ext = extension.lower()
    quality = max(1, min(95, int(quality)))
    info = image.info
    metadata = {
        key: info[key] for key in ("icc_profile", "exif") if info.get(key)
    }
    if getattr(image, "n_frames", 1) > 1:
        _save_multiframe(image, destination, quality, metadata, should_cancel)
    elif ext in JPEG_EXTENSIONS:
        if image.mode == "RGB":
            rgb = image
        elif image.mode in {"RGBA", "LA"} or "transparency" in info:
            rgba = image.convert("RGBA")
            from PIL import Image

            rgb = Image.new("RGB", rgba.size, (255, 255, 255))
            rgb.paste(rgba, mask=rgba.getchannel("A"))
        else:
            rgb = image.convert("RGB")
        rgb.save(
            destination,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            **metadata,
        )
    elif ext == ".png":
        # RGBA/LA и палитровая прозрачность остаются в исходном режиме.
        image.save(
            destination,
            format="PNG",
            optimize=True,
            **metadata,
        )
    elif ext == ".webp":
        image.save(
            destination, format="WEBP", quality=quality, method=6, **metadata
        )
    else:
        image.save(destination)
