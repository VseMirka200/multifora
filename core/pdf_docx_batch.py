"""Параллельная конвертация PDF в DOCX с ограничением числа задач."""

import os
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from app.core.models import FileItem, OperationSource
from core.workers.pdfcraft_engine import PdfCraftUnavailableError


def pdf_docx_worker_count(files: list[OperationSource]) -> int:
    """Ограничивает число движков, чтобы большие PDF не перегружали память."""
    maximum = min(4, max(1, (os.cpu_count() or 2) // 2))
    sizes = []
    for file in files:
        try:
            sizes.append(os.path.getsize(file.path))
        except OSError:
            continue
    if sizes and max(sizes) >= 25 * 1024 * 1024:
        return 1
    if sizes and max(sizes) >= 10 * 1024 * 1024:
        return min(2, maximum)
    return maximum

def run_parallel_batch(
    files: list[OperationSource],
    max_workers: int,
    *,
    convert: Callable[[OperationSource], str],
    result_item: Callable[[str], FileItem | None],
    should_cancel: Callable[[], bool],
    report_error: Callable[[OperationSource, Exception], None],
    discard: Callable[[str], None],
    progress: Callable[[int], None],
    status: Callable[[str], None],
) -> list[FileItem]:
    total = len(files)
    results_by_index: dict[int, FileItem] = {}
    valid = [(index, file) for index, file in enumerate(files) if file.path.lower().endswith(".pdf")]
    processed = total - len(valid)
    if processed:
        progress(int(processed / total * 100))
    if valid:
        status(f"Конвертация PDF: одновременно до {max_workers} файлов")
    next_file = 0
    common_error = None
    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="pdf-to-docx",
    ) as executor:
        pending = {}
        while next_file < len(valid) and len(pending) < max_workers and not should_cancel():
            index, file = valid[next_file]
            pending[executor.submit(convert, file)] = (index, file)
            next_file += 1
        while pending:
            if should_cancel():
                for future in pending:
                    future.cancel()
                status("Отмена: ожидаем завершения уже запущенных конвертаций…")
                break
            # wait с таймаутом позволяет проверить запрос отмены, даже если
            # долго обрабатывает одну страницу документа.
            done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for future in sorted(done, key=lambda item: pending[item][0]):
                index, file = pending.pop(future)
                status(f"Конвертация: {file.name}")
                try:
                    converted_item = result_item(future.result())
                    if converted_item is None:
                        raise Exception("Движок не создал выходной DOCX-файл")
                    results_by_index[index] = converted_item
                except InterruptedError as error:
                    if not should_cancel():
                        report_error(file, error)
                except Exception as error:
                    report_error(file, error)
                    if isinstance(error, PdfCraftUnavailableError):
                        common_error = error
                finally:
                    processed += 1
                    progress(int(processed / total * 100))
            while (
                common_error is None
                and next_file < len(valid)
                and len(pending) < max_workers
                and not should_cancel()
            ):
                index, file = valid[next_file]
                pending[executor.submit(convert, file)] = (index, file)
                next_file += 1

        # ThreadPoolExecutor ожидает активные задачи перед выходом из with.
        # Результаты, успевшие закончиться после запроса отмены, убираем,
        # чтобы не оставить на диске файлы, не показанные пользователю.
        if should_cancel():
            published = {item.path for item in results_by_index.values()}
            for future in pending:
                if future.cancelled():
                    continue
                try:
                    path = future.result()
                except Exception:
                    continue
                if path and path not in published:
                    discard(path)
    if common_error is not None and not should_cancel():
        for _, file in valid[next_file:]:
            report_error(file, common_error)
        progress(100)
    return [results_by_index[index] for index in sorted(results_by_index)]
