"""Immutable descriptions of file operations independent from Qt widgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class RenameRequest:
    """Rename each source path to the corresponding requested file name."""

    file_paths: tuple[str, ...]
    new_names: tuple[str, ...]
    strict: bool = False

    def __post_init__(self) -> None:
        if len(self.file_paths) != len(self.new_names):
            raise ValueError("Each rename source must have a target name.")


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    """Convert source files to a requested target representation."""

    file_paths: tuple[str, ...]
    conversion_type: str
    conversion_format: str = ""
    output_mode: str = "source_subfolder"
    output_dir: str = ""

    def __post_init__(self) -> None:
        if self.output_mode not in {"alongside", "source_subfolder", "custom"}:
            raise ValueError(
                f"Unsupported conversion output mode: {self.output_mode}"
            )
        if self.output_mode == "custom" and not self.output_dir:
            raise ValueError(
                "A custom conversion output mode requires an output directory."
            )


@dataclass(frozen=True, slots=True)
class CompressionRequest:
    """Compress image or PDF source files."""

    file_paths: tuple[str, ...]
    compression_level: int
    compression_type: str = "image"
    pdf_method: str = "auto"
    replace_pdf: bool = False
    image_output_mode: str = "alongside"
    image_output_dir: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.compression_level <= 100:
            raise ValueError("Compression level must be between 0 and 100.")
        if self.compression_type not in {"image", "pdf"}:
            raise ValueError(
                f"Unsupported compression type: {self.compression_type}"
            )
        if self.image_output_mode not in {"replace", "alongside", "custom"}:
            raise ValueError(
                "Unsupported image compression output mode: "
                f"{self.image_output_mode}"
            )
        if self.image_output_mode == "custom" and not self.image_output_dir:
            raise ValueError(
                "A custom image output mode requires an output directory."
            )


@dataclass(frozen=True, slots=True)
class MergeRequest:
    """Merge source files into one output document."""

    file_paths: tuple[str, ...]
    output_format: str = "pdf"
    output_path: str = ""

    def __post_init__(self) -> None:
        if self.output_format not in {"pdf", "docx"}:
            raise ValueError(
                f"Unsupported merge output format: {self.output_format}"
            )


OperationRequest: TypeAlias = (
    RenameRequest | ConversionRequest | CompressionRequest | MergeRequest
)
