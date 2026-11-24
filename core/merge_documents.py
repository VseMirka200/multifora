"""Объединение упорядоченных исходных файлов в документ без зависимости от Qt."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from collections.abc import Callable, Sequence
from copy import deepcopy

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
    if output_format == "pdf" and not (page_order and all(file.path.lower().endswith(".docx") for file in files)) and not all(
        file.path.lower().endswith(".pdf") for file in files
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
            if composer is not None:
                # Разделяем документы новой страницей, не теряя медиа и стили.
                merged.add_page_break()
                composer.append(source)
            else:
                if _requires_docx_composer(source):
                    raise RuntimeError(
                        "Для объединения DOCX с изображениями, ссылками или стилями "
                        "установите docxcompose: pip install docxcompose"
                    )
                merged.add_page_break()
                for element in source.element.body:
                    if not element.tag.endswith("sectPr"):
                        merged.element.body.append(deepcopy(element))
        progress(int((index + 1) / total * 100))

    with atomic_output_path(output_path) as temporary:
        merged.save(temporary)
        # Проверяем ZIP/DOCX до публикации результата.
        Document(temporary)
    return output_path

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
