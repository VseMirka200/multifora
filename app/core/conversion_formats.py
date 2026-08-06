"""Единый реестр категорий, форматов и расширений конвертации."""

from __future__ import annotations

import os


CONVERSION_CATEGORIES = ("Документы", "Фотографии", "Видео", "Звуки")

CATEGORY_FILE_TYPES = {
    "Документы": "document",
    "Фотографии": "image",
    "Видео": "video",
    "Звуки": "audio",
}
_FILE_TYPE_CATEGORIES = {file_type: category for category, file_type in CATEGORY_FILE_TYPES.items()}

CATEGORY_FORMATS = {
    "Документы": ("DOCX", "PDF", "ODT"),
    "Фотографии": ("JPG", "JPEG", "PNG", "BMP", "TIFF", "GIF", "WEBP"),
    "Видео": ("MP4", "AVI", "MKV", "MOV", "WEBM", "M4V", "WMV", "FLV"),
    "Звуки": ("MP3", "WAV", "OGG", "FLAC", "AAC", "M4A", "WMA"),
}

# DOC относится к DOCX: интерфейс и конвертер обрабатывают оба расширения как Word-документы.
FORMAT_EXTENSIONS = {
    "DOCX": (".doc", ".docx"),
    "PDF": (".pdf",),
    "ODT": (".odt",),
    "JPG": (".jpg",),
    "JPEG": (".jpeg",),
    "PNG": (".png",),
    "BMP": (".bmp",),
    "TIFF": (".tiff",),
    "GIF": (".gif",),
    "WEBP": (".webp",),
    "MP4": (".mp4",),
    "AVI": (".avi",),
    "MKV": (".mkv",),
    "MOV": (".mov",),
    "WEBM": (".webm",),
    "M4V": (".m4v",),
    "WMV": (".wmv",),
    "FLV": (".flv",),
    "MP3": (".mp3",),
    "WAV": (".wav",),
    "OGG": (".ogg",),
    "FLAC": (".flac",),
    "AAC": (".aac",),
    "M4A": (".m4a",),
    "WMA": (".wma",),
}
_EXTENSION_FORMATS = {
    extension: format_label
    for format_label, extensions in FORMAT_EXTENSIONS.items()
    for extension in extensions
}


def _extensions_for_formats(format_labels) -> tuple[str, ...]:
    return tuple(
        extension
        for format_label in format_labels
        for extension in FORMAT_EXTENSIONS[format_label]
    )


FILE_TYPE_EXTENSIONS = {
    "document": frozenset(
        (".txt", ".rtf", *_extensions_for_formats(CATEGORY_FORMATS["Документы"]))
    ),
    "image": frozenset((".svg", ".ico", *_extensions_for_formats(CATEGORY_FORMATS["Фотографии"]))),
    "video": frozenset(_extensions_for_formats(CATEGORY_FORMATS["Видео"])),
    "audio": frozenset(_extensions_for_formats(CATEGORY_FORMATS["Звуки"])),
    "archive": frozenset((".zip", ".rar", ".7z", ".tar", ".gz")),
}
KNOWN_FILE_EXTENSIONS = frozenset().union(*FILE_TYPE_EXTENSIONS.values())


def formats_for_category(category: str) -> list[str]:
    return list(CATEGORY_FORMATS.get(str(category or "").strip(), ()))


def category_for_file_type(file_type: str) -> str | None:
    normalized = str(file_type or "").strip().lower()
    return _FILE_TYPE_CATEGORIES.get(normalized)


def format_for_path(path: str) -> str | None:
    extension = os.path.splitext(str(path or ""))[1].lower()
    return _EXTENSION_FORMATS.get(extension)


def suffix_for_format(format_label: str) -> str:
    extensions = FORMAT_EXTENSIONS.get(str(format_label or "").strip(), ())
    return extensions[-1] if extensions else ""


def matches_format(path: str, format_label: str) -> bool:
    extension = os.path.splitext(str(path or ""))[1].lower()
    return extension in FORMAT_EXTENSIONS.get(str(format_label or "").strip(), ())


def extensions_for_category(category: str) -> tuple[str, ...]:
    format_labels = CATEGORY_FORMATS.get(str(category or "").strip(), ())
    return _extensions_for_formats(format_labels)


def build_file_dialog_filter() -> str:
    """Формирует фильтр выбора файлов из того же реестра, что и конвертер."""
    labels = {
        "Документы": "Документы",
        "Фотографии": "Изображения",
        "Видео": "Видео",
        "Звуки": "Аудио",
    }
    groups = ["Все файлы (*.*)"]
    for category in CONVERSION_CATEGORIES:
        masks = " ".join(f"*{extension}" for extension in extensions_for_category(category))
        groups.append(f"{labels[category]} ({masks})")
    return ";;".join(groups)
