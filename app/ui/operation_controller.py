"""Связывает запросы вкладок с жизненным циклом рабочих потоков Qt."""

from app.core.app_utils import _debug_log
from app.core.models import FileItem, OperationFile
from core.operation_requests import CompressionRequest, ConversionRequest, MergeRequest, OperationRequest, RenameRequest
from core.workers.operation_worker import OperationWorker


def bind_operation_worker(window, worker: OperationWorker) -> None:
    """Отключает сигналы прежнего обработчика и подключает новый к окну."""
    if window.file_worker:
        for signal in (
            window.file_worker.progress,
            window.file_worker.status,
            window.file_worker.finished,
            window.file_worker.error,
        ):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError) as error:
                _debug_log(f"Ошибка отключения старого сигнала: {error}")

    window.file_worker = worker
    worker.progress.connect(window.progress_bar.setValue)
    worker.status.connect(window.on_worker_status)
    worker.finished.connect(window.on_operation_finished)
    worker.error.connect(window.on_operation_error)


class OperationController:
    """Подготавливает запросы и запускает соответствующие обработчики операций."""
    def __init__(self) -> None:
        self.worker: OperationWorker | None = None
        self.last_request: OperationRequest | None = None

    def start(self, window, request: OperationRequest, files: list[FileItem]) -> bool:
        """Запускает операцию и возвращает False, если окно не разрешило запуск.

        Для переименования пути файлов должны в точности совпадать с запросом;
        при несоответствии возбуждается ValueError до запуска обработчика.
        """
        sources = [OperationFile.from_item(file) for file in files]
        if isinstance(request, RenameRequest):
            names = dict(request.pairs)
            if (
                len(names) != len(request.pairs)
                or len(sources) != len(names)
                or {source.path for source in sources} != names.keys()
            ):
                raise ValueError("Файлы переименования не соответствуют запросу")
            rename_names = [names[source.path] for source in sources]
        if isinstance(request, MergeRequest):
            if not window._ensure_operation_can_start():
                return False
            from core.workers.merge.merge_worker import MergeWorker

            bind_operation_worker(window, MergeWorker(sources, request.output_format, request.output_path))
        else:
            worker_kind = request.worker_kind if isinstance(request, ConversionRequest) else request.kind
            if not window.create_file_worker(operation=worker_kind):
                return False
            worker = window.file_worker
            if isinstance(request, RenameRequest):
                worker.set_rename(sources, rename_names, strict=request.strict)
            elif isinstance(request, ConversionRequest):
                worker.set_conversion(
                    sources,
                    request.conversion_type,
                    request.target_format,
                    output_mode=request.output_mode,
                    output_dir=request.output_dir,
                )
            elif isinstance(request, CompressionRequest):
                worker.set_compression(
                    sources,
                    request.level,
                    request.compression_type,
                    request.pdf_method,
                    request.replace_pdf,
                    request.image_output_mode,
                    request.image_output_dir,
                )

        self.last_request = request
        window.file_worker.start()
        return True
