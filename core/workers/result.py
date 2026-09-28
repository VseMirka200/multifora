from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class OperationResult:
    """Результат фоновой файловой операции."""

    new_files: list[object] = field(default_factory=list)
    updated_files: list[object] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Возвращает совместимое со старым API словарное представление."""
        return {
            "new_files": self.new_files,
            "updated_files": self.updated_files,
            "errors": self.errors,
        }

    def get(self, key: str, default: object = None) -> object:
        return self.as_dict().get(key, default)

    def __getitem__(self, key: str) -> object:
        return self.as_dict()[key]

    def __contains__(self, key: object) -> bool:
        return key in self.as_dict()
