import json

from PyQt6.QtWidgets import QFileDialog, QMessageBox

import app.core.settings as app_settings
from app.core.app_ipc import _delete_ipc_token
from app.core.message_boxes import show_app_choice
from app.core.app_utils import _log_ignored_error


class LifecycleMixin:
    # Сохраняет состояние окна и не даёт закрыть его посреди файловой операции.
    def on_status_message_logged(self, message: str):
        self.log_event(message, "STATUS")

    def on_worker_status(self, message: str):
        if hasattr(self, "progress_status_label") and self.progress_status_label is not None:
            self.progress_status_label.setText(message)
        self.status_bar.showMessage(message)

    def get_settings_file_path(self):
        """Возвращает полный путь к файлу настроек (в AppData пользователя)."""
        return app_settings.get_settings_file_path()

    def load_settings(self):
        """Загрузка настроек из файла без уведомлений."""
        app_settings.load_settings(self)

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
                    json.dump(self.custom_templates, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Успех", f"Шаблоны экспортированы в {file_path}")
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать шаблоны: {str(exc)}")

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
                with open(file_path, "r", encoding="utf-8") as f:
                    imported_templates = json.load(f)
                for name, template_data in imported_templates.items():
                    if name in self.custom_templates:
                        counter = 1
                        new_name = f"{name}_{counter}"
                        while new_name in self.custom_templates:
                            counter += 1
                            new_name = f"{name}_{counter}"
                        self.custom_templates[new_name] = template_data
                    else:
                        self.custom_templates[name] = template_data
                self.update_templates_table(parent_window)
                self.save_settings()
                QMessageBox.information(
                    parent_window if parent_window else self,
                    "Успех",
                    f"Импортировано {len(imported_templates)} шаблонов",
                )
            except Exception as exc:
                QMessageBox.critical(
                    parent_window if parent_window else self,
                    "Ошибка",
                    f"Не удалось импортировать шаблоны: {str(exc)}",
                )

    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        if self.file_worker and self.file_worker.isRunning():
            if self._pending_close:
                event.ignore()
                return

            selected = show_app_choice(
                self,
                "Операция выполняется",
                "Дождаться завершения операции перед закрытием?",
                (
                    ("wait", "Подождать", "secondary"),
                    ("cancel", "Отменить", "secondary"),
                ),
                icon=QMessageBox.Icon.Question,
                default_key="wait",
                cancel_key="cancel",
            )
            if selected == "wait":
                self._pending_close = True
                self.status_bar.showMessage("Закрытие запланировано после завершения операции.")
            event.ignore()
            return

        _delete_ipc_token()
        if hasattr(self, "_settings_save_timer") and self._settings_save_timer is not None:
            try:
                self._settings_save_timer.stop()
            except Exception as error:
                _log_ignored_error("LifecycleMixin.closeEvent", error)
        self._force_settings_save = True
        self.save_settings()
        self._force_settings_save = False
        if hasattr(self, "ipc_server") and self.ipc_server:
            try:
                self.ipc_server.close()
                self.ipc_server = None
            except Exception as exc:
                self.log_event(f"Ошибка закрытия IPC: {exc}", "WARN")
        event.accept()
