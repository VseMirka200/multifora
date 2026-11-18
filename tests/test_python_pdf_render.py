import pytest
from PIL import Image
from pypdf import PdfWriter

from core.pdf_engine.render import render_pdf_pages


def _source(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=36)
    writer.add_blank_page(width=36, height=72)
    with path.open("wb") as output:
        writer.write(output)
    writer.close()


def test_render_page_dimensions_and_order(tmp_path):
    source = tmp_path / "документ.pdf"
    _source(source)
    output = tmp_path / "изображения"
    output.mkdir()
    pages = render_pdf_pages(source, output, lambda: False)
    assert len(pages) == 2
    with Image.open(pages[0]) as image:
        assert image.size == (200, 100)
    with Image.open(pages[1]) as image:
        assert image.size == (100, 200)


def test_cancel_removes_partial_pages(tmp_path):
    source = tmp_path / "input.pdf"
    _source(source)
    calls = iter([False, False, True])
    with pytest.raises(InterruptedError):
        render_pdf_pages(source, tmp_path, lambda: next(calls))
    assert not list(tmp_path.glob("*.png"))
