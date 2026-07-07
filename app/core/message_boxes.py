from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QStyle, QVBoxLayout

from app.ui.ui_components import setup_standard_secondary_button


_MESSAGE_BOX_HOOKS_INSTALLED = False
_DIALOG_MIN_WIDTH = 420
_DIALOG_MAX_WIDTH = 560
_ICON_SIZE = 32
_ICON_SLOT_SIZE = 40
_BUTTON_MIN_WIDTH = 84


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


def tune_message_box_layout(msg_box: QMessageBox, icon: QMessageBox.Icon):
    """Приводит layout системного QMessageBox к единому виду (иконка + текст)."""
    resolved_icon = _resolve_message_box_icon(msg_box, icon)
    if resolved_icon is not None:
        msg_box.setIconPixmap(resolved_icon.pixmap(_ICON_SIZE, _ICON_SIZE))

    for label in msg_box.findChildren(QLabel):
        try:
            if label.pixmap() is not None:
                label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                label.setFixedSize(_ICON_SLOT_SIZE, _ICON_SLOT_SIZE)
                continue
        except Exception:
            pass
        if label.text():
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setWordWrap(True)
            label.setMinimumHeight(36)


def _show_localized_message_box(parent, title, text, icon, default_button=QMessageBox.StandardButton.Ok):
    """Показывает локализованное модальное сообщение приложения."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(str(title))
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    try:
        dialog._effective_theme_mode = getattr(parent, "_effective_theme_mode", "dark")
        dialog.setStyleSheet(parent.styleSheet())
    except Exception:
        pass

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(12)

    content_row = QHBoxLayout()
    content_row.setContentsMargins(0, 0, 0, 0)
    content_row.setSpacing(10)

    icon_label = QLabel()
    icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    icon_label.setFixedSize(_ICON_SIZE, _ICON_SIZE)
    resolved_icon = _resolve_message_box_icon(dialog, icon)
    if resolved_icon is not None:
        icon_label.setPixmap(resolved_icon.pixmap(_ICON_SIZE, _ICON_SIZE))
    content_row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

    text_label = QLabel(str(text))
    text_label.setWordWrap(True)
    text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    text_label.setMinimumHeight(36)
    content_row.addWidget(text_label, 1, Qt.AlignmentFlag.AlignVCenter)
    layout.addLayout(content_row)

    button_row = QHBoxLayout()
    button_row.setContentsMargins(0, 0, 0, 0)
    button_row.setSpacing(8)
    button_row.addStretch()

    ok_button = QPushButton("Хорошо")
    setup_standard_secondary_button(ok_button, height=22)
    ok_button.setSizePolicy(ok_button.sizePolicy().Policy.Fixed, ok_button.sizePolicy().Policy.Fixed)
    try:
        ok_button.style().unpolish(ok_button)
        ok_button.style().polish(ok_button)
        ok_button.updateGeometry()
    except Exception:
        pass
    ok_button.setFixedWidth(max(_BUTTON_MIN_WIDTH, ok_button.sizeHint().width()))
    button_row.addWidget(ok_button)
    layout.addLayout(button_row)

    ok_button.clicked.connect(dialog.accept)

    metrics = QFontMetrics(text_label.font())
    width = max(_DIALOG_MIN_WIDTH, min(_DIALOG_MAX_WIDTH, metrics.horizontalAdvance(str(text)) + 150))
    dialog.setMinimumWidth(width)
    dialog.resize(max(width, dialog.sizeHint().width()), dialog.sizeHint().height())
    dialog.exec()
    return QMessageBox.StandardButton.Ok


def install_warning_suppression_hook():
    global _MESSAGE_BOX_HOOKS_INSTALLED
    if _MESSAGE_BOX_HOOKS_INSTALLED:
        return

    def _warning(parent, title, text, *args, **kwargs):
        if parent is not None and bool(getattr(parent, "disable_warning_dialogs", False)):
            status_bar = getattr(parent, "status_bar", None)
            if status_bar is not None and callable(getattr(status_bar, "showMessage", None)):
                try:
                    status_bar.showMessage(str(text))
                except Exception:
                    pass
            if callable(getattr(parent, "log_event", None)):
                try:
                    parent.log_event(f"{title}: {text}", "WARN")
                except Exception:
                    pass
            return QMessageBox.StandardButton.Ok
        return _show_localized_message_box(parent, title, text, QMessageBox.Icon.Warning)

    def _information(parent, title, text, *args, **kwargs):
        return _show_localized_message_box(parent, title, text, QMessageBox.Icon.Information)

    def _critical(parent, title, text, *args, **kwargs):
        return _show_localized_message_box(parent, title, text, QMessageBox.Icon.Critical)

    QMessageBox.warning = staticmethod(_warning)
    QMessageBox.information = staticmethod(_information)
    QMessageBox.critical = staticmethod(_critical)
    _MESSAGE_BOX_HOOKS_INSTALLED = True
