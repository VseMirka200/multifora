from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.models import FileItem, OperationFile
from app.ui.operation_controller import OperationController, bind_operation_worker
from core.operation_requests import CompressionRequest, ConversionRequest, MergeRequest, RenameRequest


def test_rename_matches_names_to_paths_when_files_are_reordered():
    first, second = FileItem("first.txt"), FileItem("second.txt")
    request = RenameRequest(((first.path, "one.txt"), (second.path, "two.txt")), strict=True)
    worker = Mock()
    window = SimpleNamespace(create_file_worker=Mock(return_value=True), file_worker=worker)

    assert OperationController().start(window, request, [second, first])

    worker.set_rename.assert_called_once_with(
        [OperationFile.from_item(second), OperationFile.from_item(first)], ["two.txt", "one.txt"], strict=True
    )
    worker.start.assert_called_once_with()


def test_rename_rejects_mismatched_files_before_creating_worker():
    window = SimpleNamespace(create_file_worker=Mock())
    request = RenameRequest((("first.txt", "one.txt"),))

    with pytest.raises(ValueError, match="не соответствуют запросу"):
        OperationController().start(window, request, [FileItem("other.txt")])

    window.create_file_worker.assert_not_called()


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
    window = SimpleNamespace(create_file_worker=Mock(return_value=True), file_worker=worker)
    controller = OperationController()

    assert controller.start(window, operation_request, [item])
    window.create_file_worker.assert_called_once_with(operation=kind)
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
    worker = Mock()
    window = SimpleNamespace(
        create_file_worker=Mock(return_value=False),
        _ensure_operation_can_start=Mock(return_value=False),
        file_worker=worker,
    )
    controller = OperationController()
    assert not controller.start(window, operation_request, [FileItem("source.pdf")])
    assert controller.last_request is None
    worker.start.assert_not_called()
