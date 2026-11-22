"""Типы файлов, общие для списка файлов и операций."""

DOCUMENT_EXTENSIONS = (
    ".docx",
    ".pdf",
    ".odt",
    ".rtf",
    ".txt",
    ".html",
    ".htm",
)

PRESENTATION_EXTENSIONS = (".ppt", ".pptx", ".odp")

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpe",
    ".jpeg",
    ".jfif",
    ".png",
    ".webp",
    ".bmp",
    ".dib",
    ".tif",
    ".tiff",
    ".gif",
    ".ico",
    ".tga",
    ".targa",
    ".pcx",
    ".jp2",
    ".j2k",
    ".j2c",
    ".jpf",
    ".jpx",
    ".qoi",
    ".dds",
    ".icns",
    ".xbm",
    ".sgi",
    ".rgb",
    ".rgba",
    ".bw",
    ".ppm",
    ".pgm",
    ".pbm",
    ".avif",
    ".heic",
    ".heif",
    ".hif",
    ".svg",
    ".psd",
)

FILE_TYPE_EXTENSIONS = {
    "document": frozenset(DOCUMENT_EXTENSIONS),
    "presentation": frozenset(PRESENTATION_EXTENSIONS),
    "image": frozenset(IMAGE_EXTENSIONS),
    "archive": frozenset((".zip", ".rar", ".7z", ".tar", ".gz")),
}
KNOWN_FILE_EXTENSIONS = frozenset().union(*FILE_TYPE_EXTENSIONS.values())
