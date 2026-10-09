"""Запись изображений без неявного удаления прозрачности и цветовых профилей."""
from __future__ import annotations


def save_optimized_image(image, destination: str, extension: str, quality: int) -> None:
    """Сохраняет формат и режим изображения, кроме JPEG, не поддерживающего alpha."""
    ext = extension.lower()
    quality = max(1, min(95, int(quality)))
    info = image.info
    metadata = {
        key: info[key]
        for key in ("icc_profile", "exif")
        if info.get(key)
    }
    if ext in {".jpg", ".jpeg"}:
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
            destination, format="JPEG", quality=quality, optimize=True,
            progressive=True, **metadata,
        )
    elif ext == ".png":
        # RGBA/LA и палитровая прозрачность остаются в исходном режиме.
        image.save(
            destination, format="PNG", optimize=True,
            compress_level=min(9, quality // 10), **metadata,
        )
    elif ext == ".webp":
        image.save(destination, format="WEBP", quality=quality, method=6, **metadata)
    else:
        image.save(destination)
