"""Adapter that configures the legacy worker from immutable requests."""

from __future__ import annotations

from app.core.models import FileItem
from core.workers.file_worker import FileWorker

from .requests import (
    CompressionRequest,
    ConversionRequest,
    MergeRequest,
    OperationRequest,
    RenameRequest,
)


def configure_file_worker(
    worker: FileWorker,
    request: OperationRequest,
) -> None:
    """Configure a worker once from a typed operation request."""
    files = [FileItem(path) for path in request.file_paths]
    if isinstance(request, RenameRequest):
        worker.set_rename(
            files, list(request.new_names), strict=request.strict
        )
    elif isinstance(request, ConversionRequest):
        worker.set_conversion(
            files,
            request.conversion_type,
            request.conversion_format,
            request.output_dir,
            request.output_mode,
        )
    elif isinstance(request, CompressionRequest):
        worker.set_compression(
            files,
            request.compression_level,
            request.compression_type,
            request.pdf_method,
            request.replace_pdf,
            request.image_output_mode,
            request.image_output_dir,
        )
    elif isinstance(request, MergeRequest):
        worker.set_merge(files, request.output_format, request.output_path)
    else:
        raise TypeError(f"Unsupported operation request: {type(request)!r}")
