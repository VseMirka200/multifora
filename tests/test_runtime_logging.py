import unittest
from unittest.mock import patch

from app.core import runtime_logging


class RuntimeLoggingTests(unittest.TestCase):
    def test_unhandled_exception_includes_traceback_and_source(self):
        try:
            raise RuntimeError("тестовая ошибка")
        except RuntimeError as error:
            with patch.object(runtime_logging, "_debug_log") as debug_log:
                runtime_logging.log_unhandled_exception(
                    type(error), error, error.__traceback__, "тестовый поток"
                )

        message, level = debug_log.call_args.args
        self.assertEqual(level, "ERROR")
        self.assertIn("тестовый поток", message)
        self.assertIn("RuntimeError: тестовая ошибка", message)

    def test_qt_warning_is_saved_with_warning_level(self):
        context = type("Context", (), {"file": "widget.cpp", "line": 12})()
        with patch.object(runtime_logging, "_debug_log") as debug_log:
            runtime_logging._log_qt_message(
                runtime_logging.QtMsgType.QtWarningMsg, context, "warning"
            )

        self.assertEqual(
            debug_log.call_args.args,
            ("Qt: warning (widget.cpp:12)", "WARNING"),
        )

    def test_install_is_idempotent(self):
        original_state = runtime_logging._runtime_logging_installed
        runtime_logging._runtime_logging_installed = False
        try:
            with (
                patch.object(runtime_logging.sys, "excepthook"),
                patch.object(runtime_logging.threading, "excepthook"),
                patch.object(
                    runtime_logging, "qInstallMessageHandler"
                ) as install_handler,
            ):
                runtime_logging.install_runtime_logging()
                runtime_logging.install_runtime_logging()

            install_handler.assert_called_once_with(
                runtime_logging._log_qt_message
            )
        finally:
            runtime_logging._runtime_logging_installed = original_state
