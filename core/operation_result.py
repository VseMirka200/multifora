"""Результаты файловых операций и сведения о проблемах отдельных файлов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NotRequired, TypedDict

from app.core.models import FileItem, OperationSource


class OperationIssue(TypedDict):
    """Сообщение об ошибке или предупреждении с необязательными данными файла."""
    message: str
    path: NotRequired[str | None]
    name: NotRequired[str]


@dataclass(slots=True)
class OperationResult:
    """Новые и изменённые файлы, ошибки и предупреждения фоновой операции."""

    new_files: list[FileItem] = field(default_factory=list)
    updated_files: list[tuple[OperationSource, str]] = field(default_factory=list)
    errors: list[OperationIssue] = field(default_factory=list)
    warnings: list[OperationIssue] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Возвращает совместимое со старым API словарное представление."""
        return {
            "new_files": self.new_files,
            "updated_files": self.updated_files,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def get(self, key: str, default: object = None) -> object:
        return self.as_dict().get(key, default)

    def __getitem__(self, key: str) -> object:
        return self.as_dict()[key]

    def __contains__(self, key: object) -> bool:
        return key in self.as_dict()
