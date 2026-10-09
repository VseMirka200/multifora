import concurrent.futures

from PyQt6.QtCore import QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
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

from app.core.app_icons import _get_app_icon_qt_path
from app.core.app_identity import APP_DISPLAY_NAME, APP_VERSION
from app.core.app_utils import _log_ignored_error
from app.core.update_checker import (
    REPO_PAGE,
    check_for_updates,
)
from app.ui.ui_components import (
    LeftAlignedToolButton,
    MenuLikeComboBox,
    setup_clickable_checkbox_label,
    setup_compact_checkbox,
    setup_standard_action_button,
    setup_standard_dropdown,
    setup_standard_dialog,
    setup_standard_line_input,
    setup_standard_popup_menu,
    setup_standard_primary_button,
    setup_standard_secondary_button,
    sync_standard_menu_width,
)
from app.ui.ui_spacing import (
    CHECKBOX_SIZE,
    DIALOG_MARGINS,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    SETTINGS_PANEL_COLUMN_GAP,
    SETTINGS_PANEL_MARGINS,
    SPACE_LG,
    SPACE_NONE,
    SPACE_SM,
    SPACE_XL,
)


class SettingsPanelMixin:
    # Создаёт страницы настроек по мере открытия и связывает поля с состоянием окна.
    @staticmethod
    def _create_settings_hint_label(text: str) -> QLabel:
        hint = QLabel(text)
        hint.setProperty("settingsHint", True)
        hint.setWordWrap(True)
        hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return hint

    def _create_settings_checkbox_row(self, text: str, tooltip: str = ""):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_SM)

        checkbox = QCheckBox()
        checkbox.setFixedSize(CHECKBOX_SIZE, CHECKBOX_SIZE)
        checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        setup_compact_checkbox(checkbox)
        if tooltip:
            checkbox.setToolTip(tooltip)
        layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        text_column = QWidget(row)
        text_layout = QVBoxLayout(text_column)
        text_layout.setContentsMargins(*MARGINS_NONE)
        text_layout.setSpacing(SPACE_NONE)
        label = QLabel(text)
        setup_clickable_checkbox_label(label, checkbox, tooltip=tooltip)
        text_layout.addWidget(label)
        if tooltip:
            text_layout.addWidget(self._create_settings_hint_label(tooltip))
        layout.addWidget(text_column, 1)
        return row, checkbox

    def _create_settings_select_row(
        self,
        label_text: str,
        field: QWidget,
        *,
        label_width: int = 60,
        hint: str = "",
    ):
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_NONE)

        controls = QWidget(row)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(*MARGINS_NONE)
        controls_layout.setSpacing(SPACE_NONE)
        label = QLabel(label_text)
        label.setFixedWidth(label_width)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        controls_layout.addWidget(label)
        controls_layout.addWidget(field, 0)
        controls_layout.addStretch()
        layout.addWidget(controls)
        if hint:
            field.setToolTip(hint)
            layout.addWidget(self._create_settings_hint_label(hint))
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

    def _add_help_page(self, *, compact: bool = False) -> QVBoxLayout:
        if compact:
            # Небольшая страница «О программе»: без растягиваемой прокрутки,
            # карточка имеет только необходимую содержимому высоту.
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(*MARGINS_NONE)
            page_layout.setSpacing(SPACE_NONE)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            card = QFrame(page)
            card.setObjectName("settings_card")
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(*MARGINS_NONE)
            card_layout.setSpacing(SPACE_SM)
            page_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)
            self.help_stack.addWidget(page)
            return card_layout
        page, card_layout = self._create_settings_page_card()
        self.help_stack.addWidget(page)
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

    def _ensure_help_panel_widget(self):
        if not hasattr(self, "help_panel_widget") or self.help_panel_widget is None:
            self.help_panel_widget = self.create_help_tab()

        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host_layout = host.layout()
            if host_layout is not None and host_layout.indexOf(self.help_panel_widget) < 0:
                self.help_panel_widget.setParent(None)
                host_layout.addWidget(self.help_panel_widget)
        return self.help_panel_widget

    def _show_header_panel(self, panel: QWidget, active_button: QPushButton) -> None:
        for widget_name in ("settings_panel_widget", "help_panel_widget"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setVisible(widget is panel)
        for button_name in ("btn_settings", "btn_help"):
            button = getattr(self, button_name, None)
            if button is not None:
                button.setChecked(button is active_button)

        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host.setVisible(True)
            host.adjustSize()
            host.updateGeometry()
        splitter = getattr(self, "main_splitter", None)
        if splitter is not None:
            splitter.setVisible(False)

        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            tab_bar.setProperty("settingsActive", True)
            self._apply_operations_tab_bar_theme()

    def show_settings_modal(self):
        """Показывает панель настроек поверх рабочей области."""
        settings_widget = self._ensure_settings_panel_widget()
        self._show_header_panel(settings_widget, self.btn_settings)

        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(settings_widget)

        self.log_event("Открыта панель настроек")

    def show_help_modal(self, section_index: int = 0):
        """Компактные окна справки с фиксированной геометрией.

        Только «Логи» содержит прокручиваемую область; окно «О программе»
        занимает столько места, сколько нужно его содержимому.
        """
        if section_index not in (0, 1):
            return None
        help_widget = self._ensure_help_panel_widget()
        self.help_stack.setCurrentIndex(section_index)
        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(help_widget)

        title = "Логи" if section_index == 0 else "О программе"
        dialog = QDialog(self)
        dialog._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
        setup_standard_dialog(dialog, title=title)
        dialog.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        dialog.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        dialog.setSizeGripEnabled(False)
        try:
            dialog.setStyleSheet(self.styleSheet())
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin.show_help_modal.style", error)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_LG)
        host = getattr(self, "settings_panel_host", None)
        host_layout = host.layout() if host is not None else None
        if host_layout is not None:
            host_layout.removeWidget(help_widget)
        help_widget.setParent(dialog)
        help_widget.setVisible(True)
        layout.addWidget(help_widget, 1 if section_index == 0 else 0)

        close_button = QPushButton("Закрыть", dialog)
        setup_standard_secondary_button(close_button)
        close_button.setFixedWidth(96)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

        # Ограничиваем размеры экраном: окно нельзя растянуть за заголовок.
        screen = dialog.screen() or QApplication.primaryScreen()
        screen_size = screen.availableGeometry() if screen else None
        requested_width, requested_height = (680, 420) if section_index == 0 else (510, 405)
        width = min(requested_width, screen_size.width() - 32) if screen_size else requested_width
        height = min(requested_height, screen_size.height() - 48) if screen_size else requested_height
        dialog.setFixedSize(max(320, width), max(280, height))

        self.log_event(f"Открыт раздел справки: {title}")
        if section_index == 0:
            try:
                self.load_logs_into_view()
            except Exception as error:
                _log_ignored_error("SettingsPanelMixin.show_help_modal", error)
        try:
            return dialog.exec()
        finally:
            layout.removeWidget(help_widget)
            help_widget.setParent(None)
            help_widget.setVisible(False)
            if host_layout is not None:
                host_layout.addWidget(help_widget)
            if getattr(self, "btn_help", None) is not None:
                self.btn_help.setChecked(False)
            dialog.deleteLater()

    def hide_settings_panel(self):
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            tab_bar.setProperty("settingsActive", False)
            self._apply_operations_tab_bar_theme()
        for button_name in ("btn_settings", "btn_help"):
            button = getattr(self, button_name, None)
            if button is not None:
                button.setChecked(False)
        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host.setVisible(False)
        splitter = getattr(self, "main_splitter", None)
        if splitter is not None:
            splitter.setVisible(True)

    def _ensure_about_help_page(self):
        """Страница со стандартной для настольных приложений информацией."""
        if hasattr(self, "_about_help_row"):
            return
        self._about_help_row = self.help_stack.count()
        layout = self._add_help_page(compact=True)
        layout.setSpacing(SPACE_LG)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        about_header = QWidget()
        about_header.setObjectName("about_header")
        about_header_layout = QVBoxLayout(about_header)
        about_header_layout.setContentsMargins(0, SPACE_SM, 0, SPACE_SM)
        about_header_layout.setSpacing(SPACE_SM)
        about_header_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.about_icon_label = QLabel()
        self.about_icon_label.setPixmap(QIcon(_get_app_icon_qt_path() or "").pixmap(52, 52))
        self.about_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_header_layout.addWidget(self.about_icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.about_title_label = QLabel(APP_DISPLAY_NAME)
        title_font = self.about_title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.about_title_label.setFont(title_font)
        self.about_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_header_layout.addWidget(self.about_title_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.about_version_label = QLabel(f"Версия: {APP_VERSION}")
        self.about_version_label.setProperty("aboutVersionBadge", True)
        self.about_version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_version_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        about_header_layout.addWidget(self.about_version_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(about_header)

        description = QLabel(
            "Мультифора — приложение с открытым исходным кодом для "
            "пакетной обработки документов и изображений в Windows."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(description)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(separator)

        capabilities = QLabel(
            "Переименование по шаблонам · Конвертация · "
            "Объединение PDF/DOCX · Сжатие изображений и PDF"
        )
        capabilities.setWordWrap(True)
        capabilities.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capabilities.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(capabilities)

        requirements = QLabel(
            "Для некоторых операций необходимы Microsoft Word или Ghostscript."
        )
        requirements.setWordWrap(True)
        requirements.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(requirements)

        license_label = QLabel("Лицензия MIT  •  Свободное программное обеспечение")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_label.setWordWrap(True)
        license_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(license_label)

        links_row = QWidget()
        links_layout = QHBoxLayout(links_row)
        links_layout.setContentsMargins(*MARGINS_NONE)
        links_layout.setSpacing(SPACE_SM)
        links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_open_repo = QPushButton("Исходный код")
        setup_standard_secondary_button(self.btn_open_repo)
        self.btn_open_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_PAGE)))
        links_layout.addWidget(self.btn_open_repo)

        self.btn_check_updates = QPushButton("Проверить обновления")
        setup_standard_primary_button(self.btn_check_updates)
        self.btn_check_updates.clicked.connect(self.check_updates_now)
        links_layout.addWidget(self.btn_check_updates)
        layout.addWidget(links_row)

    def create_settings_tab(self):
        """Создает панель основных настроек на всю доступную ширину."""
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
        self.settings_nav.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_nav.setStyleSheet(
            """
            QListWidget#settings_nav {
                border: none;
                outline: none;
            }
            QListWidget#settings_nav::item {
                background-color: transparent;
                border: none;
            }
            QListWidget#settings_nav::item:selected {
                background-color: transparent;
                color: #3d74b3;
                border: none;
                outline: none;
            }
            """
        )
        self._settings_nav_base_width = 192
        self.settings_nav.setFixedWidth(self._settings_nav_base_width)
        self.settings_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_nav.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.settings_nav.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.settings_nav.setWordWrap(True)
        self.settings_nav.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.settings_nav.setSpacing(0)
        self.settings_nav.setUniformItemSizes(True)
        nav_font = QFont()
        nav_font.setPointSize(10)
        for title in ("Внешний вид", "Поведение", "Автоочистка", "Ярлыки"):
            item = QListWidgetItem(title)
            item.setFont(nav_font)
            item.setSizeHint(QSize(self._settings_nav_base_width, 36))
            self.settings_nav.addItem(item)
        root_layout.addWidget(self.settings_nav, 0)

        self.settings_stack = QStackedWidget()
        self.settings_stack.setObjectName("settings_stack")
        root_layout.addWidget(self.settings_stack, 1)

        appearance_layout = self._add_settings_page()
        behavior_layout = self._add_settings_page()
        auto_clear_layout = self._add_settings_page()
        shortcuts_layout = self._add_settings_page()
        for page_layout in (
            appearance_layout,
            behavior_layout,
            auto_clear_layout,
            shortcuts_layout,
        ):
            page_layout.setSpacing(SPACE_SM)

        self.theme_mode_combo = MenuLikeComboBox()
        setup_standard_dropdown(self.theme_mode_combo, fixed_width=200)
        self.theme_mode_combo.addItem("Как в системе", "system")
        self.theme_mode_combo.addItem("Темная", "dark")
        self.theme_mode_combo.addItem("Светлая", "light")
        self.theme_mode_combo.currentIndexChanged.connect(self._on_theme_mode_changed)
        theme_row = self._create_settings_select_row(
            "Тема:",
            self.theme_mode_combo,
            label_width=40,
            hint="Определяет цветовую схему интерфейса или использует тему Windows.",
        )
        appearance_layout.addWidget(theme_row)
        appearance_layout.addStretch()

        disable_warning_row, self.disable_warning_dialogs_checkbox = (
            self._create_settings_checkbox_row(
                "Отключить предупреждающие окна",
                "Предупреждения больше не будут открываться отдельными окнами и будут показаны только в строке состояния.",
            )
        )
        self.disable_warning_dialogs_checkbox.stateChanged.connect(
            self._on_disable_warning_dialogs_changed
        )
        self.disable_warning_dialogs_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        behavior_layout.addWidget(disable_warning_row)

        auto_update_row, self.auto_update_check_checkbox = self._create_settings_checkbox_row(
            "Проверять обновления при запуске",
            "Проверка обновлений выполняется через GitHub-репозиторий проекта.",
        )
        self.auto_update_check_checkbox.setChecked(True)
        self.auto_update_check_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        behavior_layout.addWidget(auto_update_row)
        behavior_layout.addStretch()

        auto_clear_description = QLabel(
            "После успешной операции приложение может очистить весь список. "
            "Файлы на диске при автоочистке никогда не удаляются."
        )
        auto_clear_description.setWordWrap(True)
        auto_clear_layout.addWidget(auto_clear_description)

        auto_clear_enabled_row, self.auto_clear_enabled_checkbox = (
            self._create_settings_checkbox_row(
                "Включить автоочистку",
                "Автоочистка срабатывает только после выбранных ниже операций без ошибок.",
            )
        )
        self.auto_clear_enabled_checkbox.stateChanged.connect(self._sync_auto_clear_controls)
        self.auto_clear_enabled_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        auto_clear_layout.addWidget(auto_clear_enabled_row)

        self.auto_clear_operations_label = QLabel("Очищать весь список после:")
        auto_clear_layout.addWidget(self.auto_clear_operations_label)

        auto_clear_options = (
            (
                "auto_clear_rename_checkbox",
                "Переименования",
                "Очищает список после успешного переименования файлов.",
            ),
            (
                "auto_clear_convert_checkbox",
                "Конвертации",
                "Очищает список после успешного преобразования файлов.",
            ),
            (
                "auto_clear_merge_checkbox",
                "Объединения",
                "Очищает список после создания объединённого документа.",
            ),
            (
                "auto_clear_compress_checkbox",
                "Сжатия",
                "Очищает список после успешного сжатия файлов.",
            ),
        )
        self.auto_clear_operation_checkboxes = []
        self.auto_clear_operation_rows = []
        for attribute_name, label, hint in auto_clear_options:
            row, checkbox = self._create_settings_checkbox_row(label, hint)
            setattr(self, attribute_name, checkbox)
            checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
            self.auto_clear_operation_checkboxes.append(checkbox)
            self.auto_clear_operation_rows.append(row)
            auto_clear_layout.addWidget(row)
        self.auto_clear_convert_checkbox.setChecked(True)
        self._sync_auto_clear_controls()
        auto_clear_layout.addStretch()

        desktop_shortcut_row, self.desktop_shortcut_checkbox = self._create_settings_checkbox_row(
            "Добавить ярлык на рабочий стол",
            "Создает ярлык 'Мультифора' на рабочем столе.",
        )
        self.desktop_shortcut_checkbox.stateChanged.connect(self.toggle_desktop_shortcut)
        self.desktop_shortcut_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        shortcuts_layout.addWidget(desktop_shortcut_row)

        start_menu_shortcut_row, self.start_menu_shortcut_checkbox = (
            self._create_settings_checkbox_row(
                "Добавить ярлык в меню Пуск",
                "Создает ярлык 'Мультифора' в меню Пуск.",
            )
        )
        self.start_menu_shortcut_checkbox.stateChanged.connect(self.toggle_start_menu_shortcut)
        self.start_menu_shortcut_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        shortcuts_layout.addWidget(start_menu_shortcut_row)

        context_menu_row, self.context_menu_checkbox = self._create_settings_checkbox_row(
            "Добавить в контекстное меню Windows",
            "Добавляет пункт 'Добавить в Мультифору' в контекстное меню файлов и папок.",
        )
        self.context_menu_checkbox.stateChanged.connect(self.toggle_context_menu)
        self.context_menu_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        shortcuts_layout.addWidget(context_menu_row)
        shortcuts_layout.addStretch()

        self.settings_nav.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        self.settings_nav.setCurrentRow(0)

        return tab

    def create_help_tab(self):
        """Создает отдельную панель справки с логами и сведениями о программе."""
        tab = QWidget()
        tab.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        help_font = QFont()
        help_font.setPointSize(10)
        tab.setFont(help_font)
        root_layout = QHBoxLayout(tab)
        root_layout.setContentsMargins(*SETTINGS_PANEL_MARGINS)
        root_layout.setSpacing(SPACE_NONE)

        self.help_stack = QStackedWidget()
        root_layout.addWidget(self.help_stack, 1)

        logs_card_layout = self._add_help_page()
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
        setup_standard_popup_menu(self._logs_level_menu)
        self._logs_level_menu.setObjectName("header_dropdown_popup")
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

        self.btn_download_logs = QPushButton("Скачать логи")
        self.btn_download_logs.setToolTip("Сохранить отображаемые логи в текстовый файл")
        setup_standard_action_button(
            self.btn_download_logs,
            variant="secondary",
        )
        self.btn_download_logs.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_download_logs.clicked.connect(self.download_visible_logs)
        logs_filters_layout.addWidget(self.btn_download_logs)

        logs_card_layout.addWidget(logs_filters_row)

        self.logs_view = QPlainTextEdit()
        self.logs_view.setObjectName("logs_view")
        self.logs_view.setReadOnly(True)
        self.logs_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.logs_view.setMaximumBlockCount(self.max_log_lines)
        self.logs_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        try:
            self.logs_view.setFont(QFont("Consolas", 10))
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin.create_settings_tab", error)
        logs_card_layout.addWidget(self.logs_view, 1)

        self.load_logs_into_view()
        self._ensure_about_help_page()

        return tab

    def _on_theme_mode_changed(self, _index=0):
        mode = "system"
        try:
            mode = self.theme_mode_combo.currentData() or "system"
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin._on_theme_mode_changed", error)
        self.apply_theme_mode(mode)
        self._schedule_settings_save()

    def _sync_auto_clear_controls(self, *_args):
        enabled_checkbox = getattr(self, "auto_clear_enabled_checkbox", None)
        enabled = bool(enabled_checkbox is not None and enabled_checkbox.isChecked())
        label = getattr(self, "auto_clear_operations_label", None)
        if label is not None:
            label.setEnabled(enabled)
        for row in getattr(self, "auto_clear_operation_rows", ()):
            row.setEnabled(enabled)

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
            if level_filter_active and (
                not level_tokens or not any(token in line for token in level_tokens)
            ):
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

    def check_updates_now(self):
        self._start_update_check(silent=False)

    def check_updates_on_startup(self):
        try:
            if (
                hasattr(self, "auto_update_check_checkbox")
                and self.auto_update_check_checkbox.isChecked()
            ):
                self._start_update_check(silent=True)
        except Exception as error:
            _log_ignored_error("SettingsPanelMixin.check_updates_on_startup", error)

    def _start_update_check(self, silent: bool = False):
        if getattr(self, "_update_future", None) and not self._update_future.done():
            if not silent:
                self._update_silent = False
            return

        if not hasattr(self, "_update_executor"):
            self._update_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        if not hasattr(self, "_update_poll_timer"):
            self._update_poll_timer = QTimer(self)
            self._update_poll_timer.setInterval(150)
            self._update_poll_timer.timeout.connect(self._poll_update_future)

        self._update_silent = bool(silent)
        button = getattr(self, "btn_check_updates", None)
        if button is not None:
            button.setEnabled(False)
        self._update_future = self._update_executor.submit(check_for_updates)
        self._update_poll_timer.start()

    def _on_disable_warning_dialogs_changed(self, state):
        checkbox = getattr(self, "disable_warning_dialogs_checkbox", None)
        self.disable_warning_dialogs = bool(
            checkbox.isChecked()
            if checkbox is not None
            else state == Qt.CheckState.Checked.value
        )

    def _poll_update_future(self):
        if not getattr(self, "_update_future", None):
            return
        if not self._update_future.done():
            return

        self._update_poll_timer.stop()
        button = getattr(self, "btn_check_updates", None)
        if button is not None:
            button.setEnabled(True)

        try:
            result = self._update_future.result()
            current = result.get("current_version", "unknown")
            latest = result.get("latest_version", "-")
            cmp_result = result.get("comparison")

            if cmp_result == -1:
                text_msg = f"Доступно обновление: {current} → {latest}."
            elif cmp_result == 1:
                text_msg = f"Локальная версия новее GitHub: {current}"
            elif cmp_result == 0:
                text_msg = f"У вас актуальная версия: {current}"
            else:
                text_msg = f"Проверка завершена. Текущая: {current}, GitHub: {latest}"

            if not getattr(self, "_update_silent", False):
                QMessageBox.information(self, "Проверка обновлений", text_msg)
            elif cmp_result == -1:
                status_bar = getattr(self, "status_bar", None)
                if status_bar is not None:
                    status_bar.showMessage(text_msg)
        except Exception as e:
            text_msg = f"Не удалось проверить обновления: {e!s}"
            if not getattr(self, "_update_silent", False):
                QMessageBox.warning(self, "Проверка обновлений", text_msg)
