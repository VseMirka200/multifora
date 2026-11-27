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
from core.conversion_formats import PRESENTATION_FORMATS
from core.file_types import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, PRESENTATION_EXTENSIONS
from core.file_types import FILE_TYPE_EXTENSIONS as FILE_TYPE_EXTENSIONS
from core.file_types import KNOWN_FILE_EXTENSIONS as KNOWN_FILE_EXTENSIONS

from core.craft_routes import (
    WORD_INPUTS, WORD_OUTPUTS, DECK_INPUTS, DECK_OUTPUTS, GRID_INPUTS, GRID_OUTPUTS,
    PHOTO_INPUTS, PHOTO_OUTPUTS, VECTOR_INPUTS, VECTOR_OUTPUTS, PDF_OUTPUTS, route,
)
DOCUMENT_CATEGORY = "Документы"
IMAGE_CATEGORY = "Изображения"
PRESENTATION_CATEGORY = "Презентации"
SPREADSHEET_CATEGORY = "Таблицы"
CONVERSION_CATEGORIES = (DOCUMENT_CATEGORY, IMAGE_CATEGORY, PRESENTATION_CATEGORY, SPREADSHEET_CATEGORY)
CATEGORY_FILE_TYPES = {DOCUMENT_CATEGORY: "document", IMAGE_CATEGORY: "image", PRESENTATION_CATEGORY: "presentation", SPREADSHEET_CATEGORY: "spreadsheet"}
_FILE_TYPE_CATEGORIES = {v: k for k, v in CATEGORY_FILE_TYPES.items()}
MIXED_SOURCE_LABELS = {DOCUMENT_CATEGORY: "Любой поддерживаемый документ", IMAGE_CATEGORY: "Любое поддерживаемое изображение", PRESENTATION_CATEGORY: "Любая поддерживаемая презентация", SPREADSHEET_CATEGORY: "Любая поддерживаемая таблица"}
CATEGORY_SOURCE_FORMATS = {DOCUMENT_CATEGORY: (*WORD_INPUTS, "PDF"), IMAGE_CATEGORY: (*PHOTO_INPUTS, *VECTOR_INPUTS), PRESENTATION_CATEGORY: DECK_INPUTS, SPREADSHEET_CATEGORY: GRID_INPUTS}
CATEGORY_TARGET_FORMATS = {DOCUMENT_CATEGORY: tuple(dict.fromkeys((*WORD_OUTPUTS, *PDF_OUTPUTS))), IMAGE_CATEGORY: tuple(dict.fromkeys((*PHOTO_OUTPUTS,*VECTOR_OUTPUTS))), PRESENTATION_CATEGORY: DECK_OUTPUTS, SPREADSHEET_CATEGORY: GRID_OUTPUTS}

def conversion_type_for_formats(category: str, source: str, target: str) -> str:
    return {IMAGE_CATEGORY: "auto_image", PRESENTATION_CATEGORY: "presentation", SPREADSHEET_CATEGORY: "spreadsheet"}.get(category, "auto_document")


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
    category = _normalize_label(category)
    source_label = _normalize_label(source_label)
    sources = source_formats_for_category(category) if is_mixed_source_label(category, source_label) else [source_label]
    return [target for target in target_formats_for_category(category) if any(route(source, target) for source in sources)]


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
    presentations = " ".join(f"*{extension}" for extension in PRESENTATION_EXTENSIONS)
    return f"Поддерживаемые файлы ({supported});;Документы ({documents});;Изображения ({images});;Презентации ({presentations})"
