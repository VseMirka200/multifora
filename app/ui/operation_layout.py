"""Разметка карточек и подписей на страницах операций."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.ui.ui_components import setup_standard_form_label
from app.ui.ui_styles import MARGINS_NONE, SPACE_NONE, SPACE_SM


def create_operation_card(
    *,
    margins: tuple[int, int, int, int] = MARGINS_NONE,
    align_top: bool = False,
) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("card")
    card.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(*margins)
    card_layout.setSpacing(SPACE_NONE)
    if align_top:
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    content = QWidget()
    content.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    content_layout = QVBoxLayout(content)
    content_layout.setSpacing(SPACE_NONE)
    content_layout.setContentsMargins(*MARGINS_NONE)
    if align_top:
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        card_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignTop)
    else:
        card_layout.addWidget(content)

    return card, content_layout


def create_operation_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("tab_section_label")
    setup_standard_form_label(label)
    label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    return label


def add_labeled_field(layout: QBoxLayout, label_text: str, field: QWidget) -> None:
    field_layout = QVBoxLayout()
    field_layout.setContentsMargins(*MARGINS_NONE)
    field_layout.setSpacing(SPACE_SM)
    label = create_operation_label(label_text)
    label.setBuddy(field)
    field.setAccessibleName(label_text.rstrip(":"))
    field_layout.addWidget(label)
    field_layout.addWidget(field)
    layout.addLayout(field_layout)
