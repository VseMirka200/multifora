from __future__ import annotations

import os

from PySide6.QtCore import QThread, Signal

from app.core.conversion_formats import KNOWN_FILE_EXTENSIONS
from app.core.models import FileItem, normalized_path_key


class FileMetadataWorker(QThread):
    """Build FileItem metadata outside the UI thread, preserving input order."""

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
                batch.append(FileItem(path))
            except Exception as error:
                self.errors.append((path, str(error)))
                continue
            if len(batch) >= self._batch_size:
                self.batch_ready.emit(batch)
                batch = []
        if batch and not self.isInterruptionRequested():
            self.batch_ready.emit(batch)


class FolderMetadataWorker(FileMetadataWorker):
    """Expand selected folders and build metadata without blocking the UI."""

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
                continue
            seen.add(path_key)
            extension = os.path.splitext(str(path or ""))[1].lower()
            if extension not in KNOWN_FILE_EXTENSIONS:
                self.unsupported_paths.append(str(path))
                continue
            try:
                batch.append(FileItem(path))
            except Exception as error:
                self.errors.append((path, str(error)))
                continue
            if len(batch) >= self._batch_size:
                self.batch_ready.emit(batch)
                batch = []
        if batch and not self.isInterruptionRequested():
            self.batch_ready.emit(batch)
