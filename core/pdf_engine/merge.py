"""Объединение страниц PDF средствами движка Python."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from core.filesystem import atomic_output_path


def combine_pdfs(sources, destination, should_cancel, *, page_order=()):
    """Объединяет страницы в исходном порядке и атомарно публикует результат."""
    sources = [Path(source) for source in sources]
    if not sources:
        raise ValueError("Не выбраны файлы PDF для объединения")
    if should_cancel():
        raise InterruptedError("Объединение отменено")
    writer = PdfWriter()
    try:
        readers = []
        for source in sources:
            if should_cancel():
                raise InterruptedError("Объединение отменено")
            reader = PdfReader(source)
            if reader.is_encrypted:
                raise ValueError(f"Защищённый PDF не поддерживается: {source.name}")
            if page_order:
                readers.append(reader)
            else:
                writer.append(reader)
        if page_order:
            expected = {(i, p) for i, reader in enumerate(readers) for p in range(len(reader.pages))}
            if len(page_order) != len(expected) or set(page_order) != expected:
                raise ValueError("Состав страниц изменился. Откройте миниатюры заново.")
            for source_index, page_index in page_order:
                if should_cancel():
                    raise InterruptedError("Объединение отменено")
                writer.add_page(readers[source_index].pages[page_index])
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
