
from contextlib import contextmanager

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from app.ui.ui_components import setup_standard_form_label
from app.ui.ui_spacing import MARGINS_NONE, SPACE_NONE, SPACE_SM


@contextmanager
def signals_blocked(widget):
    if widget is None or not hasattr(widget, "blockSignals"):
        yield
        return
    previous = widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(previous)


def configure_layout(layout, *, margins=MARGINS_NONE, spacing=SPACE_NONE):
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def create_param_block(label_text: str, field: QWidget, *, spacing: int = SPACE_SM) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    configure_layout(layout, margins=MARGINS_NONE, spacing=spacing)

    label = QLabel(label_text)
    setup_standard_form_label(label)
    layout.addWidget(label)
    layout.addWidget(field)
    return container


def create_spin_param_block(label_text: str, spinbox: QSpinBox, *, spacing: int = SPACE_NONE) -> QWidget:
    spinbox.setProperty("renameTemplateField", True)

    field_container = QWidget()
    field_layout = QHBoxLayout(field_container)
    configure_layout(field_layout, margins=MARGINS_NONE, spacing=spacing)
    field_layout.addWidget(spinbox, 1)
    return create_param_block(label_text, field_container)
