from __future__ import annotations

import os

from PySide6.QtCore import QThread, Signal

from core.file_models import FileItem
from core.file_types import KNOWN_FILE_EXTENSIONS
from core.filesystem import normalized_path_key


class FileMetadataWorker(QThread):
    """Собирает данные FileItem вне потока интерфейса, сохраняя порядок."""

    batch_ready = Signal(list)

    def __init__(self, paths: list[str], batch_size: int = 256, parent=None):
        super().__init__(parent)
        self._paths = list(paths)
        self._batch_size = max(1, int(batch_size))
        self.errors: list[tuple[str, str]] = []

    def run(self) -> None:
        batch = []
        for path in self._paths:
            if self.isInterruptionRequested():
                break
            try:
                item = FileItem(path)
                if not item.is_file and not os.path.isdir(path):
                    raise FileNotFoundError(path)
                batch.append(item)
            except Exception as error:
                self.errors.append((path, str(error)))
                continue
            if len(batch) >= self._batch_size:
                self.batch_ready.emit(batch)
                batch = []
        if batch and not self.isInterruptionRequested():
            self.batch_ready.emit(batch)


class FolderMetadataWorker(FileMetadataWorker):
    """Раскрывает выбранные папки и собирает данные без блокировки интерфейса."""

    def __init__(
        self,
        entries: list[tuple[str, bool]],
        existing_paths: set[str],
        batch_size: int = 256,
        parent=None,
    ):
        super().__init__([], batch_size=batch_size, parent=parent)
        self._entries = list(entries)
        self._existing_paths = set(existing_paths)
        self.unsupported_paths: list[str] = []
        self.duplicates = 0

    def _expanded_paths(self):
        for path, is_directory in self._entries:
            if self.isInterruptionRequested():
                return
            if not is_directory:
                yield path
                continue
            for root, _, files in os.walk(path):
                if self.isInterruptionRequested():
                    return
                for name in files:
                    yield os.path.join(root, name)

    def run(self) -> None:
        batch = []
        seen = set(self._existing_paths)
        for path in self._expanded_paths():
            if self.isInterruptionRequested():
                break
            path_key = normalized_path_key(path)
            if path_key in seen:
                self.duplicates += 1
                continue
            seen.add(path_key)
            extension = os.path.splitext(str(path or ""))[1].lower()
            if extension not in KNOWN_FILE_EXTENSIONS:
                self.unsupported_paths.append(str(path))
                continue
            try:
                item = FileItem(path)
                if not item.is_file:
                    raise FileNotFoundError(path)
                batch.append(item)
            except Exception as error:
                self.errors.append((path, str(error)))
                continue
            if len(batch) >= self._batch_size:
                self.batch_ready.emit(batch)
                batch = []
        if batch and not self.isInterruptionRequested():
            self.batch_ready.emit(batch)
