import os


CANCELLED_STATUS = "Операция отменена пользователем"


def get_unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{base}_{counter}{ext}"
        counter += 1
    return path


def emit_progress(worker, index: int, total: int) -> None:
    if total <= 0:
        return
    worker.progress.emit(int((index + 1) / total * 100))


def finish_if_cancelled(worker, new_files=None, updated_files=None) -> bool:
    if not worker._should_cancel():
        return False
    worker.status.emit(CANCELLED_STATUS)
    worker._emit_finished(new_files or [], updated_files or [])
    return True


def record_file_error(worker, file_item, message: str) -> None:
    worker._record_error(file_item, message)
    worker.error.emit(message)
