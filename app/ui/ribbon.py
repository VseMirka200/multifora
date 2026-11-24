"""Вкладка ленты с горизонтальными группами команд."""

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QScrollArea,
    QSizePolicy, QStackedWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from app.ui.ui_styles import PAGE_SECTION_SPACING, TAB_BAR_HEIGHT
from app.ui.ui_components import IconButton, setup_standard_action_button, setup_standard_dialog


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


class RibbonStack(QStackedWidget):
    """Подбирает высоту панели по содержимому открытой вкладки."""

    def heightForWidth(self, width):
        page = self.currentWidget()
        if page is None:
            return 0
        page.ensurePolished()
        preferred = page.heightForWidth(width) if page.hasHeightForWidth() else page.sizeHint().height()
        return max(0, preferred, page.minimumSizeHint().height())

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(self.heightForWidth(self.width()))
        return hint

    def event(self, event):
        result = super().event(event)
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize, QEvent.Type.Show):
            self.fit_pages()
        return result

    def fit_pages(self):
        height = self.heightForWidth(self.width())
        if height > 0 and (height != self.minimumHeight() or height != self.maximumHeight()):
            self.setFixedHeight(height)


class RibbonPage(QWidget):
    def __init__(self, operation, *, with_card=False):
        super().__init__()
        self.setObjectName(f"{operation}_page")
        if not with_card:
            self.row = QHBoxLayout(self)
            self.row.setContentsMargins(8, 2, 8, 4)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            card = QFrame()
            card.setObjectName("operation_options")
            body = QVBoxLayout(card)
            body.setContentsMargins(12, 12, 12, 12)
            body.setSpacing(0)
            self.row = QHBoxLayout()
            body.addLayout(self.row, 1)
            layout.addWidget(card, 1)
        self.row.setSpacing(PAGE_SECTION_SPACING)

    def options_button(self, title, content, text="Параметры…"):
        content.setParent(self)
        content.hide()
        button = IconButton(text)
        setup_standard_action_button(button, variant="command", expand=False)
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
