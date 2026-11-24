from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.app_utils import signals_blocked
from app.ui.ui_components import (
    MenuLikeComboBox,
    setup_standard_dropdown,
    setup_standard_form_label,
    setup_standard_line_input,
    setup_standard_spin_input,
)
from app.ui.ui_helpers import create_param_block
from app.ui.ui_styles import (
    MARGINS_NONE,
    PAGE_SECTION_SPACING,
    SPACE_NONE,
    SPACE_SM,
)


class TemplateParamsNumberingMixin:
    # Собирает параметры нумерации, чтобы порядок файлов учитывался в новых именах.
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
        mode_getter = getattr(
            getattr(self, "template_numbering_mode", None),
            "currentText",
            lambda: "",
        )
        mode = self._normalize_numbering_mode(mode_text or mode_getter())
        for mode_name, field_name, fields_name in (
            ("Простая нумерация", "template_separator_field", "template_num_simple_widget"),
            ("Нумерация с префиксом", "template_prefix_field", "template_num_prefix_widget"),
            ("Нумерация с датой", "template_date_field", "template_num_date_widget"),
        ):
            for name in (field_name, fields_name):
                widget = getattr(self, name, None)
                if widget is not None:
                    widget.setVisible(mode == mode_name)

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
            with signals_blocked(combo):
                combo.setCurrentIndex(index)
        self._set_numbering_mode_visibility(target)

    def _create_numbering_fields(self, *fields: tuple[str, QWidget]) -> QWidget:
        container = QWidget()
        layout = QGridLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setHorizontalSpacing(PAGE_SECTION_SPACING)
        layout.setContentsMargins(*MARGINS_NONE)
        for column, (text, field) in enumerate(fields):
            label = setup_standard_form_label(QLabel(text))
            label.setBuddy(field)
            if isinstance(field, QSpinBox):
                field.setProperty("renameTemplateField", True)
            layout.addWidget(label, 0, column)
            layout.addWidget(field, 1, column)
        return container

    def create_numbering_params(self):
        """Создает параметры для нумерации"""
        container = QFrame()
        container.setObjectName("template_numbering_card")
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(SPACE_NONE, SPACE_NONE, SPACE_NONE, SPACE_SM)

        self.template_numbering_mode = MenuLikeComboBox()
        self.template_numbering_mode.addItems(self._numbering_mode_items())
        setup_standard_dropdown(self.template_numbering_mode)
        self.template_numbering_mode.currentIndexChanged.connect(
            self._on_numbering_mode_changed
        )
        mode_row = QHBoxLayout()
        mode_row.setSpacing(PAGE_SECTION_SPACING)
        mode_row.addWidget(
            create_param_block("Как нумеровать:", self.template_numbering_mode),
            2,
            Qt.AlignmentFlag.AlignBottom,
        )
        layout.addLayout(mode_row)

        self.template_prefix_text = QLineEdit("фото_")
        self.template_prefix_text.setProperty("renameTemplateField", True)
        self.template_prefix_text.setAccessibleName("Префикс")
        setup_standard_line_input(self.template_prefix_text)
        self.template_prefix_field = create_param_block("Префикс:", self.template_prefix_text)
        mode_row.addWidget(self.template_prefix_field, 1, Qt.AlignmentFlag.AlignBottom)

        self.template_num_start = QSpinBox()
        self.template_num_start.setMinimum(1)
        self.template_num_start.setMaximum(9999)
        self.template_num_start.setValue(1)
        setup_standard_spin_input(self.template_num_start)

        self.template_num_step = QSpinBox()
        self.template_num_step.setMinimum(1)
        self.template_num_step.setMaximum(100)
        self.template_num_step.setValue(1)
        setup_standard_spin_input(self.template_num_step)

        self.template_num_digits = QSpinBox()
        self.template_num_digits.setMinimum(1)
        self.template_num_digits.setMaximum(6)
        self.template_num_digits.setValue(3)
        setup_standard_spin_input(self.template_num_digits)

        self.template_num_sep = QLineEdit()
        self.template_num_sep.setText("_")
        self.template_num_sep.setMaxLength(5)
        self.template_num_sep.setToolTip("Разделитель")
        self.template_num_sep.setAccessibleName("Разделитель")
        self.template_num_sep.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_num_sep)
        self.template_separator_field = create_param_block("Раздел.", self.template_num_sep)
        mode_row.addWidget(self.template_separator_field, 1, Qt.AlignmentFlag.AlignBottom)
        self.template_num_simple_widget = self._create_numbering_fields(
            ("Начало", self.template_num_start),
            ("Шаг", self.template_num_step),
            ("Цифры", self.template_num_digits),
        )

        self.template_prefix_start = QSpinBox()
        self.template_prefix_start.setRange(1, 9999)
        self.template_prefix_start.setValue(1)
        setup_standard_spin_input(self.template_prefix_start)

        self.template_prefix_step = QSpinBox()
        self.template_prefix_step.setRange(1, 100)
        self.template_prefix_step.setValue(1)
        setup_standard_spin_input(self.template_prefix_step)

        self.template_prefix_digits = QSpinBox()
        self.template_prefix_digits.setRange(1, 6)
        self.template_prefix_digits.setValue(3)
        setup_standard_spin_input(self.template_prefix_digits)
        self.template_num_prefix_widget = self._create_numbering_fields(
            ("Начало", self.template_prefix_start),
            ("Шаг", self.template_prefix_step),
            ("Цифры", self.template_prefix_digits),
        )

        self.template_date_format = MenuLikeComboBox()
        self.template_date_format.addItems(
            [
                "2024-01-15",
                "15-01-2024",
            ]
        )
        setup_standard_dropdown(self.template_date_format)
        self.template_date_format.setAccessibleName("Формат даты")
        self.template_date_field = create_param_block("Формат даты:", self.template_date_format)
        mode_row.addWidget(self.template_date_field, 1, Qt.AlignmentFlag.AlignBottom)

        self.template_date_start = QSpinBox()
        self.template_date_start.setRange(1, 9999)
        self.template_date_start.setValue(1)
        setup_standard_spin_input(self.template_date_start)

        self.template_date_step = QSpinBox()
        self.template_date_step.setRange(1, 100)
        self.template_date_step.setValue(1)
        setup_standard_spin_input(self.template_date_step)

        self.template_date_digits = QSpinBox()
        self.template_date_digits.setRange(1, 6)
        self.template_date_digits.setValue(3)
        setup_standard_spin_input(self.template_date_digits)
        self.template_num_date_widget = self._create_numbering_fields(
            ("Начало", self.template_date_start),
            ("Шаг", self.template_date_step),
            ("Цифры", self.template_date_digits),
        )

        layout.addWidget(self.template_num_simple_widget, 1)
        layout.addWidget(self.template_num_prefix_widget, 1)
        layout.addWidget(self.template_num_date_widget, 1)

        self._set_numbering_mode_visibility(
            getattr(self, "current_template", "")
        )

        self.template_params_layout.addWidget(container)

    def create_date_original_params(self):
        """Создает параметры для даты + оригинальное название"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(*MARGINS_NONE)

        self.template_original_date_format = MenuLikeComboBox()
        self.template_original_date_format.addItems(
            [
                "2024-01-15_название",
                "15-01-2024_название",
            ]
        )
        setup_standard_dropdown(self.template_original_date_format)
        layout.addWidget(
            create_param_block(
                "Дата в начале:", self.template_original_date_format
            )
        )
        self.template_params_layout.addWidget(container)
