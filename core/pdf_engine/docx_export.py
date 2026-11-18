"""Экспорт страниц PDF в редактируемый текст или изображения отсканированных страниц."""

import re
from contextlib import ExitStack, closing
from io import BytesIO
from math import isfinite

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Pt
from docx.text.paragraph import Paragraph

from core.filesystem import atomic_output_path
from core.pdf_engine.image_placements import measure_page_images
from core.pdf_engine.render import open_pdf_renderer, render_page_image
from core.pdf_engine.text import open_pdf

_PDF_FAMILY_ALIASES = {
    "arial": "Arial", "helvetica": "Arial", "times": "Times New Roman", "timesnewroman": "Times New Roman",
    "courier": "Courier New", "couriernew": "Courier New",
}
_PDF_STYLE = re.compile(r"[-,](bolditalic|boldoblique|regular|roman|italic|oblique|bold)$", re.I)


def _format_run(run, font, size):
    if font:
        name = str(font.get("/BaseFont", "")).lstrip("/")
        name = re.sub(r"^[A-Z]{6}\+", "", name)
        name = re.sub(r"(?:PSMT|PS|MT)$", "", name)
        match = _PDF_STYLE.search(name)
        if match:
            style = match[1].lower()
            run.bold = "bold" in style
            run.italic = "italic" in style or "oblique" in style
            name = name[:match.start()]
        if name:
            run.font.name = _PDF_FAMILY_ALIASES.get(name.lower(), name)
    if size is not None and isfinite(size) and 1 <= size <= 400:
        run.font.size = Pt(size)


def _add_text(document, text, segments, should_cancel):
    if "".join(segment[0] for segment in segments) != text:
        segments = [(text, None, None)]
    paragraph = None
    for chunk, font, size in segments:
        for line in chunk.splitlines(keepends=True):
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
            if paragraph is None:
                paragraph = document.add_paragraph()
            contents = line.rstrip("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")
            if contents:
                _format_run(paragraph.add_run(contents), font, size)
            if len(contents) < len(line):
                paragraph = None


def _page_text(page):
    segments = []

    def capture(value, _ctm, _matrix, font, size):
        if value:
            segments.append((value, font, size))

    return page.extract_text(visitor_text=capture) or "", segments


def _page_size(page):
    width, height = (float(edge) * float(page.user_unit) for edge in (page.cropbox.width, page.cropbox.height))
    if not all(isfinite(edge) and edge > 0 for edge in (width, height)):
        raise ValueError("Некорректный размер страницы PDF")
    scale = min(1, 1584 / max(width, height))
    if page.rotation % 180:
        width, height = height, width
    return max(1, width * scale), max(1, height * scale)


def _set_section_size(section, size, margins):
    width, height = size
    section.orientation = WD_ORIENT.LANDSCAPE if width > height else WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = Pt(width), Pt(height)
    for name, maximum in (("left_margin", width), ("right_margin", width),
                          ("top_margin", height), ("bottom_margin", height)):
        setattr(section, name, Pt(min(margins[name], maximum * .15)))
    return (
        width - section.left_margin.pt - section.right_margin.pt,
        max(1, height - section.top_margin.pt - section.bottom_margin.pt - min(24, height * .15)),
    )


def _add_page_images(document, page, width, height, should_cancel):
    placements = {}
    measure_page_images(page, placements, should_cancel)
    for embedded in page.images:
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        picture = embedded.image
        if picture is None:
            continue
        with closing(picture):
            ref = embedded.indirect_reference
            image_width, image_height = placements.get(
                ref.idnum if ref else None, (.75 * picture.width, .75 * picture.height),
            )
            if image_width <= 0 or image_height <= 0:
                continue
            scale = min(1, width / image_width, height / image_height)
            dimensions = Pt(image_width * scale), Pt(image_height * scale)
            # pypdf возвращает самостоятельные изображения JPEG/PNG с учётом прозрачности.
            if embedded.data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")):
                with BytesIO(embedded.data) as stream:
                    document.add_picture(stream, width=dimensions[0], height=dimensions[1])
            else:
                with closing(picture.convert("RGBA")) as rgba, BytesIO() as stream:
                    rgba.save(stream, "PNG")
                    document.add_picture(stream, width=dimensions[0], height=dimensions[1])


def export_docx(source, destination, should_cancel):
    document = Document()
    section = document.sections[0]
    margins = {name: getattr(section, name).pt for name in
               ("left_margin", "right_margin", "top_margin", "bottom_margin")}
    with open_pdf(source, should_cancel) as reader, ExitStack() as resources:
        if not reader.pages:
            raise ValueError("PDF не содержит страниц")
        renderer = previous = None
        for index, page in enumerate(reader.pages):
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
            size = _page_size(page)
            if size != previous:
                if index:
                    section = document.add_section()
                width, height = _set_section_size(section, size, margins)
            body = document._body
            first_paragraph = len(body._element) - 1
            text, segments = _page_text(page)
            if text.strip():
                _add_text(document, text, segments, should_cancel)
                _add_page_images(document, page, width, height, should_cancel)
            else:
                if renderer is None:
                    renderer = resources.enter_context(open_pdf_renderer(source))
                with closing(render_page_image(renderer, index)) as picture, BytesIO() as stream:
                    picture.save(stream, "PNG")
                    image_width = min(width, height * picture.width / picture.height)
                    document.add_picture(stream, width=Pt(image_width))
            if index and size == previous:
                Paragraph(body._element[first_paragraph], body).paragraph_format.page_break_before = True
            previous = size
        with atomic_output_path(destination) as temporary:
            document.save(temporary)
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
