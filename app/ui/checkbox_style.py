"""Единая отрисовка галочек в полях, списках, таблицах и меню."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QProxyStyle, QStyle

from app.ui.ui_spacing import CHECKBOX_SIZE


def paint_checkbox(painter, option):
    enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
    checked = bool(option.state & QStyle.StateFlag.State_On)
    partial = bool(option.state & QStyle.StateFlag.State_NoChange)
    hovered = enabled and bool(option.state & QStyle.StateFlag.State_MouseOver)
    group = QPalette.ColorGroup.Active if enabled else QPalette.ColorGroup.Disabled
    border = option.palette.color(group, QPalette.ColorRole.Text)
    border.setAlpha(130)
    accent = QColor("#3d74b3") if enabled else border
    center = QRectF(option.rect).center()
    box = QRectF(
        center.x() - CHECKBOX_SIZE / 2,
        center.y() - CHECKBOX_SIZE / 2,
        CHECKBOX_SIZE,
        CHECKBOX_SIZE,
    )
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(accent if checked or partial or hovered else border, 1.2))
    painter.setBrush(accent if checked or partial else QColor(0, 0, 0, 0))
    painter.drawRoundedRect(box, 4, 4)
    if checked or partial:
        tick = QPainterPath()
        if partial:
            tick.moveTo(box.left() + 4, box.top() + 8)
            tick.lineTo(box.left() + 12, box.top() + 8)
        else:
            tick.moveTo(box.left() + 4, box.top() + 8)
            tick.lineTo(box.left() + 7, box.top() + 11)
            tick.lineTo(box.left() + 12, box.top() + 5)
        painter.setPen(QPen(QColor("white"), 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(tick)
    painter.restore()


class CheckboxStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element in (
            QStyle.PrimitiveElement.PE_IndicatorCheckBox,
            QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck,
            QStyle.PrimitiveElement.PE_IndicatorMenuCheckMark,
        ):
            paint_checkbox(painter, option)
            return
        super().drawPrimitive(element, option, painter, widget)

    def pixelMetric(self, metric, option=None, widget=None):
        if metric in (
            QStyle.PixelMetric.PM_IndicatorWidth,
            QStyle.PixelMetric.PM_IndicatorHeight,
        ):
            # Дополнительные пиксели оставляют место для сглаженной границы.
            return CHECKBOX_SIZE + 2
        return super().pixelMetric(metric, option, widget)


def install_checkbox_style(app):
    """Устанавливается один раз; смена QSS-темы сохраняет общую отрисовку."""
    if not getattr(app, "_checkbox_style_installed", False):
        app.setStyle(CheckboxStyle())
        app._checkbox_style_installed = True
