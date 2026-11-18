"""Extract text from PDF with the Python backend."""

from pathlib import Path

from pypdf import PdfReader

from core.workers.atomic_output import atomic_output_path


def open_pdf(source, should_cancel):
    if should_cancel():
        raise InterruptedError("Преобразование отменено")
    reader = PdfReader(Path(source))
    if reader.is_encrypted:
        raise ValueError("Защищённый PDF не поддерживается")
    return reader


def export_text(source, destination, should_cancel):
    """Extract text in page order and atomically publish UTF-8 output."""
    reader = open_pdf(source, should_cancel)
    pages = []
    for page in reader.pages:
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
        pages.append(page.extract_text() or "")
    text = "\n".join(pages)
    with atomic_output_path(destination, allow_empty=True) as temporary:
        Path(temporary).write_text(text, encoding="utf-8", newline="\n")
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
