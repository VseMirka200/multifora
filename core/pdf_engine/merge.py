"""PDF page merging for the Python backend."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from core.workers.atomic_output import atomic_output_path


def combine_pdfs(sources, destination, should_cancel):
    """Merge pages in source order, publishing the result atomically."""
    sources = [Path(source) for source in sources]
    if not sources:
        raise ValueError("Не выбраны файлы PDF для объединения")
    if should_cancel():
        raise InterruptedError("Объединение отменено")
    writer = PdfWriter()
    try:
        for source in sources:
            if should_cancel():
                raise InterruptedError("Объединение отменено")
            reader = PdfReader(source)
            if reader.is_encrypted:
                raise ValueError(f"Защищённый PDF не поддерживается: {source.name}")
            writer.append(reader)
        if not writer.pages:
            raise ValueError("PDF не содержит страниц")
        if should_cancel():
            raise InterruptedError("Объединение отменено")
        with atomic_output_path(destination) as temporary:
            with open(temporary, "wb") as output:
                writer.write(output)
            if should_cancel():
                raise InterruptedError("Объединение отменено")
    finally:
        writer.close()
