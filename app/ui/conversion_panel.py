"""Панель параметров конвертации и сигналы действий пользователя."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.core.conversion_formats import CONVERSION_CATEGORIES
from app.ui.operation_layout import add_labeled_field, create_operation_card, create_operation_label
from app.ui.ui_components import (
    IconButton,
    MenuLikeComboBox,
    setup_standard_dropdown,
    setup_standard_line_input,
    setup_standard_primary_button,
    setup_standard_secondary_button,
)
from app.ui.ui_styles import MARGINS_NONE, OPERATIONS_PAGE_MARGINS, SPACE_SM


class ConversionPanel(QObject):
    """Владеет элементами управления конвертацией и их сигналами Qt."""

    category_changed = Signal()
    source_changed = Signal()
    target_changed = Signal()
    output_mode_changed = Signal()
    output_folder_requested = Signal()
    conversion_requested = Signal()
    sample_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card, convert_layout = create_operation_card()
        convert_layout.setContentsMargins(*OPERATIONS_PAGE_MARGINS)

        self.convert_file_type_combo = MenuLikeComboBox()
        self.convert_file_type_combo.addItems(
            ["Выберите тип файла:", *CONVERSION_CATEGORIES]
        )
        setup_standard_dropdown(self.convert_file_type_combo)
        self.convert_file_type_combo.currentIndexChanged.connect(
            self.category_changed
        )
        add_labeled_field(
            convert_layout, "Тип файла:", self.convert_file_type_combo
        )

        self.from_convert_combo = MenuLikeComboBox()
        self.from_convert_combo.addItem("Выберите исходный формат:")
        setup_standard_dropdown(self.from_convert_combo)
        self.from_convert_combo.currentIndexChanged.connect(
            self.source_changed
        )
        add_labeled_field(
            convert_layout, "Конвертировать из:", self.from_convert_combo
        )

        self.to_convert_combo = MenuLikeComboBox()
        self.to_convert_combo.addItem("Выберите целевой формат:")
        setup_standard_dropdown(self.to_convert_combo)
        self.to_convert_combo.currentIndexChanged.connect(
            self.target_changed
        )
        self.to_convert_combo.setEnabled(False)
        add_labeled_field(
            convert_layout, "Конвертировать в:", self.to_convert_combo
        )

        self.combo_conversion_output_mode = MenuLikeComboBox()
        self.combo_conversion_output_mode.addItem(
            "Спрашивать каждый раз", "ask"
        )
        self.combo_conversion_output_mode.addItem(
            "Рядом с исходными файлами", "alongside"
        )
        self.combo_conversion_output_mode.addItem(
            "В папку «Конвертированные»",
            "source_subfolder",
        )
        self.combo_conversion_output_mode.addItem(
            "В отдельную папку", "custom"
        )
        setup_standard_dropdown(self.combo_conversion_output_mode)
        self.combo_conversion_output_mode.currentIndexChanged.connect(
            self.output_mode_changed
        )
        add_labeled_field(
            convert_layout,
            "Способ сохранения:",
            self.combo_conversion_output_mode,
        )

        self.conversion_output_path_widget = QWidget()
        conversion_output_path_layout = QHBoxLayout(
            self.conversion_output_path_widget
        )
        conversion_output_path_layout.setContentsMargins(*MARGINS_NONE)
        conversion_output_path_layout.setSpacing(SPACE_SM)

        self.input_conversion_output_path = QLineEdit()
        self.input_conversion_output_path.setReadOnly(True)
        self.input_conversion_output_path.setPlaceholderText(
            "Выберите папку сохранения"
        )
        setup_standard_line_input(self.input_conversion_output_path)
        conversion_output_path_layout.addWidget(
            self.input_conversion_output_path, 1
        )

        self.btn_select_conversion_output_folder = IconButton("Выбрать папку")
        setup_standard_secondary_button(
            self.btn_select_conversion_output_folder
        )
        self.btn_select_conversion_output_folder.clicked.connect(
            self.output_folder_requested
        )
        conversion_output_path_layout.addWidget(
            self.btn_select_conversion_output_folder, 1
        )

        self.conversion_output_path_section = QWidget()
        conversion_output_section_layout = QVBoxLayout(
            self.conversion_output_path_section
        )
        conversion_output_section_layout.setContentsMargins(*MARGINS_NONE)
        conversion_output_section_layout.setSpacing(SPACE_SM)
        conversion_output_section_layout.addWidget(
            create_operation_label("Папка сохранения:")
        )
        conversion_output_section_layout.addWidget(
            self.conversion_output_path_widget
        )
        convert_layout.addWidget(self.conversion_output_path_section)

        convert_layout.addSpacing(SPACE_SM)

        self.btn_convert = IconButton("Конвертировать")
        setup_standard_primary_button(self.btn_convert, expand=True)
        self.btn_convert.clicked.connect(self.conversion_requested)
        self.btn_convert.setEnabled(False)
        convert_layout.addWidget(self.btn_convert)
        self.sample_hint = QLabel(
            "Сложное оформление DOCX может измениться. Проверьте один файл перед запуском пакета."
        )
        self.sample_hint.setWordWrap(True)
        self.sample_hint.hide()
        convert_layout.addWidget(self.sample_hint)
        self.btn_sample = IconButton("Проверить один DOCX")
        setup_standard_secondary_button(self.btn_sample, expand=True)
        self.btn_sample.clicked.connect(self.sample_requested)
        self.btn_sample.hide()
        convert_layout.addWidget(self.btn_sample)
