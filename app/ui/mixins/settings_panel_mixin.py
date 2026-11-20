import concurrent.futures

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
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
from app.core.app_identity import APP_DISPLAY_NAME, APP_VERSION, GUIDE_URL, REPO_PAGE
from app.core.app_utils import _log_ignored_error
from app.core.auto_updater import (
    automatic_updates_supported,
    download_and_launch_latest_installer,
)
from app.core.message_boxes import show_app_choice
from app.core.update_checker import (
    check_for_updates,
)
from app.ui.ui_components import (
    MenuLikeComboBox,
    setup_clickable_checkbox_label,
    setup_standard_dialog,
    setup_standard_dropdown,
    setup_standard_secondary_button,
)
from app.ui.ui_styles import (
    CHECKBOX_SIZE,
    DIALOG_MARGINS,
    MARGINS_NONE,
    PAGE_CONTENT_MARGINS,
    PAGE_SECTION_SPACING,
    SETTINGS_PANEL_MARGINS,
    SPACE_LG,
    SPACE_NONE,
    SPACE_SM,
)


class SettingsPanelMixin:
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
        row.setObjectName("settings_row")
        layout = QGridLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setHorizontalSpacing(SPACE_SM)
        layout.setVerticalSpacing(SPACE_NONE)
        layout.setColumnStretch(1, 1)

        checkbox = QCheckBox()
        checkbox.setFixedSize(CHECKBOX_SIZE + 2, CHECKBOX_SIZE + 2)
        checkbox.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        if tooltip:
            checkbox.setToolTip(tooltip)
        layout.addWidget(checkbox, 0, 0, 2 if tooltip else 1, 1, Qt.AlignmentFlag.AlignVCenter)
        label = QLabel(text)
        setup_clickable_checkbox_label(label, checkbox, tooltip=tooltip)
        layout.addWidget(label, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        if tooltip:
            layout.addWidget(self._create_settings_hint_label(tooltip), 1, 1)
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
        row.setObjectName("settings_row")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_NONE)

        controls = QWidget(row)
        controls.setObjectName("settings_row")
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

    def _create_shortcut_action_row(self, title: str, hint: str, action):
        row = QWidget()
        row.setObjectName("settings_row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_SM)
        button = QPushButton("Создать")
        setup_standard_secondary_button(button, expand=False)
        button.clicked.connect(action)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        text_column = QWidget(row)
        text_column.setObjectName("settings_row")
        text_layout = QVBoxLayout(text_column)
        text_layout.setContentsMargins(*MARGINS_NONE)
        text_layout.setSpacing(SPACE_NONE)
        text_layout.addWidget(QLabel(title))
        text_layout.addWidget(self._create_settings_hint_label(hint))
        layout.addWidget(text_column, 1)
        return row, button

    def _create_settings_page_card(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(*MARGINS_NONE)
        page_layout.setSpacing(SPACE_NONE)
        page_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
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
            Qt.AlignmentFlag.AlignTop
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
            Qt.AlignmentFlag.AlignTop
        )

        content_layout.addWidget(card, 1)
        scroll.setWidget(content)
        return page, card_layout

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

    def _show_header_panel(self, panel: QWidget) -> None:
        for widget_name in ("settings_panel_widget", "help_panel_widget"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setVisible(widget is panel)

        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host.setVisible(True)
            host.adjustSize()
            host.updateGeometry()
        if not self.queue_panel.isHidden():
            host.setProperty("ribbonHidden", self.ribbon_panel.isHidden())
        self.queue_panel.hide()
        self.ribbon_panel.hide()

        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            self._apply_operations_tab_bar_theme()

    def show_settings_modal(self):
        """Показывает панель настроек поверх рабочей области."""
        settings_widget = self._ensure_settings_panel_widget()
        self.update_context_menu_button()
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
        setup_standard_dialog(dialog, title=title)
        dialog.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        dialog.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        dialog.setSizeGripEnabled(False)

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
        requested_width, requested_height = (510, 330)
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
            dialog.deleteLater()

    def hide_settings_panel(self):
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            self._apply_operations_tab_bar_theme()
        host = getattr(self, "settings_panel_host", None)
        was_open = host is not None and not host.isHidden()
        if host is not None:
            host.setVisible(False)
        if was_open:
            self.queue_panel.show()
            self.ribbon_panel.setVisible(not host.property("ribbonHidden"))
            if tab_bar.currentIndex() == self._settings_tab_index:
                tab_bar.setCurrentIndex(self.operations_stack.currentIndex())

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
        self.about_title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
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

        links = QHBoxLayout()
        self.about_github_button = QPushButton("GitHub")
        self.about_github_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(REPO_PAGE))
        )
        self.about_guide_button = QPushButton("Руководство")
        self.about_guide_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(GUIDE_URL))
        )
        copy_version = QPushButton("Скопировать версию")
        copy_version.clicked.connect(lambda: QApplication.clipboard().setText(f"{APP_DISPLAY_NAME} {APP_VERSION}"))
        for button in (self.about_github_button, self.about_guide_button, copy_version):
            setup_standard_secondary_button(button)
            links.addWidget(button, 1)
        layout.addLayout(links)

    def _add_settings_section(self, title: str) -> QVBoxLayout:
        section = QFrame()
        section.setObjectName("settings_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(*PAGE_CONTENT_MARGINS)
        layout.setSpacing(SPACE_SM)
        heading = QLabel(title)
        heading.setObjectName("settings_section_heading")
        heading.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(heading)
        layout.addSpacing(SPACE_SM)
        self.settings_content_layout.addWidget(section)
        return layout

    def create_settings_tab(self):
        """Создает панель основных настроек на всю доступную ширину."""
        tab = QWidget()
        tab.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        root_layout = QHBoxLayout(tab)
        root_layout.setContentsMargins(*MARGINS_NONE)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setObjectName("settings_page_scroll")
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_content = QWidget()
        settings_content.setObjectName("settings_page_content")
        self.settings_content_layout = QVBoxLayout(settings_content)
        self.settings_content_layout.setContentsMargins(*PAGE_CONTENT_MARGINS)
        self.settings_content_layout.setSpacing(PAGE_SECTION_SPACING)
        self.settings_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.settings_scroll.setWidget(settings_content)
        root_layout.addWidget(self.settings_scroll, 1)
        appearance_layout = self._add_settings_section("Внешний вид")
        behavior_layout = self._add_settings_section("Поведение")
        auto_clear_layout = self._add_settings_section("Файлы и папки")
        shortcuts_layout = self._add_settings_section("Интеграция Windows")

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

        desktop_shortcut_row, self.desktop_shortcut_button = self._create_shortcut_action_row(
            "Добавить ярлык на рабочий стол", "Создает ярлык «Мультифора» на рабочем столе.",
            self.create_desktop_shortcut,
        )
        shortcuts_layout.addWidget(desktop_shortcut_row)

        start_row, self.start_menu_shortcut_button = self._create_shortcut_action_row(
            "Меню Пуск", "Создает ярлык «Мультифора» в меню Пуск.",
            self.create_start_menu_shortcut,
        )
        shortcuts_layout.addWidget(start_row)

        context_row, self.context_menu_button = self._create_shortcut_action_row(
            "Контекстное меню Windows",
            "Добавляет пункт «Добавить в Мультифору» в меню файлов и папок.",
            self.toggle_context_menu_entry,
        )
        shortcuts_layout.addWidget(context_row)
        self.settings_content_layout.addStretch()
        return tab

    def create_help_tab(self):
        """Создает отдельную панель справки со сведениями о программе."""
        tab = QWidget()
        tab.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
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
        status_bar = getattr(self, "status_bar", None)
        if not silent and status_bar is not None:
            status_bar.showMessage("Проверяем обновления…")
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
            status_bar = getattr(self, "status_bar", None)
            if not getattr(self, "_update_silent", False) and status_bar is not None:
                status_bar.showMessage(text_msg)

            if cmp_result == -1 and not getattr(self, "_update_silent", False):
                if automatic_updates_supported():
                    confirmation = QMessageBox.question(
                        self,
                        "Установка обновления",
                        f"{text_msg}\n\n"
                        "Скачать установщик с GitHub и запустить установку?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if confirmation != QMessageBox.StandardButton.Yes:
                        return
                    self.status_bar.showMessage("Загрузка обновления…")
                    action = getattr(self, "check_updates_action", None)
                    if action is not None:
                        action.setEnabled(False)
                    self._update_future = self._update_executor.submit(
                        download_and_launch_latest_installer, expected_tag=latest
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
                status_bar = getattr(self, "status_bar", None)
                if status_bar is not None:
                    status_bar.showMessage("Не удалось проверить обновления")
                choice = show_app_choice(
                    self, "Проверка обновлений", text_msg,
                    (("retry", "Повторить", "primary"), ("close", "Закрыть", "secondary")),
                    icon=QMessageBox.Icon.Warning, default_key="close", cancel_key="close",
                )
                if choice == "retry":
                    QTimer.singleShot(0, self.check_updates_now)
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
