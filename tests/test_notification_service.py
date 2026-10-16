"""Tests for the explicit warning-suppression notification policy."""

import unittest

from app.services.notifications import NotificationService


class _StatusBar:
    def __init__(self) -> None:
        self.messages = []

    def showMessage(self, message: str) -> None:
        self.messages.append(message)


class _Owner:
    disable_warning_dialogs = True

    def __init__(self) -> None:
        self.status_bar = _StatusBar()
        self.events = []

    def log_event(self, message: str, level: str) -> None:
        self.events.append((message, level))


class NotificationServiceTests(unittest.TestCase):
    def test_suppressed_warning_is_logged_and_shown_in_status_bar(self):
        owner = _Owner()

        NotificationService().warning(owner, "Warning", "Details")

        self.assertEqual(owner.status_bar.messages, ["Details"])
        self.assertEqual(owner.events, [("Warning: Details", "WARN")])


if __name__ == "__main__":
    unittest.main()
