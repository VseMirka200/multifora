"""Форматы файлов и маршруты, доступные движкам обработки."""

import os

DOCUMENT_FORMATS = ("DOCX", "PDF", "ODT", "RTF", "TXT", "HTML")
OFFICE_OUTPUTS = frozenset(DOCUMENT_FORMATS)
OFFICE_INPUTS = OFFICE_OUTPUTS - {"PDF"}

# Идентификаторы движков разрешаются адаптером документов при обращении.
OFFICE_ROUTES = {
    "DOCX": {"PDF": "rich_pdf", "ODT": "odt", "RTF": "rtf", "TXT": "text", "HTML": "docx_html"},
    "ODT": {"DOCX": "odt_body", "PDF": "rich_pdf", "RTF": "rtf", "TXT": "text", "HTML": "odt_body"},
    "RTF": {"DOCX": "rtf_body", "PDF": "rich_pdf", "ODT": "odt", "TXT": "text", "HTML": "rtf_body"},
    "TXT": {"DOCX": "plain", "PDF": "text_pdf", "ODT": "plain", "RTF": "plain", "HTML": "plain"},
    "HTML": {"DOCX": "html_docx", "PDF": "rich_pdf", "ODT": "odt", "RTF": "rtf", "TXT": "text"},
}

PRESENTATION_FORMATS = ("PPT", "PPTX", "ODP")

IMAGE_SOURCE_FORMATS = (
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
)


FORMAT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    **{label: ("." + label.lower(),) for label in PRESENTATION_FORMATS},
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
