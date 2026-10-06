import os

from PyQt6.QtCore import (
    QAbstractAnimation,
    QAbstractTableModel,
    QEasingCurve,
    QItemSelectionModel,
    QModelIndex,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QTextOption,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionToolButton,
    QStyleOptionViewItem,
    QStylePainter,
    QTableView,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from app.core.app_utils import _log_ignored_error
from app.core.models import file_item_source_folder, file_item_type_label
from app.ui.ui_spacing import (
    ACTION_BUTTON_HEIGHT,
    FIELD_HEIGHT,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
)
from app.ui.ui_styles import (
    COMPACT_CHECKBOX_STYLE,
    FILE_LIST_DRAG_ACTIVE_STYLE,
    FILE_LIST_HEADER_STYLE,
    STANDARD_FORM_LABEL_STYLE,
    build_drop_action_tile_style,
    build_drop_action_tile_text_style,
    build_standard_button_style,
    build_standard_field_style,
)


def apply_standard_field_style(widget):
    theme = _resolve_widget_theme_mode(widget)
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
        if name == "header_cell_br":
            widget.setStyleSheet(build_standard_field_style(theme, "header"))
            return widget
        widget.setStyleSheet(build_standard_field_style(theme, "line"))
        return widget
    if isinstance(widget, QToolButton) and name in {"header_cell_tl", "header_cell_tr"}:
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
        for widget in root.findChildren(QAbstractSpinBox):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QComboBox):
            apply_standard_field_style(widget)
        for widget in root.findChildren(QToolButton):
            if widget.objectName() in {"header_cell_tl", "header_cell_tr", "menu_like_combo"}:
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
    try:
        for widget in root.findChildren(QPushButton):
            role = widget.property("buttonVariant")
            if not role:
                continue
            widget.setStyleSheet(
                build_standard_button_style(_resolve_widget_theme_mode(widget), str(role))
            )
            _refresh_widget_style(widget)
    except Exception as error:
        _log_ignored_error("refresh_standard_button_styles", error)
    return root


def _resolve_widget_theme_mode(widget) -> str:
    current = widget
    while current is not None:
        mode = getattr(current, "_effective_theme_mode", None)
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
        _log_ignored_error("_resolve_widget_theme_mode", error)
    return "dark"


def _refresh_widget_style(widget: QWidget) -> None:
    """Переприменяет QSS к виджету после изменения variant/objectName."""
    try:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
    except Exception as error:
        _log_ignored_error("_refresh_widget_style", error)


class AutoHeightTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.textChanged.connect(self._update_auto_height)
        QTimer.singleShot(0, self._update_auto_height)

    def setText(self, text: str):
        self.setPlainText(str(text or "").replace("\r", "").replace("\n", ""))
        self._update_auto_height()

    def text(self) -> str:
        return self.toPlainText().replace("\r", "").replace("\n", "")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_auto_height()

    def _update_auto_height(self):
        try:
            self.document().setTextWidth(max(0, self.viewport().width()))
            doc_height = self.document().documentLayout().documentSize().height()
            frame = self.frameWidth() * 2
            height = int(doc_height + frame + 6)
            min_height = getattr(self, "_auto_min_height", FIELD_HEIGHT)
            self.setFixedHeight(max(min_height, height))
        except Exception:
            min_height = getattr(self, "_auto_min_height", FIELD_HEIGHT)
            self.setFixedHeight(max(min_height, self.height() or min_height))


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
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

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
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    apply_standard_field_style(widget)
    return widget


def setup_standard_header_dropdown(widget):
    widget.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    widget.setFixedHeight(HEADER_FIELD_HEIGHT)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    apply_standard_field_style(widget)
    return widget


def setup_standard_action_button(
    widget,
    *,
    variant: str | None = None,
    expand: bool = False,
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
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if variant == "primary" and not widget.objectName():
        widget.setObjectName("convert_btn")
    elif variant == "danger" and not widget.objectName():
        widget.setObjectName("cancel_operation_btn")
    widget.setFlat(False)
    widget.setStyleSheet(build_standard_button_style(_resolve_widget_theme_mode(widget), role))
    _refresh_widget_style(widget)
    return widget


def setup_standard_primary_button(
    widget,
    *,
    expand: bool = False,
):
    return setup_standard_action_button(
        widget,
        variant="primary",
        expand=expand,
    )


def setup_standard_danger_button(
    widget,
    *,
    expand: bool = False,
):
    return setup_standard_action_button(
        widget,
        variant="danger",
        expand=expand,
    )


def setup_standard_secondary_button(
    widget,
    *,
    expand: bool = False,
):
    return setup_standard_action_button(widget, expand=expand)


def setup_standard_form_label(widget, *, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
    widget.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    widget.setWordWrap(True)
    widget.setFixedHeight(18)
    widget.setStyleSheet(STANDARD_FORM_LABEL_STYLE)
    return widget


def setup_compact_checkbox(widget):
    widget.setStyleSheet(COMPACT_CHECKBOX_STYLE)
    return widget


def setup_clickable_checkbox_label(label: QLabel, checkbox, *, tooltip: str = "") -> QLabel:
    """Связывает подпись с чекбоксом без дублирования обработчиков мыши."""
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    label.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        label.setToolTip(tooltip)

    def toggle_checkbox(event):
        if event.button() == Qt.MouseButton.LeftButton and checkbox.isEnabled():
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


def get_russian_text_input(parent, *, title: str, label: str, text: str = "") -> tuple[str, bool]:
    dialog = QDialog(parent)
    try:
        dialog._effective_theme_mode = getattr(parent, "_effective_theme_mode", "dark")
    except Exception as error:
        _log_ignored_error("get_russian_text_input", error)
    setup_standard_dialog(dialog, title=title, min_width=380)
    try:
        dialog.setStyleSheet(parent.styleSheet())
    except Exception as error:
        _log_ignored_error("get_russian_text_input", error)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(10, 6, 10, 6)
    layout.setSpacing(SPACE_SM)

    label_widget = QLabel(label)
    setup_standard_form_label(label_widget)
    label_widget.setFixedHeight(16)
    layout.addWidget(label_widget)

    line_edit = QLineEdit()
    line_edit.setText(text)
    setup_standard_line_input(line_edit)
    layout.addWidget(line_edit)

    buttons_row = QWidget()
    buttons_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    buttons_layout = QHBoxLayout(buttons_row)
    buttons_layout.setContentsMargins(*MARGINS_NONE)
    buttons_layout.setSpacing(SPACE_SM)
    ok_button = QPushButton("Сохранить")
    setup_standard_primary_button(ok_button, expand=True)
    cancel_button = QPushButton("Отмена")
    setup_standard_danger_button(cancel_button, expand=True)
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
    menu.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    menu.setMinimumWidth(width)
    menu.setMaximumWidth(width)
    menu.setFixedWidth(width)
    filter_list = getattr(menu, "filter_list", None)
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
    return menu


class SmoothScrollListWidget(QListWidget):
    """Список с мягкой прокруткой обычным колесом мыши."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
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
        target_value = max(scroll_bar.minimum(), min(scroll_bar.maximum(), target_value))
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


class ScrollableFilterMenu(QMenu):
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
        filter_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        filter_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        filter_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        filter_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        filter_list.setToolTip("Прокручивайте список колесом мыши")
        filter_list.setSpacing(0)
        filter_list.setMinimumWidth(0)
        filter_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        action.toggled.connect(lambda _checked=False, target=action: self._sync_filter_item(target))
        action.changed.connect(lambda target=action: self._sync_filter_item(target))
        self._sync_filter_item(action)
        self._update_filter_list_height()
        return action

    def _sync_filter_item(self, action: QAction) -> None:
        item = self._filter_items.get(action)
        if item is None:
            return
        marker = "✓" if action.isChecked() else " "
        item.setText(f"{marker}  {action.text()}")
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

    def _visible_row_count(self, available_popup_height: int | None = None) -> int:
        action_count = len(self._filter_actions)
        if action_count <= 0:
            return 1
        visible_limit = self._preferred_visible_items
        if available_popup_height is not None:
            # Верхние команды, разделители, рамка и небольшой запас меню.
            command_count = sum(
                1
                for action in self.actions()
                if not isinstance(action, QWidgetAction) and not action.isSeparator()
            )
            reserved_height = FIELD_HEIGHT * command_count + 16
            usable_height = max(FIELD_HEIGHT * 2, available_popup_height - reserved_height)
            visible_limit = min(visible_limit, max(2, usable_height // FIELD_HEIGHT))
        return max(1, min(action_count, visible_limit))

    def adjust_to_available_screen(self, anchor_widget: QWidget) -> None:
        if self._filter_list is None or anchor_widget is None:
            return
        try:
            screen = anchor_widget.screen()
            if screen is None:
                return
            available = screen.availableGeometry()
            top_left = anchor_widget.mapToGlobal(anchor_widget.rect().topLeft())
            bottom_right = anchor_widget.mapToGlobal(anchor_widget.rect().bottomRight())
            space_above = max(0, top_left.y() - available.top())
            space_below = max(0, available.bottom() - bottom_right.y())
            self._update_filter_list_height(max(space_above, space_below))
        except Exception as error:
            _log_ignored_error("ScrollableFilterMenu.adjust_to_available_screen", error)

    def _update_filter_list_height(self, available_popup_height: int | None = None) -> None:
        if self._filter_list is None:
            return
        visible_items = self._visible_row_count(available_popup_height)
        self._filter_list.setFixedHeight(max(1, visible_items) * FIELD_HEIGHT + 2)
        can_scroll = len(self._filter_actions) > visible_items
        self._filter_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            if can_scroll
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )


class MenuLikeComboBox(QToolButton):
    """Выпадающий список на QMenu с API, похожим на QComboBox."""

    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("menu_like_combo")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setMinimumWidth(0)
        # Выпадающие поля панели операций должны сжиматься вместе с разделителем,
        # а не сохранять ширину по самому длинному пункту. Текст сокращается при
        # отрисовке, поэтому политика Ignored оставляет поле адаптивным.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._items = []
        self._current_index = -1
        self._menu = QMenu(self)
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
        return QSize(min(max(120, hint.width()), 180), max(FIELD_HEIGHT, hint.height()))

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""

        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        # В узкой панели оставляем место под стрелку меню и сокращаем только
        # отображаемый текст. Полное значение остаётся доступно в подсказке и меню.
        text_rect = self.rect().adjusted(4, 0, -22, 0)
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

    def clear(self):
        self._items = []
        self._current_index = -1
        self._menu.clear()
        self.setText("")

    def addItem(self, text: str, user_data=None):
        idx = len(self._items)
        self._items.append((text, user_data))
        action = QAction(text, self._menu)
        action.triggered.connect(lambda _checked=False, i=idx: self.setCurrentIndex(i))
        self._menu.addAction(action)
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
        text = self._items[index][0]
        self.setText(text)
        self.setToolTip(text)
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(text)

    def setCurrentText(self, text: str):
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)


class LeftAlignedToolButton(QToolButton):
    """Кнопка инструмента с текстом слева и стрелкой меню справа."""

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        if self.objectName() in {"header_cell_tl", "header_cell_tr"}:
            option.state &= ~QStyle.StateFlag.State_MouseOver
        text = option.text
        option.text = ""

        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        text_rect = self.rect().adjusted(8, 0, -22, 0)
        painter.drawItemText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.palette(),
            self.isEnabled(),
            text,
            self.foregroundRole(),
        )


class FileListItemAdapter:
    def __init__(self, view, index: QModelIndex):
        self._view = view
        self._index = index

    def data(self, role):
        return self._view.model().data(self._index, role)


def selected_file_items(list_widget, *, files_only: bool = False) -> list:
    """Извлекает объекты файлов из выбранных строк любого совместимого списка."""
    if list_widget is None:
        return []
    result = []
    for item in list_widget.selectedItems():
        file_item = item.data(Qt.ItemDataRole.UserRole)
        if file_item is None:
            continue
        if files_only and not getattr(file_item, "is_file", False):
            continue
        result.append(file_item)
    return result


class FileListModel(QAbstractTableModel):
    COLUMN_OLD_NAME = 0
    COLUMN_NEW_NAME = 1
    COLUMN_TYPE = 2
    COLUMN_PATH = 3
    # Совместимость с кодом, которому нужна любая колонка для выбора строки.
    COLUMN_NAME = COLUMN_OLD_NAME
    HEADERS = ("Старое имя", "Новое имя", "Тип файла", "Исходная папка")

    # Хранит общий порядок файлов, чтобы выделение и перетаскивание не расходились с UI.
    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = []

    @staticmethod
    def _original_display_name(file_item) -> str:
        return file_item.name

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._files) if self._files else 1

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if not self._files:
            if role == Qt.ItemDataRole.DisplayRole:
                return ""
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return int(Qt.AlignmentFlag.AlignCenter)
            if role == Qt.ItemDataRole.ForegroundRole:
                return QColor(150, 150, 150)
            return None

        file_item = self._files[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == self.COLUMN_OLD_NAME:
                return self._original_display_name(file_item)
            if index.column() == self.COLUMN_NEW_NAME:
                return getattr(file_item, "preview_name", None) or self._original_display_name(
                    file_item
                )
            if index.column() == self.COLUMN_TYPE:
                return file_item_type_label(file_item)
            if index.column() == self.COLUMN_PATH:
                return file_item_source_folder(file_item)
        if role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == self.COLUMN_OLD_NAME:
                return self._original_display_name(file_item)
            if index.column() == self.COLUMN_NEW_NAME:
                return getattr(file_item, "preview_name", None) or self._original_display_name(
                    file_item
                )
            if index.column() == self.COLUMN_PATH:
                return str(getattr(file_item, "path", ""))
        if role == Qt.ItemDataRole.SizeHintRole:
            metrics = QFontMetrics(QApplication.font())
            text = self.data(index, Qt.ItemDataRole.DisplayRole) or ""
            width = metrics.horizontalAdvance(str(text)) + 12
            return QSize(width, metrics.height() + 8)
        if role == Qt.ItemDataRole.UserRole:
            return file_item
        return None

    def flags(self, index):
        if not self._files:
            return Qt.ItemFlag.ItemIsEnabled
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
        )

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def supportedDragActions(self):
        return Qt.DropAction.MoveAction

    def set_files(self, files: list):
        self.beginResetModel()
        self._files = list(files)
        self.endResetModel()

    def clear(self):
        self.set_files([])

    def files(self):
        return list(self._files)

    def moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
        if count <= 0:
            return False
        if sourceRow < 0 or (sourceRow + count) > len(self._files):
            return False
        if destinationChild < 0 or destinationChild > len(self._files):
            return False
        if destinationChild >= sourceRow and destinationChild <= sourceRow + count:
            return False

        self.beginMoveRows(
            sourceParent, sourceRow, sourceRow + count - 1, destinationParent, destinationChild
        )
        rows = self._files[sourceRow : sourceRow + count]
        del self._files[sourceRow : sourceRow + count]
        if destinationChild > sourceRow:
            destinationChild -= count
        for i, item in enumerate(rows):
            self._files.insert(destinationChild + i, item)
        self.endMoveRows()
        return True

    def refresh(self):
        if not self._files:
            return
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self._files) - 1, self.columnCount() - 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.SizeHintRole,
                Qt.ItemDataRole.ToolTipRole,
            ],
        )


class FileListItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, right_padding: int = 6):
        super().__init__(parent)
        self._right_padding = max(0, int(right_padding))

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(max(hint.height(), QFontMetrics(option.font).height() + 8))
        return hint

    def paint(self, painter, option, index):
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        available_width = max(0, view_option.rect.width() - 12 - self._right_padding)
        view_option.text = view_option.fontMetrics.elidedText(
            view_option.text,
            Qt.TextElideMode.ElideRight,
            available_width,
        )
        super().paint(painter, view_option, index)


class FileListWidget(QTableView):
    _COLUMN_RESIZE_PRECISION = 100

    filesDropped = pyqtSignal(list)
    emptyAreaClicked = pyqtSignal()
    itemDoubleClicked = pyqtSignal(object)
    itemSelectionChanged = pyqtSignal()
    orderChanged = pyqtSignal()
    deleteRequested = pyqtSignal()
    openRequested = pyqtSignal()
    copyRequested = pyqtSignal()
    renameRequested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setModel(FileListModel(self))
        self.setItemDelegate(FileListItemDelegate(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        header = self.horizontalHeader()
        header.setStyleSheet(FILE_LIST_HEADER_STYLE)
        header.setStretchLastSection(True)
        # Measuring every cell makes model resets noticeably expensive for large
        # batches.  A representative sample keeps automatic widths useful while
        # bounding the work done when filters replace the visible model.
        header.setResizeContentsPrecision(self._COLUMN_RESIZE_PRECISION)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        self.doubleClicked.connect(self._on_double_clicked)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _on_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        self.itemDoubleClicked.emit(FileListItemAdapter(self, index))

    def _on_selection_changed(self, _selected, _deselected):
        self.itemSelectionChanged.emit()

    def clear(self):
        self.model().clear()

    def selectedItems(self):
        return [
            FileListItemAdapter(self, index)
            for index in self.selectionModel().selectedRows(self.model().COLUMN_NAME)
        ]

    def selected_file_items(self, *, files_only: bool = False) -> list:
        """Возвращает объекты, связанные с выбранными строками таблицы."""
        return selected_file_items(self, files_only=files_only)

    def clearSelection(self):
        self.selectionModel().clearSelection()

    def set_files(self, files: list):
        self.model().set_files(files)
        self._resize_columns_to_contents()

    def refresh(self):
        self.model().refresh()

    def _resize_columns_to_contents(self):
        self.resizeColumnToContents(self.model().COLUMN_OLD_NAME)
        self.resizeColumnToContents(self.model().COLUMN_NEW_NAME)
        self.resizeColumnToContents(self.model().COLUMN_TYPE)

    def set_manual_sorting(self, enabled: bool):
        self.setDragEnabled(enabled)
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
            if enabled
            else QAbstractItemView.DragDropMode.DropOnly
        )
        if enabled:
            self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self.indexAt(event.position().toPoint()).isValid()
        ):
            self.emptyAreaClicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.deleteRequested.emit()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.openRequested.emit()
        elif event.key() == Qt.Key.Key_F2:
            self.renameRequested.emit()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copyRequested.emit()
        elif event.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def select_paths(self, paths: list):
        if not paths:
            return
        path_set = set(paths)
        for row in range(self.model().rowCount()):
            index = self.model().index(row, 0)
            file_item = self.model().data(index, Qt.ItemDataRole.UserRole)
            if file_item and getattr(file_item, "path", None) in path_set:
                self.selectionModel().select(
                    index,
                    QItemSelectionModel.SelectionFlag.Select
                    | QItemSelectionModel.SelectionFlag.Rows,
                )

    def dragEnterEvent(self, event):
        if event.source() == self and self.dragEnabled():
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            self.setStyleSheet(FILE_LIST_DRAG_ACTIVE_STYLE)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() == self and self.dragEnabled():
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        apply_standard_field_style(self)
        event.accept()

    def dropEvent(self, event):
        apply_standard_field_style(self)
        if event.source() == self and self.dragEnabled():
            super().dropEvent(event)
            self.orderChanged.emit()
            event.accept()
        elif event.mimeData().hasUrls():
            event.accept()
            paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.exists(file_path):
                    paths.append(file_path)
            if paths:
                self.filesDropped.emit(paths)
        else:
            event.ignore()


class DropActionTile(QFrame):
    clicked = pyqtSignal()

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

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(icon.pixmap(QSize(48, 48)))
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
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
            self.text_label.setStyleSheet(build_drop_action_tile_text_style(self._theme))


class LoggingStatusBar(QStatusBar):
    messageLogged = pyqtSignal(str)

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
