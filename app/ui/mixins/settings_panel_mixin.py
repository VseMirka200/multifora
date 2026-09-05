
import concurrent.futures

from PyQt6.QtCore import QTimer, Qt, QUrl, QSize
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.update_checker import REPO_PAGE, check_for_updates
from app.core.app_identity import APP_DISPLAY_NAME, APP_TECHNICAL_NAME, APP_VERSION
from app.core.app_icons import _get_app_icon_qt_path
from app.core.conversion_formats import CATEGORY_SOURCE_FORMATS
from app.ui.ui_components import (
    LeftAlignedToolButton,
    MenuLikeComboBox,
    apply_standard_menu_style,
    setup_standard_action_button,
    setup_standard_dropdown,
    setup_standard_line_input,
    setup_standard_form_label,
    setup_compact_checkbox,
    sync_standard_menu_width,
)
from app.ui.ui_spacing import (
    CHECKBOX_SIZE,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    SETTINGS_PANEL_MARGINS,
    SETTINGS_PANEL_COLUMN_GAP,
    SPACE_NONE,
    SPACE_SM,
)
from app.core.app_utils import _log_ignored_error


class SettingsPanelMixin:
    @staticmethod
    def _setup_settings_checkbox(checkbox: QCheckBox):
        setup_compact_checkbox(checkbox)
        return checkbox

    def _create_settings_checkbox_row(self, text: str, tooltip: str = ""):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_SM)

        checkbox = QCheckBox()
        checkbox.setFixedSize(CHECKBOX_SIZE, CHECKBOX_SIZE)
        checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._setup_settings_checkbox(checkbox)
        if tooltip:
            checkbox.setToolTip(tooltip)
        layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            label.setToolTip(tooltip)
        layout.addWidget(label, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        def _toggle_checkbox(_event):
            if checkbox.isEnabled():
                checkbox.toggle()

        label.mouseReleaseEvent = _toggle_checkbox
        return row, checkbox

    def _create_settings_select_row(
        self,
        label_text: str,
        field: QWidget,
        *,
        label_width: int = 60,
    ):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_NONE)

        label = QLabel(label_text)
        label.setFixedWidth(label_width)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label)
        layout.addWidget(field, 0)
        layout.addStretch()
        return row

    def _create_settings_page_card(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(*MARGINS_NONE)
        page_layout.setSpacing(SPACE_NONE)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll = QScrollArea()
        scroll.setObjectName("settings_page_scroll")
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        scroll.setContentsMargins(*MARGINS_NONE)
        scroll.setViewportMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("settings_page_content")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(*MARGINS_NONE)
        content_layout.setSpacing(SPACE_NONE)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        card = QFrame()
        card.setObjectName("settings_card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*MARGINS_NONE)
        card_layout.setSpacing(SPACE_NONE)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        content_layout.addWidget(card, 1)
        scroll.setWidget(content)
        return page, card_layout

    def _add_settings_page(self) -> QVBoxLayout:
        page, card_layout = self._create_settings_page_card()
        self.settings_stack.addWidget(page)
        return card_layout

    def _ensure_settings_panel_widget(self):
        if not hasattr(self, "settings_panel_widget") or self.settings_panel_widget is None:
            self.settings_panel_widget = self.create_settings_tab()

        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host_layout = host.layout()
            if host_layout is not None and host_layout.indexOf(self.settings_panel_widget) < 0:
                self.settings_panel_widget.setParent(None)
                host_layout.addWidget(self.settings_panel_widget)
        return self.settings_panel_widget

    def show_settings_modal(self):
        """Показывает панель настроек поверх рабочей области."""
        settings_widget = self._ensure_settings_panel_widget()
        self.btn_settings.setChecked(True)
        if callable(getattr(self, "_ensure_rename_history_settings_page", None)):
            self._ensure_rename_history_settings_page()

        host = getattr(self, "settings_panel_host", None)
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            tab_bar.setProperty("settingsActive", True)
            self._apply_operations_tab_bar_theme()

        if host is not None:
            host.setVisible(True)
            host.adjustSize()
            host.updateGeometry()
        splitter = getattr(self, "main_splitter", None)
        if splitter is not None:
            splitter.setVisible(False)

        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(settings_widget)

        self.log_event("Открыта панель настроек")
        try:
            self.load_logs_into_view()
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin.show_settings_modal", error)
        if hasattr(self, "settings_nav") and self.settings_nav is not None:
            target_row = getattr(self, "_pending_settings_nav_row", self.settings_nav.currentRow())
            if not isinstance(target_row, int) or target_row < 0 or target_row >= self.settings_nav.count():
                target_row = 0
            self.settings_nav.setCurrentRow(target_row)

    def hide_settings_panel(self):
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            tab_bar.setProperty("settingsActive", False)
            self._apply_operations_tab_bar_theme()
        button = getattr(self, "btn_settings", None)
        if button is not None:
            button.setChecked(False)
        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host.setVisible(False)
        splitter = getattr(self, "main_splitter", None)
        if splitter is not None:
            splitter.setVisible(True)

    def _ensure_about_settings_page(self):
        if not hasattr(self, "_about_settings_row"):
            self._about_settings_row = self.settings_stack.count()
            item = QListWidgetItem("О программе")
            item.setFont(self.settings_nav.item(0).font())
            item.setSizeHint(QSize(self._settings_nav_base_width, self._settings_nav_item_height))
            self.settings_nav.addItem(item)
            layout = self._add_settings_page()
            layout.setSpacing(SPACE_SM)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            card = layout.parentWidget()
            card.parentWidget().layout().setAlignment(Qt.AlignmentFlag.AlignTop)
            self.settings_stack.widget(self._about_settings_row).layout().setAlignment(
                Qt.AlignmentFlag.AlignTop
            )
            icon = QLabel()
            icon.setPixmap(QIcon(_get_app_icon_qt_path() or "").pixmap(64, 64))
            layout.addWidget(icon)
            title = QLabel(f"{APP_DISPLAY_NAME} ({APP_TECHNICAL_NAME})")
            font = title.font()
            font.setPointSize(18)
            font.setBold(True)
            title.setFont(font)
            layout.addWidget(title)
            paragraphs = [
                f"Версия: {APP_VERSION}",
                "Приложение для пакетной обработки файлов и папок. "
                "Добавляйте файлы кнопками или перетаскивайте их в окно.",
                "Возможности: переименование по шаблонам с предварительным просмотром "
                "и историей изменений; конвертация документов и изображений; "
                "объединение документов в PDF и DOCX; удаление метаданных; сжатие файлов.",
                "Исходные форматы документов: " + ", ".join(CATEGORY_SOURCE_FORMATS["Документы"]) + ".",
                "Исходные форматы изображений: " + ", ".join(CATEGORY_SOURCE_FORMATS["Изображения"]) + ".",
                "Доступность преобразований зависит от формата и установленных компонентов. "
                "Для отдельных операций с документами нужен Microsoft Word, "
                "для сжатия PDF используется Ghostscript.",
                "В настройках доступны светлая и тёмная темы, поведение после операций, "
                "ярлыки и контекстное меню Windows, проверка обновлений, логи и история переименований.",
            ]
            for text in paragraphs:
                label = QLabel(text)
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                layout.addWidget(label)
            repo = QPushButton("Проект на GitHub")
            setup_standard_action_button(repo)
            repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_PAGE)))
            layout.addWidget(repo, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addStretch()

    def _ensure_rename_history_settings_page(self):
        page = getattr(self, "rename_history_settings_page", None)
        if page is None:
            page = QWidget()
            page.setObjectName("rename_history_settings_page")
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(*MARGINS_NONE)
            page_layout.setSpacing(SPACE_NONE)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            content = QWidget()
            content.setObjectName("rename_history_settings_content")
            content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(*MARGINS_NONE)
            content_layout.setSpacing(SPACE_NONE)
            content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            history_label = QLabel("История переименований")
            history_label.setObjectName("settings_page_title_plain")
            setup_standard_form_label(history_label)
            history_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            content_layout.addWidget(history_label)

            self.rename_history_list = QListWidget()
            self.rename_history_list.setObjectName("rename_history_list")
            self.rename_history_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.rename_history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.rename_history_list.currentRowChanged.connect(self.on_history_row_changed)
            content_layout.addWidget(self.rename_history_list, 1)

            self.btn_history_undo = QPushButton("Откатить")
            self.btn_history_undo.clicked.connect(self.undo_last_rename)
            self.btn_history_undo.setEnabled(False)
            history_buttons_widget, _ = self._build_rename_action_row([self.btn_history_undo])
            content_layout.addWidget(history_buttons_widget)

            page_layout.addWidget(content, 1)
            self.rename_history_settings_page = page

        settings_stack = getattr(self, "settings_stack", None)
        if settings_stack is not None and settings_stack.indexOf(page) < 0:
            settings_stack.addWidget(page)

        settings_nav = getattr(self, "settings_nav", None)
        history_items = (
            settings_nav.findItems("История переименований", Qt.MatchFlag.MatchExactly)
            if settings_nav is not None
            else []
        )
        if settings_nav is not None and not history_items:
            settings_nav.addItem("История переименований")
            try:
                item = settings_nav.item(settings_nav.count() - 1)
                if item is not None:
                    item.setSizeHint(
                QSize(
                    self._settings_nav_base_width,
                    getattr(self, "_settings_nav_item_height", 36),
                )
            )
            except Exception as error:
                _log_ignored_error("SettingsPanelMixin._ensure_rename_history_settings_page", error)

        self._refresh_rename_history_view()
        self._update_undo_button()

        return page

    def create_settings_tab(self):
        """Создает панель настроек с категориями слева и содержимым справа."""
        tab = QWidget()
        tab.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        settings_font = QFont()
        settings_font.setPointSize(13)
        tab.setFont(settings_font)
        root_layout = QHBoxLayout(tab)
        root_layout.setContentsMargins(*SETTINGS_PANEL_MARGINS)
        root_layout.setSpacing(SETTINGS_PANEL_COLUMN_GAP)

        self.settings_nav = QListWidget()
        self.settings_nav.setObjectName("settings_nav")
        self._settings_nav_base_width = 192
        self.settings_nav.setFixedWidth(self._settings_nav_base_width)
        self.settings_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_nav.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.settings_nav.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.settings_nav.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.settings_nav.setWordWrap(True)
        self.settings_nav.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.settings_nav.setSpacing(0)
        self.settings_nav.setUniformItemSizes(True)
        self._settings_nav_item_height = 36
        nav_font = QFont()
        nav_font.setPointSize(10)
        for title in ["Основное", "Обновления", "Логи"]:
            item = QListWidgetItem(title)
            item.setFont(nav_font)
            item.setSizeHint(QSize(self._settings_nav_base_width, self._settings_nav_item_height))
            self.settings_nav.addItem(item)
        self.settings_nav.verticalScrollBar().rangeChanged.connect(
            lambda _min, _max: self._update_settings_nav_width()
        )
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(*MARGINS_NONE)
        nav_layout.setSpacing(SPACE_NONE)
        nav_layout.addWidget(self.settings_nav, 1)

        root_layout.addWidget(nav_container, 0)

        self.settings_stack = QStackedWidget()
        root_layout.addWidget(self.settings_stack, 1)

        main_card_layout = self._add_settings_page()
        main_card_layout.setSpacing(SPACE_SM)

        def _add_settings_section_title(layout: QVBoxLayout, text: str):
            label = QLabel(text.upper())
            label.setObjectName("settings_page_title")
            setup_standard_form_label(label)
            font = label.font()
            font.setPointSize(16)
            font.setBold(True)
            label.setFont(font)
            label.setStyleSheet("font-size: 16px; font-weight: 800; margin: 0px; padding: 0px;")
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            label.setFixedHeight(24)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(label)
            separator = QFrame()
            separator.setObjectName("settings_section_separator")
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Plain)
            separator.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            separator.setFixedHeight(3)
            layout.addWidget(separator)

        def _add_settings_section_divider(layout: QVBoxLayout):
            divider = QFrame()
            divider.setObjectName("settings_section_separator")
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setFrameShadow(QFrame.Shadow.Plain)
            divider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            divider.setFixedHeight(3)
            layout.addWidget(divider)
            layout.addSpacing(SPACE_SM)

        self.theme_mode_combo = MenuLikeComboBox()
        setup_standard_dropdown(self.theme_mode_combo, fixed_width=200)
        self.theme_mode_combo.addItem("Как в системе", "system")
        self.theme_mode_combo.addItem("Темная", "dark")
        self.theme_mode_combo.addItem("Светлая", "light")
        self.theme_mode_combo.currentIndexChanged.connect(self._on_theme_mode_changed)
        _add_settings_section_title(main_card_layout, "Внешний вид")
        theme_row = self._create_settings_select_row("Тема:", self.theme_mode_combo, label_width=40)
        main_card_layout.addWidget(theme_row)

        _add_settings_section_divider(main_card_layout)
        _add_settings_section_title(main_card_layout, "Поведение")

        auto_clear_row, self.auto_clear_checkbox = self._create_settings_checkbox_row(
            "Автоматически очищать список после операций",
            "После завершения копирования/переименования/конвертации список файлов будет очищен автоматически.",
        )
        self.auto_clear_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        main_card_layout.addWidget(auto_clear_row)

        disable_warning_row, self.disable_warning_dialogs_checkbox = self._create_settings_checkbox_row(
            "Отключить предупреждающие окна",
            "Предупреждения больше не будут открываться отдельными окнами и будут показаны только в строке состояния.",
        )
        self.disable_warning_dialogs_checkbox.stateChanged.connect(self._on_disable_warning_dialogs_changed)
        self.disable_warning_dialogs_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        main_card_layout.addWidget(disable_warning_row)

        _add_settings_section_divider(main_card_layout)
        _add_settings_section_title(main_card_layout, "Ярлыки")

        desktop_shortcut_row, self.desktop_shortcut_checkbox = self._create_settings_checkbox_row(
            "Добавить ярлык на рабочий стол",
            "Создает ярлык 'Мультифора' на рабочем столе.",
        )
        self.desktop_shortcut_checkbox.stateChanged.connect(self.toggle_desktop_shortcut)
        self.desktop_shortcut_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        main_card_layout.addWidget(desktop_shortcut_row)

        start_menu_shortcut_row, self.start_menu_shortcut_checkbox = self._create_settings_checkbox_row(
            "Добавить ярлык в меню Пуск",
            "Создает ярлык 'Мультифора' в меню Пуск.",
        )
        self.start_menu_shortcut_checkbox.stateChanged.connect(self.toggle_start_menu_shortcut)
        self.start_menu_shortcut_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        main_card_layout.addWidget(start_menu_shortcut_row)

        context_menu_row, self.context_menu_checkbox = self._create_settings_checkbox_row(
            "Добавить в контекстное меню Windows",
            "Добавляет пункт 'Добавить в Мультифору' в контекстное меню файлов и папок.",
        )
        self.context_menu_checkbox.stateChanged.connect(self.toggle_context_menu)
        self.context_menu_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        main_card_layout.addWidget(context_menu_row)
        main_card_layout.addStretch()

        updates_card_layout = self._add_settings_page()

        auto_update_row, self.auto_update_check_checkbox = self._create_settings_checkbox_row(
            "Проверять обновления при запуске",
            "Проверка обновлений выполняется через GitHub-репозиторий проекта.",
        )
        self.auto_update_check_checkbox.setChecked(True)
        self.auto_update_check_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        updates_card_layout.addWidget(auto_update_row)

        self.update_status_label = QLabel("Нажмите \"Проверить обновления\".")
        self.update_status_label.setWordWrap(True)
        updates_card_layout.addWidget(self.update_status_label)

        self.update_latest_label = QLabel("Последняя версия: -")
        updates_card_layout.addWidget(self.update_latest_label)

        self.update_source_label = QLabel("Источник: https://github.com/VseMirka200/multifora")
        self.update_source_label.setWordWrap(True)
        updates_card_layout.addWidget(self.update_source_label)

        update_buttons_layout = QHBoxLayout()
        update_buttons_layout.setContentsMargins(*MARGINS_NONE)
        update_buttons_layout.setSpacing(SPACE_NONE)

        self.btn_check_updates = QPushButton("Проверить обновления")
        setup_standard_action_button(self.btn_check_updates)
        self.btn_check_updates.clicked.connect(self.check_updates_now)
        update_buttons_layout.addWidget(self.btn_check_updates)

        self.btn_open_repo = QPushButton("Открыть GitHub")
        setup_standard_action_button(self.btn_open_repo)
        self.btn_open_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_PAGE)))
        update_buttons_layout.addWidget(self.btn_open_repo)

        updates_card_layout.addLayout(update_buttons_layout)

        logs_card_layout = self._add_settings_page()
        logs_card_layout.setSpacing(SPACE_SM)

        logs_filters_row = QWidget()
        logs_filters_layout = QHBoxLayout(logs_filters_row)
        logs_filters_layout.setContentsMargins(*MARGINS_NONE)
        logs_filters_layout.setSpacing(SPACE_SM)
        logs_filters_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.logs_level_filter = LeftAlignedToolButton()
        self.logs_level_filter.setObjectName("header_cell_tl")
        self.logs_level_filter.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.logs_level_filter.setFixedHeight(HEADER_FIELD_HEIGHT)
        self.logs_level_filter.setMinimumWidth(140)
        self.logs_level_filter.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.logs_level_filter.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._logs_level_menu = QMenu(self.logs_level_filter)
        self._logs_level_menu.setObjectName("header_dropdown_popup")
        apply_standard_menu_style(self._logs_level_menu)
        self._logs_level_actions = {}
        all_levels_action = QAction("Все уровни", self._logs_level_menu)
        all_levels_action.triggered.connect(self._select_all_log_levels)
        self._logs_level_menu.addAction(all_levels_action)
        self._logs_level_menu.addSeparator()
        for level in ["INFO", "WARNING", "ERROR", "DEBUG"]:
            action = QAction(level, self._logs_level_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self._on_log_level_filter_changed)
            self._logs_level_menu.addAction(action)
            self._logs_level_actions[level] = action
        self.logs_level_filter.setMenu(self._logs_level_menu)
        self._logs_level_menu.aboutToShow.connect(self._sync_logs_level_menu_width)
        self._update_logs_level_filter_button_text()
        logs_filters_layout.addWidget(self.logs_level_filter)

        self.logs_search_input = QLineEdit()
        self.logs_search_input.setPlaceholderText("Поиск по логам...")
        setup_standard_line_input(self.logs_search_input)
        self.logs_search_input.textChanged.connect(lambda _v: self._apply_logs_filters())
        logs_filters_layout.addWidget(self.logs_search_input, 1)

        logs_card_layout.addWidget(logs_filters_row)

        self.logs_view = QPlainTextEdit()
        self.logs_view.setObjectName("logs_view")
        self.logs_view.setReadOnly(True)
        self.logs_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.logs_view.setMaximumBlockCount(self.max_log_lines)
        self.logs_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        try:
            self.logs_view.setFont(QFont("Consolas", 13))
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin.create_settings_tab", error)
        logs_card_layout.addWidget(self.logs_view, 1)

        self.load_logs_into_view()
        self.settings_nav.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        self.settings_nav.currentRowChanged.connect(self._on_settings_nav_changed)
        self.settings_nav.setCurrentRow(0)
        self._update_settings_nav_width()

        return tab

    def _on_settings_nav_changed(self, row: int):
        self._pending_settings_nav_row = row
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()

    def _on_theme_mode_changed(self, _index=0):
        mode = "system"
        try:
            mode = self.theme_mode_combo.currentData() or "system"
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin._on_theme_mode_changed", error)
        self.apply_theme_mode(mode)
        self._schedule_settings_save()

    def _apply_logs_level_menu_style(self):
        menu = getattr(self, "_logs_level_menu", None)
        if menu is None:
            return
        apply_standard_menu_style(menu)

    def _apply_logs_filters(self):
        if not hasattr(self, "logs_view") or self.logs_view is None:
            return
        lines = list(getattr(self, "_log_lines", []) or [])
        if not lines:
            self.logs_view.setPlainText("")
            return

        selected_levels = set()
        all_levels = set()
        if hasattr(self, "_logs_level_actions") and self._logs_level_actions:
            all_levels = set(self._logs_level_actions.keys())
            selected_levels = {k for k, a in self._logs_level_actions.items() if a.isChecked()}
        query = ""
        if hasattr(self, "logs_search_input") and self.logs_search_input is not None:
            query = (self.logs_search_input.text() or "").strip().lower()

        filtered = []
        level_filter_active = bool(all_levels) and selected_levels != all_levels
        level_tokens = {f"[{level}]" for level in selected_levels} if level_filter_active else set()
        for line in lines:
            if level_filter_active and (not level_tokens or not any(token in line for token in level_tokens)):
                continue
            if query and query not in line.lower():
                continue
            filtered.append(line)

        self.logs_view.setPlainText("\n".join(filtered))
        self.logs_view.moveCursor(QTextCursor.MoveOperation.End)

    def _select_all_log_levels(self):
        if not hasattr(self, "_logs_level_actions") or not self._logs_level_actions:
            return
        for action in self._logs_level_actions.values():
            if not action.isChecked():
                action.setChecked(True)
        self._update_logs_level_filter_button_text()
        self._apply_logs_filters()

    def _on_log_level_filter_changed(self, _checked=False):
        self._update_logs_level_filter_button_text()
        self._apply_logs_filters()

    def _update_logs_level_filter_button_text(self):
        if not hasattr(self, "_logs_level_actions") or not self._logs_level_actions:
            return
        total = len(self._logs_level_actions)
        checked = sum(1 for a in self._logs_level_actions.values() if a.isChecked())
        if checked == total:
            self.logs_level_filter.setText("Все уровни")
        else:
            self.logs_level_filter.setText(f"Выбрано: {checked}")

    def _sync_logs_level_menu_width(self):
        menu = getattr(self, "_logs_level_menu", None)
        button = getattr(self, "logs_level_filter", None)
        sync_standard_menu_width(menu, button)

    def _update_settings_nav_width(self):
        if not hasattr(self, "settings_nav") or self.settings_nav is None:
            return
        base = getattr(self, "_settings_nav_base_width", 220)
        scroll = self.settings_nav.verticalScrollBar()
        extra = 0
        try:
            if scroll and scroll.maximum() > 0:
                extra = scroll.sizeHint().width() + 4
        except Exception:
            extra = 0
        self.settings_nav.setFixedWidth(base + extra)

    def check_updates_now(self):
        self._start_update_check(silent=False)

    def check_updates_on_startup(self):
        try:
            if hasattr(self, "auto_update_check_checkbox") and self.auto_update_check_checkbox.isChecked():
                self._start_update_check(silent=True)
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin.check_updates_on_startup", error)

    def _start_update_check(self, silent: bool = False):
        if getattr(self, "_update_future", None) and not self._update_future.done():
            return
        if not hasattr(self, "btn_check_updates") or self.btn_check_updates is None:
            return

        if not hasattr(self, "_update_executor"):
            self._update_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        if not hasattr(self, "_update_poll_timer"):
            self._update_poll_timer = QTimer(self)
            self._update_poll_timer.setInterval(150)
            self._update_poll_timer.timeout.connect(self._poll_update_future)

        self._update_silent = bool(silent)
        self.btn_check_updates.setEnabled(False)
        self.update_status_label.setText("Проверяем обновления на GitHub...")
        self._update_future = self._update_executor.submit(check_for_updates)
        self._update_poll_timer.start()

    def _on_disable_warning_dialogs_changed(self, state):
        self.disable_warning_dialogs = state == Qt.CheckState.Checked.value

    def _poll_update_future(self):
        if not getattr(self, "_update_future", None):
            return
        if not self._update_future.done():
            return

        self._update_poll_timer.stop()
        self.btn_check_updates.setEnabled(True)

        try:
            result = self._update_future.result()
            current = result.get("current_version", "unknown")
            latest = result.get("latest_version", "-")
            has_update = result.get("has_update")
            cmp_result = result.get("comparison")
            self.update_latest_label.setText(f"Последняя версия: {latest}")

            if has_update is True:
                text_msg = f"Доступно обновление: {current} -> {latest}"
            elif has_update is False:
                text_msg = f"У вас актуальная версия: {current}"
            elif cmp_result == 1:
                text_msg = f"Локальная версия новее GitHub: {current}"
            else:
                text_msg = f"Проверка завершена. Текущая: {current}, GitHub: {latest}"

            self.update_status_label.setText(text_msg)
            if not getattr(self, "_update_silent", False):
                QMessageBox.information(self, "Проверка обновлений", text_msg)
        except Exception as e:
            text_msg = f"Не удалось проверить обновления: {str(e)}"
            self.update_status_label.setText(text_msg)
            if not getattr(self, "_update_silent", False):
                QMessageBox.warning(self, "Проверка обновлений", text_msg)
