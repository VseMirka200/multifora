"""Операции с PDF для обработчиков Мультифоры."""

from pathlib import Path

from core.filesystem import atomic_output_path


class PdfCraftUnavailableError(RuntimeError):
    """Необходимая библиотека PDF недоступна."""


def export_pdf(source, destination, target, should_cancel):
    if target == "TXT":
        return export_text(source, destination, should_cancel)
    if target == "DOCX":
        from core.pdf_engine.docx_export import export_docx

        return export_docx(source, destination, should_cancel)
    raise ValueError(f"Неподдерживаемый формат: {target}")


def combine_pdfs(sources, destination, should_cancel):
    from core.pdf_engine.merge import combine_pdfs as merge

    return merge(sources, destination, should_cancel)


def render_pdf_pages(source, output_dir, should_cancel):
    from core.pdf_engine.render import render_pdf_pages as render

    return render(source, output_dir, should_cancel)


def optimize_pdf(source, destination, settings, should_cancel):
    from core.pdf_engine.optimize import optimize_pdf as optimize

    return optimize(source, destination, settings, should_cancel)


def open_pdf(source, should_cancel):
    from pypdf import PdfReader

    if should_cancel():
        raise InterruptedError("Преобразование отменено")
    reader = PdfReader(Path(source))
    if reader.is_encrypted:
        reader.close()
        raise ValueError("Защищённый PDF не поддерживается")
    return reader


def export_text(source, destination, should_cancel):
    """Извлекает текст в порядке страниц и атомарно публикует результат в UTF-8."""
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
