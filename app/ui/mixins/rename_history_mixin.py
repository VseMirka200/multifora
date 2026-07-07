import os
import time

from PyQt6.QtWidgets import QMessageBox


class RenameHistoryMixin:
    def _persist_rename_history_state(self):
        saver = getattr(self, "save_settings", None)
        if callable(saver):
            try:
                saver()
                return
            except Exception:
                pass
        scheduler = getattr(self, "_schedule_settings_save", None)
        if callable(scheduler):
            try:
                scheduler()
            except Exception:
                pass

    def on_history_row_changed(self, row: int):
        if getattr(self, "_is_history_refresh", False):
            return
        self._update_undo_button()

    def _get_selected_history_entry(self):
        if not hasattr(self, "rename_history_list"):
            return None
        row = self.rename_history_list.currentRow()
        if row < 0:
            return None
        idx = len(self._rename_history) - 1 - row
        if idx < 0 or idx >= len(self._rename_history):
            return None
        return idx, self._rename_history[idx]

    def _update_undo_button(self):
        can_undo = bool(self._rename_history)
        can_redo = bool(self._rename_redo_history)
        if self.file_worker and self.file_worker.isRunning():
            can_undo = False
            can_redo = False
        if hasattr(self, "btn_history_undo"):
            self.btn_history_undo.setEnabled(can_undo)
        if hasattr(self, "btn_history_redo"):
            self.btn_history_redo.setEnabled(can_redo)
        self._refresh_rename_history_view()
        self._persist_rename_history_state()

    def _refresh_rename_history_view(self):
        if not hasattr(self, "rename_history_list"):
            return
        self._is_history_refresh = True
        current_row = self.rename_history_list.currentRow()
        self.rename_history_list.blockSignals(True)
        self.rename_history_list.clear()
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
            self.rename_history_list.addItem(text)
        if current_row >= 0 and current_row < self.rename_history_list.count():
            self.rename_history_list.setCurrentRow(current_row)
        self.rename_history_list.blockSignals(False)
        self._is_history_refresh = False

    def _push_rename_history(self, entry: dict):
        entry = dict(entry)
        entry.setdefault("timestamp", time.time())
        entry.setdefault("count", len(entry.get("pairs", [])))
        self._rename_history.append(entry)
        if len(self._rename_history) > self._max_rename_history:
            self._rename_history = self._rename_history[-self._max_rename_history :]
        self._rename_redo_history.clear()
        self._refresh_rename_history_view()
        self._persist_rename_history_state()

    def _push_rename_redo(self, entry: dict):
        entry = dict(entry)
        entry.setdefault("timestamp", time.time())
        entry.setdefault("count", len(entry.get("pairs", [])))
        self._rename_redo_history.append(entry)
        if len(self._rename_redo_history) > self._max_rename_history:
            self._rename_redo_history = self._rename_redo_history[-self._max_rename_history :]
        self._persist_rename_history_state()

    def _start_rename_from_pairs(self, pairs, direction: str):
        if not pairs:
            return False
        if not self.create_file_worker():
            return False
        if direction == "undo":
            paths = [new_path for new_path, _ in pairs]
            new_names = [os.path.basename(old_path) for _, old_path in pairs]
        else:
            paths = [old_path for _, old_path in pairs]
            new_names = [os.path.basename(new_path) for new_path, _ in pairs]

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
        if self.file_worker and self.file_worker.isRunning():
            QMessageBox.warning(self, "Операция выполняется", "Дождитесь завершения текущей операции.")
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
            self._persist_rename_history_state()
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
            self._persist_rename_history_state()
            self._update_undo_button()
            return

        self._is_undo_operation = True
        self._pending_undo_entry = entry
        if not self._start_rename_from_pairs(pairs, "undo"):
            self._is_undo_operation = False
            self._pending_undo_entry = None
            if selected:
                self._rename_history.insert(entry_index, entry)
            else:
                self._rename_history.append(entry)
            self._persist_rename_history_state()
            self._update_undo_button()
            return

        self.log_event(f"Откат переименования: {len(pairs)} файлов")
        self.status_bar.showMessage(f"Откат переименования {len(pairs)} файлов...")
        self._update_undo_button()

    def redo_last_rename(self):
        if self.file_worker and self.file_worker.isRunning():
            QMessageBox.warning(self, "Операция выполняется", "Дождитесь завершения текущей операции.")
            return
        if not self._rename_redo_history:
            QMessageBox.information(self, "Информация", "Нет операций для повтора.")
            return

        entry = self._rename_redo_history.pop()
        pairs = entry.get("pairs", [])
        if not pairs:
            return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Повторить переименование {len(pairs)} файлов?",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            self._rename_redo_history.append(entry)
            return

        self._is_redo_operation = True
        self._pending_redo_entry = entry
        if not self._start_rename_from_pairs(pairs, "redo"):
            self._is_redo_operation = False
            self._pending_redo_entry = None
            self._rename_redo_history.append(entry)
            return

        self.log_event(f"Повтор переименования: {len(pairs)} файлов")
        self.status_bar.showMessage(f"Повтор переименования {len(pairs)} файлов...")
        self._update_undo_button()
