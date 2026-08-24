import json
import os
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QEvent, QTimer, Qt
from PyQt6.QtGui import QAction, QActionGroup, QColor, QIcon, QPalette
from PyQt6.QtNetwork import QLocalServer

from app.core.app_identity import APP_WINDOW_TITLE
from app.core.app_utils import _debug_log, _log_ignored_error
from app.core.app_ipc import (
    _drain_queued_files,
    _load_ipc_token,
    _get_ipc_server_name,
    _normalize_path_candidate,
)
from app.core.app_icons import _get_app_icon_qt_path
from app.core.message_boxes import install_warning_suppression_hook
from app.core.models import FileItem
from app.core.conversion_formats import (
    CONVERSION_CATEGORIES,
    build_file_dialog_filter,
    category_for_file_type,
    format_for_path,
    mixed_source_label_for_category,
    source_formats_for_category,
)

from app.ui.ui_components import (
    apply_standard_menu_style,
    apply_standard_field_style,
    DropActionTile,
    ExpandableGroupBox,
    FileListWidget,
    LeftAlignedToolButton,
    LoggingStatusBar,
    setup_standard_dialog,
    setup_standard_danger_button,
    setup_standard_header_dropdown,
    setup_standard_line_input,
    sync_standard_menu_width,
    refresh_standard_button_styles,
    refresh_standard_field_styles,
    refresh_standard_surface_styles,
)
from app.ui.ui_spacing import (
    APP_MARGINS,
    DIALOG_MARGINS,
    DROP_ZONE_MARGINS,
    HEADER_FIELD_HEIGHT,
    MARGINS_NONE,
    PROGRESS_HEIGHT,
    SPACE_NONE,
    SPACE_XXS,
    SPACE_SM,
    SPACE_XS,
    SPACE_LG,
    SPACE_XL,
    TOP_MENU_MARGINS,
)
from app.ui.mixins import (
    LifecycleMixin,
    LoggingMixin,
    RenameHistoryMixin,
    WindowsIntegrationMixin,
    WorkerOpsMixin,
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
)


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
        self.destination_folder = None
        self.file_worker = None
        self.current_template = ""
        self.custom_templates = {}
        self.windows_context_menu_enabled = False
        self.desktop_shortcut_enabled = False
        self.start_menu_shortcut_enabled = False
        self.disable_warning_dialogs = False
        self.theme_mode = "system"
        self.ghostscript_path_override = None
        self.ipc_server = None
        self.logs_view = None
        self._log_lines = []
        self.max_log_lines = 1000
        self._log_file_path = None
        self._pending_close = False
        self._operation_errors = []
        self._last_operation = None
        self._rename_history = []
        self._rename_redo_history = []
        self._max_rename_history = 20
        self._is_undo_operation = False
        self._is_redo_operation = False
        self._pending_undo_entry = None
        self._pending_redo_entry = None
        self._pending_window_geometry = None
        self._pending_window_pos = None
        self._pending_window_size = None
        self._pending_window_maximized = False
        self._geometry_restore_applied = False
        self._left_panel = None
        self._right_panel = None
        self._header_compact_mode = None
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
        pending_template_session = getattr(self, "_pending_template_session_state", None)
        if pending_template_session:
            try:
                self.restore_template_session_state(pending_template_session)
            except Exception as e:
                _debug_log(f"Ошибка восстановления шаблона сессии: {e}")
        # Тяжёлые backend-библиотеки загружаются только при первой операции.
        self._update_undo_button()
        self._refresh_rename_history_view()

        self.create_ipc_server()
        
        QTimer.singleShot(0, self.process_startup_queue)
        self.queue_timer = QTimer(self)
        self.queue_timer.setInterval(500)
        self.queue_timer.timeout.connect(self.process_startup_queue)
        self.queue_timer.start()


        QTimer.singleShot(1500, self.check_updates_on_startup)

    def create_ipc_server(self):
        """Создает IPC-сервер для приема файлов от других экземпляров."""
        self.ipc_server = QLocalServer(self)
        server_name = _get_ipc_server_name()
        try:
            QLocalServer.removeServer(server_name)
        except Exception as e:
            self.log_event(f"Ошибка IPC при removeServer: {e}", "WARN")

        if not self.ipc_server.listen(server_name):
            self.log_event(f"IPC сервер не запущен: {self.ipc_server.errorString()}", "ERROR")
            self.ipc_server = None
            return

        self.ipc_server.newConnection.connect(self._on_ipc_connection)
        self.log_event(f"IPC сервер запущен: {server_name}")

    def _on_ipc_connection(self):
        if not self.ipc_server:
            return
        while self.ipc_server.hasPendingConnections():
            socket_conn = self.ipc_server.nextPendingConnection()
            if socket_conn:
                self._read_ipc_socket(socket_conn)

    def _read_ipc_socket(self, socket_conn):
        max_bytes = 1024 * 1024
        data = b""
        for _ in range(20):
            if not socket_conn.waitForReadyRead(50):
                break
            chunk = socket_conn.readAll()
            if not chunk:
                break
            data += bytes(chunk)
            if len(data) > max_bytes:
                self.log_event("IPC: превышен лимит данных", "WARN")
                break
        socket_conn.disconnectFromServer()

        if not data:
            return

        try:
            lines = data.decode("utf-8", errors="replace").splitlines()
        except Exception:
            self.log_event("IPC: ошибка декодирования данных", "ERROR")
            return

        if not lines:
            return

        token = _load_ipc_token()
        if not token or not lines[0].startswith("TOKEN:") or lines[0][6:] != token:
            self.log_event("IPC: неверный токен", "WARN")
            return

        file_paths = []
        for line in lines[1:]:
            if line.startswith("ADD_FILE:"):
                file_path = _normalize_path_candidate(line[9:].strip())
                if file_path and os.path.exists(file_path):
                    file_paths.append(file_path)

        if file_paths:
            self.add_files_from_ipc(file_paths)
        else:
            self.log_event("IPC: нет допустимых файлов", "WARN")

    def _add_files_with_source_message(self, file_paths: list[str], source_suffix: str) -> bool:
        """Добавляет файлы и показывает унифицированный статус по источнику."""
        if not file_paths:
            return False
        self.add_files(file_paths)
        self.status_bar.showMessage(f"Добавлено {self._ru_files_label(len(file_paths))} {source_suffix}")
        return True

    def _bring_main_window_to_front(self) -> None:
        """Поднимает окно поверх остальных и снимает состояние свёрнутости."""
        self.show()
        self.activateWindow()
        self.raise_()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)

    def add_files_from_ipc(self, file_paths):
        """Добавляет файлы, пришедшие через IPC."""
        if self._add_files_with_source_message(file_paths, "через контекстное меню"):
            self._bring_main_window_to_front()

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

    def create_file_worker(self):
        """Создает новый экземпляр FileWorker и подключает сигналы."""
        if self.file_worker and self.file_worker.isRunning():
            QMessageBox.warning(self, "Операция выполняется", "Дождитесь завершения текущей операции.")
            return False
        if self.file_worker:
            try:
                self.file_worker.progress.disconnect()
                self.file_worker.status.disconnect()
                self.file_worker.finished.disconnect()
                self.file_worker.error.disconnect()
            except Exception as e:
                _debug_log(f"Ошибка отключения старых сигналов: {e}")
        
        # Импорт worker-а намеренно отложен до первой реальной операции:
        # он подтягивает PyMuPDF, Pillow, pdf2docx, python-docx и odfpy.
        from core.workers.file_worker import FileWorker

        self.file_worker = FileWorker()
        
        self.file_worker.progress.connect(self.progress_bar.setValue)
        self.file_worker.status.connect(self.on_worker_status)
        self.file_worker.finished.connect(self.on_operation_finished)
        self.file_worker.error.connect(self.on_operation_error)
        return True

    def cancel_operation(self):
        """Запрашивает отмену текущей операции."""
        if self.file_worker and self.file_worker.isRunning():
            self.file_worker.request_cancel()
            self.btn_cancel_operation.setEnabled(False)
            if hasattr(self, "progress_status_label") and self.progress_status_label is not None:
                self.progress_status_label.setText("Отмена операции...")
            self.status_bar.showMessage("Отмена операции...")

    def _create_progress_dialog(self):
        dialog = QDialog(self)
        dialog.setObjectName("progress_dialog")
        setup_standard_dialog(dialog, title="Выполнение операции", fixed_width=360)
        dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_LG)

        self.progress_status_label = QLabel("Выполняется операция...")
        self.progress_status_label.setWordWrap(True)
        layout.addWidget(self.progress_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(PROGRESS_HEIGHT)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.btn_cancel_operation = QPushButton("Отмена")
        setup_standard_danger_button(self.btn_cancel_operation)
        self.btn_cancel_operation.clicked.connect(self.cancel_operation)
        layout.addWidget(self.btn_cancel_operation)

        self.progress_dialog = dialog
        self.progress_row = dialog

    def _show_progress_dialog(self, status_text: str = "Выполняется операция..."):
        if hasattr(self, "progress_status_label") and self.progress_status_label is not None:
            self.progress_status_label.setText(status_text)
        if hasattr(self, "progress_bar") and self.progress_bar is not None:
            self.progress_bar.setVisible(True)
        if hasattr(self, "btn_cancel_operation") and self.btn_cancel_operation is not None:
            self.btn_cancel_operation.setVisible(True)
            self.btn_cancel_operation.setEnabled(True)
        if hasattr(self, "progress_dialog") and self.progress_dialog is not None:
            self.progress_dialog.show()
            self.progress_dialog.raise_()
            self.progress_dialog.activateWindow()

    def _hide_progress_dialog(self):
        if hasattr(self, "progress_dialog") and self.progress_dialog is not None:
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

    def _retry_failed_operation(self, errors: list[dict]):
        if not self._last_operation:
            return
        failed_paths = [e.get("path") for e in errors if e.get("path")]
        if not failed_paths:
            return
        op = self._last_operation.get("op")
        if not self.create_file_worker():
            return
        files = self._collect_file_items_by_paths(failed_paths)
        if op == "rename":
            name_map = self._last_operation.get("new_names_by_path", {})
            new_names = []
            valid_files = []
            for f in files:
                new_name = name_map.get(f.path)
                if new_name:
                    valid_files.append(f)
                    new_names.append(new_name)
            if not valid_files:
                return
            self.file_worker.set_rename(valid_files, new_names)
        elif op == "convert":
            self.file_worker.set_conversion(
                files,
                self._last_operation.get("conversion_type", ""),
                self._last_operation.get("conversion_format", ""),
                output_dir=self._last_operation.get("conversion_output_dir", ""),
            )
        elif op == "compress":
            self.file_worker.set_compression(
                files,
                self._last_operation.get("compression_level", 85),
                self._last_operation.get("compression_type", "image"),
                self._last_operation.get("pdf_method", "auto"),
                self._last_operation.get("replace_pdf", False),
                self._last_operation.get("replace_image", False),
            )
        elif op == "metadata":
            self.file_worker.set_metadata_cleanup(
                files,
                remove_all=self._last_operation.get("remove_all", True),
                fields=self._last_operation.get("fields", []),
            )
        else:
            return
        self.file_worker.start()
        self._show_progress_dialog("Повторное выполнение операции...")
    
    def refresh_preview_panel(self):
        if not hasattr(self, "list_files") or self.list_files is None:
            return
        try:
            self.list_files.refresh()
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow.refresh_preview_panel", error)

    def update_ghostscript_status(self):
        """Обновляет информацию о наличии Ghostscript по требованию."""
        from app.core.deps import ensure_ghostscript_detected

        status_messages = []
        has_ghostscript, ghostscript_path = ensure_ghostscript_detected(self.ghostscript_path_override)

        if has_ghostscript:
            status_messages.append(f"✓ Ghostscript доступен: {ghostscript_path}")
        else:
            status_messages.append(f"✗ Ghostscript не найден")
        if status_messages:
            self.log_event("; ".join(status_messages))
        
        if hasattr(self, 'compress_info_label'):
            current_text = self.compress_info_label.text()
            new_lines = []
                
            if has_ghostscript:
                new_lines.append("✓ Ghostscript доступен")
            else:
                new_lines.append("✗ Ghostscript не найден")
                
            new_lines.append("Поддерживаемые форматы: PDF")
            
            self.compress_info_label.setText("\n".join(new_lines))

    @staticmethod
    def _setup_info_label(label: QLabel) -> QLabel:
        label.setFixedHeight(18)
        label.setStyleSheet(
            "font-size: 13px; font-weight: 600; padding: 0px 2px;"
        )
        return label

    @staticmethod
    def _create_info_separator() -> QFrame:
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setObjectName("file_info_separator")
        separator.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.18); border: none;"
        )
        separator.setFixedWidth(1)
        separator.setFixedHeight(16)
        return separator

    def _create_top_menu_and_settings_host(self, main_layout: QVBoxLayout) -> None:
        """Создаёт скрытое верхнее меню и контейнер панели настроек."""
        self.top_menu_bar = QWidget()
        self.top_menu_bar.setObjectName("bottom_links_bar")
        self.top_menu_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.top_menu_bar.setStyleSheet("background-color: transparent;")
        top_menu_layout = QHBoxLayout(self.top_menu_bar)
        top_menu_layout.setContentsMargins(*TOP_MENU_MARGINS)
        top_menu_layout.setSpacing(SPACE_SM)
        top_menu_layout.addStretch(1)
        self.top_menu_bar.setVisible(False)
        main_layout.addWidget(self.top_menu_bar)

        self.settings_panel_host = QFrame()
        self.settings_panel_host.setObjectName("settings_panel_host")
        self.settings_panel_host.setVisible(False)
        self.settings_panel_host.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.settings_panel_host.setStyleSheet("background-color: transparent;")
        self.settings_panel_host_layout = QVBoxLayout(self.settings_panel_host)
        self.settings_panel_host_layout.setContentsMargins(*MARGINS_NONE)
        self.settings_panel_host_layout.setSpacing(SPACE_NONE)

    def _create_main_splitter(self) -> QSplitter:
        """Создаёт изменяемый разделитель рабочих панелей."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter = splitter
        splitter.setHandleWidth(max(12, SPACE_SM * 2))
        splitter.setStyleSheet(
            """
            QSplitter::handle:horizontal {
                background-color: transparent;
                border: none;
                margin: 0px;
            }
            QSplitter::handle:horizontal:hover {
                background-color: transparent;
            }
            """
        )
        return splitter

    def _create_left_panel(self, main_layout: QVBoxLayout) -> QWidget:
        """Создаёт левую панель операций и подключает панель настроек."""
        left_widget = QWidget()
        self._left_panel = left_widget
        self._left_panel_min_width = 220
        left_widget.setMinimumWidth(self._left_panel_min_width)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(*MARGINS_NONE)
        left_layout.setSpacing(SPACE_NONE)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("main_hidden_tabs")
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setStyleSheet(
            """
            QTabWidget#main_hidden_tabs::pane {
                border: none;
                margin: 0px;
                padding: 0px;
                top: 0px;
            }
            """
        )

        operations_tab = self.create_operations_tab()
        if hasattr(self, "operations_header_widget"):
            main_layout.addWidget(self.operations_header_widget)
        elif hasattr(self, "operations_tab_bar"):
            main_layout.addWidget(self.operations_tab_bar)
        self.tabs.addTab(operations_tab, "Операции с файлами")

        if (
            not hasattr(self, "settings_panel_widget")
            or self.settings_panel_widget is None
        ):
            self.settings_panel_widget = self.create_settings_tab()
        if self.settings_panel_widget.parent() is not self.settings_panel_host:
            self.settings_panel_widget.setParent(None)
            self.settings_panel_host_layout.addWidget(self.settings_panel_widget)

        ensure_history_page = getattr(
            self,
            "_ensure_rename_history_settings_page",
            None,
        )
        if callable(ensure_history_page):
            ensure_history_page()

        self.tabs.tabBar().hide()
        main_layout.addWidget(self.settings_panel_host)
        left_layout.addWidget(self.tabs)
        return left_widget

    @staticmethod
    def _set_header_menu_open_state(button, is_open: bool) -> None:
        try:
            button.setProperty("menuOpen", bool(is_open))
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        except RuntimeError as error:
            _log_ignored_error("MultiforaMainWindow._set_header_menu_open_state", error)

    def _bind_header_menu_state(self, button, menu) -> None:
        menu.aboutToShow.connect(
            lambda: self._set_header_menu_open_state(button, True)
        )
        menu.aboutToHide.connect(
            lambda: self._set_header_menu_open_state(button, False)
        )

    def _create_extension_filter(self) -> None:
        self._list_header_ext_label = QLabel("Расширения:")
        self._list_header_ext_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_header_ext_label.setFixedWidth(90)
        self._list_header_ext_label.setVisible(False)

        self.btn_ext_filter = LeftAlignedToolButton()
        self.btn_ext_filter.setObjectName("header_cell_tl")
        setup_standard_header_dropdown(self.btn_ext_filter)
        self._ext_filter_menu = QMenu(self.btn_ext_filter)
        self._ext_filter_menu.setObjectName("header_dropdown_popup")
        apply_standard_menu_style(self._ext_filter_menu)
        self._ext_filter_actions = {}

        options = (
            ("DOC", ".doc"),
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
            ("Без расширения", "__noext__"),
            ("Другое", "__otherext__"),
        )
        for label, value in options:
            action = QAction(label, self._ext_filter_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self.on_extension_filter_changed)
            self._ext_filter_menu.addAction(action)
            self._ext_filter_actions[value] = action

        self.btn_ext_filter.setMenu(self._ext_filter_menu)
        self._ext_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(
                self._ext_filter_menu,
                self.btn_ext_filter,
            )
        )
        self._bind_header_menu_state(self.btn_ext_filter, self._ext_filter_menu)
        self._update_ext_filter_button_text()

    def _create_type_filter(self) -> None:
        self._list_header_type_label = QLabel("Тип:")
        self._list_header_type_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_header_type_label.setFixedWidth(90)
        self._list_header_type_label.setVisible(False)

        self.btn_type_filter = LeftAlignedToolButton()
        self.btn_type_filter.setObjectName("header_cell_tr")
        setup_standard_header_dropdown(self.btn_type_filter)
        self._type_filter_menu = QMenu(self.btn_type_filter)
        self._type_filter_menu.setObjectName("header_dropdown_popup")
        apply_standard_menu_style(self._type_filter_menu)
        self._type_filter_actions = {}

        options = (
            ("Документы", "document"),
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
            self._type_filter_menu.addAction(action)
            self._type_filter_actions[value] = action

        self.btn_type_filter.setMenu(self._type_filter_menu)
        self._type_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(
                self._type_filter_menu,
                self.btn_type_filter,
            )
        )
        self._bind_header_menu_state(self.btn_type_filter, self._type_filter_menu)
        self._update_type_filter_button_text()

    def _create_sort_filter(self) -> None:
        self._list_header_sort_label = QLabel("Сортировка:")
        self._list_header_sort_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_header_sort_label.setFixedWidth(90)
        self._list_header_sort_label.setVisible(False)

        self.combo_sort = LeftAlignedToolButton()
        self.combo_sort.setObjectName("header_cell_bl")
        setup_standard_header_dropdown(self.combo_sort)
        self._sort_filter_menu = QMenu(self.combo_sort)
        self._sort_filter_menu.setObjectName("header_dropdown_popup")
        apply_standard_menu_style(self._sort_filter_menu)
        self._sort_action_group = QActionGroup(self._sort_filter_menu)
        self._sort_action_group.setExclusive(True)
        self._sort_filter_actions = {}
        self._sort_modes = [
            "Без сортировки (ручной порядок)",
            "Имя A→Z",
            "Имя Z→A",
            "Расширение A→Z",
            "Размер ↑",
            "Размер ↓",
        ]
        for index, mode in enumerate(self._sort_modes):
            action = QAction(mode, self._sort_filter_menu)
            action.setCheckable(True)
            action.setChecked(index == 0)
            action.triggered.connect(
                lambda _checked=False, selected_mode=mode: self._on_sort_mode_selected(
                    selected_mode
                )
            )
            self._sort_action_group.addAction(action)
            self._sort_filter_menu.addAction(action)
            self._sort_filter_actions[mode] = action

        self._sort_current_mode = self._sort_modes[0]
        self.combo_sort.setText(self._sort_current_mode)
        self.combo_sort.setMenu(self._sort_filter_menu)
        self._sort_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(
                self._sort_filter_menu,
                self.combo_sort,
            )
        )
        self._bind_header_menu_state(self.combo_sort, self._sort_filter_menu)

    def _create_list_header(self) -> QGridLayout:
        """Создаёт поиск и фильтры списка файлов."""
        list_header = QGridLayout()
        self._list_header_layout = list_header
        list_header.setContentsMargins(*MARGINS_NONE)
        list_header.setHorizontalSpacing(SPACE_SM)
        list_header.setVerticalSpacing(SPACE_NONE)

        self._create_extension_filter()
        self._create_type_filter()
        self._create_sort_filter()

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
        setup_standard_line_input(self.input_search)
        self.input_search.setMinimumWidth(0)
        self.input_search.textChanged.connect(self.on_search_text_changed)

        for widget in (
            self.btn_ext_filter,
            self.btn_type_filter,
            self.combo_sort,
            self.input_search,
        ):
            widget.setMinimumHeight(HEADER_FIELD_HEIGHT)

        list_header.addWidget(self.input_search, 0, 0, 1, 3)
        list_header.addWidget(self.btn_ext_filter, 1, 0)
        list_header.addWidget(self.btn_type_filter, 1, 1)
        list_header.addWidget(self.combo_sort, 1, 2)
        for column in range(3):
            list_header.setColumnStretch(column, 1)
        return list_header

    def _create_file_list_widget(self, files_panel_layout: QVBoxLayout) -> None:
        self.list_files = FileListWidget()
        self.list_files.setObjectName("files_list")
        self.list_files.setFrameShape(QFrame.Shape.NoFrame)
        self.list_files.setWordWrap(True)
        self.list_files.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.list_files.setUniformItemSizes(False)
        self.list_files.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        list_palette = self.list_files.palette()
        list_palette.setColor(QPalette.ColorRole.Highlight, QColor("#3d74b3"))
        list_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.list_files.setPalette(list_palette)
        self.list_files.setStyleSheet(
            "QListWidget#files_list, QListView#files_list {"
            "border: none;"
            "border-radius: 4px;"
            "margin: 0px;"
            "padding: 0px;"
            "}"
        )
        apply_standard_field_style(self.list_files)
        self.list_files.setProperty("preview_mode", True)
        self.list_files.filesDropped.connect(self.add_files)
        self.list_files.itemDoubleClicked.connect(self.open_file)
        self.list_files.itemSelectionChanged.connect(self.on_file_selection_changed)
        self.list_files.orderChanged.connect(self.on_list_order_changed)
        self.list_files.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.list_files.customContextMenuRequested.connect(
            self.show_file_context_menu
        )
        files_panel_layout.addWidget(self.list_files, 1)

    def _create_drop_zone(self, files_panel: QWidget) -> None:
        self.drop_zone_controls = QWidget(files_panel)
        self.drop_zone_controls.setObjectName("drop_zone_overlay")
        self.drop_zone_controls.setAcceptDrops(True)
        self.drop_zone_controls.installEventFilter(self)
        self.drop_zone_controls.setStyleSheet(
            """
            QWidget#drop_zone_overlay {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QWidget#drop_zone_overlay QLabel {
                background-color: transparent;
            }
            """
        )
        drop_zone_layout = QVBoxLayout(self.drop_zone_controls)
        drop_zone_layout.setContentsMargins(*DROP_ZONE_MARGINS)
        drop_zone_layout.setSpacing(SPACE_XL)
        drop_zone_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        drop_zone_layout.addStretch()

        drop_buttons_row = QGridLayout()
        drop_buttons_row.setContentsMargins(*MARGINS_NONE)
        drop_buttons_row.setHorizontalSpacing(SPACE_SM)
        drop_buttons_row.setVerticalSpacing(SPACE_NONE)
        drop_buttons_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.btn_add_files = DropActionTile(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton),
            "Добавить\nфайлы",
        )
        self.btn_add_files.clicked.connect(self.select_files)
        drop_buttons_row.addWidget(self.btn_add_files, 0, 0)

        self.btn_add_folder = DropActionTile(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Добавить\nпапки",
        )
        self.btn_add_folder.clicked.connect(self.select_folder)
        drop_buttons_row.addWidget(self.btn_add_folder, 0, 1)
        drop_buttons_row.setColumnStretch(0, 1)
        drop_buttons_row.setColumnStretch(1, 1)
        drop_zone_layout.addLayout(drop_buttons_row, 0)

        self.drop_zone_hint_label = QLabel("Или перетащите сюда файлы/папки")
        self.drop_zone_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone_hint_label.setStyleSheet(
            "color: rgba(220,220,220,180); font-size: 13px;"
        )
        drop_zone_layout.addWidget(
            self.drop_zone_hint_label,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        drop_zone_layout.addStretch()

    def _connect_drop_zone_updates(self, files_panel: QWidget) -> None:
        model = self.list_files.model()
        model.rowsInserted.connect(lambda *_args: self._update_drop_zone_controls())
        model.rowsRemoved.connect(lambda *_args: self._update_drop_zone_controls())
        model.modelReset.connect(lambda *_args: self._update_drop_zone_controls())
        files_panel.installEventFilter(self)
        self.list_files.installEventFilter(self)
        self.list_files.viewport().installEventFilter(self)
        self._update_drop_zone_controls()
        QTimer.singleShot(0, self._update_drop_zone_controls)

    def _create_files_preview(
        self,
        right_layout: QVBoxLayout,
        list_header: QGridLayout,
    ) -> None:
        files_preview_row = QWidget()
        self.files_preview_splitter = files_preview_row
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
        files_panel.setStyleSheet(
            "QWidget#drop_zone_surface {"
            "background-color: #ffffff;"
            "border: none;"
            "border-radius: 4px;"
            "}"
        )
        files_panel_layout = QVBoxLayout(files_panel)
        files_panel_layout.setContentsMargins(*MARGINS_NONE)
        files_panel_layout.setSpacing(SPACE_NONE)

        self._create_file_list_widget(files_panel_layout)
        self._create_drop_zone(files_panel)
        self._connect_drop_zone_updates(files_panel)

        files_preview_layout.addWidget(files_panel, 1)
        self._configure_right_panel_spacing(right_layout, list_header)
        right_layout.addWidget(files_preview_row, 1)

    def _create_file_info_layout(self) -> QHBoxLayout:
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(
            SPACE_NONE,
            SPACE_XXS,
            SPACE_NONE,
            SPACE_NONE,
        )
        info_layout.setSpacing(SPACE_SM)

        self.label_count = self._setup_info_label(QLabel("Файлов: 0"))
        info_layout.addWidget(self.label_count)

        count_size_separator = self._create_info_separator()
        info_layout.addWidget(count_size_separator)

        self.label_item_size = self._setup_info_label(QLabel("Размер: 0 MB"))
        info_layout.addWidget(self.label_item_size)

        size_total_separator = self._create_info_separator()
        info_layout.addWidget(size_total_separator)
        self._file_info_separators = [
            count_size_separator,
            size_total_separator,
        ]

        self.label_total_size = self._setup_info_label(
            QLabel("Общий объем: 0 MB")
        )
        info_layout.addWidget(self.label_total_size)
        info_layout.addStretch()
        return info_layout

    def _create_right_panel(self) -> QWidget:
        """Создаёт панель поиска, списка файлов и сводной информации."""
        right_widget = QWidget()
        self._right_panel = right_widget
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(*MARGINS_NONE)
        right_layout.setSpacing(SPACE_NONE)

        list_header = self._create_list_header()
        right_layout.addLayout(list_header)
        self._create_files_preview(right_layout, list_header)
        self._create_progress_dialog()
        self.on_sort_changed()
        right_layout.addLayout(self._create_file_info_layout())
        return right_widget

    def _configure_main_splitter(
        self,
        splitter: QSplitter,
        left_widget: QWidget,
        right_widget: QWidget,
    ) -> None:
        """Подключает панели к разделителю и создаёт визуальную ручку."""
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setChildrenCollapsible(False)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([1, 4])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        handle = splitter.handle(1)
        if handle is None:
            return
        handle.setEnabled(True)
        handle.setCursor(Qt.CursorShape.SizeHorCursor)
        grip_layout = QVBoxLayout(handle)
        grip_layout.setContentsMargins(*MARGINS_NONE)
        grip_layout.setSpacing(SPACE_NONE)
        grip_layout.addStretch(1)

        self._splitter_grip_label = QLabel("⋮")
        self._splitter_grip_label.setObjectName("splitter_grip_label")
        self._splitter_grip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._splitter_grip_label.setFixedSize(8, 56)
        self._splitter_grip_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        grip_layout.addWidget(
            self._splitter_grip_label,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        grip_layout.addStretch(1)

    def _create_hidden_status_bar(self) -> None:
        self.status_bar = LoggingStatusBar()
        self.status_bar.messageLogged.connect(self.on_status_message_logged)
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setFixedHeight(0)
        self.status_bar.setContentsMargins(*MARGINS_NONE)
        self.status_bar.setVisible(False)
        self.status_bar.showMessage(
            "Готово. Перетащите файлы/папки в список или используйте кнопки добавления."
        )

    def init_ui(self) -> None:
        """Создаёт основную структуру интерфейса приложения."""
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.resize(1200, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(*APP_MARGINS)
        main_layout.setSpacing(SPACE_NONE)

        self._create_top_menu_and_settings_host(main_layout)
        splitter = self._create_main_splitter()
        left_widget = self._create_left_panel(main_layout)
        right_widget = self._create_right_panel()
        self._configure_main_splitter(splitter, left_widget, right_widget)
        main_layout.addWidget(splitter, 1)
        self._create_hidden_status_bar()

        self.setMinimumSize(900, 550)
        self._default_min_size = self.minimumSize()
        self.tabs.setMinimumWidth(0)

        self.apply_theme_mode(self.theme_mode)
        self.setup_system_theme_tracking()
        self._update_header_compact_mode()
        self._connect_ui_state_autosave()


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
            QTimer.singleShot(150, lambda: setattr(self, "initial_load_complete", True))

    def _restore_window_geometry_from_pending(self):
        if self._geometry_restore_applied:
            return
        self._geometry_restore_applied = True
        self._restoring_window_geometry = True
        try:
            pending_pos = getattr(self, "_pending_window_pos", None)
            pending_size = getattr(self, "_pending_window_size", None)
            pending_geom = getattr(self, "_pending_window_geometry", None)

            settings_path_getter = getattr(self, "get_settings_file_path", None)
            if callable(settings_path_getter):
                try:
                    settings_path = settings_path_getter()
                    if settings_path and os.path.exists(settings_path):
                        with open(settings_path, "r", encoding="utf-8") as f:
                            settings_data = json.load(f)
                        pending_pos = settings_data.get("window_pos", pending_pos)
                        pending_size = settings_data.get("window_size", pending_size)
                        pending_geom = settings_data.get("window_geometry", pending_geom)
                        if settings_data.get("window_maximized"):
                            self._pending_window_maximized = True
                except Exception as e:
                    _debug_log(f"Error reading window geometry from settings file: {e}")

            applied = False
            if isinstance(pending_pos, (list, tuple)) and len(pending_pos) == 2:
                try:
                    if isinstance(pending_size, (list, tuple)) and len(pending_size) == 2:
                        self.setGeometry(
                            int(pending_pos[0]),
                            int(pending_pos[1]),
                            int(pending_size[0]),
                            int(pending_size[1]),
                        )
                    else:
                        self.move(int(pending_pos[0]), int(pending_pos[1]))
                    applied = True
                except Exception as e:
                    _debug_log(f"Error restoring window position/size: {e}")

            if not applied and isinstance(pending_geom, str) and pending_geom:
                try:
                    applied = bool(self.restoreGeometry(bytes.fromhex(pending_geom)))
                except Exception as e:
                    _debug_log(f"Error restoring window geometry: {e}")

            if not applied and not getattr(self, "_pending_window_maximized", False):
                try:
                    self.setGeometry(100, 100, 1200, 700)
                except Exception as error:
                    _log_ignored_error("MultiforaMainWindow._restore_window_geometry_from_pending", error)

            if getattr(self, "_pending_window_maximized", False):
                try:
                    self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
                except Exception as e:
                    _debug_log(f"Error restoring maximized state: {e}")
        finally:
            self._restoring_window_geometry = False
            self.initial_load_complete = True
    def _connect_ui_state_autosave(self):
        if hasattr(self, "tabs"):
            self._safe_connect_signal(
                self.tabs.currentChanged,
                lambda _: self._schedule_settings_save(),
            )
        if hasattr(self, "main_splitter"):
            self._safe_connect_signal(
                self.main_splitter.splitterMoved,
                lambda _pos, _index: self._schedule_settings_save(),
            )
            self._safe_connect_signal(
                self.main_splitter.splitterMoved,
                lambda _pos, _index: self._update_drop_zone_controls(),
            )
        try:
            for group in self.findChildren(ExpandableGroupBox):
                self._safe_connect_signal(
                    group.toggledExpanded,
                    lambda _expanded: self._schedule_settings_save(),
                )
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow._connect_ui_state_autosave", error)

    def _configure_right_panel_spacing(self, right_layout, list_header):
        """Выравнивает единый шаг промежутков для правой панели."""
        right_layout.setContentsMargins(*MARGINS_NONE)
        right_layout.setSpacing(SPACE_NONE)

        list_header.setContentsMargins(SPACE_NONE, SPACE_XS, SPACE_NONE, SPACE_SM)
        list_header.setHorizontalSpacing(SPACE_SM)
        list_header.setVerticalSpacing(SPACE_SM)

    @staticmethod
    def _safe_connect_signal(signal, callback) -> None:
        try:
            signal.connect(callback)
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow._safe_connect_signal", error)

    @staticmethod
    def _safe_polish_widget(widget) -> None:
        if widget is None:
            return
        try:
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow._safe_polish_widget", error)

    def _apply_theme_runtime_widgets(self):
        mode = getattr(self, "_effective_theme_mode", "dark")
        try:
            if callable(getattr(self, "_apply_operations_tab_bar_theme", None)):
                self._apply_operations_tab_bar_theme(mode)
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
        if hasattr(self, "main_splitter") and self.main_splitter is not None:
            try:
                self.main_splitter.setStyleSheet(
                    f"""
                    QSplitter::handle:horizontal {{
                        background-color: transparent;
                        border: none;
                        margin: 0px;
                    }}
                    QSplitter::handle:horizontal:hover {{
                        background-color: transparent;
                    }}
                    """
                )
            except Exception as error:
                _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
        for separator in getattr(self, "_file_info_separators", []):
            try:
                if mode == "light":
                    separator.setStyleSheet("background-color: rgba(31, 35, 40, 0.24); border: none;")
                else:
                    separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.18); border: none;")
            except Exception as error:
                _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
        # Кнопки фильтров хранят локальный маркер темы, потому что их всплывающие
        # меню являются отдельными виджетами. Маркер обновляется до перестроения QSS,
        # иначе после смены тёмной темы на светлую кнопки могут остаться тёмными.
        for widget_name in ("btn_ext_filter", "btn_type_filter", "combo_sort"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                try:
                    widget._effective_theme_mode = mode
                except Exception as error:
                    _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
                try:
                    menu = widget.menu()
                    if menu is not None:
                        menu._effective_theme_mode = mode
                        apply_standard_menu_style(menu)
                        self._safe_polish_widget(menu)
                except Exception as error:
                    _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
        try:
            refresh_standard_button_styles(self)
            refresh_standard_field_styles(self)
            refresh_standard_surface_styles(self)
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
        try:
            for group in self.findChildren(ExpandableGroupBox):
                if callable(getattr(group, "refresh_theme_icon", None)):
                    group.refresh_theme_icon()
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow._apply_theme_runtime_widgets", error)
        if hasattr(self, "_splitter_grip_label") and self._splitter_grip_label is not None:
            if mode == "light":
                self._splitter_grip_label.setStyleSheet(
                    "color: rgba(95, 108, 122, 0.92); background-color: rgba(222, 229, 238, 0.95); border: 1px solid rgba(189, 199, 210, 0.95); border-radius: 4px; font-size: 14px; font-weight: 600; padding: 0px;"
                )
            else:
                self._splitter_grip_label.setStyleSheet(
                    "color: rgba(255, 255, 255, 0.78); background-color: rgba(63, 63, 63, 0.96); border: 1px solid rgba(92, 92, 92, 0.96); border-radius: 4px; font-size: 14px; font-weight: 600; padding: 0px;"
                )
        if hasattr(self, "files_panel") and self.files_panel is not None:
            if mode == "light":
                self.files_panel.setStyleSheet(
                    """
                    QWidget#drop_zone_surface {
                        background-color: #ffffff;
                        border: none;
                        border-radius: 4px;
                    }
                    """
                )
            else:
                self.files_panel.setStyleSheet(
                    """
                    QWidget#drop_zone_surface {
                        background-color: #383838;
                        border: none;
                        border-radius: 4px;
                    }
                    """
                )
        if hasattr(self, "drop_zone_controls") and self.drop_zone_controls is not None:
            if mode == "light":
                self.drop_zone_controls.setStyleSheet(
                    """
                    QWidget#drop_zone_overlay {
                        background-color: transparent;
                        border: none;
                        border-radius: 4px;
                    }
                    QWidget#drop_zone_overlay QLabel {
                        background-color: transparent;
                        color: #5b6470;
                    }
                    """
                )
                if hasattr(self, "drop_zone_hint_label"):
                    self.drop_zone_hint_label.setStyleSheet("color: #5b6470; font-size: 13px;")
            else:
                self.drop_zone_controls.setStyleSheet(
                    """
                    QWidget#drop_zone_overlay {
                        background-color: transparent;
                        border: none;
                        border-radius: 4px;
                    }
                    QWidget#drop_zone_overlay QLabel {
                        background-color: transparent;
                        color: rgba(220,220,220,180);
                    }
                    """
                )
                if hasattr(self, "drop_zone_hint_label"):
                    self.drop_zone_hint_label.setStyleSheet("color: rgba(220,220,220,180); font-size: 13px;")
        for tile_name in ("btn_add_files", "btn_add_folder"):
            tile = getattr(self, tile_name, None)
            if tile is not None and callable(getattr(tile, "set_theme_mode", None)):
                tile.set_theme_mode(mode)

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
        if not hasattr(self, "_type_filter_actions") or not self._type_filter_actions:
            return
        total = len(self._type_filter_actions)
        checked = sum(1 for a in self._type_filter_actions.values() if a.isChecked())
        if checked == total:
            self.btn_type_filter.setText("Все типы")
        else:
            self.btn_type_filter.setText(f"Выбрано: {checked}")

    def _update_ext_filter_button_text(self):
        if not hasattr(self, "_ext_filter_actions") or not self._ext_filter_actions:
            return
        total = len(self._ext_filter_actions)
        checked = sum(1 for a in self._ext_filter_actions.values() if a.isChecked())
        if checked == total:
            self.btn_ext_filter.setText("Все расширения")
        else:
            self.btn_ext_filter.setText(f"Выбрано: {checked}")

    def _on_sort_mode_selected(self, mode: str):
        self.set_sort_mode(mode, notify=True)

    def get_sort_mode(self) -> str:
        if hasattr(self, "_sort_current_mode") and self._sort_current_mode:
            return self._sort_current_mode
        return "Без сортировки (ручной порядок)"

    def get_sort_mode_index(self) -> int:
        mode = self.get_sort_mode()
        if hasattr(self, "_sort_modes") and mode in self._sort_modes:
            return self._sort_modes.index(mode)
        return 0

    def set_sort_mode(self, mode: str, notify: bool = False):
        if not hasattr(self, "_sort_filter_actions") or mode not in self._sort_filter_actions:
            return
        self._sort_current_mode = mode
        action = self._sort_filter_actions[mode]
        if not action.isChecked():
            action.setChecked(True)
        if hasattr(self, "combo_sort") and self.combo_sort is not None:
            self.combo_sort.setText(mode)
        if notify:
            self.on_sort_changed()

    def _update_header_compact_mode(self):
        compact = self.width() < 1080
        if self._header_compact_mode == compact:
            return
        self._header_compact_mode = compact

        if hasattr(self, "_list_header_sort_label"):
            self._list_header_sort_label.setVisible(False)
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
            except Exception as error:
                _log_ignored_error("MultiforaMainWindow._update_header_compact_mode", error)

    def _update_drop_zone_controls(self):
        if not hasattr(self, "drop_zone_controls"):
            return
        host = getattr(self, "files_panel", None)
        if host is None:
            return
        self.drop_zone_controls.setGeometry(host.rect())
        has_files = False
        try:
            model = self.list_files.model() if hasattr(self, "list_files") else None
            has_files = bool(model and callable(getattr(model, "files", None)) and model.files())
        except Exception:
            has_files = False
        self.drop_zone_controls.setVisible(not has_files)
        if not has_files:
            self.drop_zone_controls.raise_()

    def eventFilter(self, obj, event):
        if hasattr(self, "files_panel") and obj is self.files_panel:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Move, QEvent.Type.LayoutRequest):
                self._update_drop_zone_controls()
        if hasattr(self, "list_files"):
            viewport = self.list_files.viewport()
            if obj is self.list_files or obj is viewport:
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Move, QEvent.Type.LayoutRequest):
                    self._update_drop_zone_controls()
        if hasattr(self, "drop_zone_controls") and obj is self.drop_zone_controls:
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasUrls():
                    paths = []
                    for url in event.mimeData().urls():
                        file_path = url.toLocalFile()
                        if os.path.exists(file_path):
                            paths.append(file_path)
                    if paths:
                        self.add_files(paths)
                        event.acceptProposedAction()
                        return True
            elif event.type() == QEvent.Type.DragLeave:
                event.accept()
                return True
        if hasattr(self, "input_merge_output_path") and obj is self.input_merge_output_path:
            if event.type() == QEvent.Type.MouseButtonPress:
                try:
                    self.select_merge_output_path()
                except Exception as error:
                    _log_ignored_error("MultiforaMainWindow.eventFilter", error)
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
        try:
            if callable(getattr(self, "_update_operations_narrow_layout", None)):
                self._update_operations_narrow_layout()
        except Exception as error:
            _log_ignored_error("MultiforaMainWindow.resizeEvent", error)
        self._update_drop_zone_controls()
        if not getattr(self, "_restoring_window_geometry", False) and getattr(self, "initial_load_complete", False):
            self._schedule_settings_save()

    def moveEvent(self, event):
        super().moveEvent(event)
        if not getattr(self, "_restoring_window_geometry", False) and getattr(self, "initial_load_complete", False):
            self._schedule_settings_save()
        
    def update_converter_from_format(self):
        """Обновляет конвертер и автоматически включает смешанный режим."""
        selected_items = self.list_files.selectedItems()
        category_combo = getattr(self, "convert_file_type_combo", None)

        category_label = ""
        if category_combo is not None:
            try:
                category_label = str(category_combo.currentText() or "").strip()
            except Exception:
                category_label = ""

        categories = set()
        selected_files = []
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if not file_item or not file_item.is_file:
                continue
            selected_files.append(file_item)
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
                    category_combo.blockSignals(True)
                    category_combo.setCurrentIndex(index)
                    category_combo.blockSignals(False)

        if not category_label:
            self.from_convert_combo.blockSignals(True)
            self.from_convert_combo.clear()
            self.from_convert_combo.addItem("Выберите исходный формат:")
            self.from_convert_combo.blockSignals(False)
            self.to_convert_combo.blockSignals(True)
            self.to_convert_combo.clear()
            self.to_convert_combo.addItem("Выберите целевой формат:")
            self.to_convert_combo.setEnabled(False)
            self.to_convert_combo.blockSignals(False)
            self.btn_convert.setEnabled(False)
            return

        available_formats = source_formats_for_category(category_label)
        mixed_label = mixed_source_label_for_category(category_label)
        category_source_formats = {
            format_for_path(file_item.path)
            for file_item in selected_files
            if category_for_file_type(file_item.file_type) == category_label and format_for_path(file_item.path)
        }

        previous_source = str(self.from_convert_combo.currentText() or "").strip()
        self.from_convert_combo.blockSignals(True)
        self.from_convert_combo.clear()
        self.from_convert_combo.addItem("Выберите исходный формат:")
        if mixed_label:
            self.from_convert_combo.addItem(mixed_label)
        for fmt in available_formats:
            self.from_convert_combo.addItem(fmt)
        self.from_convert_combo.blockSignals(False)

        selected_source = ""
        if len(category_source_formats) > 1:
            selected_source = mixed_label
        elif len(category_source_formats) == 1:
            selected_source = next(iter(category_source_formats))
        elif previous_source == mixed_label or previous_source in available_formats:
            selected_source = previous_source

        if selected_source:
            index = self.from_convert_combo.findText(selected_source)
            if index >= 0:
                self.from_convert_combo.blockSignals(True)
                self.from_convert_combo.setCurrentIndex(index)
                self.from_convert_combo.blockSignals(False)
        else:
            self.from_convert_combo.blockSignals(True)
            self.from_convert_combo.setCurrentIndex(0)
            self.from_convert_combo.blockSignals(False)

        self.update_to_combo_based_on_from()
        if callable(getattr(self, "update_convert_button_state", None)):
            self.update_convert_button_state()

    def on_file_selection_changed(self):
        """Обработчик изменения выбора файлов"""
        self.update_converter_from_format()
        if callable(getattr(self, "refresh_active_file_preview", None)):
            self.refresh_active_file_preview()
        if callable(getattr(self, "refresh_preview_panel", None)):
            self.refresh_preview_panel()
        if callable(getattr(self, "_auto_select_compress_type", None)):
            self._auto_select_compress_type()
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()

    def on_preview_selection_changed(self):
        """Синхронизирует выделение из окна предпросмотра обратно в список файлов."""
        if getattr(self, "_syncing_file_selection", False):
            return
        self._sync_source_selection_from_preview()
        self.on_file_selection_changed()

    def _selected_paths_from_view(self, view) -> list[str]:
        paths = []
        if view is None:
            return paths
        try:
            for item in view.selectedItems():
                file_item = item.data(Qt.ItemDataRole.UserRole)
                file_path = getattr(file_item, "path", None) if file_item else None
                if file_path:
                    paths.append(file_path)
        except Exception:
            return []
        return paths


    def _sync_source_selection_from_preview(self):
        if not hasattr(self, "list_files") or self.list_files is None:
            return
        if getattr(self, "_syncing_file_selection", False):
            return
        self._syncing_file_selection = True
        try:
            paths = self._selected_paths_from_view(self.preview_list)
            self.list_files.clearSelection()
            if paths:
                self.list_files.select_paths(paths)
        finally:
            self._syncing_file_selection = False
    
    def select_files(self):
        """Выбор файлов для обработки"""
        options = QFileDialog.Option.ReadOnly
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Выберите файлы", 
            "", 
            build_file_dialog_filter(),
            options=options
        )
        
        if files:
            self.add_files(files)

    def select_folder(self):
        """Выбор папки для добавления в список"""
        options = QFileDialog.Option.ShowDirsOnly
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку",
            "",
            options=options
        )
        
        if folder:
            self.add_files([folder])





