"""Реестр форматов, реально поддерживаемых CLI-движками ArtCraft."""
from __future__ import annotations

import os
from collections.abc import Iterable

DOCUMENT_CATEGORY = "Документы"
IMAGE_CATEGORY = "Изображения"
CONVERSION_CATEGORIES = (DOCUMENT_CATEGORY, IMAGE_CATEGORY)

CATEGORY_FILE_TYPES = {
    DOCUMENT_CATEGORY: "document",
    IMAGE_CATEGORY: "image",
}
_FILE_TYPE_CATEGORIES = {value: key for key, value in CATEGORY_FILE_TYPES.items()}
MIXED_SOURCE_LABELS = {
    DOCUMENT_CATEGORY: "Любой поддерживаемый документ",
    IMAGE_CATEGORY: "Любое поддерживаемое изображение",
}

# PdfCraft CLI accepts PDF, TXT/TEXT and the documented image extensions.
# DeckCraft CLI accepts .pptx and .deckcraft as inputs.
# PhotoCraft input list mirrors its published format documentation; formats
# marked read-only are sources, never output choices.
CATEGORY_SOURCE_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: ("PDF", "TXT", "PPTX", "DECKCRAFT"),
    IMAGE_CATEGORY: (
        "JPG", "JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO",
        "TGA", "QOI", "PPM", "PGM", "PBM", "PFM", "EXR", "HDR",
        "FITS", "PSD", "PSB", "PCRAFT", "ORA", "XCF", "KRA", "PDN",
        "SVG", "HEIC", "AFFINITY", "JP2", "J2K", "JPX", "PCX",
    ),
}

# PdfCraft output: PDF from text and supported image files.
# PhotoCraft output: flat/layered image formats documented as writable.
# DeckCraft output: deckcraft, PowerPoint, PDF, raster and text formats.
CATEGORY_TARGET_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: (
        "PDF", "DOCX", "PPTX", "POTX", "PPSX", "DECKCRAFT",
        "TXT", "HTML", "RTF", "MD", "PNG", "JPG", "JPEG", "TIFF", "GIF",
    ),
    IMAGE_CATEGORY: (
        "PNG", "JPG", "JPEG", "TIFF", "WEBP", "GIF", "BMP", "TGA",
        "ICO", "QOI", "PPM", "PGM", "PBM", "PFM", "EXR", "HDR",
        "FITS", "PSD", "PSB", "PCRAFT", "ORA", "PDF",
    ),
}

FORMAT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "PDF": (".pdf",),
    "DOCX": (".docx",),
    "PPTX": (".pptx",),
    "POTX": (".potx",),
    "PPSX": (".ppsx",),
    "DECKCRAFT": (".deckcraft",),
    "TXT": (".txt", ".text"),
    "HTML": (".html", ".htm"),
    "RTF": (".rtf",),
    "MD": (".md", ".markdown"),
    "JPG": (".jpg", ".jpe"),
    "JPEG": (".jpeg", ".jfif"),
    "PNG": (".png",),
    "WEBP": (".webp",),
    "BMP": (".bmp", ".dib"),
    "TIFF": (".tif", ".tiff"),
    "GIF": (".gif",),
    "ICO": (".ico",),
    "TGA": (".tga", ".targa"),
    "QOI": (".qoi",),
    "PPM": (".ppm",),
    "PGM": (".pgm",),
    "PBM": (".pbm",),
    "PFM": (".pfm",),
    "EXR": (".exr",),
    "HDR": (".hdr",),
    "FITS": (".fits", ".fit", ".fts"),
    "PSD": (".psd", ".psdt"),
    "PSB": (".psb",),
    "PCRAFT": (".pcraft",),
    "ORA": (".ora",),
    "XCF": (".xcf",),
    "KRA": (".kra", ".krz"),
    "PDN": (".pdn",),
    "SVG": (".svg",),
    "HEIC": (".heic",),
    "AFFINITY": (".af", ".afdesign", ".afphoto", ".afpub"),
    "JP2": (".jp2",),
    "J2K": (".j2k",),
    "JPX": (".jpx",),
    "PCX": (".pcx",),
}

PDF_IMAGE_TARGETS = ("PNG", "JPG", "JPEG", "TIFF")
PDFCRAFT_IMAGE_INPUTS = frozenset({"PNG", "JPG", "JPEG", "TIFF", "GIF", "BMP", "JP2", "J2K", "JPX", "PCX"})
PHOTOCRAFT_SOURCE_FORMATS = frozenset(CATEGORY_SOURCE_FORMATS[IMAGE_CATEGORY]) - PDFCRAFT_IMAGE_INPUTS
IMAGE_WRITABLE_FORMATS = frozenset(CATEGORY_TARGET_FORMATS[IMAGE_CATEGORY]) - {"PDF"}

_CANONICAL_SUFFIXES = {
    "JPG": ".jpg",
    "JPEG": ".jpeg",
    "TIFF": ".tiff",
    "HTML": ".html",
    "MD": ".md",
    "PCRAFT": ".pcraft",
    "DECKCRAFT": ".deckcraft",
}
_EXTENSION_FORMATS = {
    extension: label
    for label, extensions in FORMAT_EXTENSIONS.items()
    for extension in extensions
}


def _normalize_label(value: object) -> str:
    return str(value or "").strip().upper()


def _extensions_for_formats(format_labels: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        extension
        for label in format_labels
        for extension in FORMAT_EXTENSIONS.get(_normalize_label(label), ())
    )


FILE_TYPE_EXTENSIONS: dict[str, frozenset[str]] = {
    "document": frozenset(_extensions_for_formats(CATEGORY_SOURCE_FORMATS[DOCUMENT_CATEGORY])),
    "image": frozenset(_extensions_for_formats(CATEGORY_SOURCE_FORMATS[IMAGE_CATEGORY])),
    "archive": frozenset((".zip", ".rar", ".7z", ".tar", ".gz")),
}
KNOWN_FILE_EXTENSIONS = frozenset().union(*FILE_TYPE_EXTENSIONS.values())


def source_formats_for_category(category: str) -> list[str]:
    return list(CATEGORY_SOURCE_FORMATS.get(str(category or "").strip(), ()))


def target_formats_for_category(category: str) -> list[str]:
    return list(CATEGORY_TARGET_FORMATS.get(str(category or "").strip(), ()))


def mixed_source_label_for_category(category: str) -> str:
    return MIXED_SOURCE_LABELS.get(str(category or "").strip(), "")


def is_mixed_source_label(category: str, label: str) -> bool:
    return bool(label) and label == mixed_source_label_for_category(category)


def compatible_targets_for_source(category: str, source_label: str) -> list[str]:
    category = str(category or "").strip()
    source = _normalize_label(source_label)
    targets = target_formats_for_category(category)
    if is_mixed_source_label(category, source_label):
        return ["PDF"] if category == DOCUMENT_CATEGORY else targets
    if category == DOCUMENT_CATEGORY:
        if source == "PDF":
            return [target for target in targets if target not in {"DECKCRAFT", "POTX", "PPSX", "PDF"}]
        if source == "TXT":
            return ["PDF"]
        if source in {"PPTX", "DECKCRAFT"}:
            return [target for target in targets if target != source]
        return []
    if category == IMAGE_CATEGORY:
        if source in {"JP2", "J2K", "JPX", "PCX"}:
            return ["PDF"]
        return [target for target in targets if target != source]
    return []


def category_for_file_type(file_type: str) -> str | None:
    return _FILE_TYPE_CATEGORIES.get(str(file_type or "").strip().lower())


def format_for_path(path: str) -> str | None:
    extension = os.path.splitext(str(path or ""))[1].lower()
    return _EXTENSION_FORMATS.get(extension)


def suffix_for_format(format_label: str) -> str:
    label = _normalize_label(format_label)
    if label in _CANONICAL_SUFFIXES:
        return _CANONICAL_SUFFIXES[label]
    extensions = FORMAT_EXTENSIONS.get(label, ())
    return extensions[0] if extensions else ""


def matches_format(path: str, format_label: str) -> bool:
    extension = os.path.splitext(str(path or ""))[1].lower()
    return extension in FORMAT_EXTENSIONS.get(_normalize_label(format_label), ())


def extensions_for_category(category: str) -> tuple[str, ...]:
    formats = CATEGORY_SOURCE_FORMATS.get(str(category or "").strip(), ())
    return _extensions_for_formats(formats)


def build_file_dialog_filter() -> str:
    supported_masks = " ".join(f"*{ext}" for ext in sorted(KNOWN_FILE_EXTENSIONS))
    groups = [f"Поддерживаемые файлы ({supported_masks})"]
    for category in CONVERSION_CATEGORIES:
        masks = " ".join(f"*{ext}" for ext in extensions_for_category(category))
        groups.append(f"{category} ({masks})")
    return ";;".join(groups)
