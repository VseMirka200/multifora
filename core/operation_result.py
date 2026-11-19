"""Результаты файловых операций и сведения о проблемах отдельных файлов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NotRequired, TypedDict

from core.file_models import FileItem, OperationSource


class OperationIssue(TypedDict):
    """Сообщение об ошибке или предупреждении с необязательными данными файла."""
    message: str
    path: NotRequired[str | None]
    name: NotRequired[str]
    explanation: NotRequired[str]
    retryable: NotRequired[bool]


@dataclass(frozen=True, slots=True)
class CompressionSize:
    path: str
    before: int
    after: int


@dataclass(slots=True)
class OperationResult:
    """Новые и изменённые файлы, ошибки и предупреждения фоновой операции."""

    new_files: list[FileItem] = field(default_factory=list)
    updated_files: list[tuple[OperationSource, str]] = field(default_factory=list)
    errors: list[OperationIssue] = field(default_factory=list)
    warnings: list[OperationIssue] = field(default_factory=list)
    cancelled: bool = False
    compression_sizes: list[CompressionSize] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        if self.cancelled:
            return "cancelled"
        if self.errors:
            return "partial" if self.new_files or self.updated_files else "failed"
        return "warning" if self.warnings else "success"

    def as_dict(self) -> dict[str, object]:
        """Возвращает совместимое со старым API словарное представление."""
        return {
            "new_files": self.new_files,
            "updated_files": self.updated_files,
            "errors": self.errors,
            "warnings": self.warnings,
            "cancelled": self.cancelled,
            "compression_sizes": self.compression_sizes,
        }

    def get(self, key: str, default: object = None) -> object:
        return self.as_dict().get(key, default)

    def __getitem__(self, key: str) -> object:
        return self.as_dict()[key]

    def __contains__(self, key: object) -> bool:
        return key in self.as_dict()
