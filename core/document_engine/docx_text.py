"""Извлечение абзацев и таблиц DOCX в порядке документа."""

from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from core.filesystem import atomic_output_path


def export_text(source, destination, should_cancel):
    if should_cancel():
        raise InterruptedError("Преобразование отменено")
    document = Document(source)
    lines = []
    for block in document.iter_inner_content():
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
        if isinstance(block, Paragraph):
            lines.append(block.text)
        elif isinstance(block, Table):
            lines.extend("\t".join(cell.text.replace("\n", " ") for cell in row.cells) for row in block.rows)
    with atomic_output_path(destination, allow_empty=True) as temporary:
        Path(temporary).write_text("\n".join(lines), encoding="utf-8", newline="\n")
        if should_cancel():
            raise InterruptedError("Преобразование отменено")
