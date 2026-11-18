"""Document conversion through the built-in Python engines."""

from pathlib import Path
from shutil import copyfile

from core.workers.atomic_output import atomic_output_path

OFFICE_INPUTS = frozenset({"DOCX", "ODT", "RTF", "HTML", "TXT"})
OFFICE_OUTPUTS = OFFICE_INPUTS | {"PDF"}


class OfficeUnavailableError(RuntimeError):
    """A document backend required by the application is unavailable."""


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
    same_format = "HTML" if source_format == ".HTM" else source_format[1:]
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
    if source_format == ".DOCX" and target == "TXT":
        from core.document_engine.docx_text import export_text

        export_text(source, destination, should_cancel)
        return ""
    if source_format == ".DOCX" and target == "HTML":
        from core.document_engine.docx_html import export_html

        export_html(source, destination, should_cancel)
        return ""
    if source_format in {".HTML", ".HTM"} and target == "DOCX":
        from core.document_engine.html_docx import import_docx

        import_docx(source, destination, should_cancel)
        return ""
    if source_format == ".ODT" and target in {"DOCX", "HTML"}:
        from core.document_engine.odt_html import convert_odt

        convert_odt(source, destination, target, should_cancel)
        return ""
    if source_format == ".RTF" and target in {"DOCX", "HTML"}:
        from core.document_engine.odt_html import save_body
        from core.document_engine.rtf_import import read_body

        save_body(read_body(source, should_cancel), source, destination, target, should_cancel)
        return ""
    if source_format in {".DOCX", ".HTML", ".HTM", ".RTF"} and target == "ODT":
        from core.document_engine.odt_export import export_odt

        export_odt(source, destination, source_format[1:], should_cancel)
        return ""
    if source_format in {".DOCX", ".HTML", ".HTM", ".ODT"} and target == "RTF":
        from core.document_engine.rtf_export import export_rtf

        export_rtf(source, destination, source_format[1:], should_cancel)
        return ""
    if source_format in {".DOCX", ".HTML", ".HTM", ".ODT", ".RTF"} and target == "PDF":
        from core.document_engine.rich_pdf import export_pdf

        export_pdf(source, destination, source_format[1:], should_cancel)
        return ""
    if source_format in {".HTML", ".HTM", ".ODT", ".RTF"} and target == "TXT":
        from core.document_engine.structured_text import export_text as export_structured_text

        export_structured_text(source, destination, source_format[1:], should_cancel)
        return ""
    if source_format == ".TXT":
        from core.document_engine.plain_text import EDITABLE_EXPORTS, convert_text

        if target in EDITABLE_EXPORTS:
            convert_text(source, destination, target, should_cancel)
            return ""
        if target == "PDF":
            from core.document_engine.text_pdf import export_pdf

            export_pdf(source, destination, should_cancel)
            return ""
    raise ValueError(f"Неподдерживаемое преобразование: {same_format} → {target}")
