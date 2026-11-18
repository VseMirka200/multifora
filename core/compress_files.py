"""Сжатие и публикация отдельных файлов без зависимости от Qt."""

import os
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core import deps
from core.filesystem import publish_new_file
from core.image_optimizer import save_optimized_image

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


def pdf_settings(profile_name: str, file_size: int) -> dict:
    if profile_name not in {"max", "quality", "optimize"}:
        profile_name = "auto_large" if file_size > _LARGE_PDF_THRESHOLD_BYTES else "auto_standard"
    return {
        **_PDF_PROFILES[profile_name],
    }

def _publish(staged: Path, source: str, destination: str, replace: bool) -> None:
    if replace:
        os.replace(staged, source)
    else:
        publish_new_file(staged, destination)


def compress_image(
    source: str,
    destination: str,
    extension: str,
    quality: int,
    *,
    replace: bool,
    should_cancel: Callable[[], bool],
) -> float | None:
    original_size = os.path.getsize(source)
    with TemporaryDirectory(dir=os.path.dirname(os.path.abspath(destination))) as folder:
        staged = Path(folder, "image" + extension)
        with deps.Image.open(source) as image:
            save_optimized_image(image, staged, extension, quality)
        if should_cancel():
            raise InterruptedError
        size = staged.stat().st_size
        if not size:
            raise OSError("сжатый файл пустой")
        if size >= original_size:
            return None
        _publish(staged, source, destination, replace)
        return (1 - size / original_size) * 100


def compress_pdf(
    source: str,
    destination: str,
    *,
    replace: bool,
    should_cancel: Callable[[], bool],
    optimize: Callable[[str, Path], tuple[bool, str, float]],
) -> tuple[str, float] | None:
    with TemporaryDirectory(dir=os.path.dirname(os.path.abspath(destination))) as folder:
        staged = Path(folder, "document.pdf")
        success, profile_name, ratio = optimize(source, staged)
        if should_cancel():
            raise InterruptedError
        if not success:
            return None
        _publish(staged, source, destination, replace)
        return profile_name, ratio
