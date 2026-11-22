"""Параметры файловых операций, выбранные до запуска рабочего потока."""

from dataclasses import dataclass, replace
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class RenameRequest:
    """Пары исходных путей и новых имён для пакетного переименования."""
    kind: ClassVar[str] = "rename"
    pairs: tuple[tuple[str, str], ...]
    strict: bool = False

    def for_retry(self, paths: list[str]) -> "RenameRequest":
        """Сохраняет параметры запроса и оставляет только известные пути для повтора."""
        names = dict(self.pairs)
        return replace(self, pairs=tuple((path, names[path]) for path in paths if path in names))


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    """Формат и расположение результатов конвертации."""
    kind: ClassVar[str] = "convert"
    conversion_type: str
    target_format: str
    output_mode: str
    output_dir: str
    sample: bool = False

    @property
    def worker_kind(self) -> str:
        """Выбирает обработчик изображений или документов по типу конвертации."""
        return "convert_image" if self.conversion_type == "auto_image" else "convert_document"


@dataclass(frozen=True, slots=True)
class CompressionRequest:
    """Параметры сжатия PDF и изображений и размещения результата."""
    kind: ClassVar[str] = "compress"
    level: int
    compression_type: str
    pdf_method: str
    replace_pdf: bool
    image_output_mode: str
    image_output_dir: str


@dataclass(frozen=True, slots=True)
class MergeRequest:
    """Формат и путь единого результата объединения документов."""
    kind: ClassVar[str] = "merge"
    output_format: str
    output_path: str
    page_order: tuple[tuple[int, int], ...] = ()


OperationRequest = RenameRequest | ConversionRequest | CompressionRequest | MergeRequest
