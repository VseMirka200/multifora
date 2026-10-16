"""Qt bridge between operation requests and asynchronous file workers."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from core.operations import CancellationToken, OperationRequest
from core.operations.worker_adapter import configure_file_worker
from core.workers.file_worker import FileWorker


class OperationController(QObject):
    """Runs one typed request at a time and proxies worker notifications."""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    started = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: FileWorker | None = None
        self._cancellation: CancellationToken | None = None

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def start(self, request: OperationRequest) -> bool:
        """Start a request, returning ``False`` when another request runs."""
        if self.is_running:
            return False
        worker = FileWorker()
        configure_file_worker(worker, request)
        self._worker = worker
        self._cancellation = CancellationToken()
        worker.progress.connect(self.progress)
        worker.status.connect(self.status)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self.failed)
        worker.start()
        self.started.emit()
        return True

    def cancel(self) -> None:
        """Request cooperative cancellation of the active worker."""
        if self._cancellation is not None:
            self._cancellation.cancel()
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()

    def _on_finished(self, result: object) -> None:
        self.completed.emit(result)
