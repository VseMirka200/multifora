"""Реестр форматов, фактически поддерживаемых CLI-движками ArtCraft.

Входы и выходы описаны отдельно: PhotoCraft умеет читать больше форматов,
чем записывать; PDFCraft и DeckCraft имеют собственные маршруты экспорта.
"""
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
_FILE_TYPE_CATEGORIES = {
    file_type: category for category, file_type in CATEGORY_FILE_TYPES.items()
}
MIXED_SOURCE_LABELS = {
    DOCUMENT_CATEGORY: "Любой поддерживаемый документ",
    IMAGE_CATEGORY: "Любое поддерживаемое изображение",
}

# PdfCraft CLI: PDF and plain text input; DeckCraft CLI: PPTX and .deckcraft.
CATEGORY_SOURCE_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: ("PDF", "TXT", "PPTX", "DECKCRAFT"),
    IMAGE_CATEGORY: (
        "JPG", "JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO",
        "TGA", "QOI", "PPM", "PGM", "PBM", "PFM", "EXR", "HDR",
        "FITS", "PCX", "SVG", "SVGZ", "PSD", "PSB", "PCRAFT", "ORA",
        "XCF", "KRA", "PDN", "HEIC", "HEIF", "DNG", "CR2", "CR3",
        "NEF", "NRW", "ARW", "PEF", "ORF", "RW2", "RAF", "DDS",
        "DPX", "CIN", "DCM", "IFF", "LBM", "XPM",
    ),
}

# Writable formats only. Read-only import formats remain available as sources,
# but are never offered as output targets.
CATEGORY_TARGET_FORMATS: dict[str, tuple[str, ...]] = {
    DOCUMENT_CATEGORY: (
        "PDF", "DOCX", "PPTX", "DECKCRAFT", "TXT", "HTML", "RTF", "MD",
        "PNG", "JPG", "JPEG", "TIFF", "GIF",
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
    "PCX": (".pcx",),
    "SVG": (".svg",),
    "SVGZ": (".svgz",),
    "PSD": (".psd", ".psdt"),
    "PSB": (".psb",),
    "PCRAFT": (".pcraft",),
    "ORA": (".ora",),
    "XCF": (".xcf", ".xcfgz"),
    "KRA": (".kra", ".krz"),
    "PDN": (".pdn",),
    "HEIC": (".heic",),
    "HEIF": (".heif", ".hif"),
    "DNG": (".dng",),
    "CR2": (".cr2",),
    "CR3": (".cr3",),
    "NEF": (".nef",),
    "NRW": (".nrw",),
    "ARW": (".arw",),
    "PEF": (".pef",),
    "ORF": (".orf",),
    "RW2": (".rw2",),
    "RAF": (".raf",),
    "DDS": (".dds",),
    "DPX": (".dpx",),
    "CIN": (".cin",),
    "DCM": (".dcm", ".dicom", ".dc3"),
    "IFF": (".iff",),
    "LBM": (".lbm", ".ilbm"),
    "XPM": (".xpm",),
}

# PDFCraft's renderer exports all PDF pages as PNG, JPEG or TIFF.
PDF_IMAGE_TARGETS = ("PNG", "JPG", "JPEG", "TIFF")

_CANONICAL_SUFFIXES = {
    "JPG": ".jpg",
    "JPEG": ".jpeg",
    "TIFF": ".tiff",
    "HTML": ".html",
    "MD": ".md",
    "SVGZ": ".svgz",
    "HEIC": ".heic",
    "HEIF": ".heif",
    "PCRAFT": ".pcraft",
    "DECKCRAFT": ".deckcraft",
}
_EXTENSION_FORMATS = {
    extension: label
    for label, extensions in FORMAT_EXTENSIONS.items()
    for extension in extensions
}

# Flat PhotoCraft codecs with documented read/write support plus layered/native
# formats that its I/O layer writes. HEIC/HEIF, SVG, RAW and legacy project
# formats are read-only and intentionally absent from this list.
IMAGE_WRITABLE_FORMATS = frozenset(CATEGORY_TARGET_FORMATS[IMAGE_CATEGORY])


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
            return [target for target in targets if target not in {"DECKCRAFT"}]
        if source == "TXT":
            return ["PDF"]
        if source in {"PPTX", "DECKCRAFT"}:
            return [target for target in targets if target not in PDF_IMAGE_TARGETS or target in {"PNG", "JPG", "JPEG", "TIFF", "GIF"}]
        return []
    if category == IMAGE_CATEGORY:
        return [
            target for target in targets
            if target != source
        ]
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
