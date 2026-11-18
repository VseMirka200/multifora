"""Export PDF pages as editable text or images for scanned pages."""

from io import BytesIO
from tempfile import TemporaryDirectory

from docx import Document
from docx.shared import Emu
from PIL import Image

from core.pdf_engine.render import render_selected_pages
from core.pdf_engine.text import open_pdf
from core.workers.atomic_output import atomic_output_path


def export_docx(source, destination, should_cancel):
    document = Document()
    section = document.sections[0]
    width = section.page_width - section.left_margin - section.right_margin
    height = section.page_height - section.top_margin - section.bottom_margin
    reader = open_pdf(source, should_cancel)
    pages = []
    for page in reader.pages:
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        pages.append(page.extract_text() or "")
    if not pages:
        raise ValueError("PDF не содержит страниц")
    with TemporaryDirectory(prefix="multifora_pdf_docx_") as folder:
        selected = {index for index, text in enumerate(pages) if not text.strip()}
        scans = render_selected_pages(source, folder, should_cancel, only_pages=selected) if selected else {}
        for index, text in enumerate(pages):
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
            if index:
                document.add_page_break()
            if index not in scans:
                for line in text.splitlines():
                    document.add_paragraph(line)
                for embedded in reader.pages[index].images:
                    if should_cancel():
                        raise InterruptedError("Конвертация отменена")
                    if embedded.image is not None:
                        picture = embedded.image
                        with BytesIO() as stream:
                            picture.convert("RGBA").save(stream, "PNG")
                            stream.seek(0)
                            natural_width = picture.width * 9525
                            fit_width = (height - 300_000) * picture.width // picture.height
                            image_width = min(width, natural_width, fit_width)
                            document.add_picture(stream, width=Emu(image_width))
            else:
                with Image.open(scans[index]) as picture:
                    image_width = min(width, (height - 300_000) * picture.width // picture.height)
                document.add_picture(str(scans[index]), width=Emu(image_width))
        with atomic_output_path(destination) as temporary:
            document.save(temporary)
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
