"""Exercise the production PDF entry points and verify their output."""

import random

import pytest
from docx import Document
from PIL import Image, ImageCms
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from core.document_engine.office import run_office
from core.pdf_engine.operations import combine_pdfs, export_pdf, optimize_pdf, render_pdf_pages


def test_pdfcraft_export_and_combine(tmp_path):
    source = tmp_path / "input.docx"
    document = Document()
    document.add_paragraph("Multifora test document")
    document.save(source)
    pdf = tmp_path / "input.pdf"
    run_office(source, pdf, "PDF", lambda: False)
    text = tmp_path / "out.txt"
    output = tmp_path / "out.docx"
    export_pdf(pdf, text, "TXT", lambda: False)
    export_pdf(pdf, output, "DOCX", lambda: False)
    assert "Multifora test document" in text.read_text(encoding="utf-8")
    assert "Multifora test document" in "\n".join(p.text for p in Document(output).paragraphs)
    merged = tmp_path / "merged.pdf"
    combine_pdfs([pdf, pdf], merged, lambda: False)
    assert len(PdfReader(merged).pages) == 2
    images = tmp_path / "images"
    images.mkdir()
    pages = render_pdf_pages(merged, images, lambda: False)
    assert len(pages) == 2
    assert all(page.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for page in pages)
    optimized = tmp_path / "optimized.pdf"
    optimize_pdf(pdf, optimized, {"color_resolution": 150, "gray_resolution": 150, "jpeg_quality": 75}, lambda: False)
    assert len(PdfReader(optimized).pages) == 1


def test_pdfcraft_compresses_image_pdf(tmp_path):
    rng = random.Random(42)
    source = tmp_path / "scan.pdf"
    Image.frombytes("RGB", (600, 600), rng.randbytes(600 * 600 * 3)).save(source, "PDF", resolution=300)
    result = tmp_path / "compressed.pdf"
    optimize_pdf(source, result, {"color_resolution": 72, "gray_resolution": 72, "jpeg_quality": 40}, lambda: False)
    assert result.stat().st_size < source.stat().st_size
    assert len(PdfReader(result).pages) == 1


def test_lossless_optimization_preserves_image_pixels_and_text(tmp_path):
    source = tmp_path / "image.pdf"
    picture = Image.frombytes("RGB", (300, 300), random.Random(42).randbytes(300 * 300 * 3))
    pdf = Canvas(str(source), pageCompression=0)
    pdf.drawImage(ImageReader(picture), 0, 0, width=72, height=72)
    pdf.drawString(20, 100, "Searchable text")
    pdf.save()

    output = tmp_path / "optimized.pdf"
    optimize_pdf(source, output, {"lossless": True}, lambda: False)

    page = PdfReader(output).pages[0]
    assert output.stat().st_size <= source.stat().st_size
    assert "Searchable text" in page.extract_text()
    assert page.mediabox == PdfReader(source).pages[0].mediabox
    assert page.images[0].image.tobytes() == picture.tobytes()


def test_lossless_optimization_keeps_original_bytes_without_size_gain(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    with PdfWriter() as writer:
        writer.add_blank_page(100, 200)
        writer.write(source)
    original = source.read_bytes()

    def write_larger(_writer, stream):
        stream.write(b"x" * (len(original) + 1))

    monkeypatch.setattr(PdfWriter, "write", write_larger)
    output = tmp_path / "optimized.pdf"
    optimize_pdf(source, output, {"lossless": True}, lambda: False)
    assert source.read_bytes() == output.read_bytes() == original


def test_export_scan_through_production_entry_point(tmp_path):
    source = tmp_path / "scan.pdf"
    Image.new("RGB", (200, 300), "blue").save(source, "PDF")
    docx = tmp_path / "out.docx"
    export_pdf(source, docx, "DOCX", lambda: False)
    assert len(Document(docx).inline_shapes) == 1
    text = tmp_path / "out.txt"
    export_pdf(source, text, "TXT", lambda: False)
    assert text.read_bytes() == b""


def test_pdf_docx_keeps_editable_font_and_displayed_image_size(tmp_path):
    source = tmp_path / "input.pdf"
    pdf = Canvas(str(source))
    pdf.setFont("Times-BoldItalic", 22)
    pdf.drawString(30, 400, "Styled PDF text")
    pdf.drawImage(ImageReader(Image.new("RGB", (640, 320), "blue")), 30, 320, width=108, height=54)
    pdf.save()

    output = tmp_path / "output.docx"
    export_pdf(source, output, "DOCX", lambda: False)
    doc = Document(output)
    run = doc.paragraphs[0].runs[0]
    assert (run.text, run.font.name, run.font.size.pt, run.bold, run.italic) == (
        "Styled PDF text", "Times New Roman", 22, True, True,
    )
    image = doc.inline_shapes[0]
    assert (image.width.pt, image.height.pt) == pytest.approx((108, 54), abs=0.02)


def test_merge_preserves_outlines(tmp_path):
    source = tmp_path / "links.pdf"
    with PdfWriter() as writer:
        writer.add_blank_page(width=72, height=72)
        writer.add_outline_item(title="Раздел", page_number=0)
        writer.write(source)
    output = tmp_path / "merged.pdf"
    combine_pdfs([source, source], output, lambda: False)
    reader = PdfReader(output)
    assert [(item.title, reader.get_destination_page_number(item)) for item in reader.outline] == [
        ("Раздел", 0), ("Раздел", 1),
    ]


def test_lossy_profile_preserves_masks_profiles_and_largest_placement(tmp_path):
    source = tmp_path / "input.pdf"
    pixels = random.Random(7).randbytes(600 * 600 * 3)
    rgb = Image.frombytes("RGB", (600, 600), pixels)
    profiled = tmp_path / "profile.jpg"
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    rgb.save(profiled, icc_profile=profile)
    transparent = rgb.convert("RGBA")
    transparent.putalpha(Image.linear_gradient("L").resize(rgb.size))
    pdf = Canvas(str(source))
    pdf.drawImage(ImageReader(rgb), 0, 0, width=30, height=30)
    pdf.drawImage(ImageReader(transparent), 0, 40, width=72, height=72, mask="auto")
    pdf.drawImage(str(profiled), 0, 120, width=72, height=72)
    pdf.showPage()
    pdf.drawImage(ImageReader(rgb), 0, 0, width=144, height=144)
    pdf.save()

    result = tmp_path / "compressed.pdf"
    optimize_pdf(source, result, {"color_resolution": 72, "gray_resolution": 72, "jpeg_quality": 40}, lambda: False)
    assert result.stat().st_size < source.stat().st_size
    with PdfReader(source) as original, PdfReader(result) as output:
        images = list(output.pages[0].images)
        assert any(obj.image.mode == "RGBA" for obj in images)
        assert {obj.image.size for obj in images} == {(144, 144), (600, 600)}
        assert output.pages[1].images[0].image.size == (144, 144)
        for before, after in zip(original.pages[0].images, images, strict=True):
            if after.image.size == (600, 600):
                assert before.indirect_reference.get_object()._data == after.indirect_reference.get_object()._data


def test_pdf_docx_preserves_rotated_cropbox_and_scan_proportions(tmp_path):
    source = tmp_path / "input.pdf"
    pdf = Canvas(str(source), pagesize=(300, 450))
    pdf.drawString(45, 110, "Editable")
    pdf.showPage()
    pdf.setPageSize((300, 450))
    pdf.drawImage(ImageReader(Image.new("RGB", (300, 450), "blue")), 0, 0, width=300, height=450)
    pdf.save()
    rotated = tmp_path / "rotated.pdf"
    with PdfReader(source) as reader, PdfWriter() as writer:
        writer.append(reader)
        page = writer.pages[1]
        page.cropbox.upper_right = (250, 400)
        page.rotate(90)
        writer.write(rotated)
    output = tmp_path / "output.docx"
    export_pdf(rotated, output, "DOCX", lambda: False)
    document = Document(output)
    assert [section.orientation.name for section in document.sections] == ["PORTRAIT", "LANDSCAPE"]
    assert [(section.page_width.pt, section.page_height.pt) for section in document.sections] == [
        (300, 450), (400, 250),
    ]
    shape, = document.inline_shapes
    assert shape.width / shape.height == pytest.approx(400 / 250, abs=.01)
    assert document.paragraphs[0].text.strip() == "Editable"
