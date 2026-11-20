"""Вкладка ленты с горизонтальными группами команд."""

from PySide6.QtCore import QRect, QSize, Qt, Signal, QEvent
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QStackedWidget, QStyle, QStyleOptionToolButton, QStylePainter, QToolButton,
    QVBoxLayout, QWidget,
)

from app.ui.ui_styles import TAB_BAR_HEIGHT
from app.ui.ui_components import IconButton, setup_standard_dialog, setup_standard_secondary_button


class RibbonNavigation(QWidget):
    currentChanged = Signal(int)
    tabBarDoubleClicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("operations_tab_bar")
        self.group = QButtonGroup(self)
        self.group.idToggled.connect(self._selection_changed)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

    def _selection_changed(self, index, checked):
        if checked:
            self.currentChanged.emit(index)

    def addTab(self, text):
        index = self.count()
        button = QToolButton()
        button.setObjectName("navigation_tab")
        button.setText(text)
        button.setCheckable(True)
        button.setFixedHeight(TAB_BAR_HEIGHT)
        button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.installEventFilter(self)
        self.group.addButton(button, index)
        self.layout().addWidget(button)
        if not index:
            button.setChecked(True)
        return index

    def eventFilter(self, button, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            step = 1 if event.key() == Qt.Key.Key_Right else -1
            target = self.group.button((self.group.id(button) + step) % self.count())
            target.setFocus()
            target.click()
            return True
        if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
            self.tabBarDoubleClicked.emit(self.group.id(button))
            return True
        return super().eventFilter(button, event)

    def count(self):
        return len(self.group.buttons())

    def currentIndex(self):
        return self.group.checkedId()

    def setCurrentIndex(self, index):
        if button := self.group.button(index):
            button.setChecked(True)

    def tabData(self, index):
        return self.group.button(index).property("pageId")

    def setTabData(self, index, value):
        self.group.button(index).setProperty("pageId", value)

    def tabText(self, index):
        return self.group.button(index).text()


class RibbonTile(QToolButton):
    def __init__(self, caption):
        super().__init__()
        self.setText(caption)
        self.setFixedSize(78, 78)
        self.setIconSize(QSize(23, 23))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        option.icon = QIcon()
        option.text = ""
        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        icon_size = self.iconSize()
        font = painter.font()
        if font.pixelSize() > 0:
            font.setPixelSize(max(1, round(font.pixelSize() * 0.75)))
        else:
            font.setPointSizeF(font.pointSizeF() * 0.75)
        painter.setFont(font)
        line_height = painter.fontMetrics().height()
        gap = 5
        top = (self.height() - icon_size.height() - gap - line_height) // 2
        icon_rect = QRect((self.width() - icon_size.width()) // 2, top,
                          icon_size.width(), icon_size.height())
        mode = QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled
        self.icon().paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter, mode)
        text_rect = QRect(0, top + icon_size.height() + gap, self.width(), line_height)
        painter.drawItemText(text_rect, Qt.AlignmentFlag.AlignCenter, option.palette,
                             self.isEnabled(), self.text(), QPalette.ColorRole.ButtonText)


class RibbonStack(QStackedWidget):
    """Рассчитывает высоту ленты по открытой странице и доступной ширине."""

    def heightForWidth(self, width):
        page = self.currentWidget()
        if page is None:
            return 0
        if page.hasHeightForWidth():
            return max(page.minimumSizeHint().height(), page.heightForWidth(width))
        return page.sizeHint().height()

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(self.heightForWidth(self.width()))
        return hint

    def event(self, event):
        result = super().event(event)
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize, QEvent.Type.Show):
            self.fit_current_page()
        return result

    def fit_current_page(self):
        height = self.heightForWidth(self.width())
        if height > 0 and (height != self.minimumHeight() or height != self.maximumHeight()):
            self.setFixedHeight(height)


class RibbonPage(QWidget):
    def __init__(self, operation, title=None):
        super().__init__()
        self.setObjectName(f"{operation}_page")
        if title is None:
            self.row = QHBoxLayout(self)
            self.row.setContentsMargins(8, 2, 8, 4)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            heading = QLabel(title)
            heading.setStyleSheet("font-size: 24px; font-weight: 700; background: transparent;")
            self.heading_row = QHBoxLayout()
            self.heading_row.addWidget(heading)
            self.heading_row.addStretch()
            layout.addLayout(self.heading_row)
            card = QFrame()
            card.setObjectName("operation_options")
            self.row = QHBoxLayout(card)
            self.row.setContentsMargins(16, 10, 16, 10)
            layout.addWidget(card)
        self.row.setSpacing(12)

    def options_button(self, title, content, text="Параметры…"):
        content.setParent(self)
        content.hide()
        button = IconButton(text)
        setup_standard_secondary_button(button)
        button.clicked.connect(lambda: self.show_options(title, content))
        return button

    def show_options(self, title, content):
        dialog = QDialog(self.window())
        setup_standard_dialog(dialog, title=title, width=550, height=400)
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(content)
        content.show()
        layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        try:
            dialog.exec()
        finally:
            scroll.takeWidget()
            content.setParent(self)
            content.hide()
            dialog.deleteLater()
