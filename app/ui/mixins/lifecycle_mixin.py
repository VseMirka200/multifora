from PySide6.QtWidgets import QMessageBox

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
