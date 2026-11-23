from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.ui.operation_controller import OperationController, bind_operation_worker
from core.file_models import FileItem, OperationFile
from core.operation_requests import CompressionRequest, ConversionRequest, MergeRequest, RenameRequest


def test_rename_matches_names_to_paths_when_files_are_reordered():
    first, second = FileItem("first.txt"), FileItem("second.txt")
    request = RenameRequest(((first.path, "one.txt"), (second.path, "two.txt")), strict=True)
    worker = Mock()
    controller = OperationController()
    connect = Mock()

    with patch("app.workers.factory.create_operation_worker", return_value=worker):
        assert controller.start(request, [second, first], can_start=lambda: True, connect=connect)
    connect.assert_called_once_with(worker)
    assert controller.worker is worker

    worker.set_rename.assert_called_once_with(
        [OperationFile.from_item(second), OperationFile.from_item(first)], ["two.txt", "one.txt"], strict=True
    )
    worker.start.assert_called_once_with()


def test_rename_rejects_mismatched_files_before_creating_worker():
    request = RenameRequest((("first.txt", "one.txt"),))
    with patch("app.workers.factory.create_operation_worker") as create:
        with pytest.raises(ValueError, match="не соответствуют запросу"):
            OperationController().start(request, [FileItem("other.txt")], can_start=lambda: True, connect=Mock())
        create.assert_not_called()


def test_disconnect_continues_when_one_signal_is_already_disconnected():
    old_worker, new_worker = Mock(), Mock()
    old_worker.progress.disconnect.side_effect = RuntimeError("not connected")
    window = SimpleNamespace(
        file_worker=old_worker,
        progress_bar=Mock(),
        on_worker_status=Mock(),
        on_operation_finished=Mock(),
        on_operation_error=Mock(),
    )

    bind_operation_worker(window, new_worker)

    for signal in (old_worker.progress, old_worker.status, old_worker.finished, old_worker.error):
        signal.disconnect.assert_called_once_with()
    assert window.file_worker is new_worker


@pytest.mark.parametrize(
    ("operation_request", "kind", "method", "args", "kwargs"),
    [
        (
            ConversionRequest("auto_image", "png", "custom", "out"),
            "convert_image",
            "set_conversion",
            ("auto_image", "png"),
            {"output_mode": "custom", "output_dir": "out"},
        ),
        (
            CompressionRequest(75, "image", "auto", False, "custom", "out"),
            "compress",
            "set_compression",
            (75, "image", "auto", False, "custom", "out"),
            {},
        ),
    ],
)
def test_controller_passes_requests_to_worker(operation_request, kind, method, args, kwargs):
    item = FileItem("source.png")
    worker = Mock()
    controller = OperationController()

    with patch("app.workers.factory.create_operation_worker", return_value=worker) as create:
        assert controller.start(operation_request, [item], can_start=lambda: True, connect=Mock())
    create.assert_called_once_with(kind)
    getattr(worker, method).assert_called_once_with([OperationFile.from_item(item)], *args, **kwargs)
    worker.start.assert_called_once_with()
    assert controller.last_request is operation_request


@pytest.mark.parametrize(
    "operation_request",
    [
        ConversionRequest("auto_image", "png", "alongside", ""),
        MergeRequest("pdf", "out.pdf"),
    ],
)
def test_controller_does_not_remember_or_start_rejected_operation(operation_request):
    controller = OperationController()
    connect = Mock()
    with patch("app.ui.operation_controller.create_worker_for_request") as create:
        assert not controller.start(
            operation_request, [FileItem("source.pdf")], can_start=lambda: False, connect=connect
        )
    create.assert_not_called()
    connect.assert_not_called()
    assert controller.last_request is None
    assert controller.worker is None


def test_merge_uses_the_same_controller_entry_point():
    controller = OperationController()
    request = MergeRequest("pdf", "out.pdf")
    source = FileItem("source.pdf")
    connect = Mock()

    with patch("app.workers.merge_worker.MergeWorker") as create:
        assert controller.start(request, [source], can_start=lambda: True, connect=connect)
    create.assert_called_once_with([OperationFile.from_item(source)], "pdf", "out.pdf", ())
    connect.assert_called_once_with(create.return_value)
    create.return_value.start.assert_called_once_with()
