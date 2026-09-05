import os

from PyQt6.QtCore import (
    QAbstractListModel,
    QEasingCurve,
    QItemSelectionModel,
    QModelIndex,
    QPointF,
    QRect,
    QPropertyAnimation,
    QSize,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFontMetrics,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
    QPolygonF,
    QTextOption,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QPushButton,
    QHBoxLayout,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyleOptionToolButton,
    QStylePainter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from app.ui.ui_spacing import (
    ACTION_BUTTON_HEIGHT,
    FIELD_HEIGHT,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    SPACE_NONE,
    SPACE_XS,
    SPACE_SM,
    SPACE_MD,
)
from app.ui.ui_styles import (
    MENU_STYLE_DARK,
    MENU_STYLE_LIGHT,
    build_standard_field_style,
)
from app.core.app_utils import _log_ignored_error
from app.ui.file_icons import FILE_ICON_SIZE, file_icon

_MENU_STYLE_LIGHT = MENU_STYLE_LIGHT
_MENU_STYLE_DARK = MENU_STYLE_DARK
_build_standard_field_style = build_standard_field_style


def _build_standard_button_style(theme: str, role: str) -> str:
    dark_theme = str(theme).lower() != "light"
    role = str(role or "secondary").lower()

    if role == "link":
        return """
            QPushButton {
                background-color: transparent;
                color: #d8e6ff;
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: rgba(61, 116, 179, 0.08);
            }
            QPushButton:pressed {
                background-color: rgba(61, 116, 179, 0.14);
            }
            QPushButton:disabled {
                background-color: transparent;
                color: rgba(216, 230, 255, 0.45);
            }
        """

    if dark_theme:
        palettes = {
            "primary": {
                "bg": "#3d74b3",
                "hover": "#4a82c2",
                "pressed": "#315f93",
                "border": "#4f89c9",
                "fg": "#ffffff",
                "disabled_bg": "#3a3a3a",
                "disabled_border": "#4a4a4a",
                "disabled_fg": "#8d8d8d",
            },
            "danger": {
                "bg": "#8f3b3b",
                "hover": "#a44646",
                "pressed": "#793232",
                "border": "#b85a5a",
                "fg": "#ffffff",
                "disabled_bg": "#3a3a3a",
                "disabled_border": "#4a4a4a",
                "disabled_fg": "#8d8d8d",
            },
            "section": {
                "bg": "#363636",
                "hover": "#404040",
                "pressed": "#2f2f2f",
                "border": "#4d4d4d",
                "fg": "#f2f2f2",
                "disabled_bg": "#303030",
                "disabled_border": "#404040",
                "disabled_fg": "#7f7f7f",
            },
            "secondary": {
                "bg": "#303030",
                "hover": "#3a3a3a",
                "pressed": "#2a2a2a",
                "border": "#474747",
                "fg": "#f1f1f1",
                "disabled_bg": "#292929",
                "disabled_border": "#3b3b3b",
                "disabled_fg": "#787878",
            },
        }
    else:
        palettes = {
            "primary": {
                "bg": "#3d74b3",
                "hover": "#4a82c2",
                "pressed": "#315f93",
                "border": "#3b6ea8",
                "fg": "#ffffff",
                "disabled_bg": "#eef2f7",
                "disabled_border": "#d7dee8",
                "disabled_fg": "#9aa4b2",
            },
            "danger": {
                "bg": "#c55353",
                "hover": "#d36161",
                "pressed": "#ab4747",
                "border": "#b94d4d",
                "fg": "#ffffff",
                "disabled_bg": "#eef2f7",
                "disabled_border": "#d7dee8",
                "disabled_fg": "#9aa4b2",
            },
            "section": {
                "bg": "#f3f5f8",
                "hover": "#e9edf3",
                "pressed": "#dde5ee",
                "border": "#d2dbe6",
                "fg": "#1f2933",
                "disabled_bg": "#f8fafc",
                "disabled_border": "#e4eaf2",
                "disabled_fg": "#9aa4b2",
            },
            "secondary": {
                "bg": "#f6f8fb",
                "hover": "#edf2f7",
                "pressed": "#e2eaf3",
                "border": "#d6dee8",
                "fg": "#243244",
                "disabled_bg": "#f8fafc",
                "disabled_border": "#e4eaf2",
                "disabled_fg": "#9aa4b2",
            },
        }

    colors = palettes.get(role, palettes["secondary"])
    return f"""
        QPushButton {{
            background-color: {colors['bg']};
            color: {colors['fg']};
            border: 1px solid {colors['border']};
            border-radius: 7px;
            padding: 2px 9px;
            font-weight: 500;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['border']};
        }}
        QPushButton:pressed {{
            background-color: {colors['pressed']};
            border-color: {colors['border']};
        }}
        QPushButton:disabled {{
            background-color: {colors['disabled_bg']};
            color: {colors['disabled_fg']};
            border: 1px solid {colors['disabled_border']};
        }}
    """




def apply_standard_field_style(widget):
    theme = _resolve_widget_theme_mode(widget)
    name = widget.objectName() if hasattr(widget, "objectName") else ""
    if isinstance(widget, MenuLikeComboBox):
        widget.setStyleSheet(_build_standard_field_style(theme, "menu"))
        widget._apply_popup_style()
        return widget
    if isinstance(widget, QComboBox):
        widget.setStyleSheet(_build_standard_field_style(theme, "combo"))
        try:
            view = QListView(widget)
            view.setSpacing(0)
            view.setUniformItemSizes(True)
            view.setItemDelegate(ComboPopupItemDelegate(widget))
            view.setStyleSheet(_MENU_STYLE_LIGHT if theme == "light" else _MENU_STYLE_DARK)
            widget.setView(view)
        except Exception as error:
            _log_ignored_error("apply_standard_field_style", error)
        return widget
    if isinstance(widget, QAbstractSpinBox):
        widget.setStyleSheet(_build_standard_field_style(theme, "spin"))
        return widget
    if isinstance(widget, QTextEdit):
        widget.setStyleSheet(_build_standard_field_style(theme, "textedit"))
        return widget
    if isinstance(widget, QLineEdit):
        if name == "header_cell_br":
            widget.setStyleSheet(_build_standard_field_style(theme, "header"))
            return widget
        widget.setStyleSheet(_build_standard_field_style(theme, "line"))
        return widget
    if isinstance(widget, QToolButton) and name in {"header_cell_tl", "header_cell_tr", "header_cell_bl"}:
        widget.setStyleSheet(_build_standard_field_style(theme, "header"))
        return widget
    if isinstance(widget, QAbstractItemView) and name == "files_list":
        widget.setStyleSheet(_build_standard_field_style(theme, "surface"))
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
            if widget.objectName() in {"header_cell_tl", "header_cell_tr", "header_cell_bl", "menu_like_combo"}:
                apply_standard_field_style(widget)
        for widget in root.findChildren(QAbstractItemView):
            if widget.objectName() == "files_list":
                apply_standard_field_style(widget)
    except Exception as error:
        _log_ignored_error("refresh_standard_field_styles", error)
    return root


def refresh_standard_surface_styles(root: QWidget):
    if root is None:
        return root
    try:
        for widget in root.findChildren(QAbstractItemView):
            if widget.objectName() == "files_list":
                apply_standard_field_style(widget)
    except Exception as error:
        _log_ignored_error("refresh_standard_surface_styles", error)
    return root


def refresh_standard_button_styles(root: QWidget):
    if root is None:
        return root
    try:
        for widget in root.findChildren(QPushButton):
            role = widget.property("buttonVariant")
            if not role:
                continue
            widget.setStyleSheet(_build_standard_button_style(_resolve_widget_theme_mode(widget), str(role)))
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
    header_fields = {"header_cell_tl", "header_cell_tr", "header_cell_bl"}
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


def setup_standard_action_button(widget, *, height: int = ACTION_BUTTON_HEIGHT, variant: str | None = None):
    role = variant or widget.property("buttonVariant") or "secondary"
    widget.setFixedHeight(height)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    widget.setProperty("buttonVariant", role)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if variant == "primary" and not widget.objectName():
        widget.setObjectName("convert_btn")
    elif variant == "danger" and not widget.objectName():
        widget.setObjectName("cancel_operation_btn")
    elif variant == "link" and not widget.objectName():
        widget.setObjectName("top_menu_link_btn")
    if variant == "link":
        widget.setFlat(True)
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setFlat(False)
    widget.setStyleSheet(_build_standard_button_style(_resolve_widget_theme_mode(widget), role))
    _refresh_widget_style(widget)
    return widget


def setup_standard_primary_button(widget, *, height: int = ACTION_BUTTON_HEIGHT):
    return setup_standard_action_button(widget, height=height, variant="primary")


def setup_standard_danger_button(widget, *, height: int = ACTION_BUTTON_HEIGHT):
    return setup_standard_action_button(widget, height=height, variant="danger")


def setup_standard_secondary_button(widget, *, height: int = ACTION_BUTTON_HEIGHT):
    return setup_standard_action_button(widget, height=height)


def setup_standard_section_button(widget, *, height: int = 34):
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return setup_standard_action_button(widget, height=height, variant="section")


def setup_standard_form_label(widget, *, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
    widget.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    widget.setWordWrap(True)
    widget.setFixedHeight(18)
    widget.setStyleSheet("font-size: 13px; margin: 0px; padding: 0px;")
    return widget


def setup_compact_checkbox(widget):
    widget.setStyleSheet(
        """
        QCheckBox {
            margin-top: 1px;
        }
        """
    )
    return widget


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
    buttons_layout.addStretch()

    ok_button = QPushButton("Сохранить")
    setup_standard_secondary_button(ok_button)
    cancel_button = QPushButton("Отмена")
    setup_standard_secondary_button(cancel_button)
    buttons_layout.addWidget(ok_button)
    buttons_layout.addWidget(cancel_button)
    layout.addWidget(buttons_row)

    ok_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    line_edit.selectAll()
    line_edit.setFocus()

    accepted = dialog.exec() == int(QDialog.DialogCode.Accepted)
    return line_edit.text(), accepted


def apply_standard_menu_style(menu: QMenu):
    theme = _resolve_widget_theme_mode(menu)
    menu.setStyleSheet(_MENU_STYLE_LIGHT if theme == "light" else _MENU_STYLE_DARK)
    return menu


def sync_standard_menu_width(menu: QMenu, anchor_widget: QWidget):
    if menu is None or anchor_widget is None:
        return
    apply_standard_menu_style(menu)
    width = anchor_widget.width()
    if width <= 0:
        width = anchor_widget.sizeHint().width()
    menu.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    menu.setMinimumWidth(width)
    menu.setMaximumWidth(width)
    menu.setFixedWidth(width)


class ExpandableGroupBox(QGroupBox):
    toggledExpanded = pyqtSignal(bool)

    def __init__(self, title="", parent=None):
        super().__init__("", parent)
        self.setCheckable(False)
        self._expanded = False
        self._title = title
        self.content_widget = None
        self.main_layout = None
        self.header_button = None
        self._is_animating = False
        self._content_animation = None
        self._animation_duration_ms = 180
        self._init_header()

    def _init_header(self):
        self.header_button = QPushButton(self._format_header_text())
        self.header_button.setObjectName("expand_header")
        self.header_button.setCheckable(True)
        self.header_button.setChecked(False)
        self.header_button.setIcon(self._build_disclosure_icon(pointing_down=False))
        self.header_button.setIconSize(QSize(10, 10))
        self.header_button.clicked.connect(self._toggle)
        setup_standard_section_button(self.header_button, height=34)

    def _format_header_text(self):
        return self._title

    def _build_disclosure_icon(self, pointing_down: bool) -> QIcon:
        pix = QPixmap(10, 10)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        theme = _resolve_widget_theme_mode(self)
        painter.setBrush(QColor("#1f2328" if theme == "light" else "#f0f0f0"))
        if pointing_down:
            triangle = QPolygonF([QPointF(2.0, 3.0), QPointF(8.0, 3.0), QPointF(5.0, 7.5)])
        else:
            triangle = QPolygonF([QPointF(3.0, 2.0), QPointF(7.5, 5.0), QPointF(3.0, 8.0)])
        painter.drawPolygon(triangle)
        painter.end()
        return QIcon(pix)

    def refresh_theme_icon(self):
        if self.header_button is None:
            return
        self.header_button.setIcon(self._build_disclosure_icon(pointing_down=self._expanded))
        self.header_button.update()

    def _toggle(self):
        self._set_expanded_state(self.header_button.isChecked(), animated=True)

    def setChecked(self, checked: bool):
        self._set_expanded_state(bool(checked), animated=False)

    def isExpanded(self) -> bool:
        return self._expanded

    def _apply_size_policy(self):
        if self._is_animating:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            return
        header_h = self.header_button.sizeHint().height()
        if self._expanded:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            if self.content_widget:
                self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            # В свёрнутом виде оставляем только заголовок, иначе layout сохраняет пустой зазор.
            self.setMinimumHeight(header_h)
            self.setMaximumHeight(header_h)
            self.resize(self.width(), header_h)
            if self.content_widget:
                self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setFixedContentHeight(self, height: int):
        self._fixed_content_height = max(0, int(height))
        if not self._expanded and self.content_widget:
            self.content_widget.setFixedHeight(0)
        elif self.content_widget:
            self.content_widget.setFixedHeight(self._fixed_content_height)
        self.updateGeometry()

    def sizeHint(self):
        if self._is_animating:
            return super().sizeHint()
        if not self._expanded:
            h = self.header_button.sizeHint().height()
            return QSize(0, h)
        return super().sizeHint()

    def minimumSizeHint(self):
        if self._is_animating:
            return super().minimumSizeHint()
        if not self._expanded:
            h = self.header_button.sizeHint().height()
            return QSize(0, h)
        return super().minimumSizeHint()

    def setContentLayout(self, layout):
        self.content_widget = QWidget()
        self.content_widget.setLayout(layout)
        self.content_widget.setVisible(self._expanded)
        self.content_widget.setMaximumHeight(0 if not self._expanded else 16777215)
        self.content_widget.setMinimumHeight(0)
        self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(*MARGINS_NONE)
        self.main_layout.setSpacing(SPACE_NONE)
        self.main_layout.addWidget(self.header_button)
        self.main_layout.addWidget(self.content_widget)
        self._content_animation = QPropertyAnimation(self.content_widget, b"maximumHeight", self)
        self._content_animation.setDuration(self._animation_duration_ms)
        self._content_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._content_animation.valueChanged.connect(lambda _v: self._refresh_parent_layouts())
        self._content_animation.finished.connect(self._on_content_animation_finished)
        # Фиксируем собранную высоту, чтобы дальнейшее изменение окна не растягивало группу.
        self._apply_size_policy()

    def _target_content_height(self) -> int:
        if not self.content_widget:
            return 0
        if hasattr(self, "_fixed_content_height"):
            return int(self._fixed_content_height)
        lay = self.content_widget.layout()
        if lay is not None:
            return max(0, int(lay.sizeHint().height()))
        return max(0, int(self.content_widget.sizeHint().height()))

    def _set_expanded_state(self, expanded: bool, animated: bool):
        self._expanded = bool(expanded)
        self.header_button.setChecked(self._expanded)
        self.header_button.setText(self._format_header_text())
        self.header_button.setIcon(self._build_disclosure_icon(pointing_down=self._expanded))

        if not self.content_widget:
            self.toggledExpanded.emit(self._expanded)
            self.updateGeometry()
            self._refresh_parent_layouts()
            return

        self.content_widget.setMinimumHeight(0)
        target_h = self._target_content_height() if self._expanded else 0

        if animated and self._content_animation is not None:
            self._is_animating = True
            self.content_widget.setVisible(True)
            # Перед анимацией снимаем ограничение, иначе высота не сможет плавно изменяться.
            self.content_widget.setMinimumHeight(0)
            self.content_widget.setMaximumHeight(16777215)
            self._apply_size_policy()
            try:
                self._content_animation.stop()
            except Exception as error:
                _log_ignored_error("ExpandableGroupBox._set_expanded_state", error)
            # Берём фактическую высоту: maximumHeight может содержать служебное значение 16777215.
            start_h = max(0, int(self.content_widget.height()))
            self._content_animation.setStartValue(start_h)
            self._content_animation.setEndValue(target_h)
            self._content_animation.start()
        else:
            self._is_animating = False
            self.content_widget.setVisible(self._expanded)
            if hasattr(self, "_fixed_content_height"):
                if self._expanded:
                    self.content_widget.setFixedHeight(int(self._fixed_content_height))
                else:
                    self.content_widget.setFixedHeight(0)
            else:
                self.content_widget.setMaximumHeight(16777215 if self._expanded else 0)
            self._apply_size_policy()
            self.updateGeometry()
            self._refresh_parent_layouts()

        self.toggledExpanded.emit(self._expanded)

    def _on_content_animation_finished(self):
        self._is_animating = False
        if not self.content_widget:
            return
        if self._expanded:
            if hasattr(self, "_fixed_content_height"):
                self.content_widget.setFixedHeight(int(self._fixed_content_height))
            else:
                self.content_widget.setMaximumHeight(16777215)
            self.content_widget.setVisible(True)
        else:
            if hasattr(self, "_fixed_content_height"):
                self.content_widget.setFixedHeight(0)
            else:
                self.content_widget.setMaximumHeight(0)
            self.content_widget.setVisible(False)
        self._apply_size_policy()
        self.updateGeometry()
        self._refresh_parent_layouts()

    def _refresh_parent_layouts(self):
        parent = self.parentWidget()
        while parent is not None:
            try:
                lay = parent.layout()
                if lay is not None:
                    lay.invalidate()
                    lay.activate()
                parent.updateGeometry()
            except Exception as error:
                _log_ignored_error("ExpandableGroupBox._refresh_parent_layouts", error)
            parent = parent.parentWidget()


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
        self._menu.setObjectName("menu_like_combo_popup")
        self._apply_popup_style()
        self._menu.aboutToShow.connect(self._sync_popup_width)
        self._menu.aboutToShow.connect(self._mark_menu_open)
        self._menu.aboutToHide.connect(self._mark_menu_closed)
        self.setMenu(self._menu)

    def _sync_popup_width(self):
        sync_standard_menu_width(self._menu, self)
        actions = self._menu.actions()
        if 0 <= self._current_index < len(actions):
            self._menu.setActiveAction(actions[self._current_index])

    def _apply_popup_style(self):
        apply_standard_menu_style(self._menu)

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
        if self.objectName() in {"header_cell_tl", "header_cell_tr", "header_cell_bl"}:
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

    def isSelected(self):
        return self._view.selectionModel().isSelected(self._index)

    def setSelected(self, selected: bool):
        if selected:
            self._view.selectionModel().select(self._index, QItemSelectionModel.SelectionFlag.Select)
        else:
            self._view.selectionModel().select(self._index, QItemSelectionModel.SelectionFlag.Deselect)


class FileListModel(QAbstractListModel):
    # Хранит общий порядок файлов, чтобы выделение и перетаскивание не расходились с UI.
    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = []


    @staticmethod
    def _full_display_name(file_item) -> str:
        display_name = file_item.name
        preview_name = getattr(file_item, "preview_name", None)
        if preview_name and preview_name != file_item.name:
            display_name = f"{file_item.name} -> {preview_name}"
        return display_name

    @staticmethod
    def _original_display_name(file_item) -> str:
        return file_item.name



    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._files) if self._files else 1

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
            return self._original_display_name(file_item)
        if role == Qt.ItemDataRole.DecorationRole:
            return file_icon(file_item)
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._full_display_name(file_item)
        if role == Qt.ItemDataRole.SizeHintRole:
            metrics = QFontMetrics(QApplication.font())
            width = metrics.horizontalAdvance(self._original_display_name(file_item)) + FILE_ICON_SIZE + 20
            return QSize(width, FILE_ICON_SIZE + 8)
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

    def append_files(self, files: list):
        if not files:
            return
        if not self._files:
            self.beginResetModel()
            self._files = list(files)
            self.endResetModel()
            return
        start = len(self._files)
        end = start + len(files) - 1
        self.beginInsertRows(QModelIndex(), start, end)
        self._files.extend(files)
        self.endInsertRows()

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

        self.beginMoveRows(sourceParent, sourceRow, sourceRow + count - 1, destinationParent, destinationChild)
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
        bottom_right = self.index(len(self._files) - 1, 0)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.SizeHintRole, Qt.ItemDataRole.ToolTipRole],
        )


class FileListItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, right_padding: int = 6):
        super().__init__(parent)
        self._right_padding = max(0, int(right_padding))

    @staticmethod
    def _view_width(view, fallback: int = 260) -> int:
        if view is None:
            return fallback
        try:
            widget = view.viewport() if hasattr(view, "viewport") else view
            width = widget.width()
        except Exception:
            width = fallback
        return max(fallback, int(width))

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        file_item = index.data(Qt.ItemDataRole.UserRole)
        preview_name = getattr(file_item, "preview_name", None) if file_item else None
        view = option.widget
        if file_item:
            metrics = QFontMetrics(option.font)
            text = str(preview_name or file_item.name)
            available_width = self._view_width(view, hint.width())
            icon_width = FILE_ICON_SIZE
            text_width = max(40, available_width - icon_width - 20 - self._right_padding)
            text_rect = metrics.boundingRect(
                QRect(0, 0, text_width, 10000),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                text,
            )
            width = 6 + icon_width + 8 + text_rect.width() + 6 + self._right_padding
            height = max(icon_width, metrics.height(), text_rect.height()) + 8
            hint.setWidth(max(hint.width(), width))
            hint.setHeight(max(hint.height(), height))
        return hint

    def paint(self, painter, option, index):
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        file_item = index.data(Qt.ItemDataRole.UserRole)
        preview_name = getattr(file_item, "preview_name", None) if file_item else None
        view = view_option.widget
        if file_item:
            painter.save()
            base_color = view_option.palette.color(QPalette.ColorRole.Base)
            alt_color = view_option.palette.color(QPalette.ColorRole.AlternateBase)
            if base_color == alt_color:
                if base_color.lightness() < 128:
                    alt_color = base_color.lighter(124)
                else:
                    alt_color = base_color.darker(118)
            background = alt_color if (index.row() % 2) else base_color
            if view_option.state & QStyle.StateFlag.State_Selected:
                if base_color.lightness() < 128:
                    background = QColor(255, 255, 255, 46)
                else:
                    background = QColor(61, 116, 179, 56)
            if view_option.state & QStyle.StateFlag.State_MouseOver:
                if base_color.lightness() < 128:
                    background = QColor(255, 255, 255, 18)
                else:
                    background = QColor(61, 116, 179, 26)
            text_color = view_option.palette.color(QPalette.ColorRole.Text)

            painter.fillRect(view_option.rect, background)

            painter.setFont(view_option.font)
            metrics = painter.fontMetrics()
            left_padding = 6
            top_padding = 2
            text = str(preview_name or file_item.name)
            icon_width = FILE_ICON_SIZE
            available_width = self._view_width(view, view_option.rect.width())
            text_width = max(40, available_width - icon_width - 20 - self._right_padding)
            text_rect_size = metrics.boundingRect(
                QRect(0, 0, text_width, 10000),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                text,
            )

            x = view_option.rect.x() + left_padding
            y = view_option.rect.y() + top_padding
            h = max(view_option.rect.height() - top_padding * 2, metrics.height())

            icon_rect = QRect(x, y + (h - icon_width) // 2, icon_width, icon_width)
            text_rect = QRect(x + icon_width + 8, y, text_rect_size.width(), max(h, text_rect_size.height()))

            painter.setPen(text_color)
            painter.setFont(view_option.font)
            file_icon(file_item).paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap),
                text,
            )
            painter.restore()
            return
        super().paint(painter, view_option, index)


class FileListWidget(QListView):
    filesDropped = pyqtSignal(list)
    emptyAreaClicked = pyqtSignal()
    itemDoubleClicked = pyqtSignal(object)
    itemSelectionChanged = pyqtSignal()
    orderChanged = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setModel(FileListModel(self))
        self.setItemDelegate(FileListItemDelegate(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionRectVisible(True)
        self.setAlternatingRowColors(True)
        self.setWordWrap(True)
        self.setUniformItemSizes(False)
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
        self._drag_rows = None

        self.doubleClicked.connect(self._on_double_clicked)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _on_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        self.itemDoubleClicked.emit(FileListItemAdapter(self, index))

    def _on_selection_changed(self, selected, deselected):
        self.itemSelectionChanged.emit()

    def count(self):
        return self.model().rowCount()

    def clear(self):
        self.model().clear()

    def item(self, row: int):
        index = self.model().index(row, 0)
        if not index.isValid():
            return None
        return FileListItemAdapter(self, index)

    def selectedItems(self):
        items = []
        for index in self.selectionModel().selectedIndexes():
            items.append(FileListItemAdapter(self, index))
        return items

    def clearSelection(self):
        self.selectionModel().clearSelection()

    def set_files(self, files: list):
        self.model().set_files(files)

    def add_files(self, files: list):
        self.model().append_files(files)

    def refresh(self):
        self.model().refresh()

    def set_manual_sorting(self, enabled: bool):
        self.setDragEnabled(enabled)
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove if enabled else QAbstractItemView.DragDropMode.DropOnly
        )
        if enabled:
            self.setDefaultDropAction(Qt.DropAction.MoveAction)
        else:
            self._drag_rows = None

    def startDrag(self, supported_actions):
        if not self.dragEnabled():
            return
        super().startDrag(supported_actions)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.indexAt(event.position().toPoint()).isValid():
            self.emptyAreaClicked.emit()
        super().mousePressEvent(event)

    def select_paths(self, paths: list):
        if not paths:
            return
        path_set = set(paths)
        for row in range(self.model().rowCount()):
            index = self.model().index(row, 0)
            file_item = self.model().data(index, Qt.ItemDataRole.UserRole)
            if file_item and getattr(file_item, "path", None) in path_set:
                self.selectionModel().select(index, QItemSelectionModel.SelectionFlag.Select)

    def dragEnterEvent(self, event):
        if event.source() == self and self.dragEnabled():
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            self.setStyleSheet(
                """
                QListView {
                    border: 2px dashed #3d74b3;
                }
                """
            )
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


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class DropActionTile(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon: QIcon, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("drop_action_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(144, 132)
        self._theme = "dark"
        self._apply_theme_style()

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
        self.text_label.setStyleSheet('font-family: "Segoe UI"; font-size: 12px; font-weight: 600;')
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)

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
        if self._theme == "light":
            self.setStyleSheet(
                "QFrame#drop_action_tile {"
                "background-color: transparent;"
                "border: 2px dashed rgba(90, 100, 110, 170);"
                "border-radius: 12px;"
                "}"
                "QFrame#drop_action_tile:hover {"
                "border-color: rgba(61,116,179,220);"
                "background-color: rgba(61,116,179,18);"
                "}"
            )
            if hasattr(self, "text_label"):
                self.text_label.setStyleSheet(
                    'font-family: "Segoe UI"; font-size: 12px; font-weight: 600; color: #1f2328;'
                )
        else:
            self.setStyleSheet(
                "QFrame#drop_action_tile {"
                "background-color: transparent;"
                "border: 2px dashed rgba(255,255,255,120);"
                "border-radius: 12px;"
                "}"
                "QFrame#drop_action_tile:hover {"
                "border-color: rgba(255,255,255,210);"
                "background-color: rgba(255,255,255,24);"
                "}"
            )
            if hasattr(self, "text_label"):
                self.text_label.setStyleSheet(
                    'font-family: "Segoe UI"; font-size: 12px; font-weight: 600; color: #f0f0f0;'
                )


class LoggingStatusBar(QStatusBar):
    messageLogged = pyqtSignal(str)

    def showMessage(self, text: str, timeout: int = 0):
        super().showMessage(text, timeout)
        if text:
            self.messageLogged.emit(text)


__all__ = [
    "ClickableLabel",
    "DropActionTile",
    "ExpandableGroupBox",
    "FileListItemAdapter",
    "FileListModel",
    "FileListWidget",
    "LoggingStatusBar",
]
