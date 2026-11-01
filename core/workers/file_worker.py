from .compression_worker import CompressionWorker
from .conversion_worker import ConversionWorker
from .rename_worker import _format_rename_error as _format_rename_error


class FileWorker(ConversionWorker, CompressionWorker):
    """Backward-compatible worker; production UI uses feature workers."""
