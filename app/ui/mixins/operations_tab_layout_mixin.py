# -*- coding: utf-8 -*-

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.ui_components import MenuLikeComboBox, setup_standard_action_button, setup_standard_dropdown, setup_standard_primary_button
from app.core.conversion_formats import CONVERSION_CATEGORIES


class OperationsTabLayoutMixin:
    def _build_rename_action_row(
        self,
        buttons: list[QPushButton],
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: int = 4,
    ) -> tuple[QWidget, QGridLayout]:
        row_widget = QWidget()
        row_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row_layout = QGridLayout(row_widget)
        row_layout.setContentsMargins(*margins)
        row_layout.setHorizontalSpacing(spacing)
        row_layout.setVerticalSpacing(0)

        for index, button in enumerate(buttons):
            setup_standard_action_button(button)
            row_layout.setColumnStretch(index, 1)
            row_layout.addWidget(button, 0, index)

        return row_widget, row_layout

    def create_operations_tab(self):
        """Создает объединенную вкладку для операций с файлами"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        self.operations_tab_bar = QTabBar()
        self.operations_tab_bar.setObjectName("operations_tab_bar")
        self.operations_tab_bar.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.operations_tab_bar.setContentsMargins(0, 0, 0, 0)
        self.operations_tab_bar.setExpanding(False)
        self.operations_tab_bar.setDrawBase(False)
        self.operations_tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        self.operations_tab_bar.setUsesScrollButtons(False)
        self.operations_tab_bar.setDocumentMode(False)
        self.operations_tab_bar.setFixedHeight(36)
        self.operations_tab_bar.setStyleSheet(self.operations_tab_bar.styleSheet() + "QTabBar { margin-bottom: 0px; }")
        self.operations_tab_bar.setStyleSheet(
            """
            QTabBar#operations_tab_bar {
                background-color: transparent;
                margin: 0px;
                padding: 0px;
                border: none;
            }
            QTabBar#operations_tab_bar::tab {
                margin: 0px;
                padding: 0px 10px;
                min-width: 24px;
                min-height: 36px;
                max-height: 36px;
                font-weight: 700;
                color: #ffffff;
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }
            QTabBar#operations_tab_bar::tab:selected {
                background-color: transparent;
                color: #ffffff;
                border-bottom: 2px solid #2f79c6;
            }
            QTabBar#operations_tab_bar::tab:!selected {
                background-color: transparent;
                color: #ffffff;
            }
            QTabBar#operations_tab_bar::tab:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            """
        )
        self.operations_stack = QStackedWidget()
        self.operations_stack.setStyleSheet("QStackedWidget { margin: 0px 4px 0 0; }")
        self.operations_stack.setObjectName("operations_stack")
        self._settings_tab_index = -1
        self._current_operations_tab_index = 0
        self.operations_tab_bar.currentChanged.connect(self._on_operations_tab_changed)
        tab_layout.addWidget(self.operations_stack)
        
        # Секция 1: Переименование (карточка)
        rename_card = QFrame()
        rename_card.setObjectName("card")
        rename_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        rename_card_layout = QVBoxLayout(rename_card)
        rename_card_layout.setContentsMargins(8, 6, 8, 5)
        rename_card_layout.setSpacing(4)

        rename_content = QWidget()
        rename_layout = QVBoxLayout(rename_content)
        rename_layout.setSpacing(4)
        rename_layout.setContentsMargins(0, 0, 0, 0)
        
        # Шаблоны переименования
        template_layout = QVBoxLayout()
        template_layout.setContentsMargins(0, 0, 0, 0)
        template_layout.setSpacing(4)
        label_template = QLabel("Шаблон:")
        label_template.setStyleSheet("font-size: 13px;")
        label_template.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label_template.setWordWrap(True)
        
        self.combo_templates = MenuLikeComboBox()
        self.combo_templates.currentTextChanged.connect(self.on_template_selected)
        setup_standard_dropdown(self.combo_templates)
        
        template_layout.addWidget(label_template)
        template_layout.addWidget(self.combo_templates)
        rename_layout.addLayout(template_layout)
        
        # Виджет для параметров шаблона
        self.template_params_widget = QWidget()
        self.template_params_widget.setObjectName("template_params_widget")
        self.template_params_widget.setVisible(False)
        self.template_params_widget.setStyleSheet("background-color: transparent;")
        self.template_params_layout = QVBoxLayout(self.template_params_widget)
        self.template_params_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.template_params_layout.setContentsMargins(0, 0, 0, 0)
        self.template_params_layout.setSpacing(2)
        rename_layout.addWidget(self.template_params_widget)
        
        self.btn_apply_rename = QPushButton("Начать действие")
        self.btn_apply_rename.clicked.connect(self.apply_rename)
        self.btn_apply_rename.setEnabled(False)

        rename_buttons_widget, rename_buttons = self._build_rename_action_row([self.btn_apply_rename])
        self._rename_buttons_layout = rename_buttons
        self._rename_buttons_widget = rename_buttons_widget
        self._rename_buttons_compact = None

        rename_layout.addWidget(rename_buttons_widget)

        rename_card_layout.addWidget(rename_content)

        self._add_operations_page(self._wrap_operations_page(rename_card, "rename_page"), "Переименование")

        # Секция 2: Конвертация документов (карточка)
        convert_card = QFrame()
        convert_card.setObjectName("card")
        convert_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        convert_card_layout = QVBoxLayout(convert_card)
        convert_card_layout.setContentsMargins(8, 6, 8, 6)
        convert_card_layout.setSpacing(4)

        convert_content = QWidget()
        convert_layout = QVBoxLayout(convert_content)
        convert_layout.setSpacing(4)
        convert_layout.setContentsMargins(0, 0, 0, 0)

        # Поле: Тип конвертируемых файлов
        file_type_container = QVBoxLayout()
        file_type_container.setContentsMargins(0, 0, 0, 0)
        file_type_container.setSpacing(4)
        file_type_label = QLabel("Тип файла:")
        file_type_label.setStyleSheet("font-size: 13px;")
        file_type_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        file_type_label.setWordWrap(True)
        file_type_container.addWidget(file_type_label)

        self.convert_file_type_combo = MenuLikeComboBox()
        self.convert_file_type_combo.addItems(["Выберите тип файла:", *CONVERSION_CATEGORIES])
        setup_standard_dropdown(self.convert_file_type_combo)
        self.convert_file_type_combo.currentIndexChanged.connect(self.update_converter_from_format)
        self.convert_file_type_combo.currentIndexChanged.connect(self.update_convert_button_state)
        file_type_container.addWidget(self.convert_file_type_combo)
        convert_layout.addLayout(file_type_container)
        
        # Первое поле: Что конвертировать
        from_container = QVBoxLayout()
        from_container.setContentsMargins(0, 0, 0, 0)
        from_container.setSpacing(4)
        from_label = QLabel("Конвертировать из:")
        from_label.setStyleSheet("font-size: 13px;")
        from_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        from_label.setWordWrap(True)
        from_container.addWidget(from_label)
        
        self.from_convert_combo = MenuLikeComboBox()
        self.from_convert_combo.addItem("Выберите исходный формат:")
        setup_standard_dropdown(self.from_convert_combo)
        self.from_convert_combo.currentIndexChanged.connect(self.update_to_combo_based_on_from)
        from_container.addWidget(self.from_convert_combo)
        convert_layout.addLayout(from_container)
        
        # Второе поле: Во что конвертировать
        to_container = QVBoxLayout()
        to_container.setContentsMargins(0, 0, 0, 0)
        to_container.setSpacing(4)
        to_label = QLabel("Конвертировать в:")
        to_label.setStyleSheet("font-size: 13px;")
        to_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        to_label.setWordWrap(True)
        to_container.addWidget(to_label)
        
        self.to_convert_combo = MenuLikeComboBox()
        self.to_convert_combo.addItem("Выберите целевой формат:")
        setup_standard_dropdown(self.to_convert_combo)
        self.to_convert_combo.setEnabled(False)
        to_container.addWidget(self.to_convert_combo)
        convert_layout.addLayout(to_container)
        
        # Кнопка конвертации на всю ширину
        self.btn_convert = QPushButton("Конвертировать")
        setup_standard_primary_button(self.btn_convert, height=28)
        self.btn_convert.clicked.connect(self.convert_files_dual_combo)
        self.btn_convert.setEnabled(False)
        convert_layout.addSpacing(4)
        convert_layout.addWidget(self.btn_convert)
        
        convert_card_layout.addWidget(convert_content)

        self._add_operations_page(self._wrap_operations_page(convert_card, "convert_page"), "Конвертация")

        # Секция 3: Объединение документов (карточка)
        merge_card = QFrame()
        merge_card.setObjectName("card")
        merge_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        merge_card_layout = QVBoxLayout(merge_card)
        merge_card_layout.setContentsMargins(8, 6, 8, 6)
        merge_card_layout.setSpacing(4)

        merge_content = QWidget()
        merge_layout = QVBoxLayout(merge_content)
        merge_layout.setSpacing(4)
        merge_layout.setContentsMargins(0, 0, 0, 0)

        merge_format_label = QLabel("Формат результата:")
        merge_format_label.setStyleSheet("font-size: 13px;")
        merge_format_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        merge_format_label.setWordWrap(True)
        merge_layout.addWidget(merge_format_label)

        self.combo_merge_format = MenuLikeComboBox()
        self.combo_merge_format.addItem("PDF (Word и PDF)", "pdf")
        self.combo_merge_format.addItem("DOCX (только DOCX)", "docx")
        self.combo_merge_format.addItem("Авто", "auto")
        setup_standard_dropdown(self.combo_merge_format)
        self.combo_merge_format.currentIndexChanged.connect(self.on_merge_format_changed)
        merge_layout.addWidget(self.combo_merge_format)

        merge_output_label = QLabel("Сохранить как:")
        merge_output_label.setStyleSheet("font-size: 13px;")
        merge_output_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        merge_output_label.setWordWrap(True)
        merge_layout.addWidget(merge_output_label)

        merge_output_row = QWidget()
        merge_output_row_layout = QHBoxLayout(merge_output_row)
        merge_output_row_layout.setContentsMargins(0, 0, 0, 0)
        merge_output_row_layout.setSpacing(4)

        self.input_merge_output_path = QLineEdit()
        self.input_merge_output_path.setReadOnly(True)
        self.input_merge_output_path.setPlaceholderText("Выберите файл сохранения")
        merge_output_row_layout.addWidget(self.input_merge_output_path, 1)

        self.btn_merge_output_path = QPushButton("...")
        self.btn_merge_output_path.setFixedWidth(34)
        setup_standard_action_button(self.btn_merge_output_path, height=28)
        self.btn_merge_output_path.clicked.connect(self.select_merge_output_path)
        merge_output_row_layout.addWidget(self.btn_merge_output_path)
        merge_layout.addWidget(merge_output_row)

        self.btn_merge = QPushButton("Объединить")
        setup_standard_primary_button(self.btn_merge, height=28)
        self.btn_merge.clicked.connect(self.merge_files)
        merge_layout.addSpacing(4)
        merge_layout.addWidget(self.btn_merge)

        merge_card_layout.addWidget(merge_content)

        self._add_operations_page(self._wrap_operations_page(merge_card, "merge_page"), "Объединение")

        # Секция 4: Сжатие файлов (карточка)
        compress_card = QFrame()
        compress_card.setObjectName("card")
        compress_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        compress_card_layout = QVBoxLayout(compress_card)
        compress_card_layout.setContentsMargins(8, 6, 8, 6)
        compress_card_layout.setSpacing(4)
        compress_card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        compress_content = QWidget()
        compress_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        compress_layout = QVBoxLayout(compress_content)
        compress_layout.setSpacing(4)
        compress_layout.setContentsMargins(0, 0, 0, 0)
        compress_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Выбор типа сжатия
        type_layout = QVBoxLayout()
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(4)

        type_label = QLabel("Тип файлов:")
        type_label.setStyleSheet("font-size: 13px;")
        type_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        type_label.setWordWrap(True)
        type_layout.addWidget(type_label)

        self.combo_compress_type = MenuLikeComboBox()
        self.combo_compress_type.addItems(["Изображения", "PDF документы"])
        setup_standard_dropdown(self.combo_compress_type)
        self.combo_compress_type.currentTextChanged.connect(self.on_compress_type_changed)
        type_layout.addWidget(self.combo_compress_type)
        compress_layout.addLayout(type_layout)

        self.compress_mode_stack = QStackedWidget()
        self.compress_mode_stack.setContentsMargins(0, 0, 0, 0)
        self.compress_mode_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Для PDF: выбор метода сжатия
        self.pdf_mode_widget = QWidget()
        pdf_mode_layout = QVBoxLayout(self.pdf_mode_widget)
        pdf_mode_layout.setSpacing(4)
        pdf_mode_layout.setContentsMargins(0, 0, 0, 0)

        self.pdf_method_widget = QWidget()
        pdf_method_layout = QVBoxLayout(self.pdf_method_widget)
        pdf_method_layout.setSpacing(4)
        pdf_method_layout.setContentsMargins(0, 0, 0, 0)

        pdf_method_label = QLabel("Метод сжатия PDF:")
        pdf_method_label.setStyleSheet("font-size: 13px;")
        pdf_method_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        pdf_method_label.setWordWrap(True)
        pdf_method_layout.addWidget(pdf_method_label)

        self.combo_pdf_method = MenuLikeComboBox()
        self.combo_pdf_method.addItems([
            "Авто (рекомендуется)",
            "Максимальное сжатие",
            "Сохранить качество",
            "Только оптимизация"
        ])
        setup_standard_dropdown(self.combo_pdf_method)
        self.combo_pdf_method.currentTextChanged.connect(self.on_pdf_method_changed)
        pdf_method_layout.addWidget(self.combo_pdf_method)

        self.replace_pdf_row = QWidget()
        self.replace_pdf_row.setFixedHeight(24)
        self.replace_pdf_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        replace_pdf_layout = QHBoxLayout(self.replace_pdf_row)
        replace_pdf_layout.setContentsMargins(0, 0, 0, 0)
        replace_pdf_layout.setSpacing(4)
        replace_pdf_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.checkbox_replace_pdf = QCheckBox()
        self.checkbox_replace_pdf.setFixedSize(16, 16)
        self.checkbox_replace_pdf.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.checkbox_replace_pdf.setStyleSheet("margin-top: 1px;")
        self.checkbox_replace_pdf.setToolTip("Исходный PDF будет перезаписан сжатой версией")
        self.checkbox_replace_pdf.stateChanged.connect(self.on_replace_pdf_checked)
        self.checkbox_replace_pdf.setChecked(False)
        replace_pdf_layout.addWidget(
            self.checkbox_replace_pdf,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        replace_pdf_label = QLabel("Заменять файлы")
        replace_pdf_label.setFixedHeight(24)
        replace_pdf_layout.addWidget(replace_pdf_label, 0, Qt.AlignmentFlag.AlignVCenter)
        replace_pdf_layout.addStretch()

        self.pdf_method_warning_label = QLabel()
        self.pdf_method_warning_label.setStyleSheet("font-size: 13px; color: #FFA726; margin-top: 2px;")
        self.pdf_method_warning_label.setWordWrap(True)
        self.pdf_method_warning_label.setVisible(False)
        pdf_method_layout.addWidget(self.pdf_method_warning_label)
        pdf_mode_layout.addWidget(self.pdf_method_widget)
        pdf_mode_layout.addWidget(self.replace_pdf_row)

        # Уровень сжатия (только для изображений)
        self.image_mode_widget = QWidget()
        image_mode_layout = QVBoxLayout(self.image_mode_widget)
        image_mode_layout.setContentsMargins(0, 0, 0, 0)
        image_mode_layout.setSpacing(4)

        self.compression_level_widget = QWidget()
        level_layout = QVBoxLayout(self.compression_level_widget)
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.setSpacing(4)

        level_label = QLabel("Уровень сжатия PNG/JPG:")
        level_label.setStyleSheet("font-size: 13px; margin-top: 0px;")
        level_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        level_label.setWordWrap(True)
        level_layout.addWidget(level_label)

        self.combo_compression_level = MenuLikeComboBox()
        self.combo_compression_level.addItem("Максимальное сжатие (40%)", 40)
        self.combo_compression_level.addItem("Сбалансированное (65%)", 65)
        self.combo_compression_level.addItem("Хорошее качество (85%)", 85)
        self.combo_compression_level.addItem("Максимальное качество (95%)", 95)
        self.combo_compression_level.setCurrentIndex(2)
        setup_standard_dropdown(self.combo_compression_level)
        self.combo_compression_level.currentIndexChanged.connect(self.on_compression_level_changed)
        level_layout.addWidget(self.combo_compression_level)
        image_mode_layout.addWidget(self.compression_level_widget)

        self.replace_image_row = QWidget()
        self.replace_image_row.setFixedHeight(24)
        self.replace_image_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        replace_image_layout = QHBoxLayout(self.replace_image_row)
        replace_image_layout.setContentsMargins(0, 0, 0, 0)
        replace_image_layout.setSpacing(4)
        replace_image_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.checkbox_replace_image = QCheckBox()
        self.checkbox_replace_image.setFixedSize(16, 16)
        self.checkbox_replace_image.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.checkbox_replace_image.setStyleSheet("margin-top: 1px;")
        self.checkbox_replace_image.setToolTip("Исходное изображение будет перезаписано сжатой версией")
        self.checkbox_replace_image.stateChanged.connect(self.on_replace_image_checked)
        self.checkbox_replace_image.setChecked(False)
        replace_image_layout.addWidget(
            self.checkbox_replace_image,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        replace_image_label = QLabel("Заменять файлы")
        replace_image_label.setFixedHeight(24)
        replace_image_layout.addWidget(replace_image_label, 0, Qt.AlignmentFlag.AlignVCenter)
        replace_image_layout.addStretch()
        image_mode_layout.addWidget(self.replace_image_row)

        self.compress_mode_stack.addWidget(self.image_mode_widget)
        self.compress_mode_stack.addWidget(self.pdf_mode_widget)
        self.compress_mode_stack.setCurrentWidget(self.image_mode_widget)
        self.compress_mode_stack.setFixedHeight(self.image_mode_widget.sizeHint().height())
        compress_layout.addWidget(self.compress_mode_stack)
        compress_layout.addSpacing(4)

        # Кнопка сжатия
        self.btn_compress = QPushButton("Сжать файлы")
        setup_standard_primary_button(self.btn_compress, height=28)
        self.btn_compress.clicked.connect(self.compress_files)
        self.btn_compress.setEnabled(True)
        compress_layout.addWidget(self.btn_compress)

        # Советы по сжатию
        self.compress_tips_label = QLabel()
        self.compress_tips_label.setStyleSheet("font-size: 13px; color: #FFA726; margin-top: 3px;")
        self.compress_tips_label.setWordWrap(True)
        self.compress_tips_label.setVisible(False)
        compress_layout.addWidget(self.compress_tips_label)

        # Информация о требованиях (только для PDF)
        self.compress_info_label = QLabel()
        self.compress_info_label.setStyleSheet("font-size: 13px; color: #90caf9; margin-top: 0px;")
        self.compress_info_label.setWordWrap(True)
        self.compress_info_label.setVisible(False)
        self.compress_info_label.setMaximumHeight(0)
        compress_layout.addWidget(self.compress_info_label)

        # Обновляем информацию о требованиях
        self.on_compress_type_changed(self.combo_compress_type.currentText())

        compress_card_layout.addWidget(compress_content, 0, Qt.AlignmentFlag.AlignTop)

        self._add_operations_page(self._wrap_operations_page(compress_card, "compress_page"), "Сжатие")

        self._settings_tab_index = self.operations_tab_bar.addTab("Настройки")

        self._update_operations_narrow_layout()

        return tab

    def _add_operations_page(self, page: QWidget, label: str):
        self.operations_stack.addWidget(page)
        self.operations_tab_bar.addTab(label)
        if self.operations_stack.count() == 1:
            self.operations_tab_bar.setCurrentIndex(0)
            self.operations_stack.setCurrentIndex(0)
            self._current_operations_tab_index = 0

    def _build_action_row(self, buttons: list[QPushButton]) -> tuple[QWidget, QGridLayout]:
        return self._build_rename_action_row(buttons)

    def _on_operations_tab_changed(self, index: int):
        if index == getattr(self, "_settings_tab_index", -1):
            if callable(getattr(self, "show_settings_modal", None)):
                self.show_settings_modal()
            if callable(getattr(self, "_schedule_settings_save", None)):
                self._schedule_settings_save()
            return

        if callable(getattr(self, "hide_settings_panel", None)):
            self.hide_settings_panel()

        stack_index = index
        if 0 <= stack_index < self.operations_stack.count():
            self._current_operations_tab_index = index
            self.operations_stack.setCurrentIndex(stack_index)
            if callable(getattr(self, "refresh_active_file_preview", None)):
                self.refresh_active_file_preview()
            if callable(getattr(self, "_schedule_settings_save", None)):
                self._schedule_settings_save()

    def _wrap_operations_page(self, card: QWidget, object_name: str) -> QWidget:
        page = QWidget()
        page.setObjectName(object_name)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(card)
        content_layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        page_layout.addWidget(scroll)
        return page

    def _update_operations_narrow_layout(self):
        layout = getattr(self, "_rename_buttons_layout", None)
        widget = getattr(self, "_rename_buttons_widget", None)
        btn_apply = getattr(self, "btn_apply_rename", None)
        if layout is None or widget is None or btn_apply is None:
            return

        if self._rename_buttons_compact is False:
            return
        self._rename_buttons_compact = False

        layout.addWidget(btn_apply, 0, 0, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(0)
