"""Framework-neutral dispatcher for typed file-operation requests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import Literal, TypeAlias

from core.workers.result import OperationResult

from .requests import OperationRequest

OperationEventKind: TypeAlias = Literal["progress", "status", "error"]
OperationEventListener: TypeAlias = Callable[["OperationEvent"], None]


@dataclass(frozen=True, slots=True)
class OperationEvent:
    """A notification emitted while an operation is being dispatched."""

    kind: OperationEventKind
    value: int | str


class CancellationToken:
    """Thread-safe cancellation signal shared by a caller and its handler."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        """Request cancellation without interrupting the handler forcibly."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested."""
        return self._event.is_set()


class OperationContext:
    """Cancellation and event publishing interface supplied to a handler."""

    def __init__(
        self,
        cancellation: CancellationToken,
        event_listener: OperationEventListener | None = None,
    ) -> None:
        self._cancellation = cancellation
        self._event_listener = event_listener

    @property
    def is_cancelled(self) -> bool:
        """Return whether the caller has requested cancellation."""
        return self._cancellation.is_cancelled

    def report_progress(self, value: int) -> None:
        """Publish a normalized percentage progress update."""
        self._publish(OperationEvent("progress", max(0, min(100, int(value)))))

    def report_status(self, value: str) -> None:
        """Publish a user-visible operation status message."""
        self._publish(OperationEvent("status", str(value)))

    def report_error(self, value: str) -> None:
        """Publish a non-fatal operation error message."""
        self._publish(OperationEvent("error", str(value)))

    def _publish(self, event: OperationEvent) -> None:
        if self._event_listener is not None:
            self._event_listener(event)


OperationHandler: TypeAlias = Callable[
    [OperationRequest, OperationContext], OperationResult
]


class OperationDispatcher:
    """Dispatches requests to registered handlers without UI or Qt coupling."""

    def __init__(self) -> None:
        self._handlers: dict[type[object], OperationHandler] = {}

    def register(
        self,
        request_type: type[OperationRequest],
        handler: OperationHandler,
    ) -> None:
        """Register the single handler for an operation request type."""
        if request_type in self._handlers:
            raise ValueError(
                f"Handler already registered for {request_type.__name__}"
            )
        self._handlers[request_type] = handler

    def dispatch(
        self,
        request: OperationRequest,
        *,
        cancellation: CancellationToken | None = None,
        event_listener: OperationEventListener | None = None,
    ) -> OperationResult:
        """Run the matching handler and return failures in the result."""
        handler = self._handlers.get(type(request))
        if handler is None:
            message = f"No handler registered for {type(request).__name__}."
            if event_listener is not None:
                event_listener(OperationEvent("error", message))
            return OperationResult(errors=[{"message": message}])

        context = OperationContext(
            cancellation or CancellationToken(), event_listener
        )
        try:
            return handler(request, context)
        except Exception as error:
            message = str(error) or type(error).__name__
            context.report_error(message)
            return OperationResult(errors=[{"message": message}])
