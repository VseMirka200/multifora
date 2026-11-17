"""Единый реестр форматов конвертации документов и изображений.

Входные и выходные форматы разделены намеренно: приложение может читать
формат, но не обязано уметь надёжно сохранять данные обратно в него.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

from app.core.file_types import FILE_TYPE_EXTENSIONS as FILE_TYPE_EXTENSIONS
from app.core.file_types import KNOWN_FILE_EXTENSIONS as KNOWN_FILE_EXTENSIONS
from app.core.file_types import build_file_dialog_filter as build_file_dialog_filter

DOCUMENT_CATEGORY = "Документы"
IMAGE_CATEGORY = "Изображения"
CONVERSION_CATEGORIES = (DOCUMENT_CATEGORY, IMAGE_CATEGORY)

CATEGORY_FILE_TYPES: dict[str, str] = {
    DOCUMENT_CATEGORY: "document",
    IMAGE_CATEGORY: "image",
}
_FILE_TYPE_CATEGORIES = {file_type: category for category, file_type in CATEGORY_FILE_TYPES.items()}

MIXED_SOURCE_LABELS: dict[str, str] = {
    DOCUMENT_CATEGORY: "Любой поддерживаемый документ",
    IMAGE_CATEGORY: "Любое поддерживаемое изображение",
}

CATEGORY_SOURCE_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: (
        "DOCX",
        "PDF",
        "ODT",
        "RTF",
        "TXT",
        "HTML",
    ),
    IMAGE_CATEGORY: (
        "JPG",
        "JPEG",
        "PNG",
        "WEBP",
        "BMP",
        "TIFF",
        "GIF",
        "ICO",
        "TGA",
        "PCX",
        "JP2",
        "QOI",
        "DDS",
        "ICNS",
        "XBM",
        "SGI",
        "PPM",
        "PGM",
        "PBM",
        "AVIF",
        "HEIC",
        "HEIF",
        "SVG",
        "PSD",
    ),
}

# PDF доступен как цель для изображений, потому что каждое изображение можно
# сохранить в отдельный PDF, в том числе при обработке смешанного набора.
CATEGORY_TARGET_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: (
        "DOCX",
        "PDF",
        "ODT",
        "RTF",
        "TXT",
        "HTML",
    ),
    IMAGE_CATEGORY: (
        "JPG",
        "JPEG",
        "PNG",
        "WEBP",
        "BMP",
        "TIFF",
        "GIF",
        "ICO",
        "TGA",
        "PCX",
        "JP2",
        "QOI",
        "DDS",
        "EPS",
        "ICNS",
        "XBM",
        "SGI",
        "PPM",
        "PGM",
        "PBM",
        "AVIF",
        "HEIC",
        "HEIF",
        "PDF",
        "SVG",
    ),
}

FORMAT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "DOC": (".doc",),
    "DOCX": (".docx",),
    "PDF": (".pdf",),
    "ODT": (".odt",),
    "RTF": (".rtf",),
    "TXT": (".txt",),
    "HTML": (".html", ".htm"),
    "JPG": (".jpg", ".jpe"),
    "JPEG": (".jpeg", ".jfif"),
    "PNG": (".png",),
    "WEBP": (".webp",),
    "BMP": (".bmp", ".dib"),
    "TIFF": (".tif", ".tiff"),
    "GIF": (".gif",),
    "ICO": (".ico",),
    "TGA": (".tga", ".targa"),
    "PCX": (".pcx",),
    "JP2": (".jp2", ".j2k", ".j2c", ".jpf", ".jpx"),
    "QOI": (".qoi",),
    "DDS": (".dds",),
    "EPS": (".eps",),
    "ICNS": (".icns",),
    "XBM": (".xbm",),
    "SGI": (".sgi", ".rgb", ".rgba", ".bw"),
    "PPM": (".ppm",),
    "PGM": (".pgm",),
    "PBM": (".pbm",),
    "AVIF": (".avif",),
    "HEIC": (".heic",),
    "HEIF": (".heif", ".hif"),
    "SVG": (".svg",),
    "PSD": (".psd",),
}

PDF_IMAGE_TARGETS = ("JPG", "JPEG", "PNG", "WEBP", "TIFF", "BMP")
CATEGORY_TARGET_FORMATS[DOCUMENT_CATEGORY] += PDF_IMAGE_TARGETS


_CANONICAL_SUFFIXES: dict[str, str] = {
    "JPG": ".jpg",
    "JPEG": ".jpeg",
    "TIFF": ".tiff",
    "HTML": ".html",
    "HEIC": ".heic",
    "HEIF": ".heif",
    "JP2": ".jp2",
}

_EXTENSION_FORMATS = {
    extension: format_label for format_label, extensions in FORMAT_EXTENSIONS.items() for extension in extensions
}


def _normalize_label(value: object) -> str:
    return str(value or "").strip()


def _extensions_for_formats(format_labels: Iterable[str]) -> tuple[str, ...]:
    return tuple(extension for format_label in format_labels for extension in FORMAT_EXTENSIONS.get(format_label, ()))


def source_formats_for_category(category: str) -> list[str]:
    """Возвращает поддерживаемые входные форматы категории."""
    return list(CATEGORY_SOURCE_FORMATS.get(_normalize_label(category), ()))


def target_formats_for_category(category: str) -> list[str]:
    """Возвращает поддерживаемые выходные форматы категории."""
    return list(CATEGORY_TARGET_FORMATS.get(_normalize_label(category), ()))


def mixed_source_label_for_category(category: str) -> str:
    """Возвращает подпись режима смешанных исходных форматов."""
    return MIXED_SOURCE_LABELS.get(_normalize_label(category), "")


def is_mixed_source_label(category: str, label: str) -> bool:
    """Проверяет, выбран ли режим смешанных исходных форматов."""
    normalized_label = _normalize_label(label)
    return bool(normalized_label) and normalized_label == mixed_source_label_for_category(category)


def compatible_targets_for_source(category: str, source_label: str) -> list[str]:
    """Возвращает доступные цели для одного источника или смешанного режима."""
    normalized_category = _normalize_label(category)
    normalized_source = _normalize_label(source_label)
    targets = target_formats_for_category(normalized_category)
    if normalized_category == DOCUMENT_CATEGORY and normalized_source != "PDF":
        targets = [target for target in targets if target not in PDF_IMAGE_TARGETS]
    if is_mixed_source_label(normalized_category, normalized_source):
        return targets
    return [target for target in targets if target != normalized_source]


def category_for_file_type(file_type: str) -> str | None:
    """Возвращает категорию конвертации по внутреннему типу файла."""
    return _FILE_TYPE_CATEGORIES.get(_normalize_label(file_type).lower())


def format_for_path(path: str) -> str | None:
    """Определяет формат по расширению пути."""
    extension = os.path.splitext(str(path or ""))[1].lower()
    return _EXTENSION_FORMATS.get(extension)


def suffix_for_format(format_label: str) -> str:
    """Возвращает каноническое расширение выходного файла."""
    label = _normalize_label(format_label)
    if label in _CANONICAL_SUFFIXES:
        return _CANONICAL_SUFFIXES[label]
    extensions = FORMAT_EXTENSIONS.get(label, ())
    return extensions[0] if extensions else ""


def matches_format(path: str, format_label: str) -> bool:
    """Проверяет соответствие расширения пути выбранному формату."""
    extension = os.path.splitext(str(path or ""))[1].lower()
    return extension in FORMAT_EXTENSIONS.get(_normalize_label(format_label), ())


def extensions_for_category(category: str) -> tuple[str, ...]:
    """Возвращает все входные расширения категории."""
    formats = CATEGORY_SOURCE_FORMATS.get(_normalize_label(category), ())
    return _extensions_for_formats(formats)
