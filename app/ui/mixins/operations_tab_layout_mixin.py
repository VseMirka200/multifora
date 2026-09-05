
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.ui_components import (
    MenuLikeComboBox,
    setup_compact_checkbox,
    setup_standard_action_button,
    setup_standard_dropdown,
    setup_standard_danger_button,
    setup_standard_form_label,
    setup_standard_primary_button,
)
from app.core.conversion_formats import CONVERSION_CATEGORIES
from app.ui.ui_styles import build_operations_tab_bar_style
from app.ui.ui_spacing import (
    CHECKBOX_SIZE,
    CONTROL_HEIGHT,
    MARGINS_NONE,
    OPERATIONS_PAGE_MARGINS,
    SPACE_NONE,
    SPACE_SM,
    TAB_BAR_HEIGHT,
)


class OperationsTabLayoutMixin:

    def _apply_operations_tab_bar_theme(self, theme: str | None = None):
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is None:
            return
        effective = theme or getattr(self, "_effective_theme_mode", None)
        if effective not in ("light", "dark"):
            effective = (
                "light"
                if str(getattr(self, "theme_mode", "dark")).lower() == "light"
                else "dark"
            )
        tab_bar.setStyleSheet(build_operations_tab_bar_style(effective))
        foreground = "#202833" if effective == "light" else "#e3e6ea"
        button = getattr(self, "btn_settings", None)
        if button is not None:
            button.setStyleSheet(f"""
                QPushButton {{ color: {foreground}; background: transparent;
                    border: none; border-bottom: 1px solid transparent;
                    border-radius: 0px; padding: 0px 2px; font-weight: 500; }}
                QPushButton:checked {{ border-bottom: 1px solid #3d74b3; }}
            """)

    def _build_rename_action_row(
        self,
        buttons: list[QPushButton],
        margins: tuple[int, int, int, int] = (0, SPACE_SM, 0, 0),
        spacing: int = SPACE_SM,
    ) -> tuple[QWidget, QGridLayout]:
        row_widget = QWidget()
        row_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row_layout = QGridLayout(row_widget)
        row_layout.setContentsMargins(*margins)
        row_layout.setHorizontalSpacing(spacing)
        row_layout.setVerticalSpacing(SPACE_NONE)

        for index, button in enumerate(buttons):
            setup_standard_action_button(button)
            self._make_action_button_fill_width(button)
            row_layout.setColumnStretch(index, 1)
            row_layout.addWidget(button, 0, index)

        return row_widget, row_layout

    def _make_action_button_fill_width(self, button: QPushButton):
        try:
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        return button

    def _create_operation_card(
        self,
        *,
        margins: tuple[int, int, int, int] = MARGINS_NONE,
        align_top: bool = False,
    ) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*margins)
        card_layout.setSpacing(SPACE_NONE)
        if align_top:
            card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(SPACE_NONE)
        content_layout.setContentsMargins(*MARGINS_NONE)
        if align_top:
            content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            card_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignTop)
        else:
            card_layout.addWidget(content)

        return card, content_layout

    def _create_operation_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("tab_section_label")
        setup_standard_form_label(label)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _create_operation_hint_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("tab_hint_label")
        setup_standard_form_label(label)
        # Обычные подписи формы имеют фиксированную высоту 18 px. Для подсказок
        # это неверно: длинный текст переносится на несколько строк и раньше
        # рисовался поверх следующего элемента (например, кнопки метаданных).
        label.setMinimumHeight(0)
        label.setMaximumHeight(16777215)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        return label

    def _add_labeled_field(self, layout: QVBoxLayout, label_text: str, field: QWidget):
        field_layout = QVBoxLayout()
        field_layout.setContentsMargins(*MARGINS_NONE)
        field_layout.setSpacing(SPACE_SM)
        field_layout.addWidget(self._create_operation_label(label_text))
        field_layout.addWidget(field)
        layout.addLayout(field_layout)

    def _create_replace_row(self, checkbox: QCheckBox, tooltip: str, callback) -> QWidget:
        row = QWidget()
        row.setFixedHeight(CONTROL_HEIGHT)
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_NONE)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        checkbox.setFixedSize(CHECKBOX_SIZE, CHECKBOX_SIZE)
        checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        setup_compact_checkbox(checkbox)
        checkbox.setToolTip(tooltip)
        checkbox.stateChanged.connect(callback)
        checkbox.setChecked(False)
        layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addSpacing(SPACE_SM)

        label = QLabel("Заменять файлы")
        label.setFixedHeight(CONTROL_HEIGHT)
        layout.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()
        return row

    def create_operations_tab(self) -> QWidget:
        """Создаёт контейнер вкладок файловых операций."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(*MARGINS_NONE)
        tab_layout.setSpacing(SPACE_NONE)

        self.operations_tab_bar = QTabBar()
        self.operations_tab_bar.setObjectName("operations_tab_bar")
        self.operations_tab_bar.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.operations_tab_bar.setContentsMargins(*MARGINS_NONE)
        self.operations_tab_bar.setExpanding(False)
        self.operations_tab_bar.setDrawBase(False)
        self.operations_tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        self.operations_tab_bar.setUsesScrollButtons(False)
        self.operations_tab_bar.setDocumentMode(False)
        self.operations_tab_bar.setFixedHeight(TAB_BAR_HEIGHT)
        self._apply_operations_tab_bar_theme()

        self.operations_header_widget = QWidget()
        self.operations_header_widget.setObjectName("operations_header_widget")
        self.operations_header_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        operations_header_layout = QHBoxLayout(self.operations_header_widget)
        operations_header_layout.setContentsMargins(*MARGINS_NONE)
        operations_header_layout.setSpacing(SPACE_NONE)
        operations_header_layout.addWidget(self.operations_tab_bar, 0, Qt.AlignmentFlag.AlignLeft)
        operations_header_layout.addStretch(1)

        self.operations_stack = QStackedWidget()
        self.operations_stack.setObjectName("operations_stack")
        self._settings_tab_index = -1
        self._current_operations_tab_index = 0
        self.operations_tab_bar.currentChanged.connect(self._on_operations_tab_changed)
        tab_layout.addWidget(self.operations_stack)
        
        self._create_rename_operation_page()
        self._create_conversion_operation_page()
        self._create_merge_operation_page()
        self._create_metadata_operation_page()
        self._create_compression_operation_page()

        self.operations_tab_bar.tabBarClicked.connect(self._on_operation_tab_clicked)
        self.operations_tab_bar.setUsesScrollButtons(True)
        self.operations_tab_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.btn_settings = QPushButton("Настройки")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setFixedHeight(TAB_BAR_HEIGHT)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        operations_header_layout.addWidget(self.btn_settings)
        self.btn_settings.clicked.connect(self.show_settings_modal)
        self._apply_operations_tab_bar_theme()

        self._update_operations_narrow_layout()

        self._update_operations_narrow_layout()
        return tab

    def _create_rename_operation_page(self) -> None:
        """Создаёт страницу переименования."""
        rename_card, rename_layout = self._create_operation_card()
        rename_layout.setContentsMargins(SPACE_SM, SPACE_NONE, SPACE_NONE, SPACE_NONE)
        
        self.combo_templates = MenuLikeComboBox()
        self.combo_templates.setProperty("renameTemplateField", True)
        self.combo_templates.currentTextChanged.connect(self.on_template_selected)
        setup_standard_dropdown(self.combo_templates)
        self._add_labeled_field(rename_layout, "Шаблон:", self.combo_templates)
        rename_layout.addSpacing(SPACE_SM)
        
        self.template_params_widget = QWidget()
        self.template_params_widget.setObjectName("template_params_widget")
        self.template_params_widget.setVisible(False)
        self.template_params_layout = QVBoxLayout(self.template_params_widget)
        self.template_params_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.template_params_layout.setContentsMargins(*MARGINS_NONE)
        self.template_params_layout.setSpacing(SPACE_SM)
        rename_layout.addWidget(self.template_params_widget)
        
        self.btn_apply_rename = QPushButton("Начать действие")
        self.btn_apply_rename.setProperty("buttonVariant", "primary")
        self.btn_apply_rename.clicked.connect(self.apply_rename)
        self.btn_apply_rename.setEnabled(False)

        rename_buttons_widget, rename_buttons = self._build_rename_action_row(
            [self.btn_apply_rename]
        )
        self._rename_buttons_layout = rename_buttons
        self._rename_buttons_widget = rename_buttons_widget
        self._rename_buttons_compact = None

        rename_layout.addWidget(rename_buttons_widget)

        self._add_operations_page(
            self._wrap_operations_page(rename_card, "rename_page"),
            "Переименование",
        )


    def _create_conversion_operation_page(self) -> None:
        """Создаёт страницу конвертации."""
        convert_card, convert_layout = self._create_operation_card()
        convert_layout.setContentsMargins(SPACE_SM, SPACE_NONE, SPACE_NONE, SPACE_NONE)

        self.convert_file_type_combo = MenuLikeComboBox()
        self.convert_file_type_combo.addItems(["Выберите тип файла:", *CONVERSION_CATEGORIES])
        setup_standard_dropdown(self.convert_file_type_combo)
        self.convert_file_type_combo.currentIndexChanged.connect(self.update_converter_from_format)
        self.convert_file_type_combo.currentIndexChanged.connect(self.update_convert_button_state)
        self._add_labeled_field(convert_layout, "Тип файла:", self.convert_file_type_combo)
        
        self.from_convert_combo = MenuLikeComboBox()
        self.from_convert_combo.addItem("Выберите исходный формат:")
        setup_standard_dropdown(self.from_convert_combo)
        self.from_convert_combo.currentIndexChanged.connect(self.update_to_combo_based_on_from)
        self._add_labeled_field(convert_layout, "Конвертировать из:", self.from_convert_combo)
        
        self.to_convert_combo = MenuLikeComboBox()
        self.to_convert_combo.addItem("Выберите целевой формат:")
        setup_standard_dropdown(self.to_convert_combo)
        self.to_convert_combo.currentIndexChanged.connect(self.update_convert_button_state)
        self.to_convert_combo.setEnabled(False)
        self._add_labeled_field(convert_layout, "Конвертировать в:", self.to_convert_combo)

        convert_layout.addSpacing(SPACE_SM)
        
        self.btn_convert = QPushButton("Конвертировать")
        setup_standard_primary_button(self.btn_convert, height=24)
        self._make_action_button_fill_width(self.btn_convert)
        self.btn_convert.clicked.connect(self.convert_files_dual_combo)
        self.btn_convert.setEnabled(False)
        convert_layout.addWidget(self.btn_convert)

        self._add_operations_page(
            self._wrap_operations_page(convert_card, "convert_page"),
            "Конвертация",
        )


    def _create_merge_operation_page(self) -> None:
        """Создаёт страницу объединения документов."""
        merge_card, merge_layout = self._create_operation_card()
        merge_layout.setContentsMargins(SPACE_SM, SPACE_NONE, SPACE_NONE, SPACE_NONE)

        self.combo_merge_format = MenuLikeComboBox()
        self.combo_merge_format.addItem("PDF (Word и PDF)", "pdf")
        self.combo_merge_format.addItem("DOCX (только DOCX)", "docx")
        self.combo_merge_format.addItem("Авто", "auto")
        setup_standard_dropdown(self.combo_merge_format)
        self.combo_merge_format.currentIndexChanged.connect(self.on_merge_format_changed)
        self._add_labeled_field(merge_layout, "Формат результата:", self.combo_merge_format)

        merge_layout.addWidget(self._create_operation_label("Сохранить как:"))

        merge_output_row = QWidget()
        merge_output_row_layout = QHBoxLayout(merge_output_row)
        merge_output_row_layout.setContentsMargins(*MARGINS_NONE)
        merge_output_row_layout.setSpacing(SPACE_NONE)

        self.input_merge_output_path = QLineEdit()
        self.input_merge_output_path.setReadOnly(True)
        self.input_merge_output_path.setPlaceholderText("Выберите файл сохранения")
        self.input_merge_output_path.setCursor(Qt.CursorShape.PointingHandCursor)
        self.input_merge_output_path.installEventFilter(self)
        merge_output_row_layout.addWidget(self.input_merge_output_path, 1)
        merge_layout.addWidget(merge_output_row)
        merge_layout.addSpacing(SPACE_SM)

        self.btn_merge = QPushButton("Объединить")
        setup_standard_primary_button(self.btn_merge, height=24)
        self._make_action_button_fill_width(self.btn_merge)
        self.btn_merge.clicked.connect(self.merge_files)
        merge_layout.addWidget(self.btn_merge)

        self._add_operations_page(
            self._wrap_operations_page(merge_card, "merge_page"),
            "Объединение",
        )


    def _create_metadata_operation_page(self) -> None:
        """Создаёт страницу очистки метаданных."""
        metadata_card, metadata_layout = self._create_operation_card(align_top=True)
        metadata_layout.setContentsMargins(SPACE_SM, SPACE_NONE, SPACE_NONE, SPACE_NONE)

        metadata_layout.addWidget(self._create_operation_label("Что удалить:"))

        self.metadata_field_checkboxes = {}
        metadata_fields = [
            ("author", "Автор / создатель"),
            ("title", "Заголовок"),
            ("subject", "Тема / описание"),
            ("keywords", "Ключевые слова"),
            ("comments", "Комментарии / категория"),
            ("dates", "Даты создания / изменения"),
            ("application", "Программа / производитель"),
            ("custom", "Пользовательские свойства"),
        ]
        for field_key, field_label in metadata_fields:
            checkbox = QCheckBox(field_label)
            setup_compact_checkbox(checkbox)
            checkbox.stateChanged.connect(self._update_metadata_controls)
            if field_key == "custom":
                checkbox.setToolTip("Дополнительные / пользовательские свойства")
            self.metadata_field_checkboxes[field_key] = checkbox
            metadata_layout.addWidget(checkbox)

        metadata_hint = self._create_operation_hint_label(
            "Поддерживаются PDF, DOCX, ODT и DOC (DOC очищается через Microsoft Word в Windows). "
            "Если файлы не выделены, операция применяется ко всем документам в списке."
        )
        metadata_hint.setWordWrap(True)
        metadata_layout.addSpacing(SPACE_SM)
        metadata_layout.addWidget(metadata_hint)
        metadata_layout.addSpacing(SPACE_SM)

        self.btn_remove_metadata = QPushButton("Удалить выбранные")
        setup_standard_danger_button(self.btn_remove_metadata, height=28)
        self._make_action_button_fill_width(self.btn_remove_metadata)
        self.btn_remove_metadata.clicked.connect(lambda: self.remove_document_metadata(remove_all=False))
        metadata_layout.addWidget(self.btn_remove_metadata)
        metadata_layout.addSpacing(SPACE_SM)

        self.btn_remove_all_metadata = QPushButton("Удалить все метаданные")
        setup_standard_danger_button(self.btn_remove_all_metadata, height=28)
        self._make_action_button_fill_width(self.btn_remove_all_metadata)
        self.btn_remove_all_metadata.clicked.connect(lambda: self.remove_document_metadata(remove_all=True))
        metadata_layout.addWidget(self.btn_remove_all_metadata)
        self._update_metadata_controls()

        self._add_operations_page(
            self._wrap_operations_page(metadata_card, "metadata_page"),
            "Метаданные",
        )


    def _create_pdf_compression_mode(self) -> QWidget:
        """Создаёт набор элементов для сжатия PDF."""
        self.pdf_mode_widget = QWidget()
        pdf_mode_layout = QVBoxLayout(self.pdf_mode_widget)
        pdf_mode_layout.setSpacing(SPACE_NONE)
        pdf_mode_layout.setContentsMargins(*MARGINS_NONE)

        self.pdf_method_widget = QWidget()
        pdf_method_layout = QVBoxLayout(self.pdf_method_widget)
        pdf_method_layout.setSpacing(SPACE_NONE)
        pdf_method_layout.setContentsMargins(*MARGINS_NONE)

        self.combo_pdf_method = MenuLikeComboBox()
        self.combo_pdf_method.addItems(
            [
                "Авто (рекомендуется)",
                "Максимальное сжатие",
                "Сохранить качество",
                "Только оптимизация",
            ]
        )
        setup_standard_dropdown(self.combo_pdf_method)
        self.combo_pdf_method.currentTextChanged.connect(self.on_pdf_method_changed)
        self._add_labeled_field(
            pdf_method_layout,
            "Метод сжатия PDF:",
            self.combo_pdf_method,
        )

        self.checkbox_replace_pdf = QCheckBox()
        self.replace_pdf_row = self._create_replace_row(
            self.checkbox_replace_pdf,
            "Исходный PDF будет перезаписан сжатой версией",
            self.on_replace_pdf_checked,
        )

        self.pdf_method_warning_label = self._create_operation_hint_label("")
        self.pdf_method_warning_label.setWordWrap(True)
        self.pdf_method_warning_label.setVisible(False)
        pdf_method_layout.addWidget(self.pdf_method_warning_label)
        pdf_mode_layout.addWidget(self.pdf_method_widget)
        pdf_mode_layout.addWidget(self.replace_pdf_row)
        return self.pdf_mode_widget

    def _create_image_compression_mode(self) -> QWidget:
        """Создаёт набор элементов для сжатия изображений."""
        self.image_mode_widget = QWidget()
        image_mode_layout = QVBoxLayout(self.image_mode_widget)
        image_mode_layout.setContentsMargins(*MARGINS_NONE)
        image_mode_layout.setSpacing(SPACE_NONE)

        self.compression_level_widget = QWidget()
        level_layout = QVBoxLayout(self.compression_level_widget)
        level_layout.setContentsMargins(*MARGINS_NONE)
        level_layout.setSpacing(SPACE_NONE)

        self.combo_compression_level = MenuLikeComboBox()
        levels = (
            ("Максимальное сжатие (40%)", 40),
            ("Сбалансированное (65%)", 65),
            ("Хорошее качество (85%)", 85),
            ("Максимальное качество (95%)", 95),
        )
        for label, value in levels:
            self.combo_compression_level.addItem(label, value)
        self.combo_compression_level.setCurrentIndex(2)
        setup_standard_dropdown(self.combo_compression_level)
        self.combo_compression_level.currentIndexChanged.connect(
            self.on_compression_level_changed
        )
        self._add_labeled_field(
            level_layout,
            "Уровень сжатия PNG/JPG:",
            self.combo_compression_level,
        )
        image_mode_layout.addWidget(self.compression_level_widget)

        self.checkbox_replace_image = QCheckBox()
        self.replace_image_row = self._create_replace_row(
            self.checkbox_replace_image,
            "Исходное изображение будет перезаписано сжатой версией",
            self.on_replace_image_checked,
        )
        image_mode_layout.addWidget(self.replace_image_row)
        return self.image_mode_widget

    def _create_compression_operation_page(self) -> None:
        """Создаёт страницу сжатия."""
        compress_card, compress_layout = self._create_operation_card(align_top=True)
        compress_layout.setContentsMargins(
            SPACE_SM,
            SPACE_NONE,
            SPACE_NONE,
            SPACE_NONE,
        )

        self.combo_compress_type = MenuLikeComboBox()
        self.combo_compress_type.addItems(["Изображения", "PDF документы"])
        setup_standard_dropdown(self.combo_compress_type)
        self.combo_compress_type.currentTextChanged.connect(
            self.on_compress_type_changed
        )
        self._add_labeled_field(
            compress_layout,
            "Тип файлов:",
            self.combo_compress_type,
        )

        self.compress_mode_stack = QStackedWidget()
        self.compress_mode_stack.setContentsMargins(*MARGINS_NONE)
        self.compress_mode_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        image_mode = self._create_image_compression_mode()
        pdf_mode = self._create_pdf_compression_mode()
        self.compress_mode_stack.addWidget(image_mode)
        self.compress_mode_stack.addWidget(pdf_mode)
        self.compress_mode_stack.setCurrentWidget(image_mode)
        self.compress_mode_stack.setFixedHeight(image_mode.sizeHint().height())
        compress_layout.addWidget(self.compress_mode_stack)

        self.btn_compress = QPushButton("Сжать файлы")
        setup_standard_primary_button(self.btn_compress, height=24)
        self._make_action_button_fill_width(self.btn_compress)
        self.btn_compress.clicked.connect(self.compress_files)
        self.btn_compress.setEnabled(True)
        compress_layout.addSpacing(SPACE_SM)
        compress_layout.addWidget(self.btn_compress)

        self.compress_tips_label = self._create_operation_hint_label("")
        self.compress_tips_label.setWordWrap(True)
        self.compress_tips_label.setVisible(False)
        compress_layout.addWidget(self.compress_tips_label)

        self.compress_info_label = self._create_operation_hint_label("")
        self.compress_info_label.setWordWrap(True)
        self.compress_info_label.setVisible(False)
        self.compress_info_label.setMaximumHeight(0)
        compress_layout.addWidget(self.compress_info_label)

        self.on_compress_type_changed(self.combo_compress_type.currentText())
        page = self._wrap_operations_page(compress_card, "compress_page")
        self._add_operations_page(page, "Сжатие")


    def _add_operations_page(self, page: QWidget, label: str) -> None:
        self.operations_stack.addWidget(page)
        self.operations_tab_bar.addTab(label)
        if self.operations_stack.count() == 1:
            self.operations_tab_bar.setCurrentIndex(0)
            self.operations_stack.setCurrentIndex(0)
            self._current_operations_tab_index = 0

    def _on_operation_tab_clicked(self, index: int) -> None:
        host = getattr(self, "settings_panel_host", None)
        if host is not None and not host.isHidden() and index == self.operations_tab_bar.currentIndex():
            self._on_operations_tab_changed(index)

    def _on_operations_tab_changed(self, index: int) -> None:
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
        scroll.setObjectName("operation_page_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setContentsMargins(*MARGINS_NONE)
        scroll.setViewportMargins(0, 0, 0, 0)
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        content = QWidget()
        content.setObjectName("operation_page_content")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(*MARGINS_NONE)
        content_layout.setSpacing(SPACE_NONE)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(card)
        content_layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(*OPERATIONS_PAGE_MARGINS)
        page_layout.setSpacing(SPACE_NONE)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        page_layout.addWidget(scroll)
        return page

    def _update_operations_narrow_layout(self):
        # Левая панель изменяет ширину через основной разделитель, поэтому элементы
        # должны оставаться удобными и при узкой, и при широкой компоновке.
        stack = getattr(self, "operations_stack", None)
        panel_width = (
            stack.viewport().width()
            if hasattr(stack, "viewport")
            else (stack.width() if stack else 0)
        )
        compact = bool(panel_width and panel_width < 310)

        rename_layout = getattr(self, "_rename_buttons_layout", None)
        rename_widget = getattr(self, "_rename_buttons_widget", None)
        btn_apply = getattr(self, "btn_apply_rename", None)
        if rename_layout is not None and rename_widget is not None and btn_apply is not None:
            if self._rename_buttons_compact is not False:
                self._rename_buttons_compact = False
                rename_layout.addWidget(btn_apply, 0, 0, 1, 1)
                rename_layout.setColumnStretch(0, 1)
                rename_layout.setHorizontalSpacing(SPACE_NONE)
                rename_layout.setVerticalSpacing(SPACE_NONE)
