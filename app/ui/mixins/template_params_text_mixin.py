
from PyQt6.QtWidgets import QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget
from app.ui.ui_components import setup_standard_form_label, setup_standard_line_input, setup_standard_spin_input
from app.ui.ui_helpers import create_param_block, create_spin_param_block
from app.ui.ui_spacing import MARGINS_NONE, SPACE_SM


class TemplateParamsTextMixin:
    # Настраивает текстовые части имени: замену, префикс, суффикс и расширение.
    def create_add_prefix_params(self):
        """Создает параметры для добавления префикса"""
        self.template_prefix = QLineEdit()
        self.template_prefix.setPlaceholderText("префикс_")
        self.template_prefix.setText("префикс_")
        self.template_prefix.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_prefix)
        container = create_param_block("Добавить в начало:", self.template_prefix)
        self.template_params_layout.addWidget(container)

    def create_add_suffix_params(self):
        """Создает параметры для добавления суффикса"""
        self.template_suffix = QLineEdit()
        self.template_suffix.setPlaceholderText("_суффикс")
        self.template_suffix.setText("_суффикс")
        self.template_suffix.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_suffix)
        container = create_param_block("Добавить в конец:", self.template_suffix)
        self.template_params_layout.addWidget(container)

    def create_remove_start_params(self):
        """Создает параметры для удаления первых N символов"""
        self.template_remove_start = QSpinBox()
        self.template_remove_start.setMinimum(1)
        self.template_remove_start.setMaximum(100)
        self.template_remove_start.setValue(1)
        setup_standard_spin_input(self.template_remove_start)
        container = create_spin_param_block("Удалить сначала:", self.template_remove_start)
        self.template_params_layout.addWidget(container)

    def create_remove_end_params(self):
        """Создает параметры для удаления последних N символов"""
        self.template_remove_end = QSpinBox()
        self.template_remove_end.setMinimum(1)
        self.template_remove_end.setMaximum(100)
        self.template_remove_end.setValue(1)
        setup_standard_spin_input(self.template_remove_end)
        container = create_spin_param_block("Удалить с конца:", self.template_remove_end)
        self.template_params_layout.addWidget(container)

    def create_remove_text_params(self):
        """Создает параметры для удаления текста"""
        self.template_remove_text = QLineEdit()
        self.template_remove_text.setPlaceholderText("Текст")
        self.template_remove_text.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_remove_text)
        container = create_param_block("Удалить текст:", self.template_remove_text)
        self.template_params_layout.addWidget(container)

    def create_replace_text_params(self):
        """Создает параметры для замены текста"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(*MARGINS_NONE)
        
        find_label = QLabel("Что заменить:")
        setup_standard_form_label(find_label)
        layout.addWidget(find_label)
        
        self.template_find = QLineEdit()
        self.template_find.setPlaceholderText("старый текст")
        self.template_find.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_find)
        layout.addWidget(self.template_find)
        
        replace_label = QLabel("На что заменить:")
        setup_standard_form_label(replace_label)
        layout.addWidget(replace_label)
        
        self.template_replace = QLineEdit()
        self.template_replace.setPlaceholderText("новый текст")
        self.template_replace.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_replace)
        layout.addWidget(self.template_replace)
        
        self.template_params_layout.addWidget(container)

