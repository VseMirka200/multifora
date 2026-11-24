"""Диалог прогресса файловой операции."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout

from app.ui.ui_components import setup_standard_dialog, setup_standard_secondary_button
from app.ui.ui_styles import DIALOG_MARGINS, PROGRESS_HEIGHT, SPACE_LG

_DEFAULT_STATUS = "Выполняется операция..."


class OperationProgressDialog(QDialog):
    """Показывает статус, прогресс и запрос на отмену операции."""

    cancel_requested = Signal()

    def __init__(self, parent, theme_mode: str):
        super().__init__(parent)
        self._effective_theme_mode = theme_mode
        self.setObjectName("progress_dialog")
        setup_standard_dialog(self, title="Выполнение операции", fixed_width=self._width_for_screen())
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_LG)

        self.status_label = QLabel(_DEFAULT_STATUS)
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_scroll = QScrollArea(self)
        self.status_scroll.setObjectName("progressStatusScroll")
        self.status_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.status_scroll.setWidgetResizable(True)
        self.status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.status_scroll.setWidget(self.status_label)
        layout.addWidget(self.status_scroll)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(PROGRESS_HEIGHT)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("Отмена", self)
        setup_standard_secondary_button(self.cancel_button, expand=True)
        self.cancel_button.clicked.connect(self._request_cancel)
        layout.addWidget(self.cancel_button)

    def _request_cancel(self) -> None:
        if self.cancel_button.isEnabled():
            self.cancel_button.setEnabled(False)
            self.set_status("Отмена операции…")
            self.cancel_requested.emit()

    def reject(self) -> None:
        self._request_cancel()

    def closeEvent(self, event) -> None:
        self._request_cancel()
        event.ignore()

    def _width_for_screen(self) -> int:
        screen = self.parentWidget().screen() if self.parentWidget() else self.screen()
        return min(360, max(240, screen.availableGeometry().width() - 32)) if screen else 360

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        left, _top, right, _bottom = DIALOG_MARGINS
        available_width = max(1, self.width() - left - right)
        required_height = max(
            self.status_label.fontMetrics().height(), self.status_label.heightForWidth(available_width)
        )
        self.status_label.setMinimumHeight(required_height)
        screen = self.screen()
        max_height = max(80, screen.availableGeometry().height() // 3) if screen else 240
        self.status_scroll.setFixedHeight(min(required_height + 2, max_height))
        self.layout().activate()
        self.adjustSize()

    def show_progress(self, status_text: str = _DEFAULT_STATUS, *, indeterminate: bool = False) -> None:
        self.setFixedWidth(self._width_for_screen())
        self.set_status(status_text)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0 if indeterminate else 100)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.show()
        self.raise_()
        self.activateWindow()

    def reset(self) -> None:
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_button.setVisible(False)
        self.cancel_button.setEnabled(True)
        self.hide()
