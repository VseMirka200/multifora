"""Карточки справки и переключатель настроек."""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.ui.palette import standard_palette
from app.ui.typography import SECTION_PX, TITLE_PX
from app.ui.ui_components import IconButton, resolve_widget_theme_mode, setup_standard_primary_button


class SettingsSwitch(QCheckBox):
    def __init__(self):
        super().__init__()
        self.setFixedSize(50, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        colors = standard_palette(resolve_widget_theme_mode(self))
        track = "accent" if self.isChecked() and self.isEnabled() else "hover_border"
        painter.setBrush(QColor(colors[track]))
        painter.drawRoundedRect(QRectF(2, 2, 46, 22), 11, 11)
        painter.setBrush(QColor(colors["on_accent"]))
        painter.drawEllipse(QRectF(29 if self.isChecked() else 5, 5, 16, 16))
        if self.hasFocus():
            painter.setPen(QPen(QColor(colors["accent"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0.5, 0.5, 49, 25), 12, 12)


class SupportPage(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        content = QWidget()
        self.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        self.icons = {}

        guide = QFrame()
        guide.setObjectName("support_card")
        layout.addWidget(guide)
        guide_row = self._row(guide, "guide", "Руководство",
                              "Как настроить операции и обработать файлы.", featured=True)
        self.guide = IconButton("Открыть руководство")
        setup_standard_primary_button(self.guide, expand=False)
        self.guide.setFixedHeight(36)
        self.guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.guide.setAccessibleName(self.guide.text())
        self.guide.setObjectName("guide_action")
        guide_row.addWidget(self.guide)

        card = QFrame()
        card.setObjectName("support_card")
        rows = QVBoxLayout(card)
        rows.setContentsMargins(1, 1, 1, 1)
        rows.setSpacing(0)
        layout.addWidget(card)
        layout.addStretch()
        self.commands = {}
        for key, title, description in (
            ("updates", "Проверить обновления", "Посмотреть, доступна ли новая версия."),
            ("save", "Журнал операций", "Посмотреть ход операций и сообщения об ошибках."),
            ("bug", "Сообщить об ошибке", "Описать проблему в работе приложения."),
            ("help", "О программе", "Версия и сведения о проекте."),
        ):
            if rows.count():
                line = QFrame()
                line.setObjectName("section_line")
                line.setFixedHeight(1)
                rows.addWidget(line)
            button = QPushButton()
            button.setObjectName("support_action")
            button.setAccessibleName(title)
            button.setAccessibleDescription(description)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            row = self._row(button, key, title, description)
            arrow = QLabel("›")
            arrow.setStyleSheet(f"font-size: {TITLE_PX}px;")
            row.addWidget(arrow)
            for child in button.findChildren(QWidget):
                child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            rows.addWidget(button)
            self.commands[key] = button

    def _row(self, widget, key, title, description, featured=False):
        row = QHBoxLayout(widget)
        row.setContentsMargins(18, 12 if featured else 7, 18, 12 if featured else 7)
        row.setSpacing(20)
        widget.setMinimumHeight(90 if featured else 64)
        icon = QLabel()
        icon.setFixedWidth(54)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icons[key] = icon
        row.addWidget(icon)
        divider = QFrame()
        divider.setObjectName("section_line")
        divider.setFixedSize(1, 48 if featured else 38)
        row.addWidget(divider)
        labels = QVBoxLayout()
        labels.setSpacing(2)
        heading = QLabel(title)
        heading.setStyleSheet(f"font-size: {SECTION_PX}px; font-weight: 600;")
        labels.addWidget(heading)
        hint = QLabel(description)
        hint.setProperty("sectionHint", True)
        hint.setWordWrap(True)
        labels.addWidget(hint)
        row.addLayout(labels, 1)
        return row
