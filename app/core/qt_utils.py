"""Shared QObject helpers without dependencies on UI widgets."""

from contextlib import contextmanager


@contextmanager
def signals_blocked(widget):
    if widget is None or not hasattr(widget, "blockSignals"):
        yield
        return
    previous = widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(previous)
