from PySide6.QtCore import (
    Qt,
    QUrl,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.app_identity import (
    GITHUB_NEW_ISSUE_URL,
    GUIDE_URL,
)
from app.ui.conversion_panel import ConversionPanel
from app.ui.operation_layout import add_labeled_field, create_operation_label
from app.ui.ribbon import RibbonNavigation, RibbonPage, RibbonStack
from app.ui.support_page import SupportPage
from app.ui.typography import BODY_PX
from app.ui.ui_components import (
    IconButton,
    MenuLikeComboBox,
    resolve_widget_theme_mode,
    setup_clickable_checkbox_label,
    setup_standard_dropdown,
    setup_standard_form_label,
    setup_standard_line_input,
    setup_standard_primary_button,
    setup_standard_secondary_button,
)
from app.ui.ui_styles import (
    CHECKBOX_SIZE,
    CONTROL_HEIGHT,
    DROPDOWN_HEIGHT,
    MAIN_BUTTON_HEIGHT,
    MARGINS_NONE,
    SPACE_NONE,
    SPACE_SM,
    TAB_BAR_HEIGHT,
    build_operations_tab_bar_style,
)


class OperationsTabLayoutMixin:
    # Собирает страницы операций; выполнение файловых задач остаётся в обработчиках.

    def _apply_operations_tab_bar_theme(self, theme: str | None = None):
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is None:
            return
        effective = resolve_widget_theme_mode(self, theme)
        tab_bar.setStyleSheet(build_operations_tab_bar_style(effective))

    def _create_operation_hint_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("tab_hint_label")
        setup_standard_form_label(label)
        # Обычные подписи формы имеют высоту одной строки. Для подсказок
        # это неверно: длинный текст переносится на несколько строк и раньше
        # рисовался поверх следующего элемента.
        label.setMinimumHeight(0)
        label.setMaximumHeight(16777215)
        label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        return label

    def _create_replace_row(
        self, checkbox: QCheckBox, tooltip: str, callback
    ) -> QWidget:
        row = QWidget()
        row.setFixedHeight(CONTROL_HEIGHT)
        row.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_NONE)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        checkbox.setFixedSize(CHECKBOX_SIZE + 2, CHECKBOX_SIZE + 2)
        checkbox.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        checkbox.setToolTip(tooltip)
        checkbox.stateChanged.connect(callback)
        checkbox.setChecked(False)
        layout.addWidget(
            checkbox,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addSpacing(SPACE_SM)

        self.replace_files_label = QLabel("Заменять файлы")
        self.replace_files_label.setFixedHeight(CONTROL_HEIGHT)
        setup_clickable_checkbox_label(
            self.replace_files_label, checkbox, tooltip=tooltip
        )
        layout.addWidget(
            self.replace_files_label, 0, Qt.AlignmentFlag.AlignVCenter
        )
        layout.addStretch()
        return row

    def create_operations_tab(self) -> QWidget:
        """Создаёт контейнер вкладок файловых операций."""
        self.operations_tab_bar = RibbonNavigation()
        self.operations_tab_bar.setFixedHeight(TAB_BAR_HEIGHT)
        self._apply_operations_tab_bar_theme()

        self.operations_header_widget = QWidget()
        self.operations_header_widget.setObjectName("operations_header_widget")
        self.operations_header_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        header = QHBoxLayout(self.operations_header_widget)
        header.setContentsMargins(20, 0, 20, 0)
        header.setSpacing(0)
        header.addWidget(self.operations_tab_bar)

        self.operations_stack = RibbonStack()
        self.operations_stack.setObjectName("operations_stack")
        self.operations_stack.currentChanged.connect(self.operations_stack.fit_pages)
        self.operations_tab_bar.currentChanged.connect(
            self._on_operations_tab_changed
        )

        self.operations_tab_bar.tabBarDoubleClicked.connect(self._toggle_ribbon)
        self._create_rename_operation_page()
        self._create_conversion_operation_page()
        self._create_compression_operation_page()
        self._create_merge_operation_page()
        for button in (self.btn_open_rename_history, self.btn_convert, self.btn_compress, self.btn_merge):
            button.setFixedHeight(MAIN_BUTTON_HEIGHT)

        self.operations_tab_bar.layout().addStretch(1)
        self._settings_tab_index = self.operations_stack.count()
        self._add_operations_page(RibbonPage("settings"), "Настройки")
        self._help_tab_index = self.operations_stack.count()
        self._add_operations_page(RibbonPage("help"), "Справка")
        return self.operations_stack

    def _create_support_page(self):
        page = SupportPage()
        self.check_updates_action = page.commands["updates"]
        self.check_updates_action.clicked.connect(self.check_updates_now)
        page.commands["save"].clicked.connect(self.show_operation_log)
        page.commands["help"].clicked.connect(self.show_help_modal)
        page.commands["bug"].clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_NEW_ISSUE_URL)))
        page.guide.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GUIDE_URL)))
        return page

    def _toggle_ribbon(self, index):
        if 0 <= index < self._settings_tab_index:
            self.ribbon_panel.setVisible(self.ribbon_panel.isHidden())

    def _create_rename_operation_page(self) -> None:
        """Создаёт страницу переименования."""
        self.combo_templates = MenuLikeComboBox()
        self.combo_templates.setProperty("ruleSelector", True)
        self.combo_templates.currentTextChanged.connect(
            self.on_template_selected
        )
        setup_standard_dropdown(self.combo_templates)

        self.template_params_widget = QWidget()
        self.template_params_widget.setObjectName("template_params_widget")
        self.template_params_widget.setVisible(False)
        self.template_params_layout = QVBoxLayout(self.template_params_widget)
        self.template_params_layout.setContentsMargins(*MARGINS_NONE)
        self.template_params_layout.setSpacing(SPACE_SM)

        self.btn_apply_rename = IconButton("Переименовать")
        self.btn_apply_rename.setAccessibleName("Переименовать")
        self.btn_apply_rename.setToolTip("Переименовать")
        self.btn_apply_rename.clicked.connect(self.apply_rename)
        self.btn_apply_rename.setEnabled(False)

        setup_standard_primary_button(self.btn_apply_rename, expand=False)
        self.btn_apply_rename.setFixedHeight(DROPDOWN_HEIGHT)
        page = RibbonPage("rename", with_card=True)
        self.btn_open_rename_history = IconButton("История")
        setup_standard_secondary_button(self.btn_open_rename_history)
        self.btn_open_rename_history.clicked.connect(self.show_rename_history_dialog)

        row = page.row
        rule_label = add_labeled_field(row, "Правило", self.combo_templates)
        parameters = QVBoxLayout()
        parameters.setSpacing(SPACE_SM)
        parameters.addWidget(self.template_params_widget)
        row.addLayout(parameters, 3)
        action = QVBoxLayout()
        action.setContentsMargins(0, rule_label.sizeHint().height() + SPACE_SM, 0, 0)
        action.addWidget(self.btn_apply_rename)
        action.addStretch()
        row.addLayout(action)
        row.setAlignment(row.itemAt(0).layout(), Qt.AlignmentFlag.AlignTop)
        self._add_operations_page(page, "Переименование")

    def _create_conversion_operation_page(self) -> None:
        panel = ConversionPanel(self)
        self.conversion_panel = panel
        self.convert_file_type_combo = panel.convert_file_type_combo
        self.from_convert_combo = panel.from_convert_combo
        self.to_convert_combo = panel.to_convert_combo
        self.combo_conversion_output_mode = panel.combo_conversion_output_mode
        self.input_conversion_output_path = panel.input_conversion_output_path
        self.btn_select_conversion_output_folder = panel.btn_select_conversion_output_folder
        self.conversion_output_path_section = panel.conversion_output_path_section

        panel.category_changed.connect(self.update_converter_from_format)
        panel.category_changed.connect(self.update_convert_button_state)
        panel.source_changed.connect(self.on_conversion_source_changed)
        panel.target_changed.connect(self.update_convert_button_state)
        panel.output_mode_changed.connect(self.on_conversion_output_mode_changed)
        panel.output_folder_requested.connect(self.select_conversion_output_folder)
        panel.conversion_requested.connect(self.convert_files_dual_combo)
        self.on_conversion_output_mode_changed()
        self.btn_convert = panel.btn_convert
        page = RibbonPage("convert", with_card=True)
        panel.card.setParent(page)
        panel.card.hide()
        page.row.addWidget(panel.formats, 1)
        self._add_operations_page(page, "Конвертация")

    def _create_merge_operation_page(self) -> None:
        """Создаёт страницу объединения документов."""

        self.merge_format_hint_label = QLabel(
            "Объединяйте файлы одного формата: PDF с PDF или DOCX с DOCX"
        )
        self.merge_format_hint_label.setWordWrap(True)

        self.btn_merge = IconButton("Объединить")
        setup_standard_primary_button(self.btn_merge)
        self.btn_merge.clicked.connect(self.merge_files)
        self.btn_merge.setEnabled(False)
        self._update_merge_button_state()

        page = RibbonPage("merge", with_card=True)
        instructions = QVBoxLayout()
        instructions.setSpacing(3)
        self.merge_format_hint_label.setStyleSheet(f"font-size: {BODY_PX}px;")
        instructions.addWidget(self.merge_format_hint_label)
        instructions.addWidget(QLabel("Расставьте миниатюры страниц в нужном порядке и нажмите «Объединить»"))
        page.row.addLayout(instructions)
        self._add_operations_page(page, "Объединение")

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
        self.combo_pdf_method.currentTextChanged.connect(
            self.on_pdf_method_changed
        )
        add_labeled_field(
            pdf_method_layout,
            "Метод сжатия PDF:",
            self.combo_pdf_method,
        )

        self.checkbox_replace_pdf = QCheckBox()
        self.replace_pdf_row = self._create_replace_row(
            self.checkbox_replace_pdf,
            "Исходный PDF будет перезаписан сжатой версией",
            self._refresh_compression_preview_if_available,
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
            self._refresh_compression_preview_if_available
        )
        add_labeled_field(
            level_layout,
            "Качество JPEG/WebP",
            self.combo_compression_level,
        )
        fields = QHBoxLayout()
        fields.setSpacing(12)
        fields.addWidget(self.compression_level_widget, 1)
        image_mode_layout.addLayout(fields)

        self.combo_image_output_mode = MenuLikeComboBox()
        self.combo_image_output_mode.addItem(
            "Заменять исходные файлы", "replace"
        )
        self.combo_image_output_mode.addItem(
            "Рядом с исходными файлами", "alongside"
        )
        self.combo_image_output_mode.addItem("В отдельную папку", "custom")
        self.combo_image_output_mode.setCurrentIndex(1)
        setup_standard_dropdown(self.combo_image_output_mode)
        self.combo_image_output_mode.currentIndexChanged.connect(
            self.on_image_output_mode_changed
        )
        add_labeled_field(
            fields,
            "Способ сохранения:",
            self.combo_image_output_mode,
        )
        fields.setStretch(1, 1)

        self.image_output_path_widget = QWidget()
        image_output_path_layout = QHBoxLayout(self.image_output_path_widget)
        image_output_path_layout.setContentsMargins(*MARGINS_NONE)
        image_output_path_layout.setSpacing(SPACE_SM)

        self.input_image_output_path = QLineEdit()
        self.input_image_output_path.setReadOnly(True)
        self.input_image_output_path.setPlaceholderText(
            "Выберите папку сохранения"
        )
        setup_standard_line_input(self.input_image_output_path)
        image_output_path_layout.addWidget(self.input_image_output_path, 1)

        self.btn_select_image_output_path = IconButton("Выбрать папку")
        setup_standard_secondary_button(self.btn_select_image_output_path)
        self.btn_select_image_output_path.clicked.connect(
            self.select_image_output_folder
        )
        image_output_path_layout.addWidget(self.btn_select_image_output_path, 1)

        self.image_output_path_section = QWidget()
        image_output_section_layout = QVBoxLayout(
            self.image_output_path_section
        )
        image_output_section_layout.setContentsMargins(*MARGINS_NONE)
        image_output_section_layout.setSpacing(SPACE_SM)
        image_output_section_layout.addWidget(
            create_operation_label("Папка сохранения:")
        )
        image_output_section_layout.addWidget(self.image_output_path_widget)
        image_mode_layout.addWidget(self.image_output_path_section)
        self.on_image_output_mode_changed()
        return self.image_mode_widget

    def _create_compression_operation_page(self) -> None:
        """Создаёт страницу сжатия."""
        compress_layout = QVBoxLayout()
        compress_layout.setSpacing(SPACE_SM)

        self.combo_compress_type = MenuLikeComboBox()
        self.combo_compress_type.addItems(["Изображения", "PDF документы"])
        setup_standard_dropdown(self.combo_compress_type)
        self.combo_compress_type.currentTextChanged.connect(
            self.on_compress_type_changed
        )
        self.combo_compress_type.setAccessibleName("Тип файлов")
        self.combo_compress_type.setMinimumWidth(165)

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

        self.btn_compress = IconButton("Сжать файлы")
        setup_standard_primary_button(self.btn_compress)
        self.btn_compress.clicked.connect(self.compress_files)
        self.btn_compress.setEnabled(False)

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
        page = RibbonPage("compress", with_card=True)
        self.combo_compress_type.setMaximumWidth(360)
        add_labeled_field(page.row, "Тип файлов", self.combo_compress_type)
        page.row.setStretch(0, 1)
        page.row.setAlignment(page.row.itemAt(0).layout(), Qt.AlignmentFlag.AlignTop)
        page.row.addLayout(compress_layout, 2)
        self._add_operations_page(page, "Сжатие")

    def _add_operations_page(self, page: QWidget, label: str) -> None:
        self.operations_stack.addWidget(page)
        tab_index = self.operations_tab_bar.addTab(label)
        # Не привязываем логику операций к переводу видимых названий вкладок.
        self.operations_tab_bar.setTabData(
            tab_index, page.objectName().removesuffix("_page")
        )
        if self.operations_stack.count() == 1:
            self.operations_tab_bar.setCurrentIndex(0)
            self.operations_stack.setCurrentIndex(0)

    def _on_operations_tab_changed(self, index: int) -> None:
        # Добавление первой вкладки может вызвать currentChanged до создания
        # списка файлов. Обновление списка в этот момент завершило бы процесс
        # из-за исключения в слоте Qt.
        if hasattr(self, "launch_buttons"):
            operation = self.operations_tab_bar.tabData(index)
            self.rename_status_group.setVisible(operation == "rename")
            if operation in self.launch_buttons:
                self.operation_result_panel.launch_stack.setCurrentWidget(self.launch_buttons[operation])
        if not hasattr(self, "list_files"):
            if 0 <= index < self.operations_stack.count():
                self.operations_stack.setCurrentIndex(index)
            return
        if index == self._help_tab_index:
            self._show_header_panel(self.support_page)
            return
        if index == self._settings_tab_index:
            self.show_settings_modal()
            return
        if callable(getattr(self, "sync_file_preview_columns", None)):
            self.sync_file_preview_columns()
        merge = self._active_operation_id() == "merge"
        if hasattr(self, "merge_pages_panel"):
            self.list_files.setVisible(not merge)
            self.merge_pages_panel.setVisible(merge)
            if merge:
                self._update_merge_button_state()
        self.list_files.keyboard_reordering_enabled = merge
        if merge:
            self.list_files.set_manual_sorting(True)
        if callable(getattr(self, "hide_settings_panel", None)):
            self.hide_settings_panel()

        stack_index = index
        if 0 <= stack_index < self.operations_stack.count():
            self.operations_stack.setCurrentIndex(stack_index)
            # Для объединения очередь показывает только PDF и DOCX; при
            # возврате на другую вкладку скрытые строки снова становятся видны.
            if callable(getattr(self, "update_file_list", None)):
                self.update_file_list()
            if callable(getattr(self, "refresh_active_file_preview", None)):
                self.refresh_active_file_preview()
            if callable(getattr(self, "_schedule_settings_save", None)):
                self._schedule_settings_save()
