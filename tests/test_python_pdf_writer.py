import pytest
from pypdf import PdfReader

from core.pdf_engine.objects import Name, Reference
from core.pdf_engine.writer import Stream, write_pdf


def test_writer_produces_readable_pdf(tmp_path):
    pdf = write_pdf({
        1: {b"Type": Name(b"Catalog"), b"Pages": Reference(2, 0)},
        2: {b"Type": Name(b"Pages"), b"Kids": [Reference(3, 0)], b"Count": 1},
        3: {b"Type": Name(b"Page"), b"Parent": Reference(2, 0), b"MediaBox": [0, 0, 72, 72],
            b"Contents": Reference(5, 0)},
        5: Stream({}, b"q Q"),
    }, Reference(1, 0))
    offset = int(pdf.split(b"startxref\n")[1].splitlines()[0])
    assert pdf[offset:offset + 4] == b"xref"
    assert b"/Length 3" in pdf
    path = tmp_path / "generated.pdf"
    path.write_bytes(pdf)
    assert len(PdfReader(path).pages) == 1


def test_writer_rejects_invalid_root():
    with pytest.raises(ValueError):
        write_pdf({1: {}}, Reference(1, 0))
