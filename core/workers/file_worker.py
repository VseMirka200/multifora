from .compression_worker import CompressionWorker
from .conversion_worker import ConversionWorker
from .rename_worker import _format_rename_error as _format_rename_error


class FileWorker(ConversionWorker, CompressionWorker):
    """Совместимый обработчик; интерфейс использует отдельные обработчики."""
