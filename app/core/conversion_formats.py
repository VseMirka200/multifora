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

CATEGORY_FORMATS = {
    "Документы": ("DOCX", "PDF", "ODT"),
    "Фотографии": ("JPG", "JPEG", "PNG", "BMP", "TIFF", "GIF", "WEBP"),
    "Видео": ("MP4", "AVI", "MKV", "MOV", "WEBM", "M4V", "WMV", "FLV"),
    "Звуки": ("MP3", "WAV", "OGG", "FLAC", "AAC", "M4A", "WMA"),
}

# DOC is intentionally grouped with DOCX because the conversion backends handle it
# as a Word document and the UI exposes one common source format.
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

FILE_TYPE_EXTENSIONS = {
    "document": frozenset((".txt", ".rtf", *FORMAT_EXTENSIONS["DOCX"], *FORMAT_EXTENSIONS["PDF"], *FORMAT_EXTENSIONS["ODT"])),
    "image": frozenset(),
    "video": frozenset(),
    "audio": frozenset(),
    "archive": frozenset((".zip", ".rar", ".7z", ".tar", ".gz")),
}


def formats_for_category(category: str) -> list[str]:
    return list(CATEGORY_FORMATS.get(str(category or "").strip(), ()))


def category_for_file_type(file_type: str) -> str | None:
    normalized = str(file_type or "").strip().lower()
    for category, expected_type in CATEGORY_FILE_TYPES.items():
        if normalized == expected_type:
            return category
    return None


def format_for_path(path: str) -> str | None:
    extension = os.path.splitext(str(path or ""))[1].lower()
    for format_label, extensions in FORMAT_EXTENSIONS.items():
        if extension in extensions:
            return format_label
    return None


def suffix_for_format(format_label: str) -> str:
    extensions = FORMAT_EXTENSIONS.get(str(format_label or "").strip(), ())
    return extensions[-1] if extensions else ""


def matches_format(path: str, format_label: str) -> bool:
    extension = os.path.splitext(str(path or ""))[1].lower()
    return extension in FORMAT_EXTENSIONS.get(str(format_label or "").strip(), ())


def extensions_for_category(category: str) -> tuple[str, ...]:
    return tuple(
        extension
        for format_label in CATEGORY_FORMATS.get(str(category or "").strip(), ())
        for extension in FORMAT_EXTENSIONS[format_label]
    )


# Populate broad file-type groups after helper-independent constants are declared.
FILE_TYPE_EXTENSIONS["image"] = frozenset((".svg", ".ico", *extensions_for_category("Фотографии")))
FILE_TYPE_EXTENSIONS["video"] = frozenset(extensions_for_category("Видео"))
FILE_TYPE_EXTENSIONS["audio"] = frozenset(extensions_for_category("Звуки"))
KNOWN_FILE_EXTENSIONS = frozenset().union(*FILE_TYPE_EXTENSIONS.values())


def build_file_dialog_filter() -> str:
    """Формирует фильтр выбора файлов из того же реестра, что и конвертер."""
    labels = {"Документы": "Документы", "Фотографии": "Изображения", "Видео": "Видео", "Звуки": "Аудио"}
    groups = ["Все файлы (*.*)"]
    for category in CONVERSION_CATEGORIES:
        masks = " ".join(f"*{extension}" for extension in extensions_for_category(category))
        groups.append(f"{labels[category]} ({masks})")
    return ";;".join(groups)
