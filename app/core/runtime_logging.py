"""Last-resort logging for failures outside normal application handlers."""

import sys
import threading
import traceback

from PyQt6.QtCore import QtMsgType, qInstallMessageHandler

from app.core.app_utils import _debug_log

_runtime_logging_installed = False


def log_unhandled_exception(exc_type, exc_value, exc_traceback, source: str) -> None:
    details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)).strip()
    _debug_log(f"Необработанная ошибка ({source}):\n{details}", "ERROR")


def _log_qt_message(message_type, context, message: str) -> None:
    levels = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "ERROR",
    }
    location = ""
    file_name = getattr(context, "file", None)
    line_number = getattr(context, "line", None)
    if file_name:
        location = f" ({file_name}:{line_number})"
    _debug_log(f"Qt: {message}{location}", levels.get(message_type, "DEBUG"))


def install_runtime_logging() -> None:
    """Capture uncaught Python/thread exceptions and Qt diagnostics in the main log."""
    global _runtime_logging_installed
    if _runtime_logging_installed:
        return

    previous_excepthook = sys.excepthook

    def excepthook(exc_type, exc_value, exc_traceback):
        log_unhandled_exception(exc_type, exc_value, exc_traceback, "главный поток")
        previous_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = excepthook

    if hasattr(threading, "excepthook"):
        previous_threading_excepthook = threading.excepthook

        def threading_excepthook(args):
            log_unhandled_exception(
                args.exc_type,
                args.exc_value,
                args.exc_traceback,
                f"поток {args.thread.name}",
            )
            previous_threading_excepthook(args)

        threading.excepthook = threading_excepthook

    qInstallMessageHandler(_log_qt_message)
    _runtime_logging_installed = True
