"""Render PDF pages using PDFium."""

from pathlib import Path
from threading import Lock

import pypdfium2 as pdfium

_PDFIUM_LOCK = Lock()


def render_pdf_pages(source, output_dir, should_cancel):
    """Render pages at 200 DPI; remove partial results if rendering fails."""
    return list(render_selected_pages(source, output_dir, should_cancel).values())


def render_selected_pages(source, output_dir, should_cancel, *, only_pages=None):
    # PDFium calls must not run concurrently in the same process.
    with _PDFIUM_LOCK:
        return _render_pdf_pages(source, output_dir, should_cancel, only_pages)


def _render_pdf_pages(source, output_dir, should_cancel, only_pages):
    if should_cancel():
        raise InterruptedError("Преобразование отменено")
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    document = pdfium.PdfDocument(str(source))
    created = {}
    try:
        count = len(document)
        if not count:
            raise ValueError("PDF не содержит страниц")
        for index in range(count):
            if should_cancel():
                raise InterruptedError("Преобразование отменено")
            if only_pages is not None and index not in only_pages:
                continue
            output = output_dir / f"page-{index + 1:06d}.png"
            if output.exists():
                raise FileExistsError(output)
            page = document[index]
            bitmap = None
            try:
                bitmap = page.render(scale=200 / 72)
                created[index] = output
                bitmap.to_pil().save(output, format="PNG")
            finally:
                if bitmap is not None:
                    bitmap.close()
                page.close()
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
        return created
    except BaseException:
        for output in created.values():
            output.unlink(missing_ok=True)
        raise
    finally:
        document.close()
