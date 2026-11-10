from __future__ import annotations

from .operation_worker import OperationWorker


def create_operation_worker(operation: str | None) -> OperationWorker:
    """Создаёт подходящий обработчик с минимальными зависимостями."""
    if operation == "rename":
        from .rename_worker import RenameWorker

        return RenameWorker()
    if operation == "convert":
        from .conversion_worker import ConversionWorker

        return ConversionWorker()
    if operation == "convert_image":
        from .image_worker import ImageWorker

        return ImageWorker()
    if operation == "convert_document":
        from .document_worker import DocumentWorker

        return DocumentWorker()
    if operation == "compress":
        from .compression_worker import CompressionWorker

        return CompressionWorker()

    # Совместимость с интеграциями, которые ещё не выбрали операцию.
    from .file_worker import FileWorker

    return FileWorker()
