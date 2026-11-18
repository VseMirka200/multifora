from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.core.models import FileItem
from core.compress_files import compress_image, compress_pdf, pdf_settings
from core.filesystem import atomic_output_path, get_unique_path
from core.merge_documents import merge_documents
from core.rename_transaction import rename_batch


def test_atomic_output_rejects_empty_and_cleans_up(tmp_path):
    destination = tmp_path / "result.pdf"
    with pytest.raises(OSError):
        with atomic_output_path(str(destination)):
            pass
    assert list(tmp_path.iterdir()) == []


def test_unique_path_skips_occupied_names(tmp_path):
    for name in ("result.pdf", "result_1.pdf"):
        (tmp_path / name).write_bytes(b"original")
    assert get_unique_path(str(tmp_path / "result.pdf")) == str(tmp_path / "result_2.pdf")


def test_rename_rolls_back_after_first_target_is_placed(tmp_path):
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"
    first.write_text("first")
    second.write_text("second")
    import core.rename_transaction as transaction

    original = transaction._move_without_overwriting
    calls = 0

    def fail_fourth(source, target):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise PermissionError("placement failed")
        original(source, target)

    with patch.object(transaction, "_move_without_overwriting", side_effect=fail_fourth):
        successes, errors = rename_batch([str(first), str(second)], [str(second), str(first)])
    assert not successes
    assert len(errors) == 1
    assert first.read_text() == "first"
    assert second.read_text() == "second"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["a.txt", "b.txt"]


def test_rename_reports_actual_temporary_path_when_rollback_fails(tmp_path):
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"
    first.write_text("first")
    second.write_text("second")
    import core.rename_transaction as transaction

    original = transaction._move_without_overwriting
    calls = 0

    def fail_placement_and_restore(source, target):
        nonlocal calls
        calls += 1
        if calls in (4, 6):
            raise PermissionError("simulated failure")
        original(source, target)

    with patch.object(transaction, "_move_without_overwriting", side_effect=fail_placement_and_restore):
        successes, errors = rename_batch([str(first), str(second)], [str(second), str(first)])
    assert len(errors) == 2
    assert len(successes) == 1
    index, remaining = successes[0]
    assert index == 1
    assert Path(remaining).read_text() == "second"
    assert first.read_text() == "first"


@pytest.mark.parametrize("outcome", ["failure", "cancel", "exception", "occupied"])
def test_pdf_compression_preserves_files_on_failure(tmp_path, outcome):
    source, destination = tmp_path / "source.pdf", tmp_path / "output.pdf"
    source.write_bytes(b"original")
    if outcome == "occupied":
        destination.write_bytes(b"existing")

    def optimize(_source, staged):
        staged.write_bytes(b"partial")
        if outcome == "exception":
            raise ValueError("engine failed")
        return outcome != "failure", "profile", 50.0

    def run():
        return compress_pdf(
            str(source), str(destination), replace=False, should_cancel=lambda: outcome == "cancel", optimize=optimize
        )

    if outcome == "failure":
        assert run() is None
    else:
        error = {"cancel": InterruptedError, "exception": ValueError, "occupied": FileExistsError}[outcome]
        with pytest.raises(error):
            run()
    assert source.read_bytes() == b"original"
    assert destination.read_bytes() == b"existing" if outcome == "occupied" else not destination.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == (
        ["output.pdf", "source.pdf"] if outcome == "occupied" else ["source.pdf"]
    )


def test_pdf_profile_threshold_and_independent_settings():
    assert pdf_settings("auto", 10 * 1024 * 1024)["jpeg_quality"] == 85
    assert pdf_settings("auto", 10 * 1024 * 1024 + 1)["jpeg_quality"] == 75
    settings = pdf_settings("max", 0)
    settings["jpeg_quality"] = 1
    assert pdf_settings("max", 0)["jpeg_quality"] == 40


def test_image_compression_cancel_preserves_source(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (50, 50), "red").save(source)
    original = source.read_bytes()
    destination = tmp_path / "result.png"
    with pytest.raises(InterruptedError):
        compress_image(str(source), str(destination), ".png", 80, replace=True, should_cancel=lambda: True)
    assert source.read_bytes() == original
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == [source]


def test_merge_rejects_missing_input_and_cancel_preserves_documents(tmp_path):
    from docx import Document

    paths = [tmp_path / "a.docx", tmp_path / "b.docx"]
    for path in paths:
        document = Document()
        document.add_paragraph(path.stem)
        document.save(path)
    original = [path.read_bytes() for path in paths]
    items = [FileItem(str(path)) for path in paths]
    output = tmp_path / "merged.docx"
    options = {"should_cancel": lambda: True, "status": lambda _value: None, "progress": lambda _value: None}
    with pytest.raises(InterruptedError):
        merge_documents(items, "docx", str(output), **options)
    assert [path.read_bytes() for path in paths] == original
    assert not output.exists()
    paths[1].unlink()
    with pytest.raises(FileNotFoundError):
        merge_documents(items, "docx", str(output), **options)
    assert not output.exists()
