"""Typed requests and dispatching primitives for file operations."""

from .dispatcher import (
    CancellationToken,
    OperationContext,
    OperationDispatcher,
    OperationEvent,
)
from .requests import (
    CompressionRequest,
    ConversionRequest,
    MergeRequest,
    OperationRequest,
    RenameRequest,
)

__all__ = [
    "CancellationToken",
    "CompressionRequest",
    "ConversionRequest",
    "MergeRequest",
    "OperationContext",
    "OperationDispatcher",
    "OperationEvent",
    "OperationRequest",
    "RenameRequest",
]
