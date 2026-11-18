"""Extract text from PDF with the Python backend."""

from pathlib import Path

from pypdf import PdfReader

from core.workers.atomic_output import atomic_output_path


def open_pdf(source, should_cancel):
    if should_cancel():
        raise InterruptedError("Преобразование отменено")
    reader = PdfReader(Path(source))
    if reader.is_encrypted:
        reader.close()
        raise ValueError("Защищённый PDF не поддерживается")
    return reader


def export_text(source, destination, should_cancel):
    """Extract text in page order and atomically publish UTF-8 output."""
    with open_pdf(source, should_cancel) as reader, atomic_output_path(destination, allow_empty=True) as temporary:
        with Path(temporary).open("w", encoding="utf-8", newline="\n") as output:
            for index, page in enumerate(reader.pages):
                if should_cancel():
                    raise InterruptedError("Преобразование отменено")
                if index:
                    output.write("\n")
                output.write(page.extract_text() or "")
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
