from __future__ import annotations

from .operation_worker import OperationWorker


def create_operation_worker(operation: str | None) -> OperationWorker:
    """Create the lightest worker that supports the requested operation."""
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

    # Compatibility for integrations that have not selected an operation yet.
    from .file_worker import FileWorker

    return FileWorker()
