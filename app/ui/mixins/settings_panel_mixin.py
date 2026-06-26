# -*- coding: utf-8 -*-

import concurrent.futures

from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
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

from app.core.update_checker import REPO_PAGE, check_for_updates
from app.ui.ui_components import (
    LeftAlignedToolButton,
    MenuLikeComboBox,
    apply_standard_menu_style,
    setup_standard_action_button,
    setup_standard_dialog,
    setup_standard_dropdown,
    setup_standard_line_input,
    sync_standard_menu_width,
)


class SettingsPanelMixin:
    @staticmethod
    def _setup_settings_checkbox(checkbox: QCheckBox):
        checkbox.setStyleSheet(
            """
            QCheckBox::indicator {
                margin-top: 1px;
            }
            """
        )
        return checkbox

    def _create_settings_checkbox_row(self, text: str, tooltip: str = ""):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        checkbox = QCheckBox()
        checkbox.setFixedSize(16, 16)
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(label_text)
        label.setFixedWidth(label_width)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label)
        layout.addWidget(field, 0)
        layout.addStretch()
        return row

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
        if callable(getattr(self, "_ensure_rename_history_settings_page", None)):
            self._ensure_rename_history_settings_page()

        host = getattr(self, "settings_panel_host", None)
        settings_index = getattr(self, "_settings_tab_index", -1)
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None and settings_index >= 0 and tab_bar.currentIndex() != settings_index:
            tab_bar.blockSignals(True)
            try:
                tab_bar.setCurrentIndex(settings_index)
            finally:
                tab_bar.blockSignals(False)

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
        except Exception:
            pass
        if hasattr(self, "settings_nav") and self.settings_nav is not None:
            target_row = getattr(self, "_pending_settings_nav_row", self.settings_nav.currentRow())
            if not isinstance(target_row, int) or target_row < 0 or target_row >= self.settings_nav.count():
                target_row = 0
            self.settings_nav.setCurrentRow(target_row)

    def hide_settings_panel(self):
        host = getattr(self, "settings_panel_host", None)
        if host is not None:
            host.setVisible(False)
        splitter = getattr(self, "main_splitter", None)
        if splitter is not None:
            splitter.setVisible(True)

    def _ensure_rename_history_settings_page(self):
        page = getattr(self, "rename_history_settings_page", None)
        if page is None:
            page = QWidget()
            page.setObjectName("rename_history_settings_page")
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(4)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            content = QWidget()
            content.setObjectName("rename_history_settings_content")
            content.setMaximumWidth(310)
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(4)
            content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            history_label = QLabel("История переименований")
            history_label.setStyleSheet("font-size: 13px;")
            history_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            content_layout.addWidget(history_label)

            self.rename_history_list = QListWidget()
            self.rename_history_list.setObjectName("rename_history_list")
            self.rename_history_list.setFixedHeight(86)
            self.rename_history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.rename_history_list.currentRowChanged.connect(self.on_history_row_changed)
            content_layout.addWidget(self.rename_history_list)

            self.btn_history_undo = QPushButton("Откатить")
            self.btn_history_undo.clicked.connect(self.undo_last_rename)
            self.btn_history_undo.setEnabled(False)
            history_buttons_widget, _ = self._build_rename_action_row([self.btn_history_undo])
            content_layout.addWidget(history_buttons_widget)

            page_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            page_layout.addStretch(1)

            self.rename_history_settings_page = page

        settings_stack = getattr(self, "settings_stack", None)
        if settings_stack is not None and settings_stack.indexOf(page) < 0:
            settings_stack.addWidget(page)

        settings_nav = getattr(self, "settings_nav", None)
        if settings_nav is not None and settings_nav.findItems("История переименований", Qt.MatchFlag.MatchExactly) == []:
            settings_nav.addItem("История переименований")

        return page

    def create_settings_tab(self):
        """Создает панель настроек с категориями слева и содержимым справа."""
        tab = QWidget()
        tab.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        settings_font = QFont()
        settings_font.setPointSize(13)
        tab.setFont(settings_font)
        root_layout = QHBoxLayout(tab)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        self.settings_nav = QListWidget()
        self.settings_nav.setObjectName("settings_nav")
        self._settings_nav_base_width = 180
        self.settings_nav.setFixedWidth(self._settings_nav_base_width)
        self.settings_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_nav.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.settings_nav.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.settings_nav.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        nav_font = QFont()
        nav_font.setPointSize(10)
        nav_font.setBold(True)
        nav_font.setWeight(800)
        for title in ["Внешний вид", "Поведения", "Ярлыки", "Обновления", "Логи"]:
            item = QListWidgetItem(title)
            item.setFont(nav_font)
            self.settings_nav.addItem(item)
        self.settings_nav.verticalScrollBar().rangeChanged.connect(lambda _min, _max: self._update_settings_nav_width())
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)
        nav_layout.addWidget(self.settings_nav, 1)

        root_layout.addWidget(nav_container, 0)

        self.settings_stack = QStackedWidget()
        root_layout.addWidget(self.settings_stack, 1)

        appearance_page = QWidget()
        appearance_layout = QVBoxLayout(appearance_page)
        appearance_layout.setContentsMargins(0, 0, 0, 0)
        appearance_layout.setSpacing(0)

        appearance_scroll = QScrollArea()
        appearance_scroll.setWidgetResizable(True)
        appearance_scroll.setFrameShape(QFrame.Shape.NoFrame)
        appearance_scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        appearance_layout.addWidget(appearance_scroll)

        appearance_content = QWidget()
        appearance_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        appearance_content_layout = QVBoxLayout(appearance_content)
        appearance_content_layout.setContentsMargins(0, 4, 0, 0)
        appearance_content_layout.setSpacing(0)
        appearance_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        appearance_card = QFrame()
        appearance_card.setObjectName("settings_card")
        appearance_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        appearance_card_layout = QVBoxLayout(appearance_card)
        appearance_card_layout.setContentsMargins(8, 6, 8, 6)
        appearance_card_layout.setSpacing(4)

        self.theme_mode_combo = MenuLikeComboBox()
        setup_standard_dropdown(self.theme_mode_combo, fixed_width=200)
        self.theme_mode_combo.addItem("Как в системе", "system")
        self.theme_mode_combo.addItem("Темная", "dark")
        self.theme_mode_combo.addItem("Светлая", "light")
        self.theme_mode_combo.currentIndexChanged.connect(self._on_theme_mode_changed)
        theme_row = self._create_settings_select_row("Тема:", self.theme_mode_combo)
        appearance_card_layout.addWidget(theme_row)

        appearance_card_layout.addStretch()
        appearance_content_layout.addWidget(appearance_card)
        appearance_scroll.setWidget(appearance_content)
        self.settings_stack.addWidget(appearance_page)

        behavior_page = QWidget()
        behavior_layout = QVBoxLayout(behavior_page)
        behavior_layout.setContentsMargins(0, 0, 0, 0)
        behavior_layout.setSpacing(0)

        behavior_scroll = QScrollArea()
        behavior_scroll.setWidgetResizable(True)
        behavior_scroll.setFrameShape(QFrame.Shape.NoFrame)
        behavior_scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        behavior_layout.addWidget(behavior_scroll)

        behavior_content = QWidget()
        behavior_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        behavior_content_layout = QVBoxLayout(behavior_content)
        behavior_content_layout.setContentsMargins(0, 4, 0, 0)
        behavior_content_layout.setSpacing(0)
        behavior_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        behavior_card = QFrame()
        behavior_card.setObjectName("settings_card")
        behavior_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        behavior_card_layout = QVBoxLayout(behavior_card)
        behavior_card_layout.setContentsMargins(8, 6, 8, 6)
        behavior_card_layout.setSpacing(4)

        auto_clear_row, self.auto_clear_checkbox = self._create_settings_checkbox_row(
            "Автоматически очищать список после операций",
            "После завершения копирования/переименования/конвертации список файлов будет очищен автоматически.",
        )
        self.auto_clear_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        behavior_card_layout.addWidget(auto_clear_row)

        disable_warning_row, self.disable_warning_dialogs_checkbox = self._create_settings_checkbox_row(
            "Отключить предупреждающие окна",
            "Предупреждения больше не будут открываться отдельными окнами и будут показаны только в строке состояния.",
        )
        self.disable_warning_dialogs_checkbox.stateChanged.connect(self._on_disable_warning_dialogs_changed)
        self.disable_warning_dialogs_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        behavior_card_layout.addWidget(disable_warning_row)

        behavior_card_layout.addStretch()

        behavior_content_layout.addWidget(behavior_card)
        behavior_scroll.setWidget(behavior_content)
        self.settings_stack.addWidget(behavior_page)

        shortcuts_page = QWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_page)
        shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        shortcuts_layout.setSpacing(0)

        shortcuts_scroll = QScrollArea()
        shortcuts_scroll.setWidgetResizable(True)
        shortcuts_scroll.setFrameShape(QFrame.Shape.NoFrame)
        shortcuts_scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        shortcuts_layout.addWidget(shortcuts_scroll)

        shortcuts_content = QWidget()
        shortcuts_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        shortcuts_content_layout = QVBoxLayout(shortcuts_content)
        shortcuts_content_layout.setContentsMargins(0, 4, 0, 0)
        shortcuts_content_layout.setSpacing(0)
        shortcuts_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        shortcuts_card = QFrame()
        shortcuts_card.setObjectName("settings_card")
        shortcuts_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        shortcuts_card_layout = QVBoxLayout(shortcuts_card)
        shortcuts_card_layout.setContentsMargins(8, 6, 8, 6)
        shortcuts_card_layout.setSpacing(4)

        desktop_shortcut_row, self.desktop_shortcut_checkbox = self._create_settings_checkbox_row(
            "Добавить ярлык на рабочий стол",
            "Создает ярлык 'Мультифора' на рабочем столе.",
        )
        self.desktop_shortcut_checkbox.stateChanged.connect(self.toggle_desktop_shortcut)
        self.desktop_shortcut_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        shortcuts_card_layout.addWidget(desktop_shortcut_row)

        start_menu_shortcut_row, self.start_menu_shortcut_checkbox = self._create_settings_checkbox_row(
            "Добавить ярлык в меню Пуск",
            "Создает ярлык 'Мультифора' в меню Пуск.",
        )
        self.start_menu_shortcut_checkbox.stateChanged.connect(self.toggle_start_menu_shortcut)
        self.start_menu_shortcut_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        shortcuts_card_layout.addWidget(start_menu_shortcut_row)

        context_menu_row, self.context_menu_checkbox = self._create_settings_checkbox_row(
            "Добавить в контекстное меню Windows",
            "Добавляет пункт 'Добавить в Мультифору' в контекстное меню файлов и папок.",
        )
        self.context_menu_checkbox.stateChanged.connect(self.toggle_context_menu)
        self.context_menu_checkbox.stateChanged.connect(lambda _state: self._schedule_settings_save())
        shortcuts_card_layout.addWidget(context_menu_row)
        shortcuts_card_layout.addStretch()

        shortcuts_content_layout.addWidget(shortcuts_card)
        shortcuts_scroll.setWidget(shortcuts_content)
        self.settings_stack.addWidget(shortcuts_page)

        updates_page = QWidget()
        updates_layout = QVBoxLayout(updates_page)
        updates_layout.setContentsMargins(0, 0, 0, 0)
        updates_layout.setSpacing(0)

        updates_scroll = QScrollArea()
        updates_scroll.setWidgetResizable(True)
        updates_scroll.setFrameShape(QFrame.Shape.NoFrame)
        updates_scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        updates_layout.addWidget(updates_scroll)

        updates_content = QWidget()
        updates_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        updates_content_layout = QVBoxLayout(updates_content)
        updates_content_layout.setContentsMargins(0, 4, 0, 0)
        updates_content_layout.setSpacing(0)
        updates_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        updates_card = QFrame()
        updates_card.setObjectName("settings_card")
        updates_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        updates_card_layout = QVBoxLayout(updates_card)
        updates_card_layout.setContentsMargins(8, 6, 8, 6)
        updates_card_layout.setSpacing(4)

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
        update_buttons_layout.setContentsMargins(0, 0, 0, 0)
        update_buttons_layout.setSpacing(4)

        self.btn_check_updates = QPushButton("Проверить обновления")
        setup_standard_action_button(self.btn_check_updates)
        self.btn_check_updates.clicked.connect(self.check_updates_now)
        update_buttons_layout.addWidget(self.btn_check_updates)

        self.btn_open_repo = QPushButton("Открыть GitHub")
        setup_standard_action_button(self.btn_open_repo)
        self.btn_open_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_PAGE)))
        update_buttons_layout.addWidget(self.btn_open_repo)

        updates_card_layout.addLayout(update_buttons_layout)
        updates_content_layout.addWidget(updates_card)
        updates_scroll.setWidget(updates_content)
        self.settings_stack.addWidget(updates_page)

        logs_page = QWidget()
        logs_layout = QVBoxLayout(logs_page)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(0)

        logs_scroll = QScrollArea()
        logs_scroll.setWidgetResizable(True)
        logs_scroll.setFrameShape(QFrame.Shape.NoFrame)
        logs_scroll.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        logs_layout.addWidget(logs_scroll)

        logs_content = QWidget()
        logs_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        logs_content_layout = QVBoxLayout(logs_content)
        logs_content_layout.setContentsMargins(0, 4, 0, 0)
        logs_content_layout.setSpacing(0)
        logs_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        logs_card = QFrame()
        logs_card.setObjectName("settings_card")
        logs_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        logs_card_layout = QVBoxLayout(logs_card)
        logs_card_layout.setContentsMargins(8, 6, 8, 6)
        logs_card_layout.setSpacing(4)

        logs_filters_row = QWidget()
        logs_filters_layout = QHBoxLayout(logs_filters_row)
        logs_filters_layout.setContentsMargins(0, 0, 0, 0)
        logs_filters_layout.setSpacing(4)

        self.logs_level_filter = LeftAlignedToolButton()
        self.logs_level_filter.setObjectName("header_cell_tl")
        self.logs_level_filter.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.logs_level_filter.setFixedHeight(24)
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
        self.logs_view.setReadOnly(True)
        self.logs_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.logs_view.setMaximumBlockCount(self.max_log_lines)
        try:
            self.logs_view.setFont(QFont("Consolas", 13))
        except Exception:
            pass
        logs_card_layout.addWidget(self.logs_view)

        logs_content_layout.addWidget(logs_card)
        logs_scroll.setWidget(logs_content)
        self.settings_stack.addWidget(logs_page)

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
        except Exception:
            pass
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
        except Exception:
            pass

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
