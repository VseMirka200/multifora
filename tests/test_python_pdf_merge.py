import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from core.pdf_engine.merge import combine_pdfs


def _pdf(path, widths):
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=100)
    with path.open("wb") as output:
        writer.write(output)
    writer.close()


def test_combine_preserves_page_order_and_sources(tmp_path):
    first, second = tmp_path / "один.pdf", tmp_path / "два.pdf"
    _pdf(first, [100, 200])
    _pdf(second, [300])
    original = first.read_bytes()
    output = tmp_path / "результат.pdf"
    combine_pdfs([first, second], output, lambda: False)
    assert [int(page.mediabox.width) for page in PdfReader(output).pages] == [100, 200, 300]
    assert first.read_bytes() == original


def test_cancel_does_not_replace_existing_output(tmp_path):
    source = tmp_path / "source.pdf"
    _pdf(source, [100])
    output = tmp_path / "out.pdf"
    output.write_bytes(b"original")
    with pytest.raises(InterruptedError):
        combine_pdfs([source], output, lambda: True)
    assert output.read_bytes() == b"original"


def test_invalid_pdf_does_not_replace_output(tmp_path):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"broken")
    output = tmp_path / "out.pdf"
    output.write_bytes(b"original")
    with pytest.raises(PdfReadError):
        combine_pdfs([source], output, lambda: False)
    assert output.read_bytes() == b"original"
