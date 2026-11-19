"""Метаданные файлов и снимок входных данных операции."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass

from core.file_types import FILE_TYPE_EXTENSIONS


class FileItem:
    """Хранит путь и вычисляемые метаданные файла или папки."""

    def __init__(self, path: str):
        self.path = path
        self.is_file = False
        self.name = ""
        self.folder = ""
        self.size = 0
        self.file_type = "other"
        self._refresh_path_metadata()

    def _refresh_path_metadata(self) -> None:
        try:
            path_stat = os.stat(self.path)
        except OSError:
            path_stat = None
        self.is_file = bool(path_stat and stat.S_ISREG(path_stat.st_mode))
        self.name = os.path.basename(self.path)
        self.folder = os.path.dirname(self.path)
        self.size = path_stat.st_size if self.is_file else 0
        self.file_type = self._detect_file_type()

    def _detect_file_type(self) -> str:
        """Определяет внутренний тип файла по расширению."""
        if not self.is_file:
            return "folder"

        extension = os.path.splitext(self.name)[1].lower()
        for file_type, extensions in FILE_TYPE_EXTENSIONS.items():
            if extension in extensions:
                return file_type
        return "other"

    def update_info(self) -> bool:
        """Повторно считывает метаданные пути, если он ещё существует."""
        if not os.path.exists(self.path):
            return False
        self._refresh_path_metadata()
        return True


@dataclass(frozen=True, slots=True)
class OperationFile:
    """Метаданные исходного пути на момент запуска файловой операции."""

    path: str
    name: str
    folder: str
    is_file: bool
    file_type: str

    @classmethod
    def from_item(cls, item: FileItem) -> OperationFile:
        return cls(item.path, item.name, item.folder, item.is_file, item.file_type)


OperationSource = FileItem | OperationFile


def natural_sort_key(value: object) -> tuple:
    """Строит ключ для естественной сортировки: file2 перед file10."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", str(value))
    )


def file_item_source_folder(file_item: object) -> str:
    """Возвращает исходную папку файла или путь самой папки."""
    path = str(getattr(file_item, "path", ""))
    if not getattr(file_item, "is_file", True):
        return path
    return str(getattr(file_item, "folder", "") or os.path.dirname(path))


def file_item_type_label(file_item: object) -> str:
    """Возвращает отображаемый тип файла или папки."""
    if not getattr(file_item, "is_file", True):
        return "Папка"
    extension = os.path.splitext(str(getattr(file_item, "path", "")))[1]
    return extension[1:].upper() if extension else "Файл"
