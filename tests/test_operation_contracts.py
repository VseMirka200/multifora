from dataclasses import FrozenInstanceError

import pytest

from core.operation_requests import ConversionRequest, RenameRequest
from core.operation_result import OperationResult
from core.output_paths import compressed_name, conversion_directory, converted_name


def test_retry_preserves_requested_order_and_strictness():
    request = RenameRequest((("a", "one"), ("b", "two")), strict=True)
    retry = request.for_retry(["b", "missing", "a"])
    assert retry.pairs == (("b", "two"), ("a", "one"))
    assert retry.strict
    assert len(request.pairs) == 2
    with pytest.raises(FrozenInstanceError):
        retry.strict = False


@pytest.mark.parametrize(("conversion_type", "kind"), [("auto_image", "convert_image"), ("docx", "convert_document")])
def test_conversion_worker_kind(conversion_type, kind):
    assert ConversionRequest(conversion_type, "pdf", "alongside", "").worker_kind == kind


def test_result_lists_are_independent_and_dictionary_compatible():
    first, second = OperationResult(), OperationResult()
    first.errors.append({"message": "failed"})
    assert second.errors == []
    assert first["errors"] == [{"message": "failed"}]
    assert "warnings" in first
    assert first.get("unknown", "fallback") == "fallback"
    with pytest.raises(KeyError):
        _ = first["unknown"]


def test_output_names_and_directories(tmp_path):
    source, custom = str(tmp_path / "source"), str(tmp_path / "custom")
    assert conversion_directory(source, "alongside", custom) == source
    assert conversion_directory(source, "custom", custom) == custom
    assert conversion_directory(source, "custom", "") == str(tmp_path / "source" / "Конвертированные")
    assert converted_name("report.old.docx", ".pdf") == "report.old.pdf"
    assert converted_name("report.docx", "") == "report.docx"
    assert compressed_name("photo.png", "jpg") == "photo_compressed.jpg"
    assert compressed_name("photo.png", ".png") == "photo_compressed.png"
