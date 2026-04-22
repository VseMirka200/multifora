import json

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QPushButton

import app.core.settings as app_settings
from app.core.app_ipc import _delete_ipc_token
from app.core.message_boxes import tune_message_box_layout
from app.ui.ui_components import setup_standard_danger_button, setup_standard_secondary_button


class LifecycleMixin:
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

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Операция выполняется")
            msg_box.setText("Дождаться завершения операции перед закрытием?")
            msg_box.setIcon(QMessageBox.Icon.Question)
            wait_button = QPushButton("Подождать")
            cancel_button = QPushButton("Отменить")
            setup_standard_secondary_button(wait_button, height=22)
            setup_standard_danger_button(cancel_button, height=22)
            msg_box.addButton(wait_button, QMessageBox.ButtonRole.YesRole)
            msg_box.addButton(cancel_button, QMessageBox.ButtonRole.NoRole)
            tune_message_box_layout(msg_box, QMessageBox.Icon.Question)
            msg_box.setDefaultButton(wait_button)
            msg_box.exec()
            clicked = msg_box.clickedButton()
            if clicked == wait_button:
                self._pending_close = True
                self.status_bar.showMessage("Закрытие запланировано после завершения операции.")
            event.ignore()
            return

        _delete_ipc_token()
        self.save_settings()
        if hasattr(self, "ipc_server") and self.ipc_server:
            try:
                self.ipc_server.close()
                self.ipc_server = None
            except Exception as exc:
                self.log_event(f"Ошибка закрытия IPC: {exc}", "WARN")
        event.accept()
