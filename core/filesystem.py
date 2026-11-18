"""Безопасное создание выходного файла рядом с конечным расположением."""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager


def publish_new_file(source, destination):
    """Публикует готовый файл в той же файловой системе, не заменяя существующий."""
    if sys.platform == "win32":
        os.rename(source, destination)
    else:
        os.link(source, destination)
        os.unlink(source)


@contextmanager
def atomic_output_path(destination: str, *, allow_empty: bool = False) -> Iterator[str]:
    """Пишет во временный файл и публикует результат только при полном успехе.

    Вызывающий код должен проверить корректность созданного файла перед выходом
    из блока. Если конечный путь уже занят, публикация завершается ошибкой.
    При ошибке временный файл удаляется, старый результат не меняется.
    """
    folder = os.path.dirname(os.path.abspath(destination))
    suffix = os.path.splitext(destination)[1]
    handle, temporary = tempfile.mkstemp(
        prefix=".__multifora_", suffix=suffix, dir=folder
    )
    os.close(handle)
    try:
        yield temporary
        if not os.path.isfile(temporary) or (not allow_empty and os.path.getsize(temporary) == 0):
            raise OSError("Операция не создала корректный выходной файл")
        publish_new_file(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def get_unique_path(path: str) -> str:
    """Подбирает незанятый путь с числовым суффиксом, не резервируя его."""
    if not os.path.exists(path):
        return path

    base, extension = os.path.splitext(path)
    counter = 1
    candidate = path
    while os.path.exists(candidate):
        candidate = f"{base}_{counter}{extension}"
        counter += 1
    return candidate
