from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from app.core.ipc_server import LocalFileServer
from core.workers.operation_worker import OperationWorker


def test_ipc_authentication_queue_and_close(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "document.txt"
    path.write_text("data")
    received, queued = [], []
    server = LocalFileServer(Mock())
    server.files_received.connect(received.append)
    server.files_queued.connect(lambda: queued.append(True))
    with patch("app.core.ipc_server._load_ipc_token", return_value="secret"):
        server._process_ipc_payload(f"TOKEN:wrong\nADD_FILE:{path}".encode())
        server._process_ipc_payload(f"TOKEN:secret\nADD_FILE:{path}\nADD_FILE:{tmp_path / 'missing'}".encode())
    assert received == []
    assert queued == [True]
    server.flush()
    assert received == [[str(path)]]
    server.enqueue([str(path)])
    server.close()
    server.flush()
    assert received == [[str(path)]]
    assert app is not None


def test_worker_cancel_before_and_during_active_action():
    worker = OperationWorker()
    action = Mock()
    worker.request_cancel()
    worker._set_active_cancel_action(action)
    action.assert_called_once_with()
    worker._prepare_operation("test", [])
    assert not worker._should_cancel()
    worker._set_active_cancel_action(action)
    worker.request_cancel()
    assert action.call_count == 2
    worker._clear_active_cancel_action(action)
    worker.request_cancel()
    assert action.call_count == 2


def test_worker_unhandled_error_emits_one_result():
    class FailingWorker(OperationWorker):
        def _operation_handlers(self):
            def fail():
                raise ValueError("engine failed")

            return {"test": fail}

    worker = FailingWorker()
    worker._prepare_operation("test", [])
    results, errors = [], []
    worker.finished.connect(results.append)
    worker.error.connect(errors.append)
    worker.run()
    assert errors == ["engine failed"]
    assert len(results) == 1
    assert results[0].errors == [{"message": "engine failed"}]
