import json

from PySide6.QtWidgets import QFileDialog, QMessageBox

import app.core.settings as app_settings
from app.core.app_ipc import _delete_ipc_token
from app.core.app_utils import _log_ignored_error
from app.core.message_boxes import show_app_choice


class LifecycleMixin:
    # Сохраняет состояние окна и не даёт закрыть его посреди файловой операции.
    def on_status_message_logged(self, message: str):
        self.log_event(message, "STATUS")

    def on_worker_status(self, message: str):
        update_progress_status = getattr(
            self, "_set_progress_status_text", None
        )
        if callable(update_progress_status):
            update_progress_status(message)
        self.status_bar.showMessage(message)

    def get_settings_file_path(self):
        """Возвращает полный путь к файлу настроек (в AppData пользователя)."""
        return app_settings.get_settings_file_path()

    def load_settings(self):
        """Загрузка настроек из файла без уведомлений."""
        app_settings.load_settings(self)
        self.apply_shortcut_settings(silent=True)

    def save_settings(self):
        """Сохранение настроек в файл."""
        app_settings.save_settings(self)

    def export_templates(self):
        """Экспорт шаблонов в файл."""
        if not self.custom_templates:
            QMessageBox.warning(self, "Ошибка", "Нет шаблонов для экспорта!")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт шаблонов",
            "шаблоны_мультифора.json",
            "JSON файлы (*.json)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        self.custom_templates, f, ensure_ascii=False, indent=2
                    )
                QMessageBox.information(
                    self, "Успех", f"Шаблоны экспортированы в {file_path}"
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось экспортировать шаблоны: {exc!s}",
                )

    def import_templates(self, parent_window):
        """Импорт шаблонов из файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            parent_window if parent_window else self,
            "Импорт шаблонов",
            "",
            "JSON файлы (*.json)",
        )
        if file_path:
            try:
                with open(file_path, encoding="utf-8") as f:
                    imported_templates = json.load(f)
                if not isinstance(imported_templates, dict):
                    raise ValueError("В файле должен быть список именованных шаблонов.")
                added = renamed = invalid = 0
                for name, template_data in imported_templates.items():
                    if (
                        not name.strip()
                        or not isinstance(template_data, dict)
                        or not isinstance(template_data.get("type"), str)
                        or not isinstance(template_data.get("data"), dict)
                    ):
                        invalid += 1
                        continue
                    if name in self.custom_templates:
                        counter = 1
                        new_name = f"{name}_{counter}"
                        while new_name in self.custom_templates:
                            counter += 1
                            new_name = f"{name}_{counter}"
                        self.custom_templates[new_name] = template_data
                        renamed += 1
                    else:
                        self.custom_templates[name] = template_data
                    added += 1
                self.update_templates_table(parent_window)
                self.save_settings()
                QMessageBox.information(
                    parent_window if parent_window else self,
                    "Импорт шаблонов",
                    f"Добавлено: {added}. Переименовано при совпадении: {renamed}. Пропущено: {invalid}.",
                )
            except Exception as exc:
                QMessageBox.critical(
                    parent_window if parent_window else self,
                    "Ошибка",
                    f"Не удалось импортировать шаблоны: {exc!s}",
                )

    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        metadata_worker = getattr(self, "_file_metadata_worker", None)
        if metadata_worker is not None and metadata_worker.isRunning():
            metadata_worker.requestInterruption()
            self._pending_metadata_close = True
            self.status_bar.showMessage(
                "Отмена чтения метаданных перед закрытием."
            )
            event.ignore()
            return

        if self.file_worker and self.file_worker.isRunning():
            if self._pending_close:
                event.ignore()
                return

            selected = show_app_choice(
                self,
                "Операция выполняется",
                "Выберите, что сделать с текущей операцией.",
                (
                    ("wait", "Закрыть после завершения", "secondary"),
                    ("stop", "Остановить и закрыть", "danger"),
                    ("stay", "Остаться", "secondary"),
                ),
                icon=QMessageBox.Icon.Question,
                default_key="stay",
                cancel_key="stay",
            )
            if selected in {"wait", "stop"}:
                self._pending_close = True
            if selected == "wait":
                self.status_bar.showMessage(
                    "Закрытие запланировано после завершения операции."
                )
            elif selected == "stop":
                self.cancel_operation()
            event.ignore()
            return

        panel = getattr(self, "merge_pages_panel", None)
        if panel is not None:
            panel.stop()
        _delete_ipc_token()
        if (
            hasattr(self, "_settings_save_timer")
            and self._settings_save_timer is not None
        ):
            try:
                self._settings_save_timer.stop()
            except Exception as error:
                _log_ignored_error("LifecycleMixin.closeEvent", error)
        self._force_settings_save = True
        self.save_settings()
        self._force_settings_save = False
        ipc_server = getattr(self, "_ipc_file_server", None)
        if ipc_server is not None:
            try:
                ipc_server.close()
                self._ipc_file_server = None
            except Exception as exc:
                self.log_event(f"Ошибка закрытия IPC: {exc}", "WARN")
        update_timer = getattr(self, "_update_poll_timer", None)
        if update_timer is not None:
            update_timer.stop()
        queue_paths_refresh_timer = getattr(self, "_queue_paths_refresh_timer", None)
        if queue_paths_refresh_timer is not None:
            queue_paths_refresh_timer.stop()
        update_executor = getattr(self, "_update_executor", None)
        if update_executor is not None:
            update_executor.shutdown(wait=False, cancel_futures=True)
        event.accept()
