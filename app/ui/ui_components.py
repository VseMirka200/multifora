# -*- coding: utf-8 -*-
import os

from PyQt6.QtCore import (
    QAbstractListModel,
    QEasingCurve,
    QItemSelectionModel,
    QModelIndex,
    QPointF,
    QRect,
    QRectF,
    QPropertyAnimation,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QFont, QFontMetrics, QIcon, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

_MENU_STYLE_LIGHT = """
    QMenu {
        background-color: #f2f4f7;
        color: #1f2328;
        border: 1px solid #c7cfda;
        margin: 0px;
        padding: 0px;
        border-radius: 0px;
    }
    QMenu::item {
        padding: 4px 8px;
        background-color: transparent;
    }
    QMenu::item:selected {
        background-color: #3d74b3;
        color: #ffffff;
    }
    QMenu::separator {
        height: 1px;
        background: rgba(0, 0, 0, 0.2);
    }
"""

_MENU_STYLE_DARK = """
    QMenu {
        background-color: #343840;
        color: #f0f0f0;
        border: 1px solid rgba(255, 255, 255, 0.55);
        margin: 0px;
        padding: 0px;
        border-radius: 0px;
    }
    QMenu::item {
        padding: 4px 8px;
        background-color: transparent;
    }
    QMenu::item:selected {
        background-color: #2f79c6;
        color: #ffffff;
    }
    QMenu::separator {
        height: 1px;
        background: rgba(255, 255, 255, 0.25);
    }
"""


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
    except Exception:
        pass
    return "dark"


def _refresh_widget_style(widget: QWidget) -> None:
    """Переприменяет QSS к виджету после изменения variant/objectName."""
    try:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
    except Exception:
        pass


class ComboPopupItemDelegate(QStyledItemDelegate):
    def __init__(self, combo: QComboBox):
        super().__init__(combo)
        self._combo = combo

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(max(22, self._combo.height()))
        return hint


def setup_standard_dropdown(widget, *, fixed_width: int | None = None):
    widget.setFixedHeight(24)
    widget.setMinimumWidth(0)
    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    if isinstance(widget, MenuLikeComboBox):
        widget._apply_popup_style()
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
    except Exception:
        pass

    widget.setStyleSheet("QComboBox { text-align: left; }")

    try:
        view = QListView(widget)
        view.setSpacing(0)
        view.setUniformItemSizes(True)
        view.setItemDelegate(ComboPopupItemDelegate(widget))
        theme = _resolve_widget_theme_mode(widget)
        if theme == "light":
            popup_style = """
                QListView {
                    background-color: #ffffff;
                    color: #1f2328;
                    border: 1px solid #c7cfda;
                    border-radius: 0px;
                    outline: 0px;
                }
                QListView::item {
                    padding: 0px 10px;
                    margin: 0px;
                    background-color: transparent;
                    color: #1f2328;
                }
                QListView::item:selected {
                    background-color: #3d74b3;
                    color: #ffffff;
                }
            """
        else:
            popup_style = """
                QListView {
                    background-color: #343840;
                    color: #f0f0f0;
                    border: 1px solid rgba(255, 255, 255, 0.55);
                    border-radius: 0px;
                    outline: 0px;
                }
                QListView::item {
                    padding: 0px 10px;
                    margin: 0px;
                    background-color: transparent;
                    color: #f0f0f0;
                }
                QListView::item:selected {
                    background-color: #2f79c6;
                    color: #ffffff;
                }
            """
        view.setStyleSheet(popup_style)
        widget.setView(view)
    except Exception:
        pass

    return widget


def setup_standard_line_input(widget, *, fixed_width: int | None = None):
    widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
    widget.setFixedHeight(24)
    widget.setMinimumWidth(0)
    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return widget


def setup_standard_spin_input(widget, *, fixed_width: int | None = None):
    widget.setFixedHeight(24)
    widget.setMinimumWidth(0)
    try:
        line_edit = widget.lineEdit()
        if line_edit is not None:
            line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
    except Exception:
        pass
    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    else:
        widget.setMaximumWidth(16777215)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return widget


def setup_standard_header_dropdown(widget):
    widget.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    widget.setFixedHeight(24)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    try:
        widget._effective_theme_mode = _resolve_widget_theme_mode(widget)
    except Exception:
        pass
    return widget


def setup_standard_action_button(widget, *, height: int = 24, variant: str | None = None):
    role = variant or "secondary"
    widget.setFixedHeight(height)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    widget.setProperty("buttonVariant", role)
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
    _refresh_widget_style(widget)
    return widget


def setup_standard_primary_button(widget, *, height: int = 24):
    return setup_standard_action_button(widget, height=height, variant="primary")


def setup_standard_danger_button(widget, *, height: int = 24):
    return setup_standard_action_button(widget, height=height, variant="danger")


def setup_standard_secondary_button(widget, *, height: int = 24):
    return setup_standard_action_button(widget, height=height)


def setup_standard_link_button(widget, *, height: int = 22):
    return setup_standard_action_button(widget, height=height, variant="link")


def setup_standard_section_button(widget, *, height: int = 34):
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return setup_standard_action_button(widget, height=height, variant="section")


def build_bookmark_icon(*, size: int = 16, theme: str = "dark") -> QIcon:
    """Creates a compact bookmark icon for saved items."""
    dark_theme = str(theme).lower() != "light"
    fill_color = QColor("#f1c44d" if dark_theme else "#d99a00")
    outline_color = QColor("#f8e7ad" if dark_theme else "#8a5f00")
    notch_color = QColor("#ffffff" if dark_theme else "#f8fbff")

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(outline_color, 1.2))
    painter.setBrush(fill_color)

    left = 3.0
    top = 2.0
    right = float(size - 3)
    bottom = float(size - 2)
    notch_x = float(size / 2)
    notch_y = float(size - 5)
    bookmark_shape = QPolygonF(
        [
            QPointF(left, top),
            QPointF(right, top),
            QPointF(right, bottom),
            QPointF(notch_x, notch_y),
            QPointF(left, bottom),
        ]
    )
    painter.drawPolygon(bookmark_shape)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(notch_color)
    notch_width = max(2.0, size * 0.14)
    painter.drawRect(int(notch_x - notch_width / 2), int(notch_y), int(notch_width), int(size - notch_y))
    painter.end()
    return QIcon(pix)


def setup_standard_form_label(widget, *, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
    widget.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    widget.setWordWrap(True)
    widget.setFixedHeight(18)
    widget.setStyleSheet("font-size: 13px; margin: 0px; padding: 0px;")
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
    except Exception:
        pass
    setup_standard_dialog(dialog, title=title, min_width=380)
    try:
        dialog.setStyleSheet(parent.styleSheet())
    except Exception:
        pass

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(10, 6, 10, 6)
    layout.setSpacing(4)

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
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(4)
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
        painter.setBrush(QColor("#ffffff"))
        if pointing_down:
            triangle = QPolygonF([QPointF(2.0, 3.0), QPointF(8.0, 3.0), QPointF(5.0, 7.5)])
        else:
            triangle = QPolygonF([QPointF(3.0, 2.0), QPointF(7.5, 5.0), QPointF(3.0, 8.0)])
        painter.drawPolygon(triangle)
        painter.end()
        return QIcon(pix)

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
            # Р–РµСЃС‚РєРѕ СЃС…Р»РѕРїС‹РІР°РµРј РіСЂСѓРїРїСѓ РґРѕ РІС‹СЃРѕС‚С‹ Р·Р°РіРѕР»РѕРІРєР°, С‡С‚РѕР±С‹ РЅРµ РѕСЃС‚Р°РІР°Р»РѕСЃСЊ РїСѓСЃС‚С‹С… Р·РѕРЅ.
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
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.header_button)
        self.main_layout.addWidget(self.content_widget)
        self._content_animation = QPropertyAnimation(self.content_widget, b"maximumHeight", self)
        self._content_animation.setDuration(self._animation_duration_ms)
        self._content_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._content_animation.valueChanged.connect(lambda _v: self._refresh_parent_layouts())
        self._content_animation.finished.connect(self._on_content_animation_finished)
        # Р¤РёРєСЃРёСЂСѓРµРј РєРѕСЂСЂРµРєС‚РЅСѓСЋ РІС‹СЃРѕС‚Сѓ СЃСЂР°Р·Сѓ РїРѕСЃР»Рµ СЃР±РѕСЂРєРё РІРёРґР¶РµС‚Р°,
        # С‡С‚РѕР±С‹ РїСЂРё РїРµСЂРІРѕРј/РїРѕСЃР»РµРґСѓСЋС‰РµРј СЂРµСЃР°Р№Р·Рµ РЅРµ РїРѕСЏРІР»СЏР»РёСЃСЊ РїСѓСЃС‚С‹Рµ Р·РѕРЅС‹.
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
            # Clear any previously forced height so animation can interpolate smoothly.
            self.content_widget.setMinimumHeight(0)
            self.content_widget.setMaximumHeight(16777215)
            self._apply_size_policy()
            try:
                self._content_animation.stop()
            except Exception:
                pass
            # Use current rendered height as animation start; maximumHeight can be 16777215.
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
            except Exception:
                pass
            parent = parent.parentWidget()


class ToggleSwitch(QCheckBox):
    """Checkbox rendered as an on/off switch with a sliding thumb."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._track_w = 36
        self._track_h = 18
        self._thumb_r = 7
        self._gap = 10
        self.setMinimumHeight(24)

    def sizeHint(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self.text())
        text_h = fm.height()
        w = self._track_w + self._gap + text_w + 8
        h = max(self._track_h, text_h) + 6
        return QSize(w, h)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        track_x = 0
        track_y = (self.height() - self._track_h) // 2
        track_rect = QRectF(track_x, track_y, self._track_w, self._track_h)

        theme = self._resolve_theme_mode()

        if not self.isEnabled():
            track_color = QColor("#555d64")
            thumb_color = QColor("#c8cdd1")
            text_color = QColor("#8ea1ab") if theme != "light" else QColor("#8b949e")
        elif self.isChecked():
            track_color = QColor("#2c8f73")
            thumb_color = QColor("#ffffff")
            text_color = QColor("#e0e0e0") if theme != "light" else QColor("#1f2328")
        else:
            if theme == "light":
                track_color = QColor("#8b949e")
                thumb_color = QColor("#ffffff")
                text_color = QColor("#1f2328")
            else:
                track_color = QColor("#626b73")
                thumb_color = QColor("#f0f0f0")
                text_color = QColor("#e0e0e0")

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(track_rect, self._track_h / 2, self._track_h / 2)

        if self.isChecked():
            thumb_cx = track_x + self._track_w - 9
        else:
            thumb_cx = track_x + 9
        thumb_cy = track_y + self._track_h / 2
        p.setBrush(thumb_color)
        p.drawEllipse(QPointF(thumb_cx, thumb_cy), self._thumb_r, self._thumb_r)

        text_rect = QRect(self._track_w + self._gap, 0, max(0, self.width() - self._track_w - self._gap), self.height())
        p.setPen(text_color)
        p.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.text())

    def _resolve_theme_mode(self) -> str:
        return _resolve_widget_theme_mode(self)


class MenuLikeComboBox(QToolButton):
    """Single-select dropdown with QMenu backend and QComboBox-like API."""

    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("menu_like_combo")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._items = []
        self._current_index = -1
        self._menu = QMenu(self)
        self._menu.setObjectName("menu_like_combo_popup")
        self._apply_popup_style()
        self._menu.aboutToShow.connect(self._sync_popup_width)
        self.setMenu(self._menu)

    def _sync_popup_width(self):
        sync_standard_menu_width(self._menu, self)
        actions = self._menu.actions()
        if 0 <= self._current_index < len(actions):
            self._menu.setActiveAction(actions[self._current_index])

    def _apply_popup_style(self):
        apply_standard_menu_style(self._menu)

    def _resolve_theme_mode(self) -> str:
        return _resolve_widget_theme_mode(self)

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""

        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        text_rect = self.rect().adjusted(0, 0, -18, 0)
        painter.drawItemText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.palette(),
            self.isEnabled(),
            text,
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
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(text)

    def setCurrentText(self, text: str):
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)


class LeftAlignedToolButton(QToolButton):
    """ToolButton that always paints text left-aligned (keeps menu arrow on the right)."""

    def paintEvent(self, event):
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = []

    @staticmethod
    def _truncate_to_half(text: str) -> str:
        text = str(text or "")
        if len(text) <= 40:
            return text
        keep = max(20, len(text) // 2)
        return f"{text[:keep]}…"

    @staticmethod
    def _full_display_name(file_item) -> str:
        display_name = file_item.name
        preview_name = getattr(file_item, "preview_name", None)
        if preview_name and preview_name != file_item.name:
            display_name = f"{file_item.name} -> {preview_name}"
        return f"{file_item.get_icon()} {display_name}"

    @classmethod
    def _short_display_name(cls, file_item) -> str:
        display_name = file_item.name
        preview_name = getattr(file_item, "preview_name", None)
        if preview_name and preview_name != file_item.name:
            display_name = f"{file_item.name} -> {preview_name}"
        return f"{file_item.get_icon()} {cls._truncate_to_half(display_name)}"

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
            return self._short_display_name(file_item)
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._full_display_name(file_item)
        if role == Qt.ItemDataRole.SizeHintRole:
            metrics = QFontMetrics(QApplication.font())
            width = metrics.horizontalAdvance(self._short_display_name(file_item)) + 20
            return QSize(width, 24)
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

    def move_rows(self, rows: list[int], target_row: int):
        if not self._files or not rows:
            return
        rows = sorted(set(rows))
        if target_row < 0:
            target_row = len(self._files)

        items = [self._files[i] for i in rows if 0 <= i < len(self._files)]
        if not items:
            return
        remaining = [f for i, f in enumerate(self._files) if i not in rows]

        removed_before = sum(1 for r in rows if r < target_row)
        target_row -= removed_before
        if target_row < 0:
            target_row = 0
        if target_row > len(remaining):
            target_row = len(remaining)

        new_files = remaining[:target_row] + items + remaining[target_row:]
        self.set_files(new_files)

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
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])


class FileListItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, right_padding: int = 6):
        super().__init__(parent)
        self._right_padding = max(0, int(right_padding))

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        file_item = index.data(Qt.ItemDataRole.UserRole)
        preview_name = getattr(file_item, "preview_name", None) if file_item else None
        if file_item and preview_name and preview_name != file_item.name:
            metrics = QFontMetrics(option.font)
            icon_text = f"{file_item.get_icon()} "
            old_width, new_width = self._rename_preview_text_widths(index, metrics)
            width = (
                6
                + metrics.horizontalAdvance(icon_text)
                + old_width
                + 8
                + metrics.horizontalAdvance("->")
                + 8
                + new_width
                + 6
            )
            hint.setWidth(max(hint.width(), width))
            hint.setHeight(max(hint.height(), 24))
        return hint

    def _rename_preview_text_widths(self, index, font_metrics: QFontMetrics | None = None) -> tuple[int, int]:
        model = index.model()
        if model is None:
            return 0, 0
        if font_metrics is None:
            font_metrics = QFontMetrics(QApplication.font())

        max_old_width = 0
        max_new_width = 0
        try:
            row_count = model.rowCount()
        except Exception:
            row_count = 0
        for row in range(row_count):
            row_index = model.index(row, 0)
            file_item = row_index.data(Qt.ItemDataRole.UserRole)
            if not file_item:
                continue
            preview_name = getattr(file_item, "preview_name", None)
            if not preview_name or preview_name == file_item.name:
                continue
            max_old_width = max(max_old_width, font_metrics.horizontalAdvance(str(file_item.name)))
            max_new_width = max(max_new_width, font_metrics.horizontalAdvance(str(preview_name)))
        return max_old_width, max_new_width

    def paint(self, painter, option, index):
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        file_item = index.data(Qt.ItemDataRole.UserRole)
        preview_name = getattr(file_item, "preview_name", None) if file_item else None
        if file_item and preview_name and preview_name != file_item.name:
            painter.save()
            if view_option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(view_option.rect, QColor("#9fc5f8"))
                text_color = QColor("#1f2328")
            else:
                text_color = view_option.palette.color(QPalette.ColorRole.Text)

            metrics = painter.fontMetrics()
            left_padding = 6
            right_padding = self._right_padding
            spacing = 8
            arrow_text = "->"
            icon_text = f"{file_item.get_icon()} "

            icon_width = metrics.horizontalAdvance(icon_text)
            arrow_width = metrics.horizontalAdvance(arrow_text)
            old_width, new_width = self._rename_preview_text_widths(index, metrics)

            x = view_option.rect.x() + left_padding
            y = view_option.rect.y()
            h = view_option.rect.height()

            icon_rect = QRect(x, y, icon_width, h)
            x += icon_width

            old_rect = QRect(x, y, old_width, h)
            x += old_width + spacing

            arrow_rect = QRect(x, y, arrow_width, h)
            x += arrow_width + spacing

            new_rect = QRect(x, y, new_width, h)

            painter.setPen(text_color)
            painter.setFont(view_option.font)
            painter.drawText(icon_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), icon_text)
            painter.drawText(
                old_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                str(file_item.name),
            )
            painter.drawText(
                arrow_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                arrow_text,
            )
            painter.drawText(
                new_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                str(preview_name),
            )
            painter.restore()
            return
        if view_option.state & QStyle.StateFlag.State_Selected:
            painter.save()
            painter.fillRect(view_option.rect, QColor("#9fc5f8"))
            text_rect = view_option.rect.adjusted(6, 0, -self._right_padding, 0)
            painter.setPen(QColor("#1f2328"))
            painter.setFont(view_option.font)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                index.data(Qt.ItemDataRole.DisplayRole) or "",
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setUniformItemSizes(True)
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
                    border: 2px dashed #4fc3f7;
                    background-color: rgba(79, 195, 247, 0.1);
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
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet("")
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


class LoggingStatusBar(QStatusBar):
    messageLogged = pyqtSignal(str)

    def showMessage(self, text: str, timeout: int = 0):
        super().showMessage(text, timeout)
        if text:
            self.messageLogged.emit(text)


__all__ = [
    "ClickableLabel",
    "ExpandableGroupBox",
    "FileListItemAdapter",
    "FileListModel",
    "FileListWidget",
    "LoggingStatusBar",
]



