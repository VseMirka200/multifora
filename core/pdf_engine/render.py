"""Render PDF pages using PDFium."""

from contextlib import closing, contextmanager
from pathlib import Path
from threading import Lock

import pypdfium2 as pdfium

from core.workers.atomic_output import atomic_output_path

_PDFIUM_LOCK = Lock()
_SHARED_BITMAP_MODES = {"RGBA", "RGBX", "L"}


@contextmanager
def open_pdf_renderer(source):
    with _PDFIUM_LOCK:
        document = pdfium.PdfDocument(str(source))
    try:
        yield document
    finally:
        with _PDFIUM_LOCK:
            document.close()


def render_page_image(document, index):
    with _PDFIUM_LOCK:
        page = document[index]
        try:
            bitmap = page.render(scale=200 / 72)
            try:
                image = bitmap.to_pil()
                # Pillow may be sharing the native bitmap for these modes.
                return image.copy() if image.mode == bitmap.mode and image.mode in _SHARED_BITMAP_MODES else image
            finally:
                bitmap.close()
        finally:
            page.close()


def render_pdf_pages(source, output_dir, should_cancel):
    """Render pages at 200 DPI; remove partial results if rendering fails."""
    return list(render_selected_pages(source, output_dir, should_cancel).values())


def render_selected_pages(source, output_dir, should_cancel, *, only_pages=None):
    if should_cancel():
        raise InterruptedError("Преобразование отменено")
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    created = {}
    try:
        with open_pdf_renderer(source) as document:
            with _PDFIUM_LOCK:
                count = len(document)
            if not count:
                raise ValueError("PDF не содержит страниц")
            for index in range(count):
                if should_cancel():
                    raise InterruptedError("Преобразование отменено")
                if only_pages is not None and index not in only_pages:
                    continue
                output = output_dir / f"page-{index + 1:06d}.png"
                with atomic_output_path(output) as temporary, closing(render_page_image(document, index)) as picture:
                    picture.save(temporary, format="PNG")
                created[index] = output
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
        return created
    except BaseException:
        for output in created.values():
            output.unlink(missing_ok=True)
        raise
