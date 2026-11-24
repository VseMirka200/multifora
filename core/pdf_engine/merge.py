"""Объединение страниц PDF средствами движка Python."""

from contextlib import ExitStack
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import Fit

from core.filesystem import atomic_output_path


def _copy_outline(writer, reader, pages, should_cancel, items, parent=None):
    previous = parent
    for item in items:
        if should_cancel():
            raise InterruptedError("Объединение отменено")
        if isinstance(item, list):
            _copy_outline(writer, reader, pages, should_cancel, item, previous)
            continue
        previous = parent
        number = pages.get(reader.get_destination_page_number(item))
        if number is None:
            continue
        flags = item.get("/F", 0)
        previous = writer.add_outline_item(
            title=item.title,
            page_number=number,
            parent=parent,
            color=tuple(item["/C"]) if "/C" in item else None,
            bold=bool(flags & 2),
            italic=bool(flags & 1),
            fit=Fit(item.typ, item.dest_array[2:]),
            is_open=item.get("/Count", 0) >= 0,
        )


def combine_pdfs(sources, destination, should_cancel, *, page_order=()):
    """Объединяет страницы в исходном порядке и атомарно публикует результат."""
    sources = [Path(source) for source in sources]
    if not sources:
        raise ValueError("Не выбраны файлы PDF для объединения")
    if should_cancel():
        raise InterruptedError("Объединение отменено")
    with PdfWriter() as writer, ExitStack() as resources:
        readers = []
        for source in sources:
            if should_cancel():
                raise InterruptedError("Объединение отменено")
            reader = resources.enter_context(PdfReader(source))
            if reader.is_encrypted:
                raise ValueError(f"Защищённый PDF не поддерживается: {source.name}")
            if page_order:
                readers.append(reader)
            else:
                writer.append(reader)
        if page_order:
            expected = {(i, p) for i, reader in enumerate(readers) for p in range(len(reader.pages))}
            if len(page_order) != len(set(page_order)) or not set(page_order).issubset(expected):
                raise ValueError("Состав страниц изменился. Откройте миниатюры заново.")
            page_maps = [{} for _ in readers]
            for output_index, (source_index, page_index) in enumerate(page_order):
                if should_cancel():
                    raise InterruptedError("Объединение отменено")
                writer.add_page(readers[source_index].pages[page_index])
                page_maps[source_index][page_index] = output_index
            for reader, pages in zip(readers, page_maps, strict=True):
                if pages:
                    _copy_outline(writer, reader, pages, should_cancel, reader.outline)
        if not writer.pages:
            raise ValueError("PDF не содержит страниц")
        if should_cancel():
            raise InterruptedError("Объединение отменено")
        with atomic_output_path(destination) as temporary:
            with open(temporary, "wb") as output:
                writer.write(output)
            if should_cancel():
                raise InterruptedError("Объединение отменено")
