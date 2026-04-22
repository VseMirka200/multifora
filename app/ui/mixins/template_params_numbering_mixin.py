# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
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
    MenuLikeComboBox,
    setup_standard_action_button,
    setup_standard_dropdown,
    setup_standard_form_label,
    setup_standard_line_input,
    setup_standard_primary_button,
    setup_standard_spin_input,
)


class TemplateParamsNumberingMixin:
    def _create_labeled_spin_block(self, label_text: str, spinbox: QSpinBox, *, label: QLabel | None = None):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 2, 0, 2)

        if label is None:
            label = QLabel(label_text)
        setup_standard_form_label(label)
        layout.addWidget(label)

        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.addWidget(spinbox)
        layout.addWidget(field_container)
        return container

    def _create_param_block(self, label_text: str, field: QWidget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 2, 0, 2)

        label = QLabel(label_text)
        setup_standard_form_label(label)
        layout.addWidget(label)
        layout.addWidget(field)
        return container

    def create_numbering_params(self):
        """Создает параметры для нумерации"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 2, 0, 2)
        
        self.template_num_start = QSpinBox()
        self.template_num_start.setMinimum(1)
        self.template_num_start.setMaximum(9999)
        self.template_num_start.setValue(1)
        setup_standard_spin_input(self.template_num_start)
        layout.addWidget(self._create_labeled_spin_block("Начальный номер:", self.template_num_start))
        
        self.template_num_step = QSpinBox()
        self.template_num_step.setMinimum(1)
        self.template_num_step.setMaximum(100)
        self.template_num_step.setValue(1)
        setup_standard_spin_input(self.template_num_step)
        layout.addWidget(self._create_labeled_spin_block("Шаг нумерации:", self.template_num_step))
        
        self.template_num_digits = QSpinBox()
        self.template_num_digits.setMinimum(1)
        self.template_num_digits.setMaximum(6)
        self.template_num_digits.setValue(3)
        setup_standard_spin_input(self.template_num_digits)
        layout.addWidget(self._create_labeled_spin_block("Кол-во цифр:", self.template_num_digits))
        
        sep_label = QLabel("Разделитель:")
        setup_standard_form_label(sep_label)
        layout.addWidget(sep_label)
        
        self.template_num_sep = QLineEdit()
        self.template_num_sep.setText("_")
        self.template_num_sep.setMaxLength(5)
        setup_standard_line_input(self.template_num_sep)
        layout.addWidget(self.template_num_sep)
        
        self.template_params_layout.addWidget(container)
    def create_numbering_prefix_params(self):
        """Создает параметры для нумерации с префиксом"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 2, 0, 2)
        
        self.template_prefix_text = QLineEdit("фото_")
        setup_standard_line_input(self.template_prefix_text)
        layout.addWidget(self._create_param_block("Префикс:", self.template_prefix_text))
        
        self.template_prefix_start = QSpinBox()
        self.template_prefix_start.setRange(1, 9999)
        self.template_prefix_start.setValue(1)
        setup_standard_spin_input(self.template_prefix_start)
        layout.addWidget(self._create_labeled_spin_block("Начальный номер:", self.template_prefix_start))
        
        self.template_prefix_step = QSpinBox()
        self.template_prefix_step.setRange(1, 100)
        self.template_prefix_step.setValue(1)
        setup_standard_spin_input(self.template_prefix_step)
        layout.addWidget(self._create_labeled_spin_block("Шаг нумерации:", self.template_prefix_step))
        
        self.template_prefix_digits = QSpinBox()
        self.template_prefix_digits.setRange(1, 6)
        self.template_prefix_digits.setValue(3)
        setup_standard_spin_input(self.template_prefix_digits)
        layout.addWidget(self._create_labeled_spin_block("Кол-во цифр:", self.template_prefix_digits))
        
        self.template_params_layout.addWidget(container)
    def create_numbering_date_params(self):
        """Создает параметры для нумерации с датой"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 2, 0, 2)
        
        self.template_date_format = MenuLikeComboBox()
        self.template_date_format.addItems([
            "2024-01-15",
            "15-01-2024",
        ])
        setup_standard_dropdown(self.template_date_format)
        layout.addWidget(self._create_param_block("Формат даты:", self.template_date_format))
        
        self.template_date_start = QSpinBox()
        self.template_date_start.setRange(1, 9999)
        self.template_date_start.setValue(1)
        setup_standard_spin_input(self.template_date_start)
        layout.addWidget(self._create_labeled_spin_block("Начальный номер:", self.template_date_start))
        
        self.template_date_step = QSpinBox()
        self.template_date_step.setRange(1, 100)
        self.template_date_step.setValue(1)
        setup_standard_spin_input(self.template_date_step)
        layout.addWidget(self._create_labeled_spin_block("Шаг нумерации:", self.template_date_step))
        
        self.template_date_digits = QSpinBox()
        self.template_date_digits.setRange(1, 6)
        self.template_date_digits.setValue(3)
        setup_standard_spin_input(self.template_date_digits)
        layout.addWidget(self._create_labeled_spin_block("Кол-во цифр:", self.template_date_digits))
        
        self.template_params_layout.addWidget(container)
    def create_date_original_params(self):
        """Создает параметры для даты + оригинальное название"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 2, 0, 2)
        
        self.template_original_date_format = MenuLikeComboBox()
        self.template_original_date_format.addItems([
            "2024-01-15_название",
            "15-01-2024_название",
        ])
        setup_standard_dropdown(self.template_original_date_format)
        layout.addWidget(self._create_param_block("Дата в начале:", self.template_original_date_format))
        self.template_params_layout.addWidget(container)
    def on_custom_numbering_toggled(self, state):
        """Добавляет/отключает нумерацию для пользовательского шаблона"""
        enabled = state in (Qt.CheckState.Checked, int(Qt.CheckState.Checked.value), 2, True)
        if hasattr(self, 'template_custom_start'):
            self.template_custom_start.setEnabled(enabled)
        if hasattr(self, 'template_custom_step'):
            self.template_custom_step.setEnabled(enabled)
        if hasattr(self, 'template_custom_start_label'):
            self.template_custom_start_label.setEnabled(enabled)
        if hasattr(self, 'template_custom_step_label'):
            self.template_custom_step_label.setEnabled(enabled)
    def create_custom_template_params(self):
        """Создает параметры для пользовательского шаблона"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)
        input_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.template_custom = QLineEdit()
        self.template_custom.setPlaceholderText("например: фото_{num:03d}_{date}_{name}")
        self.template_custom.setText("фото_{num:03d}_{date}_{name}")
        setup_standard_line_input(self.template_custom)
        input_layout.addWidget(self.template_custom)
        
        layout.addWidget(input_container)
        layout.addSpacing(4)

        numbering_toggle_container = QWidget()
        numbering_toggle_container.setFixedHeight(24)
        numbering_toggle_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        numbering_toggle_layout = QHBoxLayout(numbering_toggle_container)
        numbering_toggle_layout.setContentsMargins(0, 0, 0, 0)
        numbering_toggle_layout.setSpacing(6)
        numbering_toggle_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.template_custom_use_numbering = QCheckBox()
        self.template_custom_use_numbering.setChecked(True)
        self.template_custom_use_numbering.setFixedSize(16, 16)
        self.template_custom_use_numbering.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        checkbox_dir = Path(__file__).resolve().parents[1]
        checkbox_unchecked_url = (checkbox_dir / "checkbox_unchecked.svg").resolve().as_posix()
        checkbox_checked_url = (checkbox_dir / "checkbox_checked.svg").resolve().as_posix()
        self.template_custom_use_numbering.setStyleSheet(
            f"""
            QCheckBox {{
                margin-top: 2px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                margin: 0px;
                border: none;
                background: transparent;
                border-image: url("{checkbox_unchecked_url}") 0 0 0 0 stretch stretch;
            }}
            QCheckBox::indicator:checked {{
                border: none;
                background: transparent;
                border-image: url("{checkbox_checked_url}") 0 0 0 0 stretch stretch;
            }}
            """
        )
        self.template_custom_use_numbering.stateChanged.connect(self.on_custom_numbering_toggled)
        numbering_toggle_layout.addWidget(
            self.template_custom_use_numbering,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        numbering_toggle_layout.setStretch(0, 0)
        numbering_toggle_label = QLabel("Включить нумерацию")
        numbering_toggle_label.setStyleSheet("font-size: 13px;")
        numbering_toggle_label.setFixedHeight(24)
        numbering_toggle_layout.addWidget(numbering_toggle_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        numbering_toggle_layout.addStretch()
        layout.addWidget(numbering_toggle_container)

        self.template_custom_start = QSpinBox()
        self.template_custom_start.setRange(1, 9999)
        self.template_custom_start.setValue(1)
        setup_standard_spin_input(self.template_custom_start)
        self.template_custom_start_label = QLabel("Начальный номер:")
        layout.addWidget(
            self._create_labeled_spin_block(
                "Начальный номер:",
                self.template_custom_start,
                label=self.template_custom_start_label,
            )
        )

        self.template_custom_step = QSpinBox()
        self.template_custom_step.setRange(1, 100)
        self.template_custom_step.setValue(1)
        setup_standard_spin_input(self.template_custom_step)
        self.template_custom_step_label = QLabel("Шаг нумерации:")
        layout.addWidget(
            self._create_labeled_spin_block(
                "Шаг нумерации:",
                self.template_custom_step,
                label=self.template_custom_step_label,
            )
        )
        layout.addSpacing(4)

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
        self.on_custom_numbering_toggled(self.template_custom_use_numbering.checkState())
        
        self.template_params_layout.addWidget(container)





