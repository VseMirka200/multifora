import unittest
from unittest.mock import mock_open, patch

from app.ui.mixins.logging_mixin import LoggingMixin


class _LoggingHarness(LoggingMixin):
    def __init__(self):
        self._log_file_path = "/logs/multifora_logs.txt"
        self._log_lines = []
        self.max_log_lines = 1


class LoggingMixinTests(unittest.TestCase):
    def test_action_log_limit_does_not_rewrite_shared_log_file(self):
        logger = _LoggingHarness()
        writer = mock_open()

        with patch("builtins.open", writer):
            logger.log_event("first")
            logger.log_event("second")

        self.assertEqual(logger._log_lines[-1].endswith("second"), True)
        self.assertEqual(len(logger._log_lines), 1)
        self.assertEqual(
            [call.args[1] for call in writer.call_args_list],
            ["a", "a"],
        )


if __name__ == "__main__":
    unittest.main()
