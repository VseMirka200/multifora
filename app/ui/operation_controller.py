"""Связывает запросы вкладок с жизненным циклом рабочих потоков Qt."""

from collections.abc import Callable, Sequence

from app.core.app_utils import _debug_log
from app.workers.factory import create_worker_for_request
from app.workers.operation_worker import OperationWorker
from core.file_models import FileItem, OperationFile
from core.operation_requests import OperationRequest


def _disconnect_operation_worker(worker: OperationWorker | None) -> None:
    if worker is None:
        return
    for signal in (worker.progress, worker.status, worker.finished, worker.error):
        try:
            signal.disconnect()
        except (RuntimeError, TypeError) as error:
            _debug_log(f"Ошибка отключения старого сигнала: {error}")


def connect_operation_worker(window, worker: OperationWorker) -> None:
    """Подключает сигналы обработчика к слотам окна."""
    worker.progress.connect(window.progress_bar.setValue)
    worker.status.connect(window.on_worker_status)
    worker.finished.connect(window.on_operation_finished)
    worker.error.connect(window.on_operation_error)


def bind_operation_worker(window, worker: OperationWorker) -> None:
    """Заменяет обработчик при вызове прежней точки входа окна."""
    _disconnect_operation_worker(window.file_worker)
    connect_operation_worker(window, worker)
    window.file_worker = worker


class OperationController:
    """Владеет рабочим потоком и запросом последней запущенной операции."""

    def __init__(self) -> None:
        self.worker: OperationWorker | None = None
        self.last_request: OperationRequest | None = None

    def start(
        self,
        request: OperationRequest,
        files: Sequence[FileItem],
        *,
        can_start: Callable[[], bool],
        connect: Callable[[OperationWorker], None],
    ) -> bool:
        """Запускает операцию после проверки доступности и подключения сигналов."""
        if not can_start():
            return False
        worker = create_worker_for_request(request, [OperationFile.from_item(file) for file in files])
        _disconnect_operation_worker(self.worker)
        connect(worker)
        self.worker = worker
        self.last_request = request
        worker.start()
        return True
