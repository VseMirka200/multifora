from __future__ import annotations

from collections.abc import Sequence

from core.file_models import OperationFile
from core.operation_requests import OperationRequest, RenameRequest

from .operation_worker import OperationWorker


def create_worker_for_request(request: OperationRequest, sources: Sequence[OperationFile]) -> OperationWorker:
    """Подготавливает обработчик типизированного запроса к запуску."""
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
    from .craft_worker import CraftWorker
    return CraftWorker(request, sources)


def create_operation_worker(operation: str | None) -> OperationWorker:
    from .rename_worker import RenameWorker

    if operation in (None, "rename"):
        return RenameWorker()
    raise RuntimeError("Для обработки используйте типизированный запрос операции.")
