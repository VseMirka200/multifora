from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
)

from app.core.app_utils import _log_ignored_error
from app.ui.ui_spacing import ACTION_BUTTON_HEIGHT
from app.ui.ui_styles import build_standard_button_style

_MESSAGE_BOX_HOOKS_INSTALLED = False
_DIALOG_MIN_WIDTH = 360
_DIALOG_MAX_WIDTH = 560
_ICON_SIZE = 28
_BUTTON_MIN_WIDTH = 84
_BUTTON_HORIZONTAL_PADDING = 20


def _setup_message_box_button(
    button: QPushButton,
    *,
    variant: str = "secondary",
) -> QPushButton:
    button.setFixedHeight(ACTION_BUTTON_HEIGHT)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setProperty("buttonVariant", variant)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    theme = getattr(button.parent(), "_effective_theme_mode", "dark")
    button.setStyleSheet(build_standard_button_style(theme, variant))
    try:
        button.ensurePolished()
        button.style().unpolish(button)
        button.style().polish(button)
        button.updateGeometry()
    except Exception as error:
        _log_ignored_error("_setup_message_box_button", error)
    text_width = QFontMetrics(button.font()).horizontalAdvance(button.text())
    button.setMinimumWidth(
        max(
            _BUTTON_MIN_WIDTH,
            button.sizeHint().width(),
            text_width + _BUTTON_HORIZONTAL_PADDING,
        )
    )
    return button


def _resolve_message_box_icon(widget, icon: QMessageBox.Icon):
    style = widget.style()
    icon_map = {
        QMessageBox.Icon.Information: QStyle.StandardPixmap.SP_MessageBoxInformation,
        QMessageBox.Icon.Warning: QStyle.StandardPixmap.SP_MessageBoxWarning,
        QMessageBox.Icon.Critical: QStyle.StandardPixmap.SP_MessageBoxCritical,
        QMessageBox.Icon.Question: QStyle.StandardPixmap.SP_MessageBoxQuestion,
    }
    standard_icon = icon_map.get(icon)
    if standard_icon is None:
        return None
    try:
        return style.standardIcon(standard_icon)
    except Exception:
        return None


def show_app_choice(
    parent,
    title: str,
    text: str,
    choices: Iterable[tuple[str, str, str]],
    *,
    icon: QMessageBox.Icon = QMessageBox.Icon.Question,
    default_key: str | None = None,
    cancel_key: str | None = None,
    extra_widget=None,
) -> str | None:
    """Показывает единый диалог приложения и возвращает ключ выбранной кнопки."""
    choices = tuple(choices)
    dialog = QDialog(parent)
    dialog.setObjectName("appMessageDialog")
    dialog.setWindowTitle(str(title))
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    try:
        dialog._effective_theme_mode = getattr(parent, "_effective_theme_mode", "dark")
        dialog.setStyleSheet(parent.styleSheet())
    except Exception as error:
        _log_ignored_error("show_app_choice", error)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(10)

    content_row = QHBoxLayout()
    content_row.setObjectName("appMessageContentRow")
    content_row.setContentsMargins(0, 0, 0, 0)
    content_row.setSpacing(10)

    icon_label = QLabel()
    icon_label.setObjectName("appMessageIcon")
    icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    icon_label.setFixedWidth(_ICON_SIZE)
    icon_label.setMinimumHeight(_ICON_SIZE)
    icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    resolved_icon = _resolve_message_box_icon(dialog, icon)
    if resolved_icon is not None:
        icon_label.setPixmap(resolved_icon.pixmap(_ICON_SIZE, _ICON_SIZE))
    content_row.addWidget(icon_label)

    text_label = QLabel(str(text))
    text_label.setObjectName("appMessageText")
    text_label.setWordWrap(True)
    text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    text_label.setMinimumHeight(36)
    content_row.addWidget(text_label, 1, Qt.AlignmentFlag.AlignVCenter)
    layout.addLayout(content_row)

    if extra_widget is not None:
        extra_row = QHBoxLayout()
        extra_row.setObjectName("appMessageExtraRow")
        extra_row.setContentsMargins(0, 0, 0, 0)
        extra_row.setSpacing(0)
        extra_row.addSpacing(_ICON_SIZE + content_row.spacing())
        extra_row.addWidget(extra_widget, 1)
        layout.addLayout(extra_row)

    button_row = QHBoxLayout()
    button_row.setContentsMargins(0, 0, 0, 0)
    button_row.setSpacing(8)
    selected = {"key": None}
    buttons: list[QPushButton] = []

    def select(key: str) -> None:
        selected["key"] = key
        dialog.accept()

    for key, label, variant in choices:
        button = QPushButton(label, dialog)
        button.setObjectName(f"appMessageButton_{key}")
        effective_variant = "danger" if key == cancel_key or key in {"cancel", "no"} else variant
        button = _setup_message_box_button(button, variant=effective_variant)
        button.clicked.connect(lambda _checked=False, choice_key=key: select(choice_key))
        if key == default_key:
            button.setDefault(True)
            button.setFocus()
        button_row.addWidget(button, 1)
        buttons.append(button)

    choice_keys = {str(key) for key, _label, _variant in choices}
    if {"yes", "no"}.issubset(choice_keys):
        dialog._confirmation_shortcuts = []
        for key, selected_key in (
            (Qt.Key.Key_Return, "yes"),
            (Qt.Key.Key_Enter, "yes"),
            (Qt.Key.Key_Delete, "no"),
        ):
            shortcut = QShortcut(QKeySequence(key), dialog)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda choice_key=selected_key: select(choice_key))
            dialog._confirmation_shortcuts.append(shortcut)

    layout.addLayout(button_row)

    metrics = QFontMetrics(text_label.font())
    longest_line = max(
        (metrics.horizontalAdvance(line) for line in str(text).splitlines()), default=0
    )
    content_width = max(_DIALOG_MIN_WIDTH, min(_DIALOG_MAX_WIDTH, longest_line + 90))
    text_label.setMaximumWidth(max(240, content_width - 76))
    buttons_width = (
        sum(button.minimumWidth() for button in buttons) + max(0, len(buttons) - 1) * 8 + 24
    )
    dialog_width = max(content_width, buttons_width)
    dialog.setMinimumWidth(dialog_width)
    dialog.setMaximumWidth(dialog_width)
    dialog.resize(dialog_width, dialog.sizeHint().height())

    dialog.exec()
    return selected["key"] if selected["key"] is not None else cancel_key


def show_app_confirmation(
    parent,
    title: str,
    text: str,
    *,
    icon: QMessageBox.Icon = QMessageBox.Icon.Question,
    default_no: bool = True,
    yes_text: str = "Да",
    no_text: str = "Нет",
    destructive: bool = False,
) -> bool:
    result = show_app_choice(
        parent,
        title,
        text,
        (
            ("yes", yes_text, "danger" if destructive else "secondary"),
            ("no", no_text, "secondary"),
        ),
        icon=icon,
        default_key="no" if default_no else "yes",
        cancel_key="no",
    )
    return result == "yes"


def show_app_confirmation_with_checkbox(
    parent,
    title: str,
    text: str,
    checkbox_text: str,
    *,
    icon: QMessageBox.Icon = QMessageBox.Icon.Warning,
    default_no: bool = True,
    checkbox_checked: bool = False,
    yes_text: str = "Удалить",
    no_text: str = "Отмена",
    destructive: bool = True,
) -> tuple[bool, bool]:
    """Показывает подтверждение с дополнительным безопасно выключенным флажком."""
    checkbox = QCheckBox(str(checkbox_text), parent)
    checkbox.setObjectName("appMessageCheckbox")
    checkbox.setChecked(bool(checkbox_checked))
    checked_state = {"value": checkbox.isChecked()}
    checkbox.toggled.connect(lambda checked: checked_state.update(value=bool(checked)))
    result = show_app_choice(
        parent,
        title,
        text,
        (
            ("yes", yes_text, "danger" if destructive else "secondary"),
            ("no", no_text, "secondary"),
        ),
        icon=icon,
        default_key="no" if default_no else "yes",
        cancel_key="no",
        extra_widget=checkbox,
    )
    return result == "yes", checked_state["value"]


def _show_localized_message_box(
    parent, title, text, icon, default_button=QMessageBox.StandardButton.Ok
):
    """Показывает локализованное модальное сообщение приложения."""
    show_app_choice(
        parent,
        str(title),
        str(text),
        (("ok", "Хорошо", "secondary"),),
        icon=icon,
        default_key="ok",
        cancel_key="ok",
    )
    return QMessageBox.StandardButton.Ok


def install_warning_suppression_hook():
    global _MESSAGE_BOX_HOOKS_INSTALLED
    if _MESSAGE_BOX_HOOKS_INSTALLED:
        return

    def _warning_owner(parent):
        current = parent
        visited = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            if hasattr(current, "disable_warning_dialogs"):
                return current
            parent_getter = getattr(current, "parentWidget", None)
            current = parent_getter() if callable(parent_getter) else None
        return parent

    def _warning(parent, title, text, *args, **kwargs):
        owner = _warning_owner(parent)
        if owner is not None and bool(getattr(owner, "disable_warning_dialogs", False)):
            status_bar = getattr(owner, "status_bar", None)
            if status_bar is not None and callable(getattr(status_bar, "showMessage", None)):
                try:
                    status_bar.showMessage(str(text))
                except Exception as error:
                    _log_ignored_error("_warning", error)
            if callable(getattr(owner, "log_event", None)):
                try:
                    owner.log_event(f"{title}: {text}", "WARN")
                except Exception as error:
                    _log_ignored_error("_warning", error)
            return QMessageBox.StandardButton.Ok
        return _show_localized_message_box(parent, title, text, QMessageBox.Icon.Warning)

    def _information(parent, title, text, *args, **kwargs):
        return _show_localized_message_box(parent, title, text, QMessageBox.Icon.Information)

    def _critical(parent, title, text, *args, **kwargs):
        return _show_localized_message_box(parent, title, text, QMessageBox.Icon.Critical)

    def _question(parent, title, text, *args, **kwargs):
        default_button = kwargs.get("defaultButton", QMessageBox.StandardButton.No)
        if len(args) >= 2:
            default_button = args[1]
        accepted = show_app_confirmation(
            parent,
            str(title),
            str(text),
            default_no=default_button != QMessageBox.StandardButton.Yes,
        )
        return QMessageBox.StandardButton.Yes if accepted else QMessageBox.StandardButton.No

    QMessageBox.warning = staticmethod(_warning)
    QMessageBox.information = staticmethod(_information)
    QMessageBox.critical = staticmethod(_critical)
    QMessageBox.question = staticmethod(_question)
    _MESSAGE_BOX_HOOKS_INSTALLED = True
