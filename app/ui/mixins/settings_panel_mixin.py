import concurrent.futures

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QFontMetrics, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.app_icons import _get_app_icon_qt_path
from app.core.app_identity import APP_DISPLAY_NAME, APP_VERSION
from app.core.app_utils import _log_ignored_error
from app.core.auto_updater import (
    automatic_updates_supported,
    download_and_launch_latest_installer,
)
from app.core.update_checker import (
    check_for_updates,
)
from app.ui.ui_components import (
    MenuLikeComboBox,
    setup_clickable_checkbox_label,
    setup_standard_dialog,
    setup_standard_dropdown,
)
from app.ui.ui_spacing import (
    CHECKBOX_SIZE,
    DIALOG_MARGINS,
    MARGINS_NONE,
    SETTINGS_PANEL_COLUMN_GAP,
    SETTINGS_PANEL_MARGINS,
    SPACE_LG,
    SPACE_NONE,
    SPACE_SM,
)
from app.ui.ui_styles import build_settings_navigation_style


class SettingsPanelMixin:
    def _apply_settings_navigation_theme(
        self, theme: str | None = None
    ) -> None:
        navigation = getattr(self, "settings_nav", None)
        if navigation is None:
            return
        effective = theme or getattr(self, "_effective_theme_mode", None)
        if effective not in ("light", "dark"):
            effective = (
                "light"
                if str(getattr(self, "theme_mode", "dark")).lower() == "light"
                else "dark"
            )
        navigation.setStyleSheet(build_settings_navigation_style(effective))

    # Создаёт страницы настроек по мере открытия и связывает поля с состоянием окна.
    @staticmethod
    def _create_settings_hint_label(text: str) -> QLabel:
        hint = QLabel(text)
        hint.setProperty("settingsHint", True)
        hint.setWordWrap(True)
        hint.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        return hint

    def _create_settings_checkbox_row(self, text: str, tooltip: str = ""):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_SM)

        checkbox = QCheckBox()
        checkbox.setFixedSize(CHECKBOX_SIZE + 2, CHECKBOX_SIZE + 2)
        checkbox.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        if tooltip:
            checkbox.setToolTip(tooltip)
        layout.addWidget(
            checkbox, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

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
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
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
        page.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(*MARGINS_NONE)
        page_layout.setSpacing(SPACE_NONE)
        page_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        scroll = QScrollArea()
        scroll.setObjectName("settings_page_scroll")
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        scroll.setContentsMargins(*MARGINS_NONE)
        scroll.setViewportMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("settings_page_content")
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(*MARGINS_NONE)
        content_layout.setSpacing(SPACE_NONE)
        content_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        card = QFrame()
        card.setObjectName("settings_card")
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*MARGINS_NONE)
        card_layout.setSpacing(SPACE_NONE)
        card_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

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
            card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
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
        if (
            not hasattr(self, "settings_panel_widget")
            or self.settings_panel_widget is None
        ):
            self.settings_panel_widget = self.create_settings_tab()

        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host_layout = host.layout()
            if (
                host_layout is not None
                and host_layout.indexOf(self.settings_panel_widget) < 0
            ):
                self.settings_panel_widget.setParent(None)
                host_layout.addWidget(self.settings_panel_widget)
        return self.settings_panel_widget

    def _ensure_help_panel_widget(self):
        if (
            not hasattr(self, "help_panel_widget")
            or self.help_panel_widget is None
        ):
            self.help_panel_widget = self.create_help_tab()

        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host_layout = host.layout()
            if (
                host_layout is not None
                and host_layout.indexOf(self.help_panel_widget) < 0
            ):
                self.help_panel_widget.setParent(None)
                host_layout.addWidget(self.help_panel_widget)
        return self.help_panel_widget

    def _show_header_panel(
        self, panel: QWidget, active_button: QPushButton | None = None
    ) -> None:
        for widget_name in ("settings_panel_widget", "help_panel_widget"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setVisible(widget is panel)
        for button_name in ("btn_help",):
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
            self._apply_operations_tab_bar_theme()

    def show_settings_modal(self):
        """Показывает панель настроек поверх рабочей области."""
        settings_widget = self._ensure_settings_panel_widget()
        self._show_header_panel(settings_widget)

        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(settings_widget)

        self.log_event("Открыта панель настроек")

    def show_help_modal(self):
        """Компактные окна справки с фиксированной геометрией.

        Окно «О программе» занимает столько места, сколько нужно его содержимому.
        """
        help_widget = self._ensure_help_panel_widget()
        self.help_stack.setCurrentIndex(0)
        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(help_widget)

        title = "О программе"
        dialog = QDialog(self)
        dialog._effective_theme_mode = getattr(
            self, "_effective_theme_mode", "dark"
        )
        setup_standard_dialog(dialog, title=title)
        dialog.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        dialog.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        dialog.setSizeGripEnabled(False)
        try:
            dialog.setStyleSheet(self.styleSheet())
        except Exception as error:
            _log_ignored_error(
                "SettingsPanelMixin.show_help_modal.style", error
            )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_LG)
        host = getattr(self, "settings_panel_host", None)
        host_layout = host.layout() if host is not None else None
        if host_layout is not None:
            host_layout.removeWidget(help_widget)
        help_widget.setParent(dialog)
        help_widget.setVisible(True)
        layout.addWidget(help_widget)

        # Ограничиваем размеры экраном: окно нельзя растянуть за заголовок.
        screen = dialog.screen() or QApplication.primaryScreen()
        screen_size = screen.availableGeometry() if screen else None
        requested_width, requested_height = (510, 280)
        width = (
            min(requested_width, screen_size.width() - 32)
            if screen_size
            else requested_width
        )
        height = (
            min(requested_height, screen_size.height() - 48)
            if screen_size
            else requested_height
        )
        dialog.setFixedSize(max(320, width), max(280, height))

        self.log_event(f"Открыт раздел справки: {title}")
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
            self._apply_operations_tab_bar_theme()
        for button_name in ("btn_help",):
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
        self.about_icon_label.setPixmap(
            QIcon(_get_app_icon_qt_path() or "").pixmap(52, 52)
        )
        self.about_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_header_layout.addWidget(
            self.about_icon_label, 0, Qt.AlignmentFlag.AlignHCenter
        )

        self.about_title_label = QLabel(APP_DISPLAY_NAME)
        title_font = self.about_title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.about_title_label.setFont(title_font)
        self.about_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_header_layout.addWidget(
            self.about_title_label, 0, Qt.AlignmentFlag.AlignHCenter
        )

        self.about_version_label = QLabel(f"Версия: {APP_VERSION}")
        self.about_version_label.setProperty("aboutVersionBadge", True)
        self.about_version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_version_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        about_header_layout.addWidget(
            self.about_version_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        layout.addWidget(about_header)

        description = QLabel(
            "Мультифора — приложение с открытым исходным кодом для "
            "пакетной обработки документов и изображений в Windows."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
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
        capabilities.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(capabilities)

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

        self.settings_nav = QWidget()
        self.settings_nav.setObjectName("settings_nav")
        self._apply_settings_navigation_theme()
        navigation_layout = QVBoxLayout(self.settings_nav)
        navigation_layout.setContentsMargins(*MARGINS_NONE)
        navigation_layout.setSpacing(12)
        nav_font = QFont()
        nav_font.setPixelSize(13)
        nav_font.setBold(True)
        section_titles = ("Интерфейс", "Поведение", "Автоочистка", "Ярлыки")
        display_titles = tuple(title.upper() for title in section_titles)
        # Резервируем место для значка 16 px и отступа: фиксированные кнопки
        # иначе обрезают текст сразу после назначения значка.
        nav_button_width = max(
            QFontMetrics(nav_font).horizontalAdvance(title)
            for title in display_titles
        )
        self._settings_nav_width = nav_button_width + SPACE_LG * 4
        self.settings_nav.setFixedWidth(self._settings_nav_width)
        self.settings_nav.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        self.settings_nav_buttons = []
        for index, title in enumerate(display_titles):
            button = QPushButton(title)
            button.setObjectName("settings_nav_item")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFont(nav_font)
            button.setFixedSize(nav_button_width, 22)
            button.clicked.connect(
                lambda _checked=False, row=index: (
                    self._select_settings_navigation_row(row)
                )
            )
            navigation_layout.addWidget(
                button,
                0,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )
            self.settings_nav_buttons.append(button)
        navigation_layout.addStretch()
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
        self.theme_mode_combo.currentIndexChanged.connect(
            self._on_theme_mode_changed
        )
        theme_row = self._create_settings_select_row(
            "Тема:",
            self.theme_mode_combo,
            label_width=40,
            hint="Определяет цветовую схему интерфейса или использует тему Windows.",
        )
        appearance_layout.addWidget(theme_row)
        appearance_layout.addStretch()

        warning_description = (
            "Предупреждения больше не будут открываться отдельными окнами и будут "
            "показаны только в строке состояния."
        )
        disable_warning_row, self.disable_warning_dialogs_checkbox = (
            self._create_settings_checkbox_row(
                "Отключить предупреждающие окна",
                warning_description,
            )
        )
        self.disable_warning_dialogs_checkbox.stateChanged.connect(
            self._on_disable_warning_dialogs_changed
        )
        self.disable_warning_dialogs_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        behavior_layout.addWidget(disable_warning_row)

        auto_update_row, self.auto_update_check_checkbox = (
            self._create_settings_checkbox_row(
                "Проверять обновления при запуске",
                "Проверка обновлений выполняется через GitHub-репозиторий проекта.",
            )
        )
        self.auto_update_check_checkbox.setChecked(False)
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
        self.auto_clear_enabled_checkbox.stateChanged.connect(
            self._sync_auto_clear_controls
        )
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
            checkbox.stateChanged.connect(
                lambda _state: self._schedule_settings_save()
            )
            self.auto_clear_operation_checkboxes.append(checkbox)
            self.auto_clear_operation_rows.append(row)
            auto_clear_layout.addWidget(row)
        self.auto_clear_convert_checkbox.setChecked(False)
        self._sync_auto_clear_controls()
        auto_clear_layout.addStretch()

        desktop_shortcut_row, self.desktop_shortcut_checkbox = (
            self._create_settings_checkbox_row(
                "Добавить ярлык на рабочий стол",
                "Создает ярлык 'Мультифора' на рабочем столе.",
            )
        )
        self.desktop_shortcut_checkbox.stateChanged.connect(
            self.toggle_desktop_shortcut
        )
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
        self.start_menu_shortcut_checkbox.stateChanged.connect(
            self.toggle_start_menu_shortcut
        )
        self.start_menu_shortcut_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        shortcuts_layout.addWidget(start_menu_shortcut_row)

        context_menu_row, self.context_menu_checkbox = (
            self._create_settings_checkbox_row(
                "Добавить в контекстное меню Windows",
                "Добавляет пункт 'Добавить в Мультифору' в контекстное меню файлов и папок.",
            )
        )
        self.context_menu_checkbox.stateChanged.connect(
            self.toggle_context_menu
        )
        self.context_menu_checkbox.stateChanged.connect(
            lambda _state: self._schedule_settings_save()
        )
        shortcuts_layout.addWidget(context_menu_row)
        shortcuts_layout.addStretch()

        self._select_settings_navigation_row(0)

        return tab

    def _sync_settings_navigation_buttons(self, row: int) -> None:
        for index, button in enumerate(
            getattr(self, "settings_nav_buttons", ())
        ):
            button.setChecked(index == row)

    def _select_settings_navigation_row(self, row: int) -> None:
        self.settings_stack.setCurrentIndex(row)
        self._sync_settings_navigation_buttons(row)

    def create_help_tab(self):
        """Создает отдельную панель справки со сведениями о программе."""
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

        self._ensure_about_help_page()

        return tab

    def _on_theme_mode_changed(self, _index=0):
        mode = "system"
        try:
            mode = self.theme_mode_combo.currentData() or "system"
        except Exception as error:
            _log_ignored_error(
                "SettingsPanelMixin._on_theme_mode_changed", error
            )
        self.apply_theme_mode(mode)
        self._schedule_settings_save()

    def _sync_auto_clear_controls(self, *_args):
        enabled_checkbox = getattr(self, "auto_clear_enabled_checkbox", None)
        enabled = bool(
            enabled_checkbox is not None and enabled_checkbox.isChecked()
        )
        label = getattr(self, "auto_clear_operations_label", None)
        if label is not None:
            label.setEnabled(enabled)
        for row in getattr(self, "auto_clear_operation_rows", ()):
            row.setEnabled(enabled)

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
            _log_ignored_error(
                "SettingsPanelMixin.check_updates_on_startup", error
            )

    def _start_update_check(self, silent: bool = False):
        if (
            getattr(self, "_update_future", None)
            and not self._update_future.done()
        ):
            if not silent:
                self._update_silent = False
            return

        if not hasattr(self, "_update_executor"):
            self._update_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            )
        if not hasattr(self, "_update_poll_timer"):
            self._update_poll_timer = QTimer(self)
            self._update_poll_timer.setInterval(150)
            self._update_poll_timer.timeout.connect(self._poll_update_future)

        self._update_silent = bool(silent)
        action = getattr(self, "check_updates_action", None)
        if action is not None:
            action.setEnabled(False)
        self._update_future = self._update_executor.submit(check_for_updates)
        self._update_operation = "check"
        self._update_poll_timer.start()

    def _on_disable_warning_dialogs_changed(self, state):
        checkbox = getattr(self, "disable_warning_dialogs_checkbox", None)
        self.disable_warning_dialogs = bool(
            checkbox.isChecked()
            if checkbox is not None
            else state == Qt.CheckState.Checked.value
        )

    def _poll_update_check_future(self):
        if not getattr(self, "_update_future", None):
            return
        if not self._update_future.done():
            return

        self._update_poll_timer.stop()
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
                text_msg = (
                    f"Проверка завершена. Текущая: {current}, GitHub: {latest}"
                )

            if cmp_result == -1 and not getattr(self, "_update_silent", False):
                if automatic_updates_supported():
                    self.status_bar.showMessage("Загрузка обновления…")
                    action = getattr(self, "check_updates_action", None)
                    if action is not None:
                        action.setEnabled(False)
                    self._update_future = self._update_executor.submit(
                        download_and_launch_latest_installer
                    )
                    self._update_operation = "install"
                    self._update_poll_timer.start()
                    return

                QMessageBox.information(
                    self,
                    "Проверка обновлений",
                    f"{text_msg}\n\nАвтоматическое обновление доступно в установленной Windows-версии.",
                )
            elif not getattr(self, "_update_silent", False):
                QMessageBox.information(self, "Проверка обновлений", text_msg)
            elif cmp_result == -1:
                status_bar = getattr(self, "status_bar", None)
                if status_bar is not None:
                    status_bar.showMessage(text_msg)
        except Exception as e:
            text_msg = f"Не удалось проверить обновления: {e!s}"
            if not getattr(self, "_update_silent", False):
                QMessageBox.warning(self, "Проверка обновлений", text_msg)
        finally:
            if getattr(self, "_update_operation", "check") == "check":
                action = getattr(self, "check_updates_action", None)
                if action is not None:
                    action.setEnabled(True)

    def _poll_update_future(self):
        if getattr(self, "_update_operation", "check") != "install":
            return SettingsPanelMixin._poll_update_check_future(self)

        if (
            not getattr(self, "_update_future", None)
            or not self._update_future.done()
        ):
            return

        self._update_poll_timer.stop()
        action = getattr(self, "check_updates_action", None)
        if action is not None:
            action.setEnabled(True)
        try:
            installer_name = self._update_future.result()
        except Exception as error:
            QMessageBox.warning(
                self,
                "Обновление",
                f"Не удалось установить обновление: {error!s}",
            )
            return

        QMessageBox.information(
            self,
            "Обновление",
            f"Установщик {installer_name} запущен. Программа будет закрыта для обновления.",
        )
        QTimer.singleShot(0, self.close)
