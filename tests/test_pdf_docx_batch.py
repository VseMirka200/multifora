from threading import Event

from app.core.models import FileItem
from core.pdf_docx_batch import pdf_docx_worker_count, run_parallel_batch


def test_worker_count_limits_large_files(tmp_path, monkeypatch):
    monkeypatch.setattr("core.pdf_docx_batch.os.cpu_count", lambda: 16)
    path = tmp_path / "large.pdf"
    with path.open("wb") as stream:
        stream.truncate(25 * 1024 * 1024)
    assert pdf_docx_worker_count([FileItem(str(path))]) == 1
    with path.open("wb") as stream:
        stream.truncate(10 * 1024 * 1024)
    assert pdf_docx_worker_count([FileItem(str(path))]) == 2
    assert pdf_docx_worker_count([]) == 4


def test_batch_keeps_input_order_and_reports_partial_failure():
    files = [FileItem(name) for name in ("a.pdf", "b.pdf", "skip.txt", "c.pdf")]
    errors, progress = [], []

    def convert(file):
        if file.path == "b.pdf":
            raise ValueError("failed")
        return file.path + ".docx"

    result = run_parallel_batch(
        files,
        2,
        convert=convert,
        result_item=FileItem,
        should_cancel=lambda: False,
        report_error=lambda file, error: errors.append((file.path, str(error))),
        discard=lambda _path: None,
        progress=progress.append,
        status=lambda _text: None,
    )
    assert [item.path for item in result] == ["a.pdf.docx", "c.pdf.docx"]
    assert errors == [("b.pdf", "failed")]
    assert progress[-1] == 100


def test_batch_cancellation_discards_unreported_finished_file():
    started = Event()
    release = Event()
    discarded = []

    def convert(_file):
        started.set()
        assert release.wait(5)
        return "generated.docx"

    def should_cancel():
        if started.is_set():
            release.set()
            return True
        return False

    result = run_parallel_batch(
        [FileItem("a.pdf")],
        1,
        convert=convert,
        result_item=FileItem,
        should_cancel=should_cancel,
        report_error=lambda *_args: None,
        discard=discarded.append,
        progress=lambda _value: None,
        status=lambda _text: None,
    )
    assert result == []
    assert discarded == ["generated.docx"]
