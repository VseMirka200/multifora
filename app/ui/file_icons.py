"""Иконки списка файлов: точное расширение, затем нейтральный значок."""

from functools import lru_cache
import os

from PyQt6.QtGui import QIcon

from app.core.app_icons import _find_bundled_icon

FILE_ICON_SIZE = 28


@lru_cache(maxsize=256)
def _extension_icon(extension: str, is_file: bool) -> QIcon:
    if not is_file:
        return QIcon(_find_bundled_icon("folder.ico") or "")
    # Не используем тип документа или будущий формат из предпросмотра:
    # например, DOCX не должен получать значок с надписью DOC или PDF.
    if extension and extension[1:].isascii() and extension[1:].isalnum():
        for suffix in ("svg", "ico", "png"):
            path = _find_bundled_icon(f"files extension/{extension[1:]}.{suffix}")
            if path:
                return QIcon(path)
    return QIcon(_find_bundled_icon("files extension/_unknown.svg") or "")


def file_icon(file_item) -> QIcon:
    extension = os.path.splitext(file_item.path)[1].lower() if file_item.is_file else ""
    return _extension_icon(extension, file_item.is_file)
