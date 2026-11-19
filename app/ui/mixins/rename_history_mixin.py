import os
import time

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.ui.ui_components import (
    setup_standard_danger_button,
    setup_standard_dialog,
)
from app.ui.ui_styles import DIALOG_MARGINS, SPACE_SM
from core.operation_requests import RenameRequest
from core.rename_plan import resolve_rename_targets


class RenameHistoryMixin:
    # Хранит пары старых и новых путей для отмены и повтора переименования.
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
        current_row = history_list.currentRow()
        history_list.clear()
        for entry in reversed(self._rename_history):
            ts = entry.get("timestamp")
            count = entry.get("count", 0)
            label = entry.get("label")
            time_str = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                if ts
                else ""
            )
            if not label:
                label = f"{count} файлов"
            text = f"{time_str} • {label}" if time_str else label
            history_list.addItem(text)
        if history_list.count():
            target_row = current_row if 0 <= current_row < history_list.count() else 0
            history_list.setCurrentRow(target_row)

    def show_rename_history_dialog(self):
        dialog = QDialog(self)
        dialog.setObjectName("rename_history_dialog")
        setup_standard_dialog(
            dialog, title="История переименований", min_width=520, min_height=320,
        )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_SM)

        description = QLabel("История переименований за текущую сессию")
        description.setWordWrap(True)
        layout.addWidget(description)

        history_list = QListWidget(dialog)
        history_list.setObjectName("rename_history_list")
        history_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        history_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(history_list, 1)

        undo_button = QPushButton("Откатить выбранное", dialog)
        setup_standard_danger_button(undo_button, expand=True)
        undo_button.clicked.connect(self.undo_last_rename)
        layout.addWidget(undo_button)

        self.rename_history_list = history_list
        self.btn_history_undo = undo_button
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
            self._rename_history = self._rename_history[
                -self._max_rename_history :
            ]
        self._refresh_rename_history_view()

    def _start_rename_from_pairs(self, pairs):
        if not pairs:
            return False
        show_starting = getattr(self, "_show_operation_starting", None)
        if callable(show_starting):
            show_starting(f"Подготовка переименования {len(pairs)} файлов...")
        request = RenameRequest(
            tuple((new_path, os.path.basename(old_path)) for new_path, old_path in pairs),
            strict=True,
        )
        files = self._collect_file_items_by_paths([path for path, _ in request.pairs])
        if not self._start_operation(request, files):
            return False
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(
                f"Переименование {len(pairs)} файлов..."
            )
        return True

    def undo_last_rename(self):
        if not self._ensure_operation_can_start():
            return
        if not self._rename_history:
            QMessageBox.information(
                self, "Информация", "Нет операций для отката."
            )
            return

        selected = self._get_selected_history_entry()
        entry_index, entry = selected or (len(self._rename_history) - 1, self._rename_history[-1])
        pairs = entry.get("pairs", [])
        if not pairs:
            self._update_undo_button()
            return
        missing = [path for path, _ in pairs if not os.path.exists(path)]
        if missing:
            QMessageBox.warning(self, "Файлы недоступны", "\n".join(missing))
            return
        try:
            files = self._collect_file_items_by_paths([path for path, _ in pairs])
            resolve_rename_targets(files, [os.path.basename(old) for _, old in pairs], strict=True)
        except ValueError as error:
            QMessageBox.warning(self, "Откат невозможен", str(error))
            return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Откатить переименование {len(pairs)} файлов?",
            QMessageBox.Icon.Question,
            True,
            yes_text="Откатить",
            no_text="Отмена",
            destructive=True,
        )
        if not reply:
            return

        self._rename_history.pop(entry_index)
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
        self.status_bar.showMessage(
            f"Откат переименования {len(pairs)} файлов..."
        )
        self._update_undo_button()
