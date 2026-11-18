"""Конвертация документов встроенными движками Python."""

from pathlib import Path
from shutil import copyfile

from app.core.conversion_formats import OFFICE_INPUTS, OFFICE_OUTPUTS, OFFICE_ROUTES, format_for_path
from core.filesystem import atomic_output_path


class OfficeUnavailableError(RuntimeError):
    """Необходимый приложению движок обработки документов недоступен."""


def run_office(source, destination, target_format, should_cancel, *, status=None) -> str:
    target = target_format.upper()
    if target not in OFFICE_OUTPUTS:
        raise ValueError(f"Неподдерживаемый формат документа: {target}")
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_format = source.suffix.upper()
    same_format = format_for_path(source) or source_format[1:]
    if same_format not in OFFICE_INPUTS:
        raise ValueError(f"Неподдерживаемый входной формат: {same_format}")
    if callable(status):
        status(f"Преобразование {same_format} → {target}")
    if same_format == target:
        with atomic_output_path(destination, allow_empty=target == "TXT") as temporary:
            copyfile(source, temporary)
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
        return ""
    route = OFFICE_ROUTES[same_format].get(target)
    if route == "docx_text":
        from core.document_engine.docx_text import export_text

        export_text(source, destination, should_cancel)
        return ""
    if route == "docx_html":
        from core.document_engine.docx_html import export_html

        export_html(source, destination, should_cancel)
        return ""
    if route == "html_docx":
        from core.document_engine.html_docx import import_docx

        import_docx(source, destination, should_cancel)
        return ""
    if route == "odt_body":
        from core.document_engine.odt_html import convert_odt

        convert_odt(source, destination, target, should_cancel)
        return ""
    if route == "rtf_body":
        from core.document_engine.odt_html import save_body
        from core.document_engine.rtf_import import read_body

        save_body(read_body(source, should_cancel), source, destination, target, should_cancel)
        return ""
    if route == "odt":
        from core.document_engine.odt_export import export_odt

        export_odt(source, destination, source_format[1:], should_cancel)
        return ""
    if route == "rtf":
        from core.document_engine.rtf_export import export_rtf

        export_rtf(source, destination, source_format[1:], should_cancel)
        return ""
    if route == "rich_pdf":
        from core.document_engine.rich_pdf import export_pdf

        export_pdf(source, destination, source_format[1:], should_cancel)
        return ""
    if route == "text":
        from core.document_engine.structured_text import export_text as export_structured_text

        export_structured_text(source, destination, source_format[1:], should_cancel)
        return ""
    if route == "plain":
        from core.document_engine.plain_text import convert_text

        convert_text(source, destination, target, should_cancel)
        return ""
    if route == "text_pdf":
        from core.document_engine.text_pdf import export_pdf

        export_pdf(source, destination, should_cancel)
        return ""
    raise ValueError(f"Неподдерживаемое преобразование: {same_format} → {target}")
