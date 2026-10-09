"""Безопасное создание выходного файла рядом с конечным расположением."""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def atomic_output_path(destination: str) -> Iterator[str]:
    """Пишет во временный файл и публикует результат только при полном успехе.

    Вызывающий код должен проверить корректность созданного файла перед выходом
    из блока. При ошибке временный файл удаляется, старый результат не меняется.
    """
    folder = os.path.dirname(os.path.abspath(destination))
    suffix = os.path.splitext(destination)[1]
    handle, temporary = tempfile.mkstemp(prefix=".__multifora_", suffix=suffix, dir=folder)
    os.close(handle)
    try:
        yield temporary
        if not os.path.isfile(temporary) or os.path.getsize(temporary) == 0:
            raise OSError("Операция не создала корректный выходной файл")
        if os.path.exists(destination):
            raise FileExistsError(f"Выходной файл уже существует: {destination}")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
