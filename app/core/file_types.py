"""File types shared by the file list and operations."""

DOCUMENT_EXTENSIONS = (
    ".docx",
    ".pdf",
    ".odt",
    ".rtf",
    ".txt",
    ".html",
    ".htm",
)

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
    "image": frozenset(IMAGE_EXTENSIONS),
    "archive": frozenset((".zip", ".rar", ".7z", ".tar", ".gz")),
}
KNOWN_FILE_EXTENSIONS = frozenset().union(*FILE_TYPE_EXTENSIONS.values())


def build_file_dialog_filter() -> str:
    supported = " ".join(f"*{extension}" for extension in sorted(KNOWN_FILE_EXTENSIONS))
    documents = " ".join(f"*{extension}" for extension in DOCUMENT_EXTENSIONS)
    images = " ".join(f"*{extension}" for extension in IMAGE_EXTENSIONS)
    return f"Поддерживаемые файлы ({supported});;Документы ({documents});;Изображения ({images})"
