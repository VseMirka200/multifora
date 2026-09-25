import os
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.ui.ui_components import (
    setup_standard_danger_button,
    setup_standard_secondary_button,
)
from app.ui.ui_spacing import DIALOG_MARGINS, MARGINS_NONE, SPACE_SM


class RenameHistoryMixin:
    # Хранит пары старых и новых путей для отмены и повтора переименования.
    def on_history_row_changed(self, row: int):
        if getattr(self, "_is_history_refresh", False):
            return
        self._update_undo_button()

    def _get_selected_history_entry(self):
        history_list = getattr(self, "rename_history_list", None)
        if history_list is None:
            return None
        row = history_list.currentRow()
        if row < 0:
            return None
        idx = len(self._rename_history) - 1 - row
        if idx < 0 or idx >= len(self._rename_history):
            return None
        return idx, self._rename_history[idx]

    def _update_undo_button(self):
        can_undo = bool(self._rename_history)
        undo_button = getattr(self, "btn_history_undo", None)
        if undo_button is not None:
            undo_button.setEnabled(can_undo)
        self._refresh_rename_history_view()

    def _refresh_rename_history_view(self):
        history_list = getattr(self, "rename_history_list", None)
        if history_list is None:
            return
        self._is_history_refresh = True
        current_row = history_list.currentRow()
        history_list.blockSignals(True)
        history_list.clear()
        for entry in reversed(self._rename_history):
            ts = entry.get("timestamp")
            count = entry.get("count", 0)
            label = entry.get("label")
            if ts:
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            else:
                time_str = ""
            if not label:
                label = f"{count} файлов"
            text = f"{time_str} • {label}" if time_str else label
            history_list.addItem(text)
        if history_list.count():
            target_row = current_row if 0 <= current_row < history_list.count() else 0
            history_list.setCurrentRow(target_row)
        history_list.blockSignals(False)
        self._is_history_refresh = False

    def show_rename_history_dialog(self):
        dialog = QDialog(self)
        dialog.setObjectName("rename_history_dialog")
        dialog.setWindowTitle("История переименований")
        dialog.setModal(True)
        dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        dialog.setMinimumSize(520, 320)
        dialog._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
        dialog.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_SM)

        description = QLabel("История переименований за текущую сессию")
        description.setWordWrap(True)
        layout.addWidget(description)

        history_list = QListWidget(dialog)
        history_list.setObjectName("rename_history_list")
        history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        history_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        history_list.currentRowChanged.connect(self.on_history_row_changed)
        layout.addWidget(history_list, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(*MARGINS_NONE)
        buttons_layout.setSpacing(SPACE_SM)

        undo_button = QPushButton("Откатить выбранное", dialog)
        setup_standard_danger_button(undo_button, expand=True)
        undo_button.clicked.connect(self.undo_last_rename)
        buttons_layout.addWidget(undo_button, 1)

        close_button = QPushButton("Закрыть", dialog)
        setup_standard_secondary_button(close_button, expand=True)
        close_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(close_button, 1)
        layout.addLayout(buttons_layout)

        self.rename_history_list = history_list
        self.btn_history_undo = undo_button
        self._refresh_rename_history_view()
        self._update_undo_button()
        try:
            return dialog.exec()
        finally:
            if getattr(self, "rename_history_list", None) is history_list:
                self.rename_history_list = None
            if getattr(self, "btn_history_undo", None) is undo_button:
                self.btn_history_undo = None
            dialog.deleteLater()

    def _push_rename_history(self, entry: dict):
        entry = dict(entry)
        entry.setdefault("timestamp", time.time())
        entry.setdefault("count", len(entry.get("pairs", [])))
        self._rename_history.append(entry)
        if len(self._rename_history) > self._max_rename_history:
            self._rename_history = self._rename_history[-self._max_rename_history :]
        self._refresh_rename_history_view()

    def _start_rename_from_pairs(self, pairs):
        if not pairs:
            return False
        if not self.create_file_worker():
            return False
        paths = [new_path for new_path, _ in pairs]
        new_names = [os.path.basename(old_path) for _, old_path in pairs]

        files = self._collect_file_items_by_paths(paths)
        self._last_operation = {
            "op": "rename",
            "new_names_by_path": {p: n for p, n in zip(paths, new_names)},
        }
        self.file_worker.set_rename(files, new_names)
        self.file_worker.start()
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(f"Переименование {len(pairs)} файлов...")
        return True

    def undo_last_rename(self):
        if not self._ensure_operation_can_start():
            return
        if not self._rename_history:
            QMessageBox.information(self, "Информация", "Нет операций для отката.")
            return

        selected = self._get_selected_history_entry()
        if selected:
            entry_index, entry = selected
            entry = self._rename_history.pop(entry_index)
        else:
            entry = self._rename_history.pop()
        pairs = entry.get("pairs", [])
        if not pairs:
            self._update_undo_button()
            return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Откатить переименование {len(pairs)} файлов?",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            if selected:
                self._rename_history.insert(entry_index, entry)
            else:
                self._rename_history.append(entry)
            self._update_undo_button()
            return

        self._is_undo_operation = True
        self._pending_undo_entry = entry
        if not self._start_rename_from_pairs(pairs):
            self._is_undo_operation = False
            self._pending_undo_entry = None
            if selected:
                self._rename_history.insert(entry_index, entry)
            else:
                self._rename_history.append(entry)
            self._update_undo_button()
            return

        self.log_event(f"Откат переименования: {len(pairs)} файлов")
        self.status_bar.showMessage(f"Откат переименования {len(pairs)} файлов...")
        self._update_undo_button()
