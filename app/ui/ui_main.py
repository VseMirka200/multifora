# -*- coding: utf-8 -*-
import os
import sys
import shutil
import subprocess
import json
import tempfile
import time
import re
import winreg
import ctypes
from ctypes import wintypes
import secrets
import hashlib
from datetime import datetime
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QEvent, QSortFilterProxyModel, QTimer, Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QIcon, QPalette, QPixmap
from functools import partial
from PyQt6.QtNetwork import QLocalServer

from app.core.app_utils import _debug_log
from app.core.app_ipc import (
    _drain_queued_files,
    _collect_paths_from_args,
    _load_ipc_token,
    _delete_ipc_token,
    _get_ipc_server_name,
    _normalize_path_candidate,
)
from app.core.app_icons import _get_shortcut_icon_path, _get_app_icon_qt_path
from app.core.message_boxes import install_warning_suppression_hook
from app.core.deps import (
    HAS_WORD_TO_PDF,
    HAS_PDF_TO_WORD,
    HAS_PDF_TO_IMAGE,
    HAS_PANDAS,
    HAS_PYMUPDF,
    HAS_ODF_PYTHON,
    HAS_PIL,
    ensure_ghostscript_detected,
)
from app.core.models import FileItem
from core.workers import FileWorker
from core.workers.conversion.conversion_mixin import prewarm_word_background
import app.core.settings as app_settings
import app.core.rename_templates as rt

from app.ui.ui_components import (
    apply_standard_menu_style,
    ClickableLabel,
    ExpandableGroupBox,
    FileListWidget,
    FileListItemDelegate,
    LeftAlignedToolButton,
    LoggingStatusBar,
    setup_standard_dialog,
    setup_standard_danger_button,
    setup_standard_header_dropdown,
    setup_standard_line_input,
    sync_standard_menu_width,
)
from app.ui.mixins import (
    LifecycleMixin,
    LoggingMixin,
    RenameHistoryMixin,
    WindowsIntegrationMixin,
    WorkerOpsMixin,
    TemplateUiMixin,
    FileListUiMixin,
    AppearanceMixin,
    SettingsPanelMixin,
    OperationsTabMixin,
)


class DropActionTile(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon: QIcon, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("drop_action_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(144, 132)
        self._theme = "dark"
        self._apply_theme_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        layout.addStretch()

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        icon_label.setPixmap(icon.pixmap(QSize(48, 48)))
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon_label)

        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.text_label.setStyleSheet('font-family: "Segoe UI"; font-size: 12px; font-weight: 600;')
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.text_label)

        layout.addStretch()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_theme_mode(self, mode: str):
        self._theme = "light" if str(mode).lower() == "light" else "dark"
        self._apply_theme_style()

    def _apply_theme_style(self):
        if self._theme == "light":
            self.setStyleSheet(
                "QFrame#drop_action_tile {"
                "background-color: transparent;"
                "border: 2px dashed rgba(90, 100, 110, 170);"
                "border-radius: 12px;"
                "}"
                "QFrame#drop_action_tile:hover {"
                "border-color: rgba(61,116,179,220);"
                "background-color: rgba(61,116,179,18);"
                "}"
            )
            if hasattr(self, "text_label"):
                self.text_label.setStyleSheet(
                    'font-family: "Segoe UI"; font-size: 12px; font-weight: 600; color: #1f2328;'
                )
        else:
            self.setStyleSheet(
                "QFrame#drop_action_tile {"
                "background-color: transparent;"
                "border: 2px dashed rgba(255,255,255,120);"
                "border-radius: 12px;"
                "}"
                "QFrame#drop_action_tile:hover {"
                "border-color: rgba(255,255,255,210);"
                "background-color: rgba(255,255,255,24);"
                "}"
            )
            if hasattr(self, "text_label"):
                self.text_label.setStyleSheet(
                    'font-family: "Segoe UI"; font-size: 12px; font-weight: 600; color: #f0f0f0;'
                )


class PreviewSelectionProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible_rows = set()

    def set_visible_rows(self, rows):
        self._visible_rows = {int(row) for row in rows if row is not None and int(row) >= 0}
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._visible_rows:
            return True
        return source_row in self._visible_rows


class MultiforaMainWindow(
    LifecycleMixin,
    LoggingMixin,
    RenameHistoryMixin,
    WorkerOpsMixin,
    WindowsIntegrationMixin,
    TemplateUiMixin,
    FileListUiMixin,
    AppearanceMixin,
    SettingsPanelMixin,
    OperationsTabMixin,
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
        self._left_panel = None
        self._right_panel = None
        self._header_compact_mode = None
        self.init_logging()
        install_warning_suppression_hook()
        
        # Флаг для отслеживания начальной загрузки
        self.initial_load_complete = False
        
        self.init_ui()
        self.attach_action_logging()
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(250)
        self._settings_save_timer.timeout.connect(self._save_settings_if_ready)
        self.load_settings()  # Загружаем настройки ПЕРВЫМ ДЕЛОМ
        self.update_template_combo()
        pending_template_session = getattr(self, "_pending_template_session_state", None)
        if pending_template_session:
            try:
                self.restore_template_session_state(pending_template_session)
            except Exception as e:
                _debug_log(f"Ошибка восстановления шаблона сессии: {e}")
        self.update_ghostscript_status()
        self._update_undo_button()
        self._refresh_rename_history_view()

        # Create IPC server to receive files from other instances
        self.create_ipc_server()
        
        # Создаем FileWorker только при необходимости
        self.create_file_worker()
        QTimer.singleShot(900, self._start_word_background_warmup)

        # Обрабатываем очередь файлов из контекстного меню
        QTimer.singleShot(0, self.process_startup_queue)
        self.queue_timer = QTimer(self)
        self.queue_timer.setInterval(500)
        self.queue_timer.timeout.connect(self.process_startup_queue)
        self.queue_timer.start()

        # Устанавливаем флаг, что начальная загрузка завершена
        self.initial_load_complete = True
        QTimer.singleShot(1500, self.check_updates_on_startup)

    def _start_word_background_warmup(self):
        if os.name != "nt" or not HAS_WORD_TO_PDF:
            return
        try:
            started = prewarm_word_background(
                status_callback=None,
                log_callback=lambda msg: self.log_event(msg, "DEBUG"),
            )
            if started:
                self.log_event("Фоновая подготовка Microsoft Word запущена.")
        except Exception as e:
            _debug_log(f"Ошибка фоновой подготовки Microsoft Word: {e}")
    
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
    
    
    def add_files_from_command_line(self):
        """Добавляет файлы из командной строки (в т.ч. из контекстного меню)."""
        file_paths = _collect_paths_from_args(sys.argv[1:])

        if self._add_files_with_source_message(file_paths, "из командной строки"):
            self.tabs.setCurrentIndex(0)

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
        """Создает новый экземпляр FileWorker и подключает сигналы"""
        if self.file_worker and self.file_worker.isRunning():
            QMessageBox.warning(self, "Операция выполняется", "Дождитесь завершения текущей операции.")
            return False
        if self.file_worker:
            try:
                # Отключаем старые сигналы
                self.file_worker.progress.disconnect()
                self.file_worker.status.disconnect()
                self.file_worker.finished.disconnect()
                self.file_worker.error.disconnect()
            except Exception as e:
                _debug_log(f"Ошибка отключения старых сигналов: {e}")
        
        self.file_worker = FileWorker()
        
        # Подключаем сигналы
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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.progress_status_label = QLabel("Выполняется операция...")
        self.progress_status_label.setWordWrap(True)
        layout.addWidget(self.progress_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(22)
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
        else:
            return
        self.file_worker.start()
        self._show_progress_dialog("Повторное выполнение операции...")
    
    def is_admin(self):
        """Проверяет, запущена ли программа с правами администратора"""
        try:
            if os.name != 'nt':
                return os.getuid() == 0
            else:
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            _debug_log(f"Ошибка проверки прав администратора: {e}")
            return False

    def style_link(self, label: QLabel):
        """Стилизует QLabel как ссылку"""
        label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #1976d2;
                text-decoration: underline;
            }
            QLabel:hover {
                color: #0d47a1;
            }
        """)

    def create_info_row(self, label_text, value_widget):
        """Создает строку информации с меткой и значением"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(label)

        layout.addWidget(value_widget)
        layout.addStretch()
        return container

    def _create_preview_panel(self):
        panel = QFrame()
        panel.setObjectName("drop_zone_overlay")
        self.preview_panel = panel
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self.preview_list = FileListWidget()
        self.preview_list.setObjectName("files_list")
        self.preview_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.preview_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.preview_list.setAcceptDrops(False)
        self.preview_list.setDragEnabled(False)
        self.preview_list.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.preview_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.preview_list.setFrameShape(QFrame.Shape.NoFrame)
        self.preview_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            self.preview_list.doubleClicked.disconnect()
        except Exception:
            pass
        self.preview_proxy_model = PreviewSelectionProxyModel(self.preview_list)
        self.preview_list.setModel(self.preview_proxy_model)
        self.preview_list.setItemDelegate(FileListItemDelegate(self.preview_list, right_padding=0))
        panel_layout.addWidget(self.preview_list, 1)

        return panel

    def refresh_preview_panel(self):
        if not hasattr(self, "preview_list") or self.preview_list is None:
            return

        if not hasattr(self, "preview_proxy_model") or self.preview_proxy_model is None:
            return

        source_model = None
        try:
            source_model = self.list_files.model()
        except Exception:
            source_model = None

        if source_model is not None and self.preview_proxy_model.sourceModel() is not source_model:
            self.preview_proxy_model.setSourceModel(source_model)

        visible_rows = []
        try:
            selected_rows = {
                index.row()
                for index in self.list_files.selectedIndexes()
                if index.isValid() and index.column() == 0
            }
            visible_rows = sorted(selected_rows)
        except Exception:
            visible_rows = []

        if not visible_rows:
            try:
                if source_model is not None and source_model.rowCount() > 0:
                    visible_rows = [0]
            except Exception:
                visible_rows = []

        self.preview_proxy_model.set_visible_rows(visible_rows)
        self.preview_list.viewport().update()

    def update_ghostscript_status(self):
        """Обновляет информацию о наличии Ghostscript"""
        status_messages = []
        has_ghostscript, ghostscript_path = ensure_ghostscript_detected(self.ghostscript_path_override)

        if has_ghostscript:
            status_messages.append(f"✓ Ghostscript доступен: {ghostscript_path}")
        else:
            status_messages.append(f"✗ Ghostscript не найден")
        if status_messages:
            self.log_event("; ".join(status_messages))
        
        # Обновляем интерфейс
        if hasattr(self, 'compress_info_label'):
            current_text = self.compress_info_label.text()
            new_lines = []
                
            if has_ghostscript:
                new_lines.append("✓ Ghostscript доступен")
            else:
                new_lines.append("✗ Ghostscript не найден")
                
            new_lines.append("Поддерживаемые форматы: PDF")
            
            self.compress_info_label.setText("\n".join(new_lines))

    def init_ui(self):
        self.setWindowTitle("Мультифора 1.0.0")
        self.setGeometry(100, 100, 1200, 700)
        
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_menu_bar = QWidget()
        self.top_menu_bar.setObjectName("bottom_links_bar")
        self.top_menu_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.top_menu_bar.setStyleSheet("background-color: transparent;")
        top_menu_layout = QHBoxLayout(self.top_menu_bar)
        top_menu_layout.setContentsMargins(4, 2, 4, 2)
        top_menu_layout.setSpacing(4)
        top_menu_layout.addStretch(1)

        main_layout.addWidget(self.top_menu_bar)

        self.settings_panel_host = QFrame()
        self.settings_panel_host.setObjectName("settings_panel_host")
        self.settings_panel_host.setVisible(False)
        self.settings_panel_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.settings_panel_host.setStyleSheet("background-color: transparent;")
        self.settings_panel_host_layout = QVBoxLayout(self.settings_panel_host)
        self.settings_panel_host_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_panel_host_layout.setSpacing(0)

        # Основной сплиттер (занимает всю высоту)
        if hasattr(self, "top_menu_bar") and self.top_menu_bar is not None:
            try:
                self.top_menu_bar.setVisible(False)
            except Exception:
                pass

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter = splitter
        splitter.setHandleWidth(0)
        splitter.setStyleSheet(
            """
            QSplitter::handle:horizontal {
                background-color: #4a4a4a;
                margin: 0px;
            }
            QSplitter::handle:horizontal:hover {
                background-color: #4a4a4a;
            }
            """
        )

        # Левая панель - управление (занимает всю высоту)
        left_widget = QWidget()
        self._left_panel = left_widget
        self._left_panel_min_width = 0
        left_widget.setMinimumWidth(0)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

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
        
        # Вкладка: операции с файлами
        operations_tab = self.create_operations_tab()
        if hasattr(self, "operations_tab_bar"):
            main_layout.addWidget(self.operations_tab_bar)
        self.tabs.addTab(operations_tab, "Операции с файлами")
        if not hasattr(self, "settings_panel_widget") or self.settings_panel_widget is None:
            self.settings_panel_widget = self.create_settings_tab()
        if self.settings_panel_widget.parent() is not self.settings_panel_host:
            self.settings_panel_widget.setParent(None)
            self.settings_panel_host_layout.addWidget(self.settings_panel_widget)
        if callable(getattr(self, "_ensure_rename_history_settings_page", None)):
            self._ensure_rename_history_settings_page()
        self.tabs.tabBar().hide()
        main_layout.addWidget(self.settings_panel_host)
        
        left_layout.addWidget(self.tabs)

        # Правая панель - список файлов
        right_widget = QWidget()
        self._right_panel = right_widget
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Заголовок и кнопки управления списком
        list_header = QGridLayout()
        self._list_header_layout = list_header
        list_header.setContentsMargins(0, 0, 0, 2)
        list_header.setHorizontalSpacing(2)
        list_header.setVerticalSpacing(2)

        self._list_header_ext_label = QLabel("Расширения:")
        self._list_header_ext_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._list_header_ext_label.setFixedWidth(90)
        self._list_header_ext_label.setVisible(False)
        self.btn_ext_filter = LeftAlignedToolButton()
        self.btn_ext_filter.setObjectName("header_cell_tl")
        setup_standard_header_dropdown(self.btn_ext_filter)
        self._ext_filter_menu = QMenu(self.btn_ext_filter)
        self._ext_filter_menu.setObjectName("header_dropdown_popup")
        apply_standard_menu_style(self._ext_filter_menu)
        self._ext_filter_actions = {}
        for label, value in [
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
        ]:
            action = QAction(label, self._ext_filter_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self.on_extension_filter_changed)
            self._ext_filter_menu.addAction(action)
            self._ext_filter_actions[value] = action
        self.btn_ext_filter.setMenu(self._ext_filter_menu)
        self._ext_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(self._ext_filter_menu, self.btn_ext_filter)
        )
        self._update_ext_filter_button_text()
        list_header.addWidget(self.btn_ext_filter, 0, 0)

        self._list_header_type_label = QLabel("Тип:")
        self._list_header_type_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._list_header_type_label.setFixedWidth(90)
        self._list_header_type_label.setVisible(False)
        self.btn_type_filter = LeftAlignedToolButton()
        self.btn_type_filter.setObjectName("header_cell_tr")
        setup_standard_header_dropdown(self.btn_type_filter)
        self._type_filter_menu = QMenu(self.btn_type_filter)
        self._type_filter_menu.setObjectName("header_dropdown_popup")
        apply_standard_menu_style(self._type_filter_menu)
        self._type_filter_actions = {}
        for label, value in [
            ("Документы", "document"),
            ("Изображения", "image"),
            ("Архивы", "archive"),
            ("Папки", "folder"),
            ("Другое", "other"),
        ]:
            action = QAction(label, self._type_filter_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self.on_file_type_filter_changed)
            self._type_filter_menu.addAction(action)
            self._type_filter_actions[value] = action
        self.btn_type_filter.setMenu(self._type_filter_menu)
        self._type_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(self._type_filter_menu, self.btn_type_filter)
        )
        self._update_type_filter_button_text()
        list_header.addWidget(self.btn_type_filter, 0, 1)

        self._list_header_sort_label = QLabel("Сортировка:")
        self._list_header_sort_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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
        for idx, mode in enumerate(self._sort_modes):
            action = QAction(mode, self._sort_filter_menu)
            action.setCheckable(True)
            action.setChecked(idx == 0)
            action.triggered.connect(lambda _checked=False, m=mode: self._on_sort_mode_selected(m))
            self._sort_action_group.addAction(action)
            self._sort_filter_menu.addAction(action)
            self._sort_filter_actions[mode] = action
        self._sort_current_mode = self._sort_modes[0]
        self.combo_sort.setText(self._sort_current_mode)
        self.combo_sort.setMenu(self._sort_filter_menu)
        self._sort_filter_menu.aboutToShow.connect(
            lambda: sync_standard_menu_width(self._sort_filter_menu, self.combo_sort)
        )
        list_header.addWidget(self.combo_sort, 1, 0)

        self._list_header_search_label = QLabel("Поиск:")
        self._list_header_search_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._list_header_search_label.setFixedWidth(90)
        self._list_header_search_label.setVisible(False)
        self.input_search = QLineEdit()
        self.input_search.setObjectName("header_cell_br")
        self.input_search.setPlaceholderText("Введите имя файла...")
        setup_standard_line_input(self.input_search)
        self.input_search.setMinimumWidth(0)
        self.input_search.textChanged.connect(self.on_search_text_changed)

        header_border_style = (
            "QToolButton#header_cell_tl, QToolButton#header_cell_tr, "
            "QToolButton#header_cell_bl, QLineEdit#header_cell_br {"
            "border: none;"
            "border-radius: 0px;"
            "margin: 0px;"
            "padding: 2px 10px;"
            "}"
            "QToolButton#header_cell_tl:hover, QToolButton#header_cell_tr:hover, "
            "QToolButton#header_cell_bl:hover, QLineEdit#header_cell_br:hover {"
            "background-color: transparent;"
            "border: none;"
            "}"
        )
        self.btn_ext_filter.setStyleSheet(self.btn_ext_filter.styleSheet() + header_border_style)
        self.btn_type_filter.setStyleSheet(self.btn_type_filter.styleSheet() + header_border_style)
        self.combo_sort.setStyleSheet(self.combo_sort.styleSheet() + header_border_style)
        self.input_search.setStyleSheet(self.input_search.styleSheet() + header_border_style)
        for widget in (self.btn_ext_filter, self.btn_type_filter, self.combo_sort, self.input_search):
            try:
                widget.setMinimumHeight(28)
            except Exception:
                pass
        self.combo_sort.setStyleSheet(
            self.combo_sort.styleSheet()
            + "QComboBox#combo_sort { padding: 2px 10px; margin: 0px; border: none; }"
            + "QComboBox#combo_sort::drop-down { width: 18px; border: none; }"
            + "QComboBox#combo_sort::down-arrow { width: 8px; height: 8px; }"
        )
        list_header.addWidget(self.input_search, 1, 1)
        list_header.setColumnStretch(0, 1)
        list_header.setColumnStretch(1, 1)

        right_layout.addLayout(list_header)
        # Список файлов с drag-and-drop + панель предпросмотра
        files_preview_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.files_preview_splitter = files_preview_splitter
        files_preview_splitter.setHandleWidth(0)
        files_preview_splitter.setChildrenCollapsible(False)
        files_preview_splitter.setCollapsible(0, False)
        files_preview_splitter.setCollapsible(1, False)

        files_panel = QWidget()
        files_panel_layout = QVBoxLayout(files_panel)
        files_panel_layout.setContentsMargins(0, 0, 0, 0)
        files_panel_layout.setSpacing(0)

        self.list_files = FileListWidget()
        self.list_files.setObjectName("files_list")
        try:
            self.list_files.setWordWrap(True)
            self.list_files.setTextElideMode(Qt.TextElideMode.ElideNone)
            self.list_files.setUniformItemSizes(False)
            self.list_files.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        except Exception:
            pass
        list_palette = self.list_files.palette()
        list_palette.setColor(QPalette.ColorRole.Highlight, QColor("#9fc5f8"))
        list_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1f2328"))
        self.list_files.setPalette(list_palette)
        self.list_files.filesDropped.connect(self.add_files)
        self.list_files.itemDoubleClicked.connect(self.open_file)
        self.list_files.itemSelectionChanged.connect(self.on_file_selection_changed)
        self.list_files.orderChanged.connect(self.on_list_order_changed)
        self.list_files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_files.customContextMenuRequested.connect(self.show_file_context_menu)
        files_panel_layout.addWidget(self.list_files, 1)

        self.drop_zone_controls = QWidget(self.list_files.viewport())
        self.drop_zone_controls.setObjectName("drop_zone_overlay")
        self.drop_zone_controls.setStyleSheet(
            """
            QWidget#drop_zone_overlay {
                background-color: #3a3a3a;
                border: none;
                border-radius: 0px;
            }
            QWidget#drop_zone_overlay QLabel {
                background-color: transparent;
            }
            """
        )
        drop_zone_layout = QVBoxLayout(self.drop_zone_controls)
        drop_zone_layout.setContentsMargins(0, 8, 0, 8)
        drop_zone_layout.setSpacing(10)
        drop_zone_layout.addStretch()

        drop_buttons_row = QGridLayout()
        drop_buttons_row.setContentsMargins(0, 0, 0, 0)
        drop_buttons_row.setHorizontalSpacing(10)
        drop_buttons_row.setVerticalSpacing(0)
        drop_buttons_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

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
        self.drop_zone_hint_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.drop_zone_hint_label.setStyleSheet("color: rgba(220,220,220,180); font-size: 13px;")
        drop_zone_layout.addWidget(self.drop_zone_hint_label, 0, Qt.AlignmentFlag.AlignHCenter)
        drop_zone_layout.addStretch()

        try:
            model = self.list_files.model()
            model.rowsInserted.connect(lambda *_args: self._update_drop_zone_controls())
            model.rowsRemoved.connect(lambda *_args: self._update_drop_zone_controls())
            model.modelReset.connect(lambda *_args: self._update_drop_zone_controls())
        except Exception:
            pass
        try:
            self.list_files.viewport().installEventFilter(self)
            self.list_files.installEventFilter(self)
        except Exception:
            pass
        self._update_drop_zone_controls()
        QTimer.singleShot(0, self._update_drop_zone_controls)

        preview_panel = self._create_preview_panel()
        files_preview_splitter.addWidget(files_panel)
        files_preview_splitter.addWidget(preview_panel)
        files_preview_splitter.setSizes([1, 1])
        files_preview_splitter.setStretchFactor(0, 1)
        files_preview_splitter.setStretchFactor(1, 1)
        preview_handle = files_preview_splitter.handle(1)
        if preview_handle is not None:
            preview_handle.setEnabled(False)
        QTimer.singleShot(0, self._sync_files_preview_splitter)

        right_layout.addWidget(files_preview_splitter, 1)

        # Прогресс бар + кнопка отмены (под правым списком)
        self._create_progress_dialog()
        self.on_sort_changed()

        # Информация о файлах
        info_layout = QHBoxLayout()
        self.label_count = QLabel("Файлов: 0")
        self.label_count.setStyleSheet("font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.label_count)

        count_size_sep = QFrame()
        count_size_sep.setFrameShape(QFrame.Shape.VLine)
        count_size_sep.setFrameShadow(QFrame.Shadow.Plain)
        count_size_sep.setStyleSheet("background-color: #4a4a4a; border: none;")
        count_size_sep.setFixedWidth(2)
        info_layout.addWidget(count_size_sep)

        self.label_item_size = QLabel("Размер: 0 MB")
        self.label_item_size.setStyleSheet("font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.label_item_size)

        size_total_sep = QFrame()
        size_total_sep.setFrameShape(QFrame.Shape.VLine)
        size_total_sep.setFrameShadow(QFrame.Shadow.Plain)
        size_total_sep.setStyleSheet("background-color: #4a4a4a; border: none;")
        size_total_sep.setFixedWidth(2)
        info_layout.addWidget(size_total_sep)

        self.label_total_size = QLabel("Общий объем: 0 MB")
        self.label_total_size.setStyleSheet("font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.label_total_size)

        info_layout.addStretch()
        right_layout.addLayout(info_layout)

        # Оставляем метки для внутренней логики, но не занимаем нижнюю область панели.
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        handle = splitter.handle(1)
        if handle is not None:
            handle.setCursor(Qt.CursorShape.SplitHCursor)
            grip_layout = QVBoxLayout(handle)
            grip_layout.setContentsMargins(0, 0, 0, 0)
            grip_layout.setSpacing(0)
            grip_layout.addStretch()
            grip_label = QLabel("⋮", handle)
            self._splitter_grip_label = grip_label
            grip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grip_label.setStyleSheet(
                "color: rgba(255, 255, 255, 0.68); background: transparent; font-size: 15px; font-weight: 600;"
            )
            grip_layout.addWidget(grip_label, 0, Qt.AlignmentFlag.AlignCenter)
            grip_layout.addStretch()

        # Настройки сплиттера
        splitter.setChildrenCollapsible(False)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([1, 5])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        handle = splitter.handle(1)
        if handle is not None:
            handle.setEnabled(False)

        main_layout.addWidget(splitter, 1)
        
        # Статус бар
        self.status_bar = LoggingStatusBar()
        self.status_bar.messageLogged.connect(self.on_status_message_logged)
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setFixedHeight(0)
        self.status_bar.setContentsMargins(0, 0, 0, 0)
        self.status_bar.setVisible(False)
        self.status_bar.showMessage("Готово. Перетащите файлы/папки в список или используйте кнопки добавления.")
        
        # Устанавливаем минимальные размеры для окна
        self.setMinimumSize(900, 550)
        self._default_min_size = self.minimumSize()
        self.tabs.setMinimumWidth(0)

        # Применяем тему (по умолчанию: как в системе)
        self.apply_theme_mode(self.theme_mode)
        self.setup_system_theme_tracking()
        self._update_header_compact_mode()
        self._connect_ui_state_autosave()

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
        except Exception:
            pass

    @staticmethod
    def _safe_connect_signal(signal, callback) -> None:
        try:
            signal.connect(callback)
        except Exception:
            pass

    @staticmethod
    def _safe_polish_widget(widget) -> None:
        if widget is None:
            return
        try:
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        except Exception:
            pass

    def _apply_theme_runtime_widgets(self):
        mode = getattr(self, "_effective_theme_mode", "dark")
        for widget_name in ("btn_ext_filter", "btn_type_filter", "combo_sort"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                try:
                    widget._effective_theme_mode = mode
                except Exception:
                    pass
                try:
                    menu = widget.menu()
                    if menu is not None:
                        menu._effective_theme_mode = mode
                        self._safe_polish_widget(menu)
                except Exception:
                    pass
        if hasattr(self, "_splitter_grip_label") and self._splitter_grip_label is not None:
            if mode == "light":
                self._splitter_grip_label.setStyleSheet(
                    "color: rgba(70, 80, 90, 0.75); background: transparent; font-size: 15px; font-weight: 600;"
                )
            else:
                self._splitter_grip_label.setStyleSheet(
                    "color: rgba(255, 255, 255, 0.68); background: transparent; font-size: 15px; font-weight: 600;"
                )
        if hasattr(self, "drop_zone_controls") and self.drop_zone_controls is not None:
            if mode == "light":
                self.drop_zone_controls.setStyleSheet(
                    """
                    QWidget#drop_zone_overlay {
                        background-color: #f3f3f3;
                        border: none;
                        border-radius: 0px;
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
                        background-color: #3a3a3a;
                        border: none;
                        border-radius: 0px;
                    }
                    QWidget#drop_zone_overlay QLabel {
                        background-color: transparent;
                        color: rgba(220,220,220,180);
                    }
                    """
                )
                if hasattr(self, "drop_zone_hint_label"):
                    self.drop_zone_hint_label.setStyleSheet("color: rgba(220,220,220,180); font-size: 13px;")
        if hasattr(self, "preview_panel") and self.preview_panel is not None:
            if mode == "light":
                self.preview_panel.setStyleSheet(
                    """
                    QWidget#drop_zone_overlay {
                        background-color: #f3f3f3;
                        border: none;
                        border-radius: 0px;
                    }
                    QWidget#drop_zone_overlay QLabel {
                        background-color: transparent;
                        color: #5b6470;
                    }
                    """
                )
            else:
                self.preview_panel.setStyleSheet(
                    """
                    QWidget#drop_zone_overlay {
                        background-color: #3a3a3a;
                        border: none;
                        border-radius: 0px;
                    }
                    QWidget#drop_zone_overlay QLabel {
                        background-color: transparent;
                        color: rgba(220,220,220,180);
                    }
                    """
                )
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
            except Exception:
                pass

    def _update_drop_zone_controls(self):
        if not hasattr(self, "list_files") or not hasattr(self, "drop_zone_controls"):
            return
        viewport = self.list_files.viewport()
        self.drop_zone_controls.setGeometry(viewport.rect())
        has_files = bool(self.list_files.model().files())
        self.drop_zone_controls.setVisible(not has_files)
        self.drop_zone_controls.raise_()

    def eventFilter(self, obj, event):
        if hasattr(self, "list_files"):
            viewport = self.list_files.viewport()
            if obj is self.list_files or obj is viewport:
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Move, QEvent.Type.LayoutRequest):
                    self._update_drop_zone_controls()
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
        except Exception:
            pass
        try:
            self._sync_files_preview_splitter()
        except Exception:
            pass
        self._update_drop_zone_controls()
        self._schedule_settings_save()

    def _sync_files_preview_splitter(self):
        splitter = getattr(self, "files_preview_splitter", None)
        if splitter is None:
            return
        total_width = splitter.width()
        if total_width <= 0:
            return
        handle_width = splitter.handleWidth() if hasattr(splitter, "handleWidth") else 0
        available = max(0, total_width - handle_width)
        left = available // 2
        right = available - left
        splitter.setSizes([left, right])
        header_layout = getattr(self, "_list_header_layout", None)
        if header_layout is not None:
            try:
                header_layout.setColumnStretch(0, 1)
                header_layout.setColumnStretch(1, 1)
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._schedule_settings_save()
        
    def get_file_extension_type(self, file_path):
        """Определяет тип файла по расширению"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Группировка форматов
        doc_formats = ['.doc', '.docx']
        pdf_formats = ['.pdf']
        odt_formats = ['.odt']
        image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp']
        
        if ext in doc_formats:
            return "DOC/DOCX"
        elif ext in pdf_formats:
            return "PDF"
        elif ext in odt_formats:
            return "ODT (OpenDocument)"
        elif ext in image_formats:
            return "Изображения (JPG/PNG)"
        else:
            return None
    
    def update_converter_from_format(self):
        """Обновляет поле 'Из:' на основе выбранных файлов"""
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            self.from_convert_combo.setCurrentIndex(0)
            self.to_convert_combo.setEnabled(False)
            self.btn_convert.setEnabled(False)
            return
        
        # Определяем форматы всех выбранных файлов
        formats = set()
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if file_item and file_item.is_file:
                file_type = self.get_file_extension_type(file_item.path)
                if file_type:
                    formats.add(file_type)
        
        if len(formats) == 1:
            # Все файлы одного типа
            file_type = formats.pop()
            # Ищем соответствующий индекс в комбобоксе
            index = self.from_convert_combo.findText(file_type)
            if index >= 0:
                self.from_convert_combo.setCurrentIndex(index)
                self.update_to_combo_based_on_from()
        else:
            # Разные типы файлов - сброс
            self.from_convert_combo.setCurrentIndex(0)
            self.to_convert_combo.setCurrentIndex(0)
            self.to_convert_combo.setEnabled(False)
            self.btn_convert.setEnabled(False)
    
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
    
    def select_files(self):
        """Выбор файлов для обработки"""
        options = QFileDialog.Option.ReadOnly
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Выберите файлы", 
            "", 
            "Все файлы (*.*);;Документы (*.doc *.docx *.pdf);;Изображения (*.jpg *.jpeg *.png *.bmp)",
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

    def add_folder_files(self, folder_path):
        """Добавляет все файлы из папки (рекурсивно)"""
        file_paths = []
        for root, _, files in os.walk(folder_path):
            for name in files:
                file_paths.append(os.path.join(root, name))
        
        if file_paths:
            self.add_files(file_paths)
        else:
            QMessageBox.information(self, "Информация", "В выбранной папке нет файлов.")
