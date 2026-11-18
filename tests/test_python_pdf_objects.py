import pytest

from core.pdf_engine.objects import Name, Reference, parse_object, serialize_object


def test_parse_nested_pdf_objects():
    assert parse_object(b"<< /Type /Page /Parent 2 0 R /Box [0 0 72.5 72] /Text (hello) /Flag true >>") == {
        b"Type": Name(b"Page"), b"Parent": Reference(2, 0), b"Box": [0, 0, 72.5, 72],
        b"Text": b"hello", b"Flag": True,
    }


@pytest.mark.parametrize("data", [b"[1", b"<< /Key >>", b"<< 1 2 >>", b"1 0 R 2", b"0 0 R", b"word"])
def test_rejects_invalid_objects(data):
    with pytest.raises(ValueError):
        parse_object(data)


def test_object_roundtrip():
    obj = {b"A B": [Name(b"x#y"), b"\x00\xff", Reference(12, 3), -0.0000001, None, True]}
    assert parse_object(serialize_object(obj)) == obj


@pytest.mark.parametrize("value", [float("nan"), float("inf"), Reference(0, 0)])
def test_rejects_unrepresentable_values(value):
    with pytest.raises(ValueError):
        serialize_object(value)
