from __future__ import annotations

from collections.abc import Sequence
from functools import cache

from core.file_models import OperationFile
from core.operation_requests import CompressionRequest, ConversionRequest, MergeRequest, OperationRequest, RenameRequest

from .operation_worker import OperationWorker


def create_worker_for_request(request: OperationRequest, sources: Sequence[OperationFile]) -> OperationWorker:
    """Подготавливает обработчик типизированного запроса к запуску."""
    if isinstance(request, MergeRequest):
        from .merge_worker import MergeWorker

        return MergeWorker(sources, request.output_format, request.output_path, request.page_order)
    if isinstance(request, RenameRequest):
        names = dict(request.pairs)
        if (
            len(names) != len(request.pairs)
            or len(sources) != len(names)
            or {source.path for source in sources} != names.keys()
        ):
            raise ValueError("Файлы переименования не соответствуют запросу")
        worker = create_operation_worker(request.kind)
        worker.set_rename(sources, [names[source.path] for source in sources], strict=request.strict)
        return worker
    if isinstance(request, ConversionRequest):
        worker = create_operation_worker(request.worker_kind)
        worker.set_conversion(
            sources,
            request.conversion_type,
            request.target_format,
            output_mode=request.output_mode,
            output_dir=request.output_dir,
        )
        return worker
    if isinstance(request, CompressionRequest):
        worker = create_operation_worker(request.kind)
        worker.set_compression(
            sources,
            request.level,
            request.compression_type,
            request.pdf_method,
            request.replace_pdf,
            request.image_output_mode,
            request.image_output_dir,
        )
        return worker
    raise TypeError(f"Неизвестный тип запроса: {type(request).__name__}")


def create_operation_worker(operation: str | None) -> OperationWorker:
    """Создаёт подходящий обработчик с минимальными зависимостями."""
    if operation == "rename":
        from .rename_worker import RenameWorker

        return RenameWorker()
    if operation == "convert":
        from .conversion_worker import ConversionWorker

        return ConversionWorker()
    if operation == "convert_image":
        from .conversion_worker import ImageWorker

        return ImageWorker()
    if operation == "convert_document":
        from .conversion_worker import DocumentWorker

        return DocumentWorker()
    if operation == "compress":
        from .compression_worker import CompressionWorker

        return CompressionWorker()

    # Совместимость с интеграциями, которые ещё не выбрали операцию.
    return _general_worker_type()()


@cache
def _general_worker_type() -> type[OperationWorker]:
    from .compression_worker import CompressionWorker
    from .conversion_worker import ConversionWorker
    from .rename_worker import RenameWorker

    class FileWorker(ConversionWorker, CompressionWorker, RenameWorker):
        """Совместимый обработчик для вызовов без указанной операции."""

    return FileWorker
