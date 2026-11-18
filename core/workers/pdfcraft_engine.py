"""Операции с PDF для обработчиков Мультифоры."""

class PdfCraftUnavailableError(RuntimeError):
    """Необходимая библиотека PDF недоступна."""


def export_pdf(source, destination, target, should_cancel):
    if target == "TXT":
        from core.pdf_engine.text import export_text

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
