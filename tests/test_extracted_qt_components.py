from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from app.core.ipc_server import LocalFileServer
from app.ui.conversion_panel import ConversionPanel
from app.ui.operation_progress import OperationProgressDialog
from app.workers.operation_worker import OperationWorker


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


def test_progress_dialog_emits_cancel_and_resets():
    app = QApplication.instance() or QApplication([])
    dialog = OperationProgressDialog(None, "dark")
    cancel = Mock()
    dialog.cancel_requested.connect(cancel)
    dialog.show_progress("Подготовка", indeterminate=True)
    assert dialog.status_label.text() == "Подготовка"
    assert dialog.progress_bar.maximum() == 0
    dialog.show_progress("Обработка")
    dialog.progress_bar.setValue(50)
    dialog.cancel_button.click()
    cancel.assert_called_once_with()
    dialog.reset()
    assert dialog.progress_bar.value() == 0
    assert dialog.cancel_button.isHidden()
    assert not dialog.isVisible()
    dialog.deleteLater()
    assert app is not None


def test_conversion_panel_emits_changes_without_main_window():
    app = QApplication.instance() or QApplication([])
    panel = ConversionPanel()
    category_changed, folder_requested = Mock(), Mock()
    panel.category_changed.connect(category_changed)
    panel.output_folder_requested.connect(folder_requested)
    panel.convert_file_type_combo.setCurrentIndex(1)
    panel.btn_select_conversion_output_folder.click()
    category_changed.assert_called_once_with()
    folder_requested.assert_called_once_with()
    assert not panel.btn_convert.isEnabled()
    panel.card.deleteLater()
    assert app is not None


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
