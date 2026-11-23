import os
import threading

from PySide6.QtCore import QEvent, QEventLoop, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from app.ui.ui_icons import apply_window_icons, ui_icon
from app.core.app_icons import _get_app_icon_qt_path
from app.core.app_identity import APP_WINDOW_TITLE
from app.core.app_ipc import _drain_queued_files
from app.core.app_utils import _debug_log, _log_ignored_error, signals_blocked
from app.core.conversion_formats import (
    CONVERSION_CATEGORIES,
    build_file_dialog_filter,
    category_for_file_type,
    format_for_path,
    mixed_source_label_for_category,
    source_formats_for_category,
)
from app.core.ipc_server import LocalFileServer
from app.core.message_boxes import install_warning_suppression_hook
from app.ui.file_table import FileListWidget
from app.ui.mixins import (
    AppearanceMixin,
    ConversionActionsMixin,
    FileListActionsMixin,
    FileListContextMixin,
    FileListPreviewMixin,
    LifecycleMixin,
    LoggingMixin,
    OperationsCompressUiMixin,
    OperationsTabLayoutMixin,
    RenameHistoryMixin,
    SettingsPanelMixin,
    TemplateApplyMixin,
    TemplateCrudMixin,
    TemplateParamsBaseMixin,
    TemplateParamsNumberingMixin,
    TemplateParamsTextMixin,
    WindowsIntegrationMixin,
    WorkerOpsMixin,
)
from app.ui.operation_controller import OperationController, bind_operation_worker, connect_operation_worker
from app.ui.operation_progress import OperationProgressDialog
from app.ui.operation_result_panel import OperationResultPanel
from app.ui.ui_components import (
    DropZoneOverlay,
    IconButton,
    FilterToolButton,
    LoggingStatusBar,
    ScrollableFilterMenu,
    apply_standard_field_style,
    refresh_standard_button_styles,
    refresh_standard_field_styles,
    setup_standard_header_dropdown,
    setup_standard_line_input,
    setup_standard_secondary_button,
    setup_standard_primary_button,
    sync_standard_menu_width,
)
from app.ui.ui_styles import (
    APP_MARGINS,
    FILE_INFO_LABEL_STYLE,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    SPACE_NONE,
    SPACE_SM,
    SPLITTER_GRIP_LABEL_STYLE,
    build_drop_zone_hint_style,
    build_drop_zone_overlay_style,
    build_drop_zone_surface_style,
    build_workspace_style,
    build_file_info_separator_style,
)
from core.file_models import FileItem
from core.operation_requests import MergeRequest, OperationRequest, RenameRequest


class MultiforaMainWindow(
    LifecycleMixin,
    LoggingMixin,
    RenameHistoryMixin,
    WorkerOpsMixin,
    WindowsIntegrationMixin,
    TemplateCrudMixin,
    TemplateParamsBaseMixin,
    TemplateParamsTextMixin,
    TemplateParamsNumberingMixin,
    TemplateApplyMixin,
    FileListActionsMixin,
    FileListContextMixin,
    FileListPreviewMixin,
    AppearanceMixin,
    SettingsPanelMixin,
    OperationsTabLayoutMixin,
    OperationsCompressUiMixin,
    ConversionActionsMixin,
    QMainWindow,
):
    """Главное окно Мультифора"""

    def __init__(self):
        super().__init__()
        try:
            icon_path = _get_app_icon_qt_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            _debug_log(f"Ошибка установки иконки окна: {e}")
        self.files = []
        self._operations = OperationController()
        self.current_template = ""
        self.custom_templates = {}
        self.windows_context_menu_enabled = False
        self.desktop_shortcut_enabled = False
        self.start_menu_shortcut_enabled = False
        self.disable_warning_dialogs = False
        self.theme_mode = "system"
        self._ipc_file_server: LocalFileServer | None = None
        self._log_lines = []
        self.max_log_lines = 1000
        self._log_file_path = None
        self._pending_close = False
        self._operation_errors = []
        self._rename_history = []
        self._max_rename_history = 20
        self._is_undo_operation = False
        self._pending_undo_entry = None
        self._pending_window_geometry = None
        self._pending_window_pos = None
        self._pending_window_size = None
        self._pending_window_maximized = False
        self._geometry_restore_applied = False
        self._header_compact_mode = None
        self._column_sort_section = None
        self._column_sort_order = Qt.SortOrder.AscendingOrder
        self._splitter_grip_label = None
        self.init_logging()
        install_warning_suppression_hook()

        self.initial_load_complete = False

        self.init_ui()
        self.attach_action_logging()
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(250)
        self._settings_save_timer.timeout.connect(self._save_settings_if_ready)
        self.load_settings()
        self.ensure_context_menu_registration()
        self.update_template_combo()
        pending_template_session = getattr(
            self, "_pending_template_session_state", None
        )
        if pending_template_session:
            try:
                self.restore_template_session_state(pending_template_session)
            except Exception as e:
                _debug_log(f"Ошибка восстановления шаблона сессии: {e}")
        else:
            self.combo_templates.setCurrentText("Добавить текст в конец")
        self._update_undo_button()
        self.update_file_info()

        self.create_ipc_server()

        QTimer.singleShot(0, self.process_startup_queue)
        self.queue_timer = QTimer(self)
        self.queue_timer.setInterval(500)
        self.queue_timer.timeout.connect(self.process_startup_queue)
        self.queue_timer.start()

        self._queue_paths_refresh_timer = QTimer(self)
        self._queue_paths_refresh_timer.setInterval(5000)
        self._queue_paths_refresh_timer.timeout.connect(self.refresh_queue_paths)
        self._queue_paths_refresh_timer.start()

        QTimer.singleShot(1500, self.check_updates_on_startup)
        QTimer.singleShot(0, self._preload_file_worker_async)

    def _preload_file_worker_async(self) -> None:
        """Загружает необязательные библиотеки без задержки нажатия кнопки."""
        if getattr(self, "_file_worker_preload_thread", None) is not None:
            return

        def preload() -> None:
            try:
                from app.workers.compression_worker import (  # noqa: F401
                    CompressionWorker,
                )
                from app.workers.conversion_worker import (  # noqa: F401
                    ConversionWorker,
                )
            except Exception as error:
                _debug_log(f"Не удалось предварительно загрузить обработчик: {error}")

        self._file_worker_preload_thread = threading.Thread(
            target=preload,
            name="multifora-worker-preload",
            daemon=True,
        )
        self._file_worker_preload_thread.start()

    def create_ipc_server(self):
        self._ipc_file_server = LocalFileServer(self.log_event, self)
        self._ipc_file_server.files_queued.connect(self._bring_main_window_to_front)
        self._ipc_file_server.files_received.connect(self._receive_ipc_batch)
        self._ipc_file_server.start()

    def _add_files_with_source_message(
        self, file_paths: list[str], source_suffix: str
    ) -> bool:
        """Добавляет файлы и показывает унифицированный статус по источнику."""
        if not file_paths:
            return False
        self.add_files(file_paths)
        self.log_event(f"Получено {self._ru_files_label(len(file_paths))} {source_suffix}")
        return True

    def _bring_main_window_to_front(self) -> None:
        """Поднимает окно поверх остальных и снимает состояние свёрнутости."""
        self.show()
        self.activateWindow()
        self.raise_()
        self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowMinimized
            | Qt.WindowState.WindowActive
        )

    def add_files_from_ipc(self, file_paths):
        if self._ipc_file_server is not None:
            self._ipc_file_server.enqueue(file_paths)

    def _receive_ipc_batch(self, file_paths):
        self._add_files_with_source_message(file_paths, "через контекстное меню")

    def process_startup_queue(self):
        """Забирает файлы из очереди и добавляет в список."""
        files = _drain_queued_files()
        self._add_files_with_source_message(files, "из очереди")

    @staticmethod
    def _ru_files_label(count: int) -> str:
        n = abs(int(count)) % 100
        n1 = n % 10
        if 11 <= n <= 14:
            word = "файлов"
        elif n1 == 1:
            word = "файл"
        elif 2 <= n1 <= 4:
            word = "файла"
        else:
            word = "файлов"
        return f"{count} {word}"

    @property
    def file_worker(self):
        return self._operations.worker

    @file_worker.setter
    def file_worker(self, worker):
        self._operations.worker = worker

    @property
    def _last_operation_request(self) -> OperationRequest | None:
        return self._operations.last_request

    def create_file_worker(self, operation=None):
        """Создаёт обработчик операции и подключает сигналы."""
        if not self._ensure_operation_can_start():
            return False
        from app.workers.factory import create_operation_worker

        bind_operation_worker(self, create_operation_worker(operation))
        return True

    def _start_operation(self, request: OperationRequest, files: list[FileItem]) -> bool:
        started = self._operations.start(
            request,
            files,
            can_start=self._ensure_operation_can_start,
            connect=lambda worker: connect_operation_worker(self, worker),
        )
        if not started:
            self._hide_progress_dialog()
        else:
            self.operation_result_panel.set_pending("Выполняется операция…")
            self._refresh_launch_button_states()
        return started

    def _operation_start_block_reason(self) -> str:
        metadata = getattr(self, "_file_metadata_worker", None)
        if metadata is not None and metadata.isRunning():
            return "Дождитесь завершения чтения метаданных файлов"
        if self._operation_is_running():
            return "Дождитесь завершения текущей операции"
        return ""

    def _refresh_launch_button_states(self) -> None:
        reason = self._operation_start_block_reason()
        if reason:
            for button in (self.btn_apply_rename, self.btn_convert, self.btn_compress, self.btn_merge):
                button.setEnabled(False)
                button.setToolTip(reason)
            if not getattr(self, "_launch_refresh_pending", False):
                self._launch_refresh_pending = True
                QTimer.singleShot(100, self, self._poll_launch_button_states)
            return
        self.refresh_rename_preview()
        self.update_convert_button_state()
        self._update_compress_button()
        self._update_merge_button_state()
        self.refresh_active_file_preview()

    def _poll_launch_button_states(self) -> None:
        self._launch_refresh_pending = False
        self._refresh_launch_button_states()

    def _operation_is_running(self) -> bool:
        worker = getattr(self, "file_worker", None)
        is_running = getattr(worker, "isRunning", None)
        return bool(
            worker is not None and callable(is_running) and is_running()
        )

    def _ensure_operation_can_start(self) -> bool:
        metadata_worker = getattr(self, "_file_metadata_worker", None)
        if metadata_worker is not None and metadata_worker.isRunning():
            QMessageBox.warning(
                self,
                "Добавление файлов выполняется",
                "Дождитесь завершения чтения метаданных файлов.",
            )
            return False
        if not self._operation_is_running():
            return True
        QMessageBox.warning(
            self,
            "Операция уже выполняется",
            "Дождитесь завершения текущей операции, прежде чем запускать другую.",
        )
        return False

    def cancel_operation(self):
        """Запрашивает отмену текущей операции."""
        if self.file_worker and self.file_worker.isRunning():
            self.file_worker.request_cancel()
            self.progress_dialog.cancel_button.setEnabled(False)
            self._set_progress_status_text("Отмена операции...")
            self.status_bar.showMessage("Отмена операции...")

    def _set_progress_status_text(self, text: str) -> None:
        self.progress_dialog.set_status(text)

    def _create_progress_dialog(self) -> None:
        self.progress_dialog = OperationProgressDialog(
            self, getattr(self, "_effective_theme_mode", "dark")
        )
        self.progress_dialog.cancel_requested.connect(self.cancel_operation)
        self.progress_bar = self.progress_dialog.progress_bar

    def _show_progress_dialog(
        self,
        status_text: str = "Выполняется операция...",
        *,
        indeterminate: bool = False,
    ) -> None:
        self.progress_dialog.show_progress(status_text, indeterminate=indeterminate)

    def _show_operation_starting(self, status_text: str) -> None:
        """Сразу показывает запуск подтверждённой операции до подготовки.

        Загрузка необязательных библиотек может занять время. Предварительный
        показ индикатора сообщает пользователю, что нажатие обработано.
        """
        self._show_progress_dialog(status_text, indeterminate=True)
        self.status_bar.showMessage(status_text)
        QApplication.processEvents(
            QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )

    def _hide_progress_dialog(self):
        if (
            hasattr(self, "progress_dialog")
            and self.progress_dialog is not None
        ):
            self.progress_dialog.hide()

    def _collect_file_items_by_paths(self, paths: list[str]) -> list[FileItem]:
        items = []
        by_path = {getattr(f, "path", None): f for f in self.files}
        for path in paths:
            if path in by_path and by_path[path] is not None:
                items.append(by_path[path])
            else:
                try:
                    items.append(FileItem(path))
                except Exception as e:
                    _debug_log(f"Не удалось создать FileItem для {path}: {e}")
        return items

    def _retry_failed_operation(self, errors: list[dict]) -> None:
        request = self._last_operation_request
        if request is None or isinstance(request, MergeRequest):
            return
        failed_paths = [path for error in errors if (path := error.get("path"))]
        if isinstance(request, RenameRequest):
            request = request.for_retry(failed_paths)
            failed_paths = [path for path, _ in request.pairs]
        if not failed_paths:
            return
        files = self._collect_file_items_by_paths(failed_paths)
        self._show_operation_starting("Подготовка повторного выполнения операции...")
        if self._start_operation(request, files):
            self._show_progress_dialog("Повторное выполнение операции...")

    def refresh_preview_panel(self):
        if not hasattr(self, "list_files") or self.list_files is None:
            return
        try:
            self.list_files.refresh()
        except Exception as error:
            _log_ignored_error(
                "MultiforaMainWindow.refresh_preview_panel", error
            )

    @staticmethod
    def _setup_info_label(label: QLabel) -> QLabel:
        label.setFixedHeight(18)
        label.setStyleSheet(FILE_INFO_LABEL_STYLE)
        return label

    @staticmethod
    def _create_info_separator() -> QFrame:
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setObjectName("file_info_separator")
        separator.setStyleSheet(build_file_info_separator_style("dark"))
        separator.setFixedWidth(1)
        separator.setFixedHeight(16)
        return separator

    def _create_settings_panel_host(self) -> None:
        """Создаёт контейнер панели настроек."""
        self.settings_panel_host = QFrame()
        self.settings_panel_host.setObjectName("settings_panel_host")
        self.settings_panel_host.setVisible(False)
        self.settings_panel_host.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.settings_panel_host.setStyleSheet("QFrame#settings_panel_host { background: transparent; border: none; }")
        self.settings_panel_host_layout = QVBoxLayout(self.settings_panel_host)
        self.settings_panel_host_layout.setContentsMargins(*MARGINS_NONE)
        self.settings_panel_host_layout.setSpacing(SPACE_NONE)

    def _create_ribbon(self, main_layout, content_layout):
        self.ribbon_panel = self.create_operations_tab()
        main_layout.addWidget(self.operations_header_widget)
        content_layout.addWidget(self.ribbon_panel)
        self.support_page = self._create_support_page()
        self.settings_panel_host_layout.addWidget(self.support_page)
        self.support_page.hide()
        if (
            not hasattr(self, "settings_panel_widget")
            or self.settings_panel_widget is None
        ):
            self.settings_panel_widget = self.create_settings_tab()
        if self.settings_panel_widget.parent() is not self.settings_panel_host:
            self.settings_panel_widget.setParent(None)
            self.settings_panel_host_layout.addWidget(
                self.settings_panel_widget
            )
        if (
            not hasattr(self, "help_panel_widget")
            or self.help_panel_widget is None
        ):
            self.help_panel_widget = self.create_help_tab()
        if self.help_panel_widget.parent() is not self.settings_panel_host:
            self.help_panel_widget.setParent(None)
            self.settings_panel_host_layout.addWidget(self.help_panel_widget)
        self.help_panel_widget.setVisible(False)

        content_layout.addWidget(self.settings_panel_host)

    @staticmethod
    def _set_header_menu_open_state(button, is_open: bool) -> None:
        try:
            button.setProperty("menuOpen", bool(is_open))
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        except RuntimeError as error:
            _log_ignored_error(
                "MultiforaMainWindow._set_header_menu_open_state", error
            )

    def _bind_header_menu_state(self, button, menu) -> None:
        menu.aboutToShow.connect(
            lambda: self._set_header_menu_open_state(button, True)
        )
        menu.aboutToHide.connect(
            lambda: self._set_header_menu_open_state(button, False)
        )

    @staticmethod
    def _set_filter_actions_checked(
        menu, actions: dict, checked: bool, changed_callback
    ) -> None:
        for action in actions.values():
            with signals_blocked(action):
                action.setChecked(checked)
        if callable(getattr(menu, "sync_filter_items", None)):
            menu.sync_filter_items()
        changed_callback(False)

    def _add_filter_selection_actions(
        self, menu, actions: dict, changed_callback
    ):
        clear_action = QAction("Снять все отметки", menu)
        clear_action.setProperty("keepOpen", True)
        clear_action.setProperty("menuIconName", "clear-selection")
        clear_action.triggered.connect(
            lambda _checked=False: self._set_filter_actions_checked(
                menu,
                actions,
                False,
                changed_callback,
            )
        )
        menu.addAction(clear_action)

        select_all_action = QAction("Вернуть все отметки", menu)
        select_all_action.setProperty("keepOpen", True)
        select_all_action.setProperty("menuIconName", "select-all")
        select_all_action.triggered.connect(
            lambda _checked=False: self._set_filter_actions_checked(
                menu,
                actions,
                True,
                changed_callback,
            )
        )
        menu.addAction(select_all_action)
        menu.addSeparator()
        return clear_action, select_all_action

    def _create_extension_filter(self) -> None:
        self._list_header_ext_label = QLabel("Расширения:")
        self._list_header_ext_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_header_ext_label.setFixedWidth(90)
        self._list_header_ext_label.setVisible(False)

        self.btn_ext_filter = FilterToolButton()
        self.btn_ext_filter.setObjectName("header_cell_tl")
        setup_standard_header_dropdown(self.btn_ext_filter)
        self._ext_filter_menu = ScrollableFilterMenu(self.btn_ext_filter)
        self._ext_filter_menu.setObjectName("header_dropdown_popup")
        self._ext_filter_actions = {}
        (
            self._clear_ext_filter_action,
            self._select_all_ext_filter_action,
        ) = self._add_filter_selection_actions(
            self._ext_filter_menu,
            self._ext_filter_actions,
            self.on_extension_filter_changed,
        )

        options = (
            ("DOCX", ".docx"),
            ("PDF", ".pdf"),
            ("TXT", ".txt"),
            ("RTF", ".rtf"),
            ("ODT", ".odt"),
            ("JPG/JPEG", ".jpg"),
            ("PNG", ".png"),
            ("GIF", ".gif"),
            ("BMP", ".bmp"),
            ("TIFF", ".tiff"),
            ("WEBP", ".webp"),
            ("SVG", ".svg"),
            ("ICO", ".ico"),
            ("ZIP", ".zip"),
            ("RAR", ".rar"),
            ("7Z", ".7z"),
            ("TAR", ".tar"),
            ("GZ", ".gz"),
            ("Папки", "__folder__"),
            ("Другое", "__otherext__"),
        )
        for label, value in options:
            action = QAction(label, self._ext_filter_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self.on_extension_filter_changed)
            self._ext_filter_menu.add_filter_action(action)
            self._ext_filter_actions[value] = action

        self.btn_ext_filter.setMenu(self._ext_filter_menu)
        self._ext_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(
                self._ext_filter_menu,
                self.btn_ext_filter,
            )
        )
        self._bind_header_menu_state(
            self.btn_ext_filter, self._ext_filter_menu
        )
        self._update_ext_filter_button_text()

    def _create_type_filter(self) -> None:
        self._list_header_type_label = QLabel("Тип:")
        self._list_header_type_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_header_type_label.setFixedWidth(90)
        self._list_header_type_label.setVisible(False)

        self.btn_type_filter = FilterToolButton()
        self.btn_type_filter.setObjectName("header_cell_tr")
        setup_standard_header_dropdown(self.btn_type_filter)
        self._type_filter_menu = ScrollableFilterMenu(self.btn_type_filter)
        self._type_filter_menu.setObjectName("header_dropdown_popup")
        self._type_filter_actions = {}
        (
            self._clear_type_filter_action,
            self._select_all_type_filter_action,
        ) = self._add_filter_selection_actions(
            self._type_filter_menu,
            self._type_filter_actions,
            self.on_file_type_filter_changed,
        )

        options = (
            ("Документы", "document"),
            ("Презентации", "presentation"),
            ("Изображения", "image"),
            ("Архивы", "archive"),
            ("Папки", "folder"),
            ("Другое", "other"),
        )
        for label, value in options:
            action = QAction(label, self._type_filter_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self.on_file_type_filter_changed)
            self._type_filter_menu.add_filter_action(action)
            self._type_filter_actions[value] = action

        self.btn_type_filter.setMenu(self._type_filter_menu)
        self._type_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(
                self._type_filter_menu,
                self.btn_type_filter,
            )
        )
        self._bind_header_menu_state(
            self.btn_type_filter, self._type_filter_menu
        )
        self._update_type_filter_button_text()

    def _create_list_header(self) -> QGridLayout:
        """Создаёт поиск и фильтры списка файлов без отдельного поля сортировки."""
        list_header = QGridLayout()
        self._list_header_layout = list_header
        list_header.setContentsMargins(*MARGINS_NONE)
        list_header.setHorizontalSpacing(12)
        list_header.setVerticalSpacing(SPACE_SM)

        self._create_extension_filter()
        self._create_type_filter()

        self._list_header_search_label = QLabel("Поиск:")
        self._list_header_search_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_header_search_label.setFixedWidth(90)
        self._list_header_search_label.setVisible(False)
        self.input_search = QLineEdit()
        self.input_search.setObjectName("header_cell_br")
        self.input_search.setPlaceholderText("Поиск")
        self.input_search.setClearButtonEnabled(True)
        self.search_icon_action = self.input_search.addAction(
            QIcon(), QLineEdit.ActionPosition.LeadingPosition
        )
        setup_standard_line_input(self.input_search)
        self.input_search.setMinimumWidth(0)
        self.input_search.textChanged.connect(self.on_search_text_changed)

        for widget in (
            self.btn_ext_filter,
            self.btn_type_filter,
            self.input_search,
        ):
            widget.setMinimumHeight(HEADER_FIELD_HEIGHT)

        list_header.addWidget(self.btn_ext_filter, 0, 0)
        list_header.addWidget(self.btn_type_filter, 0, 1)
        list_header.addWidget(self.input_search, 0, 2)
        self.input_search.setAccessibleName("Поиск по имени файла")
        self.input_search.setToolTip("Поиск по имени файла (Ctrl+F)")
        self.btn_ext_filter.setAccessibleName("Фильтр по расширениям")
        self.btn_type_filter.setAccessibleName("Фильтр по типам")
        for label, shortcut, callback in (
            ("Добавить файлы…", QKeySequence.StandardKey.Open, self.select_files),
            ("Добавить папку…", QKeySequence("Ctrl+Shift+O"), self.select_folder),
        ):
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)
        find_action = QAction("Поиск", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.input_search.setFocus)
        self.addAction(find_action)
        list_header.setColumnStretch(0, 1)
        list_header.setColumnStretch(1, 1)
        list_header.setColumnStretch(2, 2)
        return list_header

    def _create_file_list_widget(
        self, files_panel_layout: QVBoxLayout
    ) -> None:
        self.list_files = FileListWidget()
        self.list_files.setObjectName("files_list")
        self.list_files.setAccessibleName("Очередь файлов")
        self.list_files.model().full_path_tooltip = True
        self.list_files.setFrameShape(QFrame.Shape.NoFrame)
        self.list_files.setWordWrap(False)
        self.list_files.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.list_files.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        apply_standard_field_style(self.list_files)
        self.list_files.setProperty("preview_mode", True)
        self.list_files.filesDropped.connect(self.add_files)
        self.list_files.itemDoubleClicked.connect(self.open_file)
        self.list_files.itemSelectionChanged.connect(
            self.on_file_selection_changed
        )
        self.list_files.orderChanged.connect(self.on_list_order_changed)
        self.list_files.deleteRequested.connect(
            self.remove_selected_files_from_list
        )
        self.list_files.openRequested.connect(self.open_selected_items)
        self.list_files.copyRequested.connect(
            self.copy_selected_files_to_clipboard
        )
        self.list_files.renameRequested.connect(self.rename_selected_item)
        table_header = self.list_files.horizontalHeader()
        table_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table_header.setSectionsClickable(True)
        table_header.setSortIndicatorShown(False)
        table_header.sectionClicked.connect(self.on_file_header_clicked)
        self.list_files.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.list_files.customContextMenuRequested.connect(
            self.show_file_context_menu
        )
        files_panel_layout.addWidget(self.list_files, 1)
        from app.ui.merge_pages import MergePagesPanel
        self.merge_pages_panel = MergePagesPanel(self)
        self.merge_pages_panel.hide()
        self.merge_pages_panel.ready_changed.connect(self._update_merge_button_state)
        QApplication.instance().aboutToQuit.connect(self.merge_pages_panel.stop)
        files_panel_layout.addWidget(self.merge_pages_panel, 1)

    def _create_drop_zone(self, files_panel: QWidget) -> None:
        self.drop_zone_controls = DropZoneOverlay(files_panel)
        self.drop_zone_controls.setObjectName("drop_zone_overlay")
        self.drop_zone_controls.setAcceptDrops(True)
        self.drop_zone_controls.installEventFilter(self)
        self.drop_zone_controls.setStyleSheet(
            build_drop_zone_overlay_style("dark")
        )
        drop_zone_layout = QVBoxLayout(self.drop_zone_controls)
        drop_zone_layout.setContentsMargins(10, 8, 10, 8)
        drop_zone_layout.setSpacing(10)
        drop_zone_layout.addStretch()
        self.drop_document = QLabel()
        self.drop_document.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_zone_layout.addWidget(self.drop_document)
        self.drop_zone_hint_label = QLabel("Перетащите файлы или папки сюда")
        self.drop_zone_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_zone_layout.addWidget(self.drop_zone_hint_label)
        drop_buttons_row = QHBoxLayout()
        self.drop_buttons_layout = drop_buttons_row
        drop_buttons_row.setSpacing(12)
        drop_buttons_row.addStretch()
        self.btn_add_files = IconButton("Добавить файлы")
        setup_standard_primary_button(self.btn_add_files, expand=False)
        self.btn_add_files.clicked.connect(self.select_files)
        self.btn_add_folder = IconButton("Добавить папки")
        setup_standard_secondary_button(self.btn_add_folder, expand=False)
        self.btn_add_folder.clicked.connect(self.select_folder)
        for button in (self.btn_add_files, self.btn_add_folder):
            # Иконки присваиваются позже через apply_window_icons(). Пока
            # не фиксируем ширину: иначе текст измерится без иконки и обрежется.
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            drop_buttons_row.addWidget(button)
        drop_buttons_row.addStretch()
        drop_zone_layout.addLayout(drop_buttons_row)
        self.btn_reset_queue_filters = IconButton("Сбросить фильтры")
        setup_standard_secondary_button(self.btn_reset_queue_filters)
        self.btn_reset_queue_filters.clicked.connect(self._reset_queue_filters)
        drop_zone_layout.addWidget(self.btn_reset_queue_filters)
        self.btn_show_all_queue_files = IconButton("Показать общую очередь")
        setup_standard_secondary_button(self.btn_show_all_queue_files)
        self.btn_show_all_queue_files.clicked.connect(lambda: self.operations_tab_bar.setCurrentIndex(0))
        drop_zone_layout.addWidget(self.btn_show_all_queue_files)
        drop_zone_layout.addStretch()

    def _connect_drop_zone_updates(self, files_panel: QWidget) -> None:
        model = self.list_files.model()
        model.rowsInserted.connect(
            lambda *_args: self._update_drop_zone_controls()
        )
        model.rowsRemoved.connect(
            lambda *_args: self._update_drop_zone_controls()
        )
        model.modelReset.connect(
            lambda *_args: self._update_drop_zone_controls()
        )
        files_panel.installEventFilter(self)
        self.list_files.installEventFilter(self)
        self.list_files.viewport().installEventFilter(self)
        # Во вкладке объединения список файлов скрыт, а рабочую область
        # занимает MergePagesPanel. Следим за его геометрией отдельно:
        # иначе оверлей рассчитывается по скрытому viewport списка и
        # смещается влево относительно видимой рабочей области.
        if hasattr(self, "merge_pages_panel"):
            merge_panel = self.merge_pages_panel
            # В режиме объединения принимать внешние файлы на всей площади
            # панели и на дочерних виджетах (подсказка, список, viewport и т.д.).
            # Так QLabel и другие дочерние элементы не перехватывают drag&drop.
            for target in (merge_panel, *merge_panel.findChildren(QWidget)):
                target.setAcceptDrops(True)
                target.installEventFilter(self)
        self._update_drop_zone_controls()
        QTimer.singleShot(0, self._update_drop_zone_controls)

    def _create_files_preview(
        self,
        right_layout: QVBoxLayout,
    ) -> None:
        files_preview_row = QWidget()
        files_preview_row.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        files_preview_layout = QHBoxLayout(files_preview_row)
        files_preview_layout.setContentsMargins(*MARGINS_NONE)
        files_preview_layout.setSpacing(SPACE_SM)

        files_panel = QWidget()
        self.files_panel = files_panel
        files_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        files_panel.setObjectName("drop_zone_surface")
        files_panel.setStyleSheet(build_drop_zone_surface_style("light"))
        files_panel_layout = QVBoxLayout(files_panel)
        files_panel_layout.setContentsMargins(1, 1, 1, 1)
        files_panel_layout.setSpacing(SPACE_NONE)

        self._create_file_list_widget(files_panel_layout)
        self._create_drop_zone(files_panel)
        self._connect_drop_zone_updates(files_panel)

        files_preview_layout.addWidget(files_panel, 1)
        right_layout.addWidget(files_preview_row, 1)

    def _create_file_info_layout(self) -> QHBoxLayout:
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(*MARGINS_NONE)
        info_layout.setSpacing(SPACE_SM)

        self.label_count = self._setup_info_label(QLabel("Файлов: 0"))
        info_layout.addWidget(self.label_count)

        count_size_separator = self._create_info_separator()
        info_layout.addWidget(count_size_separator)

        self.label_item_size = self._setup_info_label(QLabel("Отмечено: 0"))
        info_layout.addWidget(self.label_item_size)

        size_total_separator = self._create_info_separator()
        info_layout.addWidget(size_total_separator)
        self._file_info_separators = [
            count_size_separator,
            size_total_separator,
        ]

        self.label_total_size = self._setup_info_label(
            QLabel("Всего: 0 МБ")
        )
        info_layout.addWidget(self.label_total_size)

        self.rename_status_group = QWidget()
        status = QHBoxLayout(self.rename_status_group)
        status.setContentsMargins(*MARGINS_NONE)
        status.setSpacing(SPACE_SM)
        separator = self._create_info_separator()
        self._file_info_separators.append(separator)
        status.addWidget(separator)
        self.rename_validation_label = self._setup_info_label(QLabel("Нет файлов"))
        status.addWidget(self.rename_validation_label)
        self.btn_locate_rename_issue = IconButton("К проблеме")
        setup_standard_secondary_button(self.btn_locate_rename_issue, expand=False)
        self.btn_locate_rename_issue.setToolTip("Показать первую проблему с именем")
        self.btn_locate_rename_issue.clicked.connect(self._locate_rename_issue)
        self.btn_locate_rename_issue.hide()
        status.addWidget(self.btn_locate_rename_issue)
        info_layout.addWidget(self.rename_status_group)
        self.rename_status_group.setVisible(self._active_operation_id() == "rename")
        info_layout.addStretch()
        return info_layout

    def _create_right_panel(self) -> QWidget:
        """Создаёт панель поиска, списка файлов и сводной информации."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(*MARGINS_NONE)
        right_layout.setSpacing(12)

        list_header = self._create_list_header()
        right_layout.addLayout(list_header)
        self._create_files_preview(right_layout)
        self._create_progress_dialog()
        info_panel = QFrame()
        info_panel.setObjectName("file_info_panel")
        summary_layout = QVBoxLayout(info_panel)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)
        info_row = self._create_file_info_layout()
        self.btn_clear_active_filters = IconButton("Сбросить фильтры")
        setup_standard_secondary_button(self.btn_clear_active_filters, expand=False)
        self.btn_clear_active_filters.clicked.connect(self._reset_queue_filters)
        self.btn_clear_active_filters.hide()
        info_row.addWidget(self.btn_clear_active_filters)
        summary_layout.addLayout(info_row)
        self._filter_button_timer = QTimer(self)
        self._filter_button_timer.setSingleShot(True)
        self._filter_button_timer.timeout.connect(self._refresh_filter_button)
        self.operation_result_panel = OperationResultPanel()
        self.operation_result_panel.retry_requested.connect(self._retry_failed_operation)
        self.launch_buttons = {
            "rename": self.btn_open_rename_history,
            "convert": self.btn_convert,
            "compress": self.btn_compress,
            "merge": self.btn_merge,
        }
        for button in self.launch_buttons.values():
            self.operation_result_panel.launch_stack.addWidget(button)
        self.operation_result_panel.launch_stack.setCurrentWidget(self.launch_buttons[self._active_operation_id()])
        summary_layout.addWidget(self.operation_result_panel)
        right_layout.addWidget(info_panel)
        return right_widget

    def _create_status_bar(self) -> None:
        self.status_bar = LoggingStatusBar()
        self.status_bar.messageLogged.connect(self.on_status_message_logged)
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setContentsMargins(*MARGINS_NONE)
        self.status_bar.hide()
        self.status_bar.showMessage(
            "Готово. Перетащите файлы/папки в список или используйте кнопки добавления."
        )

    def init_ui(self) -> None:
        """Создаёт основную структуру интерфейса приложения."""
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.resize(1200, 700)

        central = QWidget()
        central.setObjectName("workspace")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, APP_MARGINS[1], 0, APP_MARGINS[3])
        main_layout.setSpacing(14)

        self._create_settings_panel_host()
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(APP_MARGINS[0], 0, APP_MARGINS[2], 0)
        content_layout.setSpacing(14)
        self._create_ribbon(main_layout, content_layout)
        self.queue_panel = self._create_right_panel()
        content_layout.addWidget(self.queue_panel, 1)
        main_layout.addWidget(content_widget, 1)
        self._create_status_bar()

        self.setMinimumSize(900, 550)
        self.apply_theme_mode(self.theme_mode)
        self.setup_system_theme_tracking()
        self._update_header_compact_mode()
        self._schedule_filter_button_refresh()

    def showEvent(self, event):
        super().showEvent(event)
        has_pending_geometry = (
            getattr(self, "_pending_window_geometry", None)
            or getattr(self, "_pending_window_pos", None)
            or getattr(self, "_pending_window_size", None)
            or getattr(self, "_pending_window_maximized", False)
        )
        if has_pending_geometry:
            QTimer.singleShot(100, self._restore_window_geometry_from_pending)
        else:
            QTimer.singleShot(
                150, lambda: setattr(self, "initial_load_complete", True)
            )

    def _restore_window_geometry_from_pending(self):
        if self._geometry_restore_applied:
            return
        self._geometry_restore_applied = True
        self._restoring_window_geometry = True
        try:
            pending_pos = getattr(self, "_pending_window_pos", None)
            pending_size = getattr(self, "_pending_window_size", None)
            pending_geom = getattr(self, "_pending_window_geometry", None)

            applied = False
            if pending_pos is not None:
                try:
                    if pending_size is not None:
                        self.setGeometry(*pending_pos, *pending_size)
                    else:
                        self.move(*pending_pos)
                    applied = True
                except (RuntimeError, TypeError, OverflowError) as error:
                    _log_ignored_error("восстановления положения окна", error)

            if not applied and isinstance(pending_geom, str) and pending_geom:
                try:
                    applied = bool(
                        self.restoreGeometry(bytes.fromhex(pending_geom))
                    )
                except Exception as e:
                    _debug_log(f"Error restoring window geometry: {e}")

            if not applied and not getattr(
                self, "_pending_window_maximized", False
            ):
                try:
                    self.setGeometry(100, 100, 1200, 700)
                except Exception as error:
                    _log_ignored_error(
                        "MultiforaMainWindow._restore_window_geometry_from_pending",
                        error,
                    )

            if getattr(self, "_pending_window_maximized", False):
                try:
                    self.setWindowState(
                        self.windowState() | Qt.WindowState.WindowMaximized
                    )
                except Exception as e:
                    _debug_log(f"Error restoring maximized state: {e}")
        finally:
            self._restoring_window_geometry = False
            self.initial_load_complete = True

    def _fit_drop_zone_button_labels(self):
        """Подгоняет кнопки после загрузки иконок, по реальной области Qt."""
        for button in (self.btn_add_files, self.btn_add_folder):
            button.ensurePolished()
            icon_width = button.icon().actualSize(button.iconSize()).width()
            # draw_icon_caption() использует интервал 5px и рисует глифы
            # через QPainterPath. Небольшой запас учитывает края глифов.
            needed = button.fontMetrics().horizontalAdvance(button.text()) + 5
            if icon_width:
                needed += icon_width + 5
            width = max(1, button.sizeHint().width())
            for _ in range(40):
                option = QStyleOptionButton()
                button.initStyleOption(option)
                option.rect.setWidth(width)
                content_rect = button.style().subElementRect(
                    QStyle.SubElement.SE_PushButtonContents, option, button
                )
                if content_rect.width() >= needed:
                    break
                width += max(4, needed - content_rect.width())
            button.setFixedWidth(width)

    def _apply_theme_runtime_widgets(self):
        mode = getattr(self, "_effective_theme_mode", "dark")
        apply_window_icons(self, mode)
        self._fit_drop_zone_button_labels()
        try:
            if callable(
                getattr(self, "_apply_operations_tab_bar_theme", None)
            ):
                self._apply_operations_tab_bar_theme(mode)
        except Exception as error:
            _log_ignored_error(
                "MultiforaMainWindow._apply_theme_runtime_widgets", error
            )
        for separator in getattr(self, "_file_info_separators", []):
            try:
                separator.setStyleSheet(build_file_info_separator_style(mode))
            except Exception as error:
                _log_ignored_error(
                    "MultiforaMainWindow._apply_theme_runtime_widgets", error
                )
        # Кнопки фильтров хранят маркер темы для локального оформления самих полей.
        # Выпадающие меню получают оформление из общего стиля приложения.
        for widget_name in ("btn_ext_filter", "btn_type_filter"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                try:
                    widget._effective_theme_mode = mode
                except Exception as error:
                    _log_ignored_error(
                        "MultiforaMainWindow._apply_theme_runtime_widgets",
                        error,
                    )
        if (
            hasattr(self, "progress_dialog")
            and self.progress_dialog is not None
        ):
            self.progress_dialog._effective_theme_mode = mode
        try:
            refresh_standard_button_styles(self)
            refresh_standard_field_styles(self)
        except Exception as error:
            _log_ignored_error(
                "MultiforaMainWindow._apply_theme_runtime_widgets", error
            )
        if (
            hasattr(self, "_splitter_grip_label")
            and self._splitter_grip_label is not None
        ):
            self._splitter_grip_label.setStyleSheet(SPLITTER_GRIP_LABEL_STYLE)
        if hasattr(self, "files_panel") and self.files_panel is not None:
            self.files_panel.setStyleSheet(build_drop_zone_surface_style(mode))
        if (
            hasattr(self, "drop_zone_controls")
            and self.drop_zone_controls is not None
        ):
            self.drop_zone_controls.setStyleSheet(
                build_drop_zone_overlay_style(mode)
            )
            if hasattr(self, "drop_zone_hint_label"):
                self.drop_zone_hint_label.setStyleSheet(
                    build_drop_zone_hint_style(mode)
                )
        self.drop_document.setPixmap(ui_icon("document", mode).pixmap(36, 36))
        self.centralWidget().setStyleSheet(build_workspace_style(mode))
        self.list_files.horizontalHeader().setFixedHeight(32)



    def _schedule_settings_save(self):
        if not getattr(self, "initial_load_complete", False):
            return
        if hasattr(self, "_settings_save_timer"):
            self._settings_save_timer.start()

    def _save_settings_if_ready(self):
        if not getattr(self, "initial_load_complete", False):
            return
        try:
            self.save_settings()
        except Exception as e:
            _debug_log(f"Ошибка автосохранения настроек: {e}")

    def _update_type_filter_button_text(self):
        if (
            not hasattr(self, "_type_filter_actions")
            or not self._type_filter_actions
        ):
            return
        total = len(self._type_filter_actions)
        checked = sum(
            1 for a in self._type_filter_actions.values() if a.isChecked()
        )
        if hasattr(self, "_clear_type_filter_action"):
            self._clear_type_filter_action.setEnabled(checked > 0)
        if hasattr(self, "_select_all_type_filter_action"):
            self._select_all_type_filter_action.setEnabled(checked < total)
        if checked == total:
            self.btn_type_filter.setText("Все типы")
        else:
            self.btn_type_filter.setText(f"Типы: {checked}")

    def _update_ext_filter_button_text(self):
        if (
            not hasattr(self, "_ext_filter_actions")
            or not self._ext_filter_actions
        ):
            return
        total = len(self._ext_filter_actions)
        checked = sum(
            1 for a in self._ext_filter_actions.values() if a.isChecked()
        )
        if hasattr(self, "_clear_ext_filter_action"):
            self._clear_ext_filter_action.setEnabled(checked > 0)
        if hasattr(self, "_select_all_ext_filter_action"):
            self._select_all_ext_filter_action.setEnabled(checked < total)
        if checked == total:
            self.btn_ext_filter.setText("Расширения")
        else:
            self.btn_ext_filter.setText(f"Расширения: {checked}")

    def _update_header_compact_mode(self):
        self._resize_queue_columns()
        compact = self.width() < 1080
        if self._header_compact_mode == compact:
            return
        self._header_compact_mode = compact

        if hasattr(self, "_list_header_type_label"):
            self._list_header_type_label.setVisible(False)
        if hasattr(self, "_list_header_ext_label"):
            self._list_header_ext_label.setVisible(False)
        if hasattr(self, "_list_header_search_label"):
            self._list_header_search_label.setVisible(False)
        if hasattr(self, "_list_header_layout"):
            layout = self._list_header_layout
            try:
                layout.setColumnStretch(0, 1)
                layout.setColumnStretch(1, 1)
                layout.setColumnStretch(2, 2)
            except Exception as error:
                _log_ignored_error(
                    "MultiforaMainWindow._update_header_compact_mode", error
                )

    def _resize_queue_columns(self, *_args):
        table = getattr(self, "list_files", None)
        if table is not None and isValid(table):
            column = table.model().COLUMN_PATH
            hide_path = table.width() < 560
            if table.isColumnHidden(column) != hide_path:
                table.setColumnHidden(column, hide_path)

    def _reset_queue_filters(self):
        with signals_blocked(self.input_search):
            self.input_search.clear()
        for menu, actions, update in (
            (self._ext_filter_menu, self._ext_filter_actions, self._update_ext_filter_button_text),
            (self._type_filter_menu, self._type_filter_actions, self._update_type_filter_button_text),
        ):
            self._set_filter_actions_checked(menu, actions, True, lambda _checked, callback=update: callback())
        self.update_file_list()
        self.input_search.setFocus()

    def _schedule_filter_button_refresh(self):
        timer = getattr(self, "_filter_button_timer", None)
        if timer is not None and isValid(timer):
            timer.start(0)

    def _refresh_filter_button(self):
        visible = self.list_files.model().rowCount()
        self.btn_clear_active_filters.setVisible(bool(visible) and self._is_any_filter_active())

    def _update_drop_zone_controls(self):
        overlay = getattr(self, "drop_zone_controls", None)
        host = getattr(self, "files_panel", None)
        if host is None or overlay is None or not isValid(host) or not isValid(overlay):
            return
        if self._active_operation_id() == "merge" and hasattr(self, "merge_pages_panel"):
            # В режиме объединения list_files скрыт. Его viewport может иметь
            # другую ширину/позицию, поэтому геометрию берём у видимой панели.
            active_surface = self.merge_pages_panel
        else:
            active_surface = self.list_files.viewport()
        field_rect = active_surface.rect()
        field_rect.moveTopLeft(active_surface.mapTo(host, field_rect.topLeft()))
        card = field_rect.adjusted(8, 6, -8, -6)
        buttons_width = (
            self.btn_add_files.sizeHint().width()
            + self.btn_add_folder.sizeHint().width()
            + self.drop_buttons_layout.spacing()
            + 20
        )
        card.setWidth(min(card.width(), max(510, buttons_width)))
        self.drop_buttons_layout.setDirection(
            QHBoxLayout.Direction.TopToBottom
            if card.width() < buttons_width
            else QHBoxLayout.Direction.LeftToRight
        )
        card.setHeight(min(card.height(), 196))
        card.moveCenter(field_rect.center())
        overlay.setGeometry(card)
        empty_view = not self.list_files.model().files()
        overlay.setVisible(empty_view)
        if not empty_view:
            return
        empty_queue = not self.files
        unsupported = not empty_queue and not self._files_visible_for_active_operation(self.files)
        self.drop_document.setVisible(empty_queue and card.height() >= 125)
        self.btn_add_files.setVisible(empty_queue)
        self.btn_add_folder.setVisible(empty_queue)
        self.btn_reset_queue_filters.setVisible(not empty_queue and not unsupported)
        self.btn_show_all_queue_files.setVisible(unsupported)
        if empty_queue:
            # На вкладке объединения явно подсказываем допустимые форматы.
            if self._active_operation_id() == "merge":
                message = "Перетащите PDF или DOCX сюда"
            else:
                message = "Перетащите файлы или папки сюда"
        elif unsupported:
            message = "Нет документов PDF или DOCX для объединения"
        else:
            message = "Ничего не найдено"
        self.drop_zone_hint_label.setText(message)
        overlay.raise_()

    def eventFilter(self, obj, event):
        if (
            hasattr(self, "files_panel")
            and obj is self.files_panel
            and event.type()
            in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.Move,
                QEvent.Type.LayoutRequest,
            )
        ):
            self._update_drop_zone_controls()
        if hasattr(self, "list_files") and isValid(self.list_files):
            viewport = self.list_files.viewport()
            merge_panel = getattr(self, "merge_pages_panel", None)
            merge_pages = getattr(merge_panel, "pages", None)
            if (
                obj is self.list_files or obj is viewport
                or obj is merge_panel or obj is merge_pages
            ) and event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.Move,
                QEvent.Type.LayoutRequest,
            ):
                self._update_drop_zone_controls()
        merge_panel = getattr(self, "merge_pages_panel", None)
        is_overlay = obj is getattr(self, "drop_zone_controls", None)
        is_merge_surface = (
            self._active_operation_id() == "merge"
            and merge_panel is not None
            and (
                obj is merge_panel
                or (isinstance(obj, QWidget) and merge_panel.isAncestorOf(obj))
            )
        )
        if (is_overlay or is_merge_surface) and event.type() in (
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
        ):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        elif (is_overlay or is_merge_surface) and event.type() == QEvent.Type.Drop:
            if event.mimeData().hasUrls():
                paths = []
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    if file_path and os.path.exists(file_path):
                        paths.append(file_path)
                if paths:
                    self.add_files(paths)
                    event.acceptProposedAction()
                    return True
        elif (is_overlay or is_merge_surface) and event.type() == QEvent.Type.DragLeave:
            event.accept()
            return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and hasattr(self, "list_files"):
            focus = self.focusWidget()
            viewport = self.list_files.viewport()
            if focus is self.list_files or focus is viewport:
                self.remove_selected_files_from_list()
                event.accept()
                return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_header_compact_mode()
        self._update_drop_zone_controls()
        if not getattr(self, "_restoring_window_geometry", False) and getattr(
            self, "initial_load_complete", False
        ):
            self._schedule_settings_save()

    def moveEvent(self, event):
        super().moveEvent(event)
        if not getattr(self, "_restoring_window_geometry", False) and getattr(
            self, "initial_load_complete", False
        ):
            self._schedule_settings_save()

    def update_converter_from_format(self):
        """Обновляет конвертер и автоматически включает смешанный режим."""
        selected_files = self._get_selected_or_all_file_items()
        category_combo = getattr(self, "convert_file_type_combo", None)

        category_label = ""
        if category_combo is not None:
            try:
                category_label = str(
                    category_combo.currentText() or ""
                ).strip()
            except Exception:
                category_label = ""

        categories = set()
        for file_item in selected_files:
            file_category = category_for_file_type(file_item.file_type)
            if file_category:
                categories.add(file_category)

        if category_label not in CONVERSION_CATEGORIES:
            category_label = ""
        if not category_label and len(categories) == 1:
            category_label = next(iter(categories))
            if category_combo is not None:
                index = category_combo.findText(category_label)
                if index >= 0:
                    with signals_blocked(category_combo):
                        category_combo.setCurrentIndex(index)

        if not category_label:
            with signals_blocked(self.from_convert_combo):
                self.from_convert_combo.clear()
                self.from_convert_combo.addItem("Выберите формат")
            with signals_blocked(self.to_convert_combo):
                self.to_convert_combo.clear()
                self.to_convert_combo.addItem("Выберите формат")
                self.to_convert_combo.setEnabled(False)
            self.btn_convert.setEnabled(False)
            return

        available_formats = source_formats_for_category(category_label)
        mixed_label = mixed_source_label_for_category(category_label)
        category_source_formats = {
            format_for_path(file_item.path)
            for file_item in selected_files
            if category_for_file_type(file_item.file_type) == category_label
            and format_for_path(file_item.path)
        }

        previous_source = str(
            self.from_convert_combo.currentText() or ""
        ).strip()
        with signals_blocked(self.from_convert_combo):
            self.from_convert_combo.clear()
            self.from_convert_combo.addItem("Выберите формат")
            if mixed_label:
                self.from_convert_combo.addItem(mixed_label)
            for fmt in available_formats:
                self.from_convert_combo.addItem(fmt)

        override = getattr(self, "_conversion_source_override", None)
        selected_source = ""
        if override is not None and override[0] == category_label:
            selected_source = override[1]
        elif len(category_source_formats) > 1:
            selected_source = mixed_label
        elif len(category_source_formats) == 1:
            selected_source = next(iter(category_source_formats))
        elif (
            previous_source == mixed_label
            or previous_source in available_formats
        ):
            selected_source = previous_source

        if selected_source:
            index = self.from_convert_combo.findText(selected_source)
            if index >= 0:
                with signals_blocked(self.from_convert_combo):
                    self.from_convert_combo.setCurrentIndex(index)
        else:
            with signals_blocked(self.from_convert_combo):
                self.from_convert_combo.setCurrentIndex(0)

        self.update_to_combo_based_on_from()
        if callable(getattr(self, "update_convert_button_state", None)):
            self.update_convert_button_state()

    def on_file_selection_changed(self):
        """Обработчик изменения выбора файлов"""
        if hasattr(self, "label_count"):
            self.update_file_info()
        self._update_merge_button_state()
        self.update_converter_from_format()
        if callable(getattr(self, "_auto_select_compress_type", None)):
            self._auto_select_compress_type()
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()
        if callable(getattr(self, "refresh_active_file_preview", None)):
            self.refresh_active_file_preview()
        elif callable(getattr(self, "refresh_preview_panel", None)):
            self.refresh_preview_panel()
        self._schedule_filter_button_refresh()

    def select_files(self):
        """Выбор файлов для обработки"""
        # Qt-диалог не загружает системные обработчики предпросмотра документов,
        # которые могут удерживать выбранные файлы после закрытия окна выбора.
        options = (
            QFileDialog.Option.ReadOnly
            | QFileDialog.Option.DontUseNativeDialog
            | QFileDialog.Option.DontUseCustomDirectoryIcons
            | QFileDialog.Option.HideNameFilterDetails
        )
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            "",
            build_file_dialog_filter(),
            options=options,
        )

        if files:
            self.add_files(files)

    def select_folder(self):
        """Выбор папки для добавления в список"""
        options = (
            QFileDialog.Option.ShowDirsOnly
            | QFileDialog.Option.DontUseNativeDialog
            | QFileDialog.Option.DontUseCustomDirectoryIcons
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку", "", options=options
        )

        if folder:
            self.add_files([folder])
