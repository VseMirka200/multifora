"""Объединение упорядоченных исходных файлов в документ без зависимости от Qt."""

import os
import re
from collections.abc import Callable, Sequence
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from core.file_models import OperationSource
from core.filesystem import atomic_output_path, get_unique_path


def merge_documents(
    sources: Sequence[OperationSource],
    output_format: str,
    output_path: str,
    *,
    should_cancel: Callable[[], bool],
    status: Callable[[str], None],
    progress: Callable[[int], None],
    unique_path: Callable[[str], str] = get_unique_path,
    page_order=(),
) -> str:
    files = [file for file in sources if file.is_file]
    if not files or (len(files) < 2 and len(page_order) < 2):
        raise Exception("Для объединения нужно выбрать минимум два файла.")

    output_format = str(output_format or "pdf").lower()
    if output_format == "docx" and not all(
        file.path.lower().endswith(".docx") for file in files
    ):
        raise Exception("Объединение в DOCX поддерживает только файлы DOCX.")
    if output_format == "pdf" and not (
        all(file.path.lower().endswith(".pdf") for file in files)
        or (page_order and all(file.path.lower().endswith(".docx") for file in files))
    ):
        raise Exception("Объединение в PDF поддерживает только файлы PDF.")
    if output_format not in {"docx", "pdf"}:
        raise Exception(f"Неподдерживаемый формат объединения: {output_format}")

    # С момента запуска файл мог быть перемещён, удалён или стать недоступным.
    missing_paths = [file.path for file in files if not os.path.isfile(file.path)]
    if missing_paths:
        listed_paths = "\n".join(f"• {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Не найдены или недоступны исходные документы:\n"
            f"{listed_paths}\n\n"
            "Удалите их из списка или добавьте снова."
        )
    destination = unique_path(_merge_output_path(files[0].path, output_format, output_path))
    if output_format == "docx":
        if page_order:
            from core.document_engine.docx_pages import merge_docx_pages

            status("Объединение страниц DOCX")
            return merge_docx_pages([file.path for file in files], destination, page_order, should_cancel, progress)
        return _merge_docx(files, destination, should_cancel, status, progress)

    from core.pdf_engine.merge import combine_pdfs

    status("Объединение PDF")
    paths = [file.path for file in files]
    if page_order:
        with TemporaryDirectory() as staging:
            sources_pdf = [paged_source(path, staging, i, should_cancel) for i, path in enumerate(paths)]
            combine_pdfs(sources_pdf, destination, should_cancel, page_order=page_order)
    else:
        combine_pdfs(paths, destination, should_cancel)
    progress(100)
    return destination


def paged_source(path, staging, index, should_cancel):
    if Path(path).suffix.lower() == ".pdf":
        return path
    from core.document_engine.office import run_office

    output = Path(staging) / f"{index}.pdf"
    run_office(path, output, "PDF", should_cancel)
    return output


def _merge_output_path(first_path: str, extension: str, output_path: str) -> str:
    requested_path = str(output_path or "").strip()
    if requested_path:
        base, ext = os.path.splitext(requested_path)
        if ext.lower() != f".{extension}":
            requested_path = (
                f"{base}.{extension}"
                if base
                else f"{requested_path}.{extension}"
            )
        return requested_path

    folder = os.path.dirname(first_path)
    return os.path.join(folder, f"Объединенный_документ.{extension}")


def _merge_docx(
    files: list[OperationSource],
    output_path: str,
    should_cancel: Callable[[], bool],
    status: Callable[[str], None],
    progress: Callable[[int], None],
) -> str:
    try:
        from docx import Document
    except ImportError as error:
        raise Exception(
            "Установите python-docx для объединения файлов DOCX."
        ) from error

    merged = Document(files[0].path)
    total = len(files)
    try:
        from docxcompose.composer import Composer
    except ImportError:
        # Без Composer простое копирование XML подходит только для
        # документов без ссылок на ресурсы и стили. Для сложных файлов
        # запрещаем повреждающее объединение, вместо выдачи битого DOCX.
        composer = None
    else:
        composer = Composer(merged)

    for index, file in enumerate(files):
        if should_cancel():
            raise InterruptedError("Операция отменена пользователем")
        status(f"Объединение: {file.name}")
        if index > 0:
            source = Document(file.path)
            if composer is None and _requires_docx_composer(source):
                raise RuntimeError(
                    "Для объединения DOCX с изображениями, ссылками или стилями "
                    "установите docxcompose: pip install docxcompose"
                )
            _match_even_page_settings(merged, source)
            previous_sections = len(merged.sections)
            merged.add_section()
            if composer is not None:
                composer.append(source)
            else:
                for element in source.element.body:
                    if not element.tag.endswith("sectPr"):
                        merged.element.body.insert(-1, deepcopy(element))
            _restore_docx_sections(merged, source, previous_sections, composer)
            if composer is not None:
                composer.renumber_docpr_ids()
                composer.renumber_nvpicpr_ids()
        progress(int((index + 1) / total * 95))

    with atomic_output_path(output_path) as temporary:
        merged.save(temporary)
        # Проверяем ZIP/DOCX до публикации результата.
        Document(temporary)
        if should_cancel():
            raise InterruptedError("Операция отменена пользователем")
    progress(100)
    return output_path


def _copy_docx_part(relationship, parent, copied, *, keep_id=False):
    source = relationship.target_part
    target = copied.get(source)
    is_new = target is None
    if is_new:
        package = parent.package
        name = source.partname
        extension = f".{name.ext}" if name.ext else ""
        stem = re.sub(r"\d+$", "", name.filename.removesuffix(extension))
        partname = package.next_partname(f"{name.baseURI.rstrip('/')}/{stem}%d{extension}")
        target = type(source).load(partname, source.content_type, source.blob, package)
        copied[source] = target
    if keep_id:
        rid = relationship.rId
        parent.load_rel(relationship.reltype, target, rid)
    else:
        rid = parent.relate_to(target, relationship.reltype)
    if is_new:
        for rel in source.rels.values():
            if rel.is_external:
                target.load_rel(rel.reltype, rel.target_ref, rel.rId, is_external=True)
            else:
                _copy_docx_part(rel, target, copied, keep_id=True)
    return rid


def _match_even_page_settings(merged, source):
    from docx.enum.section import WD_HEADER_FOOTER

    if merged.settings.odd_and_even_pages_header_footer == source.settings.odd_and_even_pages_header_footer:
        return
    document = source if merged.settings.odd_and_even_pages_header_footer else merged
    document.settings.odd_and_even_pages_header_footer = True
    for index, section in enumerate(document.sections):
        properties = section._sectPr
        for name in ("header", "footer"):
            # При включении общей настройки чётные страницы этого документа продолжают использовать обычный блок.
            if index == 0:
                getattr(section, name).is_linked_to_previous = False
            get_reference = getattr(properties, f"get_{name}Reference")
            even = get_reference(WD_HEADER_FOOTER.EVEN_PAGE)
            if even is not None:
                properties.remove(even)
            default = get_reference(WD_HEADER_FOOTER.PRIMARY)
            if default is not None:
                getattr(properties, f"add_{name}Reference")(WD_HEADER_FOOTER.EVEN_PAGE, default.rId)


def _restore_docx_sections(merged, source, previous_sections, composer):
    from docx.enum.section import WD_SECTION_START
    from docx.oxml.ns import qn
    from docx.parts.hdrftr import FooterPart, HeaderPart

    copied = {}
    for index, (original, added) in enumerate(zip(source.sections, merged.sections[previous_sections:], strict=True)):
        properties = deepcopy(original._sectPr)
        for ref in properties.xpath(".//*[@r:id]"):
            rel = source.part.rels[ref.get(qn("r:id"))]
            ref.set(qn("r:id"), _copy_docx_part(rel, merged.part, copied))
        if index == 0:
            properties.start_type = WD_SECTION_START.NEW_PAGE
        added._sectPr.getparent().replace(added._sectPr, properties)

    if composer is not None:
        for part in copied.values():
            if isinstance(part, (HeaderPart, FooterPart)):
                composer.add_styles(source, part.element)

    # Первый раздел нового документа не должен наследовать колонтитулы предыдущего.
    first_section = merged.sections[previous_sections]
    for attribute in (
        "header", "footer", "first_page_header", "first_page_footer", "even_page_header", "even_page_footer",
    ):
        getattr(first_section, attribute).is_linked_to_previous = False


def _requires_docx_composer(document) -> bool:
    """Ссылочные ресурсы нельзя переносить простым deepcopy XML-элементов."""
    from docx.oxml.ns import qn

    relationship_attributes = {qn("r:id"), qn("r:embed"), qn("r:link")}
    specialized_elements = {
        qn("w:numPr"),
        qn("w:pStyle"),
        qn("w:rStyle"),
        qn("w:tblStyle"),
        qn("w:drawing"),
        qn("w:pict"),
        qn("w:object"),
    }
    for element in document.element.body.iter():
        if element.tag in specialized_elements:
            return True
        if relationship_attributes.intersection(element.attrib):
            return True
    return False
