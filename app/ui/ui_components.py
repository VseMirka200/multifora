
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QTextOption,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionMenuItem,
    QStyleOptionToolButton,
    QStylePainter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from app.core.app_utils import _log_ignored_error
from app.ui.palette import standard_palette
from app.ui.ui_icons import UI_ICON_SIZE, apply_button_icon, button_icon
from app.ui.ui_styles import (
    ACTION_BUTTON_HEIGHT,
    FIELD_HEIGHT,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    STANDARD_FORM_LABEL_STYLE,
    build_drop_action_tile_style,
    build_drop_action_tile_text_style,
    build_standard_button_style,
    build_standard_field_style,
)

if TYPE_CHECKING:
    from app.ui.file_table import FileListItemAdapter, FileListModel, FileListWidget


def __getattr__(name: str):
    if name in {
        "FileListItemAdapter",
        "FileListItemDelegate",
        "FileListModel",
        "FileListWidget",
        "FilePreview",
        "operation_file_items",
        "selected_file_items",
    }:
        from app.ui import file_table

        return getattr(file_table, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def apply_standard_field_style(widget):
    theme = resolve_widget_theme_mode(widget)
    # В приложении не используется стандартное контекстное меню редактирования
    # Qt (Undo/Redo/Cut/Copy/Paste). Контекстные меню приложения остаются
    # доступны на списках и таблицах.
    if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
    name = widget.objectName() if hasattr(widget, "objectName") else ""
    if isinstance(widget, MenuLikeComboBox):
        widget.setStyleSheet(build_standard_field_style(theme, "menu"))
        return widget
    if isinstance(widget, QComboBox):
        widget.setStyleSheet(build_standard_field_style(theme, "combo"))
        try:
            view = QListView(widget)
            view.setSpacing(0)
            view.setUniformItemSizes(True)
            view.setItemDelegate(ComboPopupItemDelegate(widget))
            widget.setView(view)
        except Exception as error:
            _log_ignored_error("apply_standard_field_style", error)
        return widget
    if isinstance(widget, QAbstractSpinBox):
        widget.setStyleSheet(build_standard_field_style(theme, "spin"))
        return widget
    if isinstance(widget, QTextEdit):
        widget.setStyleSheet(build_standard_field_style(theme, "textedit"))
        return widget
    if isinstance(widget, QLineEdit):
        if isinstance(widget.parentWidget(), QAbstractSpinBox):
            return widget
        if name == "header_cell_br":
            widget.setStyleSheet(build_standard_field_style(theme, "header"))
            return widget
        widget.setStyleSheet(build_standard_field_style(theme, "line"))
        return widget
    if isinstance(widget, QToolButton) and name in {
        "header_cell_tl",
        "header_cell_tr",
    }:
        widget.setStyleSheet(build_standard_field_style(theme, "header"))
        return widget
    if isinstance(widget, QAbstractItemView) and name == "files_list":
        widget.setStyleSheet(build_standard_field_style(theme, "surface"))
        return widget
    return widget


def refresh_standard_field_styles(root: QWidget):
    if root is None:
        return root
    try:
        for widget in root.findChildren(QLineEdit):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QTextEdit):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QPlainTextEdit):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QAbstractSpinBox):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QComboBox):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QToolButton):
            if widget.objectName() in {
                "header_cell_tl",
                "header_cell_tr",
                "menu_like_combo",
            }:
                apply_standard_field_style(widget)
        for widget in root.findChildren(QAbstractItemView):
            if widget.objectName() == "files_list":
                apply_standard_field_style(widget)
    except Exception as error:
        _log_ignored_error("refresh_standard_field_styles", error)
    return root


def refresh_standard_button_styles(root: QWidget):
    if root is None:
        return root
    mode = resolve_widget_theme_mode(root)
    try:
        for widget in root.findChildren(QAbstractButton):
            role = widget.property("buttonVariant")
            if not role:
                continue
            widget.setStyleSheet(
                build_standard_button_style(
                    mode, str(role)
                )
            )
            apply_button_icon(widget, mode)
            _refresh_widget_style(widget)
    except Exception as error:
        _log_ignored_error("refresh_standard_button_styles", error)
    return root


def resolve_widget_theme_mode(widget, preferred: str | None = None) -> str:
    """Возвращает заданную тему или наследует её от родительских виджетов."""
    if preferred in ("light", "dark"):
        return preferred
    if widget is None:
        return "dark"
    current = widget
    while current is not None:
        mode = getattr(current, "_effective_theme_mode", None)
        if mode in ("light", "dark"):
            return mode
        mode = getattr(current, "theme_mode", None)
        if mode in ("light", "dark"):
            return mode
        next_widget = None
        try:
            next_widget = current.parentWidget()
        except Exception:
            next_widget = None
        if next_widget is None:
            try:
                next_widget = current.parent()
            except Exception:
                next_widget = None
        current = next_widget
    try:
        top = widget.window()
        if top is not None:
            mode = getattr(top, "_effective_theme_mode", None)
            if mode in ("light", "dark"):
                return mode
            parent = top.parent()
            while parent is not None:
                mode = getattr(parent, "_effective_theme_mode", None)
                if mode in ("light", "dark"):
                    return mode
                parent = parent.parent() if hasattr(parent, "parent") else None
    except Exception as error:
        _log_ignored_error("resolve_widget_theme_mode", error)
    return "dark"


def _refresh_widget_style(widget: QWidget) -> None:
    """Переприменяет QSS к виджету после изменения variant/objectName."""
    try:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
    except Exception as error:
        _log_ignored_error("_refresh_widget_style", error)


class DropZoneOverlay(QWidget):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.palette().color(QPalette.ColorRole.WindowText))
        pen.setWidthF(1.25)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 12, 12)


class AutoHeightTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.document().setDocumentMargin(0)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._resize_grip = QWidget(self)
        self._resize_grip.setStyleSheet("background: transparent;")
        self._resize_grip.setCursor(Qt.CursorShape.SizeVerCursor)
        self._resize_grip.setToolTip("Потяните нижний край, чтобы изменить высоту поля")
        self._drag_start = None
        self._resize_grip.installEventFilter(self)
        self.setFixedHeight(FIELD_HEIGHT)

    def setText(self, text: str):
        self.setPlainText(str(text or "").replace("\r", "").replace("\n", ""))

    def text(self) -> str:
        return self.toPlainText().replace("\r", "").replace("\n", "")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_grip.setGeometry(1, self.height() - 5, self.width() - 2, 5)
        self._resize_grip.raise_()

    def eventFilter(self, watched, event):
        if watched is getattr(self, "_resize_grip", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_start = (event.globalPosition().y(), self.height())
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_start is not None:
                start_y, start_height = self._drag_start
                height = max(FIELD_HEIGHT, round(start_height + event.globalPosition().y() - start_y))
                self.setFixedHeight(min(height, max(FIELD_HEIGHT, self.window().height() // 2)))
                expanded = self.height() > FIELD_HEIGHT
                self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth if expanded else QTextEdit.LineWrapMode.NoWrap)
                self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if expanded else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_start = None
                return True
        return super().eventFilter(watched, event)


class ComboPopupItemDelegate(QStyledItemDelegate):
    def __init__(self, combo: QComboBox):
        super().__init__(combo)
        self._combo = combo

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(max(22, self._combo.height()))
        return hint


def setup_standard_dropdown(widget, *, fixed_width: int | None = None):
    header_fields = {"header_cell_tl", "header_cell_tr"}
    height = (
        HEADER_FIELD_HEIGHT
        if getattr(widget, "objectName", lambda: "")() in header_fields
        else FIELD_HEIGHT
    )
    widget.setFixedHeight(height)
    widget.setMinimumWidth(0)
    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
        widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

    if isinstance(widget, MenuLikeComboBox):
        apply_standard_field_style(widget)
        return widget

    if not isinstance(widget, QComboBox):
        return widget

    try:
        widget.setEditable(True)
        line_edit = widget.lineEdit()
        if line_edit is not None:
            line_edit.setReadOnly(True)
            line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
            line_edit.setFont(widget.font())
    except Exception as error:
        _log_ignored_error("setup_standard_dropdown", error)

    try:
        view = QListView(widget)
        view.setSpacing(0)
        view.setUniformItemSizes(True)
        view.setItemDelegate(ComboPopupItemDelegate(widget))
        widget.setView(view)
    except Exception as error:
        _log_ignored_error("setup_standard_dropdown", error)

    apply_standard_field_style(widget)

    return widget


def setup_standard_line_input(widget, *, fixed_width: int | None = None):
    widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
    widget.setFixedHeight(FIELD_HEIGHT)
    widget.setMinimumWidth(0)
    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
        widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    apply_standard_field_style(widget)
    return widget


def setup_standard_spin_input(widget, *, fixed_width: int | None = None):
    widget.setFixedHeight(FIELD_HEIGHT)
    widget.setMinimumWidth(0)
    try:
        line_edit = widget.lineEdit()
        if line_edit is not None:
            line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
    except Exception as error:
        _log_ignored_error("setup_standard_spin_input", error)
    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
        widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    apply_standard_field_style(widget)
    return widget


def setup_standard_header_dropdown(widget):
    widget.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    widget.setFixedHeight(HEADER_FIELD_HEIGHT)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    apply_standard_field_style(widget)
    return widget


def setup_standard_action_button(
    widget,
    *,
    variant: str | None = None,
    expand: bool = True,
    icon_name: str | None = None,
):
    role = variant or widget.property("buttonVariant") or "secondary"
    widget.setFixedHeight(ACTION_BUTTON_HEIGHT)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(
        QSizePolicy.Policy.Expanding if expand else QSizePolicy.Policy.Maximum,
        QSizePolicy.Policy.Fixed,
    )
    widget.setProperty("buttonVariant", role)
    if icon_name is not None:
        widget.setProperty("buttonIconName", icon_name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if role == "primary" and not widget.objectName():
        widget.setObjectName("convert_btn")
    elif role == "danger" and not widget.objectName():
        widget.setObjectName("cancel_operation_btn")
    if isinstance(widget, QPushButton):
        widget.setFlat(False)
    widget.setStyleSheet(
        build_standard_button_style(resolve_widget_theme_mode(widget), role)
    )
    apply_button_icon(widget, resolve_widget_theme_mode(widget))
    _refresh_widget_style(widget)
    return widget


def setup_standard_primary_button(
    widget,
    *,
    expand: bool = True,
    icon_name: str | None = None,
):
    return setup_standard_action_button(
        widget,
        variant="primary",
        expand=expand,
        icon_name=icon_name,
    )


def setup_standard_danger_button(
    widget,
    *,
    expand: bool = True,
    icon_name: str | None = None,
):
    return setup_standard_action_button(
        widget,
        variant="danger",
        expand=expand,
        icon_name=icon_name,
    )


def setup_standard_secondary_button(
    widget,
    *,
    expand: bool = True,
    icon_name: str | None = None,
):
    return setup_standard_action_button(widget, expand=expand, icon_name=icon_name)


def setup_standard_form_label(
    widget, *, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft
):
    widget.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    widget.setWordWrap(True)
    widget.setStyleSheet(STANDARD_FORM_LABEL_STYLE)
    widget.ensurePolished()
    widget.setFixedHeight(widget.fontMetrics().lineSpacing())
    return widget


def setup_clickable_checkbox_label(
    label: QLabel, checkbox, *, tooltip: str = ""
) -> QLabel:
    """Связывает подпись с чекбоксом без дублирования обработчиков мыши."""
    label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    label.setCursor(Qt.CursorShape.PointingHandCursor)
    label.setProperty("clickableCheckboxLabel", True)
    if tooltip:
        label.setToolTip(tooltip)

    def toggle_checkbox(event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and checkbox.isEnabled()
        ):
            checkbox.toggle()
            event.accept()

    label.mouseReleaseEvent = toggle_checkbox
    return label


def setup_standard_dialog(
    dialog: QDialog,
    *,
    title: str,
    min_width: int | None = None,
    min_height: int | None = None,
    width: int | None = None,
    height: int | None = None,
    fixed_width: int | None = None,
    size_grip: bool = False,
    allow_minmax: bool = False,
):
    dialog._effective_theme_mode = resolve_widget_theme_mode(dialog.parent())
    parent = dialog.parent()
    if parent is not None:
        try:
            dialog.setStyleSheet(parent.styleSheet())
        except Exception as error:
            _log_ignored_error("setup_standard_dialog", error)
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    if allow_minmax:
        dialog.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        dialog.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, False)
    if min_width is not None:
        dialog.setMinimumWidth(min_width)
    if min_height is not None:
        dialog.setMinimumHeight(min_height)
    if width is not None and height is not None:
        dialog.resize(width, height)
    elif width is not None:
        dialog.resize(width, dialog.height())
    elif height is not None:
        dialog.resize(dialog.width(), height)
    if fixed_width is not None:
        dialog.setFixedWidth(fixed_width)
    dialog.setSizeGripEnabled(size_grip)
    return dialog


def get_russian_text_input(
    parent, *, title: str, label: str, text: str = ""
) -> tuple[str, bool]:
    dialog = QDialog(parent)
    setup_standard_dialog(dialog, title=title, min_width=380)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(10, 6, 10, 6)
    layout.setSpacing(SPACE_SM)

    label_widget = QLabel(label)
    setup_standard_form_label(label_widget)
    layout.addWidget(label_widget)

    line_edit = QLineEdit()
    line_edit.setText(text)
    setup_standard_line_input(line_edit)
    layout.addWidget(line_edit)

    buttons_row = QWidget()
    buttons_row.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    buttons_layout = QHBoxLayout(buttons_row)
    buttons_layout.setContentsMargins(*MARGINS_NONE)
    buttons_layout.setSpacing(SPACE_SM)
    ok_button = QPushButton("Сохранить", dialog)
    setup_standard_primary_button(ok_button, expand=True, icon_name="save")
    cancel_button = QPushButton("Отмена", dialog)
    setup_standard_secondary_button(cancel_button, expand=True, icon_name="close")
    buttons_layout.addWidget(ok_button, 1)
    buttons_layout.addWidget(cancel_button, 1)
    layout.addWidget(buttons_row)

    ok_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    line_edit.selectAll()
    line_edit.setFocus()

    accepted = dialog.exec() == int(QDialog.DialogCode.Accepted)
    return line_edit.text(), accepted


def sync_standard_menu_width(menu: QMenu, anchor_widget: QWidget):
    if menu is None or anchor_widget is None:
        return
    adjust_to_screen = getattr(menu, "adjust_to_available_screen", None)
    if callable(adjust_to_screen):
        adjust_to_screen(anchor_widget)
    width = anchor_widget.width()
    if width <= 0:
        width = anchor_widget.sizeHint().width()
    filter_list = getattr(menu, "filter_list", None)
    metrics = menu.fontMetrics()
    for action in menu.actions():
        if action.text() and not isinstance(action, QWidgetAction):
            text = action.property("fullText") or action.text().replace("&&", "&")
            width = max(width, metrics.horizontalAdvance(text) + 64)
    if filter_list is not None:
        for row in range(filter_list.count()):
            width = max(width, metrics.horizontalAdvance(filter_list.item(row).text()) + 64)
    screen = anchor_widget.screen()
    if screen is not None:
        width = min(width, max(1, screen.availableGeometry().width() - 16))
    menu.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    menu.setMinimumWidth(width)
    menu.setMaximumWidth(width)
    menu.setFixedWidth(width)
    if filter_list is not None:
        # QWidgetAction иначе сохраняет sizeHint по самому длинному пункту:
        # меню сжимается до ширины кнопки, а вертикальный скроллбар остаётся
        # за его правой границей и визуально пропадает.
        filter_list.setFixedWidth(max(1, width - 2))


def setup_standard_popup_menu(menu: QMenu):
    """Разрешает QSS-скруглению меню оставлять прозрачные внешние углы."""
    if menu is not None:
        # На Windows прозрачные пиксели верхнеуровневого popup корректно
        # компонуются только без системной прямоугольной рамки.
        menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setToolTipsVisible(True)
    return menu


class StandardPopupMenu(QMenu):
    """Общие геометрия, отметки, иконки и раскрытие меню по кнопке."""

    ICON_SIZE = QSize(18, 18)

    def __init__(self, anchor: QWidget | None = None, *, theme_widget: QWidget | None = None):
        super().__init__(anchor)
        self.anchor = anchor
        self.theme_widget = theme_widget or anchor
        self.setObjectName("menu_like_combo_popup")
        self._pressed_action = None
        setup_standard_popup_menu(self)
        self.aboutToShow.connect(self._prepare_popup)
        self.aboutToHide.connect(lambda: self._set_open(False))

    def add_command(self, text: str, *, icon_name: str = "", tooltip: str = "") -> QAction:
        action = self.addAction(text.replace("&", "&&"))
        action.setProperty("fullText", text)
        action.setProperty("menuIconName", icon_name)
        action.setToolTip(tooltip or text)
        return action

    def _set_open(self, value: bool) -> None:
        if self.anchor is None:
            return
        self.anchor.setProperty("menuOpen", value)
        _refresh_widget_style(self.anchor)

    def _prepare_popup(self) -> None:
        mode = resolve_widget_theme_mode(self.theme_widget)
        for action in self.actions():
            name = action.property("menuIconName")
            if name:
                action.setIcon(button_icon(str(name), mode, "secondary"))
        sync_standard_menu_width(self, self.anchor)
        self._set_open(True)

    def showEvent(self, event):
        super().showEvent(event)
        if self.anchor is None:
            return
        screen = self.anchor.screen()
        if screen is None:
            return
        available = screen.availableGeometry().adjusted(8, 8, -8, -8)
        origin = self.anchor.mapToGlobal(self.anchor.rect().topLeft())
        below = origin.y() + self.anchor.height()
        height = min(self.height(), available.height())
        self.resize(min(self.width(), available.width()), height)
        y = below if below + height <= available.bottom() + 1 else origin.y() - height
        y = max(available.top(), min(y, available.bottom() + 1 - height))
        x = max(available.left(), min(origin.x(), available.right() + 1 - self.width()))
        self.move(x, y)

    def mousePressEvent(self, event):
        self._pressed_action = self.actionAt(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.position().toPoint())
        if (event.button() == Qt.MouseButton.LeftButton and action is not None
                and action is self._pressed_action and action.isEnabled() and action.property("keepOpen")):
            action.trigger()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        action = self.activeAction()
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space)
                and action is not None and action.isEnabled() and action.property("keepOpen")):
            action.trigger()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QStylePainter(self)
        palette = standard_palette(resolve_widget_theme_mode(self.theme_widget))
        actions = self.actions()
        has_checks = any(action.isCheckable() for action in actions)
        has_icons = any(not action.icon().isNull() for action in actions)
        for action in actions:
            row = self.actionGeometry(action)
            if isinstance(action, QWidgetAction) or action.isSeparator() or not row.intersects(event.rect()):
                continue
            option = QStyleOptionMenuItem()
            self.initStyleOption(option, action)
            option.rect = row
            option.text = ""
            option.icon = QIcon()
            option.checkType = QStyleOptionMenuItem.CheckType.NotCheckable
            option.checked = False
            painter.drawControl(QStyle.ControlElement.CE_MenuItem, option)
            painter.setFont(option.font)
            painter.setPen(QColor(palette["fg"] if action.isEnabled() else palette["disabled_fg"]))
            left = row.left() + 8
            if has_checks:
                if action.isChecked():
                    painter.save()
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setPen(QPen(painter.pen().color(), 1.65))
                    y = row.center().y()
                    painter.drawLine(left + 2, y, left + 6, y + 4)
                    painter.drawLine(left + 6, y + 4, left + 13, y - 4)
                    painter.restore()
                left += 22
            if has_icons:
                icon_rect = QRect(left, row.center().y() - 8, 18, 18)
                action.icon().paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter,
                                    QIcon.Mode.Normal if action.isEnabled() else QIcon.Mode.Disabled)
                left += 24
            text_rect = row.adjusted(left - row.left(), 0, -8, 0)
            text = action.property("fullText") or action.text().replace("&&", "&")
            label, separator, shortcut = str(text).partition("\t")
            shortcut_width = painter.fontMetrics().horizontalAdvance(shortcut) if separator else 0
            label_rect = text_rect.adjusted(0, 0, -(shortcut_width + (16 if separator else 0)), 0)
            label = painter.fontMetrics().elidedText(
                label, Qt.TextElideMode.ElideRight, max(0, label_rect.width())
            )
            painter.drawText(
                label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label
            )
            if separator:
                painter.setPen(QColor(palette["disabled_fg"]))
                painter.drawText(
                    text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, shortcut
                )


class SmoothScrollListWidget(QListWidget):
    """Список с мягкой прокруткой обычным колесом мыши."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scroll_animation = QPropertyAnimation(
            self.verticalScrollBar(), b"value", self
        )
        self._scroll_animation.setDuration(180)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _animate_scroll_steps(self, steps: float) -> None:
        scroll_bar = self.verticalScrollBar()
        current_value = scroll_bar.value()
        if self._scroll_animation.state() == QAbstractAnimation.State.Running:
            base_value = int(self._scroll_animation.endValue())
        else:
            base_value = current_value
        target_value = round(base_value - steps * FIELD_HEIGHT)
        target_value = max(
            scroll_bar.minimum(), min(scroll_bar.maximum(), target_value)
        )
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(current_value)
        self._scroll_animation.setEndValue(target_value)
        self._scroll_animation.start()

    def wheelEvent(self, event) -> None:
        # Тачпад уже передаёт плавное попиксельное смещение — не заменяем его.
        if not event.pixelDelta().isNull():
            super().wheelEvent(event)
            return
        angle_delta = event.angleDelta().y()
        if angle_delta == 0:
            super().wheelEvent(event)
            return
        self._animate_scroll_steps(angle_delta / 120.0)
        event.accept()


class ScrollableFilterMenu(StandardPopupMenu):
    """Компактное меню с прокручиваемым списком переключаемых действий."""

    def __init__(self, parent=None, *, max_visible_items: int = 8):
        super().__init__(parent)
        setup_standard_popup_menu(self)
        self._preferred_visible_items = max(1, int(max_visible_items))
        self._filter_actions: list[QAction] = []
        self._filter_items: dict[QAction, QListWidgetItem] = {}
        self._filter_list: SmoothScrollListWidget | None = None

    def _ensure_filter_list(self) -> SmoothScrollListWidget:
        if self._filter_list is not None:
            return self._filter_list

        filter_list = SmoothScrollListWidget(self)
        filter_list.setObjectName("scrollable_filter_list")
        filter_list.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        filter_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        filter_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        filter_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        filter_list.setToolTip("Прокручивайте список колесом мыши")
        filter_list.setSpacing(0)
        filter_list.setMinimumWidth(0)
        filter_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        filter_list.itemClicked.connect(self._toggle_filter_item)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(filter_list)
        super().addAction(widget_action)

        self._filter_list = filter_list
        return filter_list

    @property
    def filter_list(self) -> SmoothScrollListWidget | None:
        return self._filter_list

    def add_filter_action(self, action: QAction) -> QAction:
        filter_list = self._ensure_filter_list()
        action.setParent(self)
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, FIELD_HEIGHT))
        filter_list.addItem(item)
        self._filter_actions.append(action)
        self._filter_items[action] = item
        action.toggled.connect(
            lambda _checked=False, target=action: self._sync_filter_item(
                target
            )
        )
        action.changed.connect(
            lambda target=action: self._sync_filter_item(target)
        )
        self._sync_filter_item(action)
        self._update_filter_list_height()
        return action

    def _sync_filter_item(self, action: QAction) -> None:
        item = self._filter_items.get(action)
        if item is None:
            return
        item.setText(action.text())
        item.setCheckState(Qt.CheckState.Checked if action.isChecked() else Qt.CheckState.Unchecked)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if not action.isEnabled():
            flags = Qt.ItemFlag.NoItemFlags
        item.setFlags(flags)

    def sync_filter_items(self) -> None:
        """Обновляет видимые отметки после группового изменения действий."""
        for action in self._filter_actions:
            self._sync_filter_item(action)

    def _toggle_filter_item(self, item: QListWidgetItem) -> None:
        if self._filter_list is None:
            return
        row = self._filter_list.row(item)
        if 0 <= row < len(self._filter_actions):
            action = self._filter_actions[row]
            if action.isEnabled():
                action.trigger()

    def _visible_row_count(
        self, available_popup_height: int | None = None
    ) -> int:
        action_count = len(self._filter_actions)
        if action_count <= 0:
            return 1
        visible_limit = self._preferred_visible_items
        if available_popup_height is not None:
            # Верхние команды, разделители, рамка и небольшой запас меню.
            command_count = sum(
                1
                for action in self.actions()
                if not isinstance(action, QWidgetAction)
                and not action.isSeparator()
            )
            reserved_height = FIELD_HEIGHT * command_count + 16
            usable_height = max(
                FIELD_HEIGHT * 2, available_popup_height - reserved_height
            )
            visible_limit = min(
                visible_limit, max(2, usable_height // FIELD_HEIGHT)
            )
        return max(1, min(action_count, visible_limit))

    def adjust_to_available_screen(self, anchor_widget: QWidget) -> None:
        if self._filter_list is None or anchor_widget is None:
            return
        try:
            screen = anchor_widget.screen()
            if screen is None:
                return
            available = screen.availableGeometry()
            top_left = anchor_widget.mapToGlobal(
                anchor_widget.rect().topLeft()
            )
            bottom_right = anchor_widget.mapToGlobal(
                anchor_widget.rect().bottomRight()
            )
            space_above = max(0, top_left.y() - available.top())
            space_below = max(0, available.bottom() - bottom_right.y())
            self._update_filter_list_height(max(space_above, space_below))
        except Exception as error:
            _log_ignored_error(
                "ScrollableFilterMenu.adjust_to_available_screen", error
            )

    def _update_filter_list_height(
        self, available_popup_height: int | None = None
    ) -> None:
        if self._filter_list is None:
            return
        visible_items = self._visible_row_count(available_popup_height)
        self._filter_list.setFixedHeight(
            max(1, visible_items) * FIELD_HEIGHT + 2
        )
        can_scroll = len(self._filter_actions) > visible_items
        self._filter_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            if can_scroll
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )


class MenuLikeComboBox(QToolButton):
    """Выпадающий список на QMenu с API, похожим на QComboBox."""

    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("menu_like_combo")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setMinimumWidth(0)
        # Выпадающие поля панели операций должны сжиматься вместе с разделителем,
        # а не сохранять ширину по самому длинному пункту. Текст сокращается при
        # отрисовке, поэтому политика Ignored оставляет поле адаптивным.
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self._items = []
        self._current_index = -1
        self._menu = StandardPopupMenu(self)
        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)
        setup_standard_popup_menu(self._menu)
        self._menu.setObjectName("menu_like_combo_popup")
        self._menu.aboutToShow.connect(self._sync_popup_width)
        self._menu.aboutToShow.connect(self._mark_menu_open)
        self._menu.aboutToHide.connect(self._mark_menu_closed)
        self.setMenu(self._menu)

    def _sync_popup_width(self):
        sync_standard_menu_width(self._menu, self)
        actions = self._menu.actions()
        if 0 <= self._current_index < len(actions):
            self._menu.setActiveAction(actions[self._current_index])

    def _mark_menu_open(self):
        self.setProperty("menuOpen", True)
        _refresh_widget_style(self)

    def _mark_menu_closed(self):
        self.setProperty("menuOpen", False)
        _refresh_widget_style(self)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(0, max(FIELD_HEIGHT, hint.height()))

    def sizeHint(self):
        hint = super().sizeHint()
        # Начальная ширина должна быть удобной, но не должна заставлять узкую
        # боковую панель выходить за доступные границы.
        return QSize(
            min(max(120, hint.width()), 180), max(FIELD_HEIGHT, hint.height())
        )

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""

        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        # В узкой панели оставляем место под стрелку меню и сокращаем только
        # отображаемый текст. Полное значение остаётся доступно в подсказке и меню.
        inset = 12 if self.property("ruleSelector") else 4
        text_rect = self.rect().adjusted(inset, 0, -22, 0)
        metrics = QFontMetrics(self.font())
        painted_text = metrics.elidedText(
            text,
            Qt.TextElideMode.ElideRight,
            max(0, text_rect.width()),
        )
        painter.drawItemText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.palette(),
            self.isEnabled(),
            painted_text,
            self.foregroundRole(),
        )
        draw_dropdown_arrow(painter, self)

    def clear(self):
        self._items = []
        self._current_index = -1
        self._menu.clear()
        self.setText("")
        self.setToolTip("")

    def addItem(self, text: str, user_data=None, *, icon_name: str = ""):
        idx = len(self._items)
        self._items.append((text, user_data))
        action = self._menu.add_command(text, icon_name=icon_name)
        action.setCheckable(True)
        self._action_group.addAction(action)
        action.triggered.connect(
            lambda _checked=False, i=idx: self.setCurrentIndex(i)
        )
        if self._current_index < 0:
            self.setCurrentIndex(0)

    def addItems(self, items):
        for text in items:
            self.addItem(str(text))

    def currentIndex(self) -> int:
        return self._current_index

    def currentText(self) -> str:
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][0]
        return ""

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def findText(self, text: str) -> int:
        target = str(text)
        for i, (t, _d) in enumerate(self._items):
            if t == target:
                return i
        return -1

    def findData(self, user_data) -> int:
        for i, (_t, data) in enumerate(self._items):
            if data == user_data:
                return i
        return -1

    def setCurrentIndex(self, index: int):
        index = int(index)
        if index < 0 or index >= len(self._items):
            return
        if self._current_index == index:
            return
        self._current_index = index
        self._menu.actions()[index].setChecked(True)
        text = self._items[index][0]
        self.setText(text)
        self.setToolTip(text)
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(text)

    def setCurrentText(self, text: str):
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)


def draw_dropdown_arrow(painter, widget):
    """Одинаковый индикатор раскрытия для полей, фильтров и кнопок."""
    palette = standard_palette(resolve_widget_theme_mode(widget))
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(palette["fg"] if widget.isEnabled() else palette["disabled_fg"]), 1.4))
    x, y = widget.width() - 12, widget.height() // 2
    direction = -1 if widget.property("menuOpen") else 1
    painter.drawLine(x - 3, y - direction, x, y + direction * 2)
    painter.drawLine(x, y + direction * 2, x + 3, y - direction)
    painter.restore()


def draw_icon_caption(painter, rect, icon, icon_size, text, enabled, *,
                      align_left=False, text_y_offset=0):
    metrics = painter.fontMetrics()
    size = icon.actualSize(icon_size)
    offset = 0 if size.isEmpty() else size.width() + 5
    text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(0, rect.width() - offset))
    glyphs = QPainterPath()
    glyphs.addText(0, 0, painter.font(), text)
    bounds = glyphs.boundingRect()
    width = offset + bounds.width()
    left = rect.left() if align_left else round(rect.x() + (rect.width() - width) / 2)
    if not size.isEmpty():
        icon_rect = QRect(0, 0, size.width(), size.height())
        icon_rect.moveCenter(rect.center())
        icon_rect.moveLeft(left)
        mode = QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled
        icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter, mode)
    glyphs.translate(left + offset - bounds.left(),
                     rect.y() + rect.height() / 2 - bounds.center().y() + text_y_offset)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillPath(glyphs, painter.pen().brush())
    painter.restore()


class IconButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIconSize(UI_ICON_SIZE)

    def sizeHint(self):
        hint = super().sizeHint()
        if self.icon().isNull():
            return hint
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.rect.setSize(hint)
        content = self.style().subElementRect(
            QStyle.SubElement.SE_PushButtonContents, option, self
        )
        caption_width = self.fontMetrics().horizontalAdvance(self.text())
        required = self.icon().actualSize(self.iconSize()).width() + 5 + caption_width
        hint.setWidth(hint.width() + max(0, required - content.width()))
        return hint

    def paintEvent(self, event):
        has_popup = self.menu() is not None or self.property("hasPopup")
        if self.icon().isNull() and not has_popup:
            return super().paintEvent(event)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.icon = QIcon()
        option.text = ""
        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)
        painter.setPen(option.palette.buttonText().color())
        rect = self.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, self)
        if has_popup:
            rect.adjust(0, 0, -18, 0)
        draw_icon_caption(painter, rect, self.icon(), self.iconSize(), self.text(),
                          self.isEnabled(), align_left=self.objectName() == "help_button",
                          text_y_offset=1)
        if has_popup:
            draw_dropdown_arrow(painter, self)


class MenuWidthButton(MenuLikeComboBox):
    """Выделяет кнопке столько места, сколько нужно её выпадающему меню."""

    def sizeHint(self):
        hint = super().sizeHint()
        menu = self.menu()
        if menu is not None:
            hint.setWidth(max(hint.width(), menu.sizeHint().width()))
        return hint


class FilterToolButton(QToolButton):
    """Кнопка фильтра с подписью слева и стрелкой меню справа."""

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""
        icon = option.icon
        option.icon = QIcon()

        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        painter.setPen(option.palette.buttonText().color())
        draw_icon_caption(painter, self.rect().adjusted(12, 0, -22, 0), icon,
                          option.iconSize, text, self.isEnabled(), align_left=True, text_y_offset=1)
        draw_dropdown_arrow(painter, self)


class DropActionTile(QFrame):
    clicked = Signal()

    def __init__(self, icon: QIcon, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("drop_action_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(144, 132)
        self._theme = "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_XS, SPACE_XS, SPACE_XS, SPACE_XS)
        layout.setSpacing(SPACE_MD)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if not icon.isNull():
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(icon.pixmap(UI_ICON_SIZE))
            icon_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self._apply_theme_style()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_theme_mode(self, mode: str):
        self._theme = "light" if str(mode).lower() == "light" else "dark"
        self._apply_theme_style()

    def _apply_theme_style(self):
        self.setStyleSheet(build_drop_action_tile_style(self._theme))
        if hasattr(self, "text_label"):
            self.text_label.setStyleSheet(
                build_drop_action_tile_text_style(self._theme)
            )


class LoggingStatusBar(QStatusBar):
    messageLogged = Signal(str)

    def showMessage(self, text: str, timeout: int = 0):
        super().showMessage(text, timeout)
        if text:
            self.messageLogged.emit(text)


__all__ = [
    "DropActionTile",
    "FileListItemAdapter",
    "FileListModel",
    "FileListWidget",
    "LoggingStatusBar",
]
