from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from app.ui.ui_components import (
    MenuLikeComboBox,
    setup_standard_dropdown,
    setup_standard_line_input,
    setup_standard_spin_input,
)
from app.ui.ui_helpers import create_param_block, create_spin_param_block
from app.ui.ui_styles import MARGINS_NONE, PAGE_SECTION_SPACING


class TemplateParamsTextMixin:
    # Настраивает текстовые части имени: замену, префикс, суффикс и расширение.
    def _create_text_position_selector(self, start_label: str, end_label: str) -> MenuLikeComboBox:
        selector = MenuLikeComboBox()
        selector.addItem(start_label, "start")
        selector.addItem(end_label, "end")
        selector.setAccessibleName("Позиция")
        setup_standard_dropdown(selector)
        selector.currentIndexChanged.connect(lambda _index: self.refresh_rename_preview())
        selector.currentIndexChanged.connect(self._schedule_settings_save)
        return selector

    def create_add_text_params(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(PAGE_SECTION_SPACING)

        self.template_add_position = self._create_text_position_selector("В начало", "В конец")
        layout.addWidget(create_param_block("Позиция", self.template_add_position), 1)

        self.template_add_text = QLineEdit("префикс_")
        self.template_add_text.setPlaceholderText("Текст")
        self.template_add_text.setAccessibleName("Добавляемый текст")
        self.template_add_text.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_add_text)
        layout.addWidget(create_param_block("Текст", self.template_add_text), 2)
        self.template_params_layout.addWidget(container)

    def create_remove_chars_params(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(PAGE_SECTION_SPACING)

        self.template_remove_position = self._create_text_position_selector("С начала", "С конца")
        layout.addWidget(create_param_block("Позиция", self.template_remove_position), 1)

        self.template_remove_count = QSpinBox()
        self.template_remove_count.setRange(1, 100)
        self.template_remove_count.setAccessibleName("Количество символов")
        setup_standard_spin_input(self.template_remove_count)
        layout.addWidget(create_spin_param_block("Символов", self.template_remove_count), 2)
        self.template_params_layout.addWidget(container)

    def create_remove_text_params(self):
        """Создает параметры для удаления текста"""
        self.template_remove_text = QLineEdit()
        self.template_remove_text.setPlaceholderText("Текст")
        self.template_remove_text.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_remove_text)
        container = create_param_block(
            "Удалить текст:", self.template_remove_text
        )
        self.template_params_layout.addWidget(container)

    def create_replace_text_params(self):
        """Создает параметры для замены текста"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(PAGE_SECTION_SPACING)
        layout.setContentsMargins(*MARGINS_NONE)

        self.template_find = QLineEdit()
        self.template_find.setPlaceholderText("старый текст")
        self.template_find.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_find)
        layout.addWidget(create_param_block("Что заменить:", self.template_find))

        self.template_replace = QLineEdit()
        self.template_replace.setPlaceholderText("новый текст")
        self.template_replace.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_replace)
        layout.addWidget(create_param_block("На что заменить:", self.template_replace))

        self.template_params_layout.addWidget(container)

    def create_case_params(self):
        """Создаёт выбор преобразования регистра имени файла."""
        self.template_case_mode = MenuLikeComboBox()
        for mode, label in (
            ("lower", "нижний регистр"),
            ("upper", "ВЕРХНИЙ РЕГИСТР"),
            ("title", "Каждое Слово С Заглавной"),
            ("sentence", "Первая буква заглавная"),
            ("swap", "иНВЕРТИРОВАТЬ РЕГИСТР"),
        ):
            self.template_case_mode.addItem(label, mode)
        setup_standard_dropdown(self.template_case_mode)
        self.template_params_layout.addWidget(
            create_param_block("Преобразование:", self.template_case_mode)
        )
