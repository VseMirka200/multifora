"""Единый реестр форматов конвертации документов и изображений.

Входные и выходные форматы разделены намеренно: приложение может читать
формат, но не обязано уметь надёжно сохранять данные обратно в него.
"""

from __future__ import annotations

from collections.abc import Iterable

from core.conversion_formats import DOCUMENT_FORMATS as DOCUMENT_FORMATS
from core.conversion_formats import FORMAT_EXTENSIONS as FORMAT_EXTENSIONS
from core.conversion_formats import IMAGE_SOURCE_FORMATS
from core.conversion_formats import OFFICE_INPUTS as OFFICE_INPUTS
from core.conversion_formats import OFFICE_OUTPUTS as OFFICE_OUTPUTS
from core.conversion_formats import OFFICE_ROUTES as OFFICE_ROUTES
from core.conversion_formats import PDF_IMAGE_TARGETS as PDF_IMAGE_TARGETS
from core.conversion_formats import format_for_path as format_for_path
from core.conversion_formats import matches_format as matches_format
from core.conversion_formats import suffix_for_format as suffix_for_format
from core.file_types import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS
from core.file_types import FILE_TYPE_EXTENSIONS as FILE_TYPE_EXTENSIONS
from core.file_types import KNOWN_FILE_EXTENSIONS as KNOWN_FILE_EXTENSIONS

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

_OPTIMIZED_DOCUMENT_ROUTES: dict[tuple[str, str], str] = {
    ("DOCX", "PDF"): "docx_to_pdf",
    ("PDF", "DOCX"): "pdf_to_docx",
    ("ODT", "PDF"): "odt_to_pdf",
    ("PDF", "ODT"): "pdf_to_odt",
}


def conversion_type_for_formats(category: str, source: str, target: str) -> str:
    if category != DOCUMENT_CATEGORY:
        return "auto_image"
    return _OPTIMIZED_DOCUMENT_ROUTES.get((source, target), "auto_document")


CATEGORY_SOURCE_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: DOCUMENT_FORMATS,
    IMAGE_CATEGORY: IMAGE_SOURCE_FORMATS,
}


# PDF доступен как цель для изображений, потому что каждое изображение можно
# сохранить в отдельный PDF, в том числе при обработке смешанного набора.
CATEGORY_TARGET_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: DOCUMENT_FORMATS,
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

CATEGORY_TARGET_FORMATS[DOCUMENT_CATEGORY] += PDF_IMAGE_TARGETS


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
    if normalized_category == DOCUMENT_CATEGORY and normalized_source in OFFICE_ROUTES:
        return [target for target in targets if target in OFFICE_ROUTES[normalized_source]]
    if normalized_category == DOCUMENT_CATEGORY and normalized_source != "PDF":
        targets = [target for target in targets if target not in PDF_IMAGE_TARGETS]
    if is_mixed_source_label(normalized_category, normalized_source):
        return targets
    return [target for target in targets if target != normalized_source]


def category_for_file_type(file_type: str) -> str | None:
    """Возвращает категорию конвертации по внутреннему типу файла."""
    return _FILE_TYPE_CATEGORIES.get(_normalize_label(file_type).lower())


def extensions_for_category(category: str) -> tuple[str, ...]:
    """Возвращает все входные расширения категории."""
    formats = CATEGORY_SOURCE_FORMATS.get(_normalize_label(category), ())
    return _extensions_for_formats(formats)


def build_file_dialog_filter() -> str:
    supported = " ".join(f"*{extension}" for extension in sorted(KNOWN_FILE_EXTENSIONS))
    documents = " ".join(f"*{extension}" for extension in DOCUMENT_EXTENSIONS)
    images = " ".join(f"*{extension}" for extension in IMAGE_EXTENSIONS)
    return f"Поддерживаемые файлы ({supported});;Документы ({documents});;Изображения ({images})"
