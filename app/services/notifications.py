"""Explicit application notification API for UI scenarios."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from app.core.message_boxes import (
    show_app_choice,
    show_app_confirmation,
    show_app_confirmation_with_checkbox,
)


class NotificationService:
    """Display dialogs without mutating ``QMessageBox`` globally."""

    def information(self, parent, title: str, text: str) -> None:
        self._show(parent, title, text, QMessageBox.Icon.Information)

    def warning(self, parent, title: str, text: str) -> None:
        owner = self._warning_owner(parent)
        if bool(getattr(owner, "disable_warning_dialogs", False)):
            self._report_suppressed_warning(owner, title, text)
            return
        self._show(parent, title, text, QMessageBox.Icon.Warning)

    def error(self, parent, title: str, text: str) -> None:
        self._show(parent, title, text, QMessageBox.Icon.Critical)

    def confirm(
        self, parent, title: str, text: str, *, default_no: bool = True
    ) -> bool:
        return show_app_confirmation(
            parent, title, text, default_no=default_no
        )

    def confirm_with_checkbox(
        self,
        parent,
        title: str,
        text: str,
        checkbox_text: str,
        *,
        default_no: bool = True,
        checkbox_checked: bool = False,
    ) -> tuple[bool, bool]:
        return show_app_confirmation_with_checkbox(
            parent,
            title,
            text,
            checkbox_text,
            default_no=default_no,
            checkbox_checked=checkbox_checked,
        )

    @staticmethod
    def _show(parent, title: str, text: str, icon: QMessageBox.Icon) -> None:
        show_app_choice(
            parent,
            title,
            text,
            (("ok", "Хорошо", "secondary"),),
            icon=icon,
            default_key="ok",
            cancel_key="ok",
        )

    @staticmethod
    def _warning_owner(parent):
        current = parent
        visited = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            if hasattr(current, "disable_warning_dialogs"):
                return current
            parent_widget = getattr(current, "parentWidget", None)
            current = parent_widget() if callable(parent_widget) else None
        return parent

    @staticmethod
    def _report_suppressed_warning(owner, title: str, text: str) -> None:
        status_bar = getattr(owner, "status_bar", None)
        show_message = getattr(status_bar, "showMessage", None)
        if callable(show_message):
            show_message(text)
        log_event = getattr(owner, "log_event", None)
        if callable(log_event):
            log_event(f"{title}: {text}", "WARN")
