# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from app.ui.ui_components import (
    AutoHeightTextEdit,
    MenuLikeComboBox,
    setup_standard_action_button,
    setup_standard_dropdown,
    setup_standard_form_label,
    setup_standard_line_input,
    setup_standard_spin_input,
)
from app.ui.ui_spacing import (
    MARGINS_NONE,
    SPACE_NONE,
    SPACE_SM,
)


class TemplateParamsNumberingMixin:
    def _numbering_mode_items(self):
        return [
            "Простая нумерация",
            "Нумерация с префиксом",
            "Нумерация с датой",
        ]

    def _normalize_numbering_mode(self, value: str) -> str:
        text = str(value or "").strip()
        if text in self._numbering_mode_items():
            return text
        if text == "Простая нумерация":
            return "Простая нумерация"
        if text == "Нумерация с префиксом":
            return "Нумерация с префиксом"
        if text == "Нумерация с датой":
            return "Нумерация с датой"
        return "Простая нумерация"

    def _set_numbering_mode_visibility(self, mode_text: str | None = None):
        mode = self._normalize_numbering_mode(mode_text or getattr(getattr(self, "template_numbering_mode", None), "currentText", lambda: "")())
        simple_visible = mode == "Простая нумерация"
        prefix_visible = mode == "Нумерация с префиксом"
        date_visible = mode == "Нумерация с датой"

        for widget in (
            getattr(self, "template_num_simple_widget", None),
            getattr(self, "template_num_prefix_widget", None),
            getattr(self, "template_num_date_widget", None),
        ):
            if widget is not None:
                widget.setVisible(False)

        if simple_visible and getattr(self, "template_num_simple_widget", None) is not None:
            self.template_num_simple_widget.setVisible(True)
        elif prefix_visible and getattr(self, "template_num_prefix_widget", None) is not None:
            self.template_num_prefix_widget.setVisible(True)
        elif date_visible and getattr(self, "template_num_date_widget", None) is not None:
            self.template_num_date_widget.setVisible(True)

    def _on_numbering_mode_changed(self, _index=None):
        self._set_numbering_mode_visibility()
        if callable(getattr(self, "refresh_rename_preview", None)):
            self.refresh_rename_preview()
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()

    def get_numbering_mode(self) -> str:
        combo = getattr(self, "template_numbering_mode", None)
        if combo is None:
            return "Простая нумерация"
        return self._normalize_numbering_mode(combo.currentText())

    def set_numbering_mode(self, mode_text: str):
        combo = getattr(self, "template_numbering_mode", None)
        if combo is None:
            return
        target = self._normalize_numbering_mode(mode_text)
        index = combo.findText(target)
        if index >= 0:
            was_blocked = combo.blockSignals(True)
            try:
                combo.setCurrentIndex(index)
            finally:
                combo.blockSignals(was_blocked)
        self._set_numbering_mode_visibility(target)

    def _create_labeled_spin_block(self, label_text: str, spinbox: QSpinBox, *, label: QLabel | None = None):
        spinbox.setProperty("renameTemplateField", True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_NONE)
        layout.setContentsMargins(*MARGINS_NONE)

        if label is None:
            label = QLabel(label_text)
        setup_standard_form_label(label)
        layout.addWidget(label)

        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(*MARGINS_NONE)
        field_layout.addWidget(spinbox)
        layout.addWidget(field_container)
        return container

    def _create_param_block(self, label_text: str, field: QWidget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(*MARGINS_NONE)

        label = QLabel(label_text)
        setup_standard_form_label(label)
        layout.addWidget(label)
        layout.addWidget(field)
        return container

    def create_numbering_params(self):
        """Создает параметры для нумерации"""
        container = QFrame()
        container.setObjectName("template_numbering_card")
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(MARGINS_NONE[0], SPACE_SM, SPACE_SM, SPACE_SM)

        self.template_numbering_mode = MenuLikeComboBox()
        self.template_numbering_mode.addItems(self._numbering_mode_items())
        setup_standard_dropdown(self.template_numbering_mode)
        self.template_numbering_mode.currentIndexChanged.connect(self._on_numbering_mode_changed)
        layout.addWidget(self._create_param_block("Как нумеровать:", self.template_numbering_mode))

        self.template_num_simple_widget = QWidget()
        simple_layout = QVBoxLayout(self.template_num_simple_widget)
        simple_layout.setSpacing(SPACE_SM)
        simple_layout.setContentsMargins(*MARGINS_NONE)
        
        self.template_num_start = QSpinBox()
        self.template_num_start.setMinimum(1)
        self.template_num_start.setMaximum(9999)
        self.template_num_start.setValue(1)
        setup_standard_spin_input(self.template_num_start)
        simple_layout.addWidget(self._create_labeled_spin_block("Начальный номер:", self.template_num_start))
        
        self.template_num_step = QSpinBox()
        self.template_num_step.setMinimum(1)
        self.template_num_step.setMaximum(100)
        self.template_num_step.setValue(1)
        setup_standard_spin_input(self.template_num_step)
        simple_layout.addWidget(self._create_labeled_spin_block("Шаг нумерации:", self.template_num_step))
        
        self.template_num_digits = QSpinBox()
        self.template_num_digits.setMinimum(1)
        self.template_num_digits.setMaximum(6)
        self.template_num_digits.setValue(3)
        setup_standard_spin_input(self.template_num_digits)
        simple_layout.addWidget(self._create_labeled_spin_block("Кол-во цифр:", self.template_num_digits))
        
        sep_label = QLabel("Разделитель:")
        setup_standard_form_label(sep_label)
        simple_layout.addWidget(sep_label)
        
        self.template_num_sep = QLineEdit()
        self.template_num_sep.setText("_")
        self.template_num_sep.setMaxLength(5)
        self.template_num_sep.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_num_sep)
        simple_layout.addWidget(self.template_num_sep)

        self.template_num_prefix_widget = QWidget()
        prefix_layout = QVBoxLayout(self.template_num_prefix_widget)
        prefix_layout.setSpacing(SPACE_SM)
        prefix_layout.setContentsMargins(*MARGINS_NONE)

        self.template_prefix_text = QLineEdit("фото_")
        self.template_prefix_text.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_prefix_text)
        prefix_layout.addWidget(self._create_param_block("Префикс:", self.template_prefix_text))

        self.template_prefix_start = QSpinBox()
        self.template_prefix_start.setRange(1, 9999)
        self.template_prefix_start.setValue(1)
        setup_standard_spin_input(self.template_prefix_start)
        prefix_layout.addWidget(self._create_labeled_spin_block("Начальный номер:", self.template_prefix_start))

        self.template_prefix_step = QSpinBox()
        self.template_prefix_step.setRange(1, 100)
        self.template_prefix_step.setValue(1)
        setup_standard_spin_input(self.template_prefix_step)
        prefix_layout.addWidget(self._create_labeled_spin_block("Шаг нумерации:", self.template_prefix_step))

        self.template_prefix_digits = QSpinBox()
        self.template_prefix_digits.setRange(1, 6)
        self.template_prefix_digits.setValue(3)
        setup_standard_spin_input(self.template_prefix_digits)
        prefix_layout.addWidget(self._create_labeled_spin_block("Кол-во цифр:", self.template_prefix_digits))

        self.template_num_date_widget = QWidget()
        date_layout = QVBoxLayout(self.template_num_date_widget)
        date_layout.setSpacing(SPACE_SM)
        date_layout.setContentsMargins(*MARGINS_NONE)

        self.template_date_format = MenuLikeComboBox()
        self.template_date_format.addItems([
            "2024-01-15",
            "15-01-2024",
        ])
        setup_standard_dropdown(self.template_date_format)
        date_layout.addWidget(self._create_param_block("Формат даты:", self.template_date_format))

        self.template_date_start = QSpinBox()
        self.template_date_start.setRange(1, 9999)
        self.template_date_start.setValue(1)
        setup_standard_spin_input(self.template_date_start)
        date_layout.addWidget(self._create_labeled_spin_block("Начальный номер:", self.template_date_start))

        self.template_date_step = QSpinBox()
        self.template_date_step.setRange(1, 100)
        self.template_date_step.setValue(1)
        setup_standard_spin_input(self.template_date_step)
        date_layout.addWidget(self._create_labeled_spin_block("Шаг нумерации:", self.template_date_step))

        self.template_date_digits = QSpinBox()
        self.template_date_digits.setRange(1, 6)
        self.template_date_digits.setValue(3)
        setup_standard_spin_input(self.template_date_digits)
        date_layout.addWidget(self._create_labeled_spin_block("Кол-во цифр:", self.template_date_digits))

        layout.addWidget(self.template_num_simple_widget)
        layout.addWidget(self.template_num_prefix_widget)
        layout.addWidget(self.template_num_date_widget)

        self._set_numbering_mode_visibility(getattr(self, "current_template", ""))

        self.template_params_layout.addWidget(container)

    def create_date_original_params(self):
        """Создает параметры для даты + оригинальное название"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(*MARGINS_NONE)
        
        self.template_original_date_format = MenuLikeComboBox()
        self.template_original_date_format.addItems([
            "2024-01-15_название",
            "15-01-2024_название",
        ])
        setup_standard_dropdown(self.template_original_date_format)
        layout.addWidget(self._create_param_block("Дата в начале:", self.template_original_date_format))
        self.template_params_layout.addWidget(container)
    def create_custom_template_params(self):
        """Создает параметры для пользовательского шаблона"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_NONE)
        layout.setContentsMargins(*MARGINS_NONE)
        
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(*MARGINS_NONE)
        input_layout.setSpacing(SPACE_NONE)
        input_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.template_custom = AutoHeightTextEdit()
        self.template_custom._auto_min_height = 44
        self.template_custom.setPlaceholderText("например: фото_{num:03d,start=1,step=1}_{date}_{name}")
        self.template_custom.setText("фото_{num:03d,start=1,step=1}_{date}_{name}")
        self.template_custom.setProperty("renameTemplateField", True)
        self.template_custom.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.template_custom, 1)
        
        layout.addWidget(input_container)

        self.btn_save_template = QPushButton("Сохранить")
        self.btn_save_template.setToolTip("Сохранить шаблон")
        setup_standard_action_button(self.btn_save_template)
        self.btn_save_template.clicked.connect(self.save_current_template)

        self.btn_manage_templates = QPushButton("Управление")
        self.btn_manage_templates.setToolTip("Управление шаблонов")
        setup_standard_action_button(self.btn_manage_templates)
        self.btn_manage_templates.clicked.connect(self.show_template_manager)

        buttons_container, _buttons_layout = self._build_rename_action_row(
            [self.btn_save_template, self.btn_manage_templates]
        )
        layout.addWidget(buttons_container)
        layout.setStretch(layout.count() - 1, 0)
        
        self.template_params_layout.addWidget(container)
