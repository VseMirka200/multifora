"""Animated splash screen displayed while the main window is prepared."""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.core.app_identity import APP_DISPLAY_NAME


class StartupSplash(QWidget):
    """A compact, non-blocking startup screen with fade transitions."""

    def __init__(self, icon_path: str | None = None):
        super().__init__(
            None,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(460, 268)
        self.setWindowTitle(APP_DISPLAY_NAME)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._animation = QPropertyAnimation(self._opacity, b"opacity", self)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build_ui(icon_path)

    def _build_ui(self, icon_path: str | None) -> None:
        card = QFrame(self)
        card.setObjectName("startupCard")
        card.setStyleSheet(
            """
            QFrame#startupCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #18263d, stop:0.54 #13213a, stop:1 #0d1728);
                border: 1px solid #3d6ca7;
                border-radius: 18px;
            }
            QLabel#startupTitle { color: #f6f9ff; font-size: 27px; font-weight: 700; }
            QLabel#startupSubtitle { color: #aebfd8; font-size: 14px; }
            QLabel#startupStatus { color: #7eabdf; font-size: 12px; }
            QProgressBar {
                border: 0; background: #0b1424; border-radius: 3px; min-height: 6px;
                max-height: 6px;
            }
            QProgressBar::chunk {
                background: #4f9fff; border-radius: 3px;
            }
            """
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 26)
        card_layout.setSpacing(0)

        heading = QHBoxLayout()
        heading.setSpacing(18)
        icon = QLabel()
        icon.setFixedSize(68, 68)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon.setPixmap(
                    pixmap.scaled(
                        64,
                        64,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel(APP_DISPLAY_NAME)
        title.setObjectName("startupTitle")
        subtitle = QLabel("Инструменты для работы с файлами")
        subtitle.setObjectName("startupSubtitle")
        title_box.addStretch()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addStretch()
        heading.addWidget(icon)
        heading.addLayout(title_box)
        heading.addStretch()

        self._status = QLabel("Подготавливаем рабочее пространство…")
        self._status.setObjectName("startupStatus")
        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(False)

        card_layout.addLayout(heading)
        card_layout.addStretch()
        card_layout.addWidget(self._status)
        card_layout.addSpacing(9)
        card_layout.addWidget(progress)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(card)

    def show_animated(self) -> None:
        screen = self.screen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())
        self.show()
        self._fade_to(1.0, 180)

    def finish(self) -> None:
        """Fade out after the main window has become visible."""
        self._status.setText("Готово")
        self._animation.finished.connect(self._close_when_hidden)
        self._fade_to(0.0, 220)

    def _fade_to(self, opacity: float, duration: int) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._opacity.opacity())
        self._animation.setEndValue(opacity)
        self._animation.setDuration(duration)
        self._animation.start()

    def _close_when_hidden(self) -> None:
        if self._opacity.opacity() == 0.0:
            self.close()
            self.deleteLater()
