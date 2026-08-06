import os
from datetime import datetime

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QDialog,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QTabBar,
    QWidget,
)

from app.core.app_utils import _get_app_data_dir, _log_ignored_error


class LoggingMixin:
    def init_logging(self):
        """Инициализация логирования."""
        self._log_file_path = self.get_log_file_path()
        self.log_event("Запуск программы")

    def get_logs_dir(self):
        """Возвращает папку логов только в AppData пользователя."""
        base_dir = _get_app_data_dir()
        logs_dir = os.path.join(base_dir, "logs")
        legacy_logs_dir = os.path.join(base_dir, "lods")
        try:
            if not os.path.exists(logs_dir) and os.path.isdir(legacy_logs_dir):
                try:
                    os.replace(legacy_logs_dir, logs_dir)
                except Exception as error:
                    _log_ignored_error("LoggingMixin.get_logs_dir", error)
            os.makedirs(logs_dir, exist_ok=True)
        except Exception as error:
            _log_ignored_error("LoggingMixin.get_logs_dir", error)
        return logs_dir

    def get_log_file_path(self):
        """Возвращает путь к файлу логов."""
        return os.path.join(self.get_logs_dir(), "multifora_logs.txt")

    def log_event(self, message: str, level: str = "INFO"):
        if not message:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}"
        self._log_lines.append(line)
        trimmed = False
        if self.max_log_lines and len(self._log_lines) > self.max_log_lines:
            self._log_lines = self._log_lines[-self.max_log_lines :]
            trimmed = True
        try:
            log_path = self._log_file_path or self.get_log_file_path()
            if trimmed or not os.path.exists(log_path):
                with open(log_path, "w", encoding="utf-8") as f:
                    if self._log_lines:
                        f.write("\n".join(self._log_lines) + "\n")
            else:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as error:
            _log_ignored_error("LoggingMixin.log_event", error)
        self._append_log_line(line)

    def attach_action_logging(self, root: QWidget | None = None):
        """Подключает логирование пользовательских действий к виджетам."""
        root_widget = root if isinstance(root, QWidget) else self
        widgets = [root_widget]
        try:
            widgets.extend(root_widget.findChildren(QWidget))
        except Exception as error:
            _log_ignored_error("LoggingMixin.attach_action_logging", error)

        for widget in widgets:
            self._attach_widget_logger(widget)

    def _attach_widget_logger(self, widget: QWidget):
        if widget is None:
            return
        if bool(widget.property("_action_logging_attached")):
            return
        if self._should_skip_action_logging(widget):
            return

        widget.setProperty("_action_logging_attached", True)

        try:
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(lambda checked, w=widget: self._log_checkbox_action(w, checked))
                return
            if isinstance(widget, QComboBox):
                widget.setProperty("_last_logged_value", widget.currentText())
                widget.currentTextChanged.connect(lambda text, w=widget: self._log_combo_action(w, text))
                return
            if isinstance(widget, QLineEdit):
                widget.setProperty("_last_logged_value", widget.text())
                widget.editingFinished.connect(lambda w=widget: self._log_line_edit_action(w))
                return
            if isinstance(widget, QSpinBox):
                widget.setProperty("_last_logged_value", widget.value())
                widget.valueChanged.connect(lambda value, w=widget: self._log_spin_action(w, value))
                return
            if isinstance(widget, QTabBar):
                widget.currentChanged.connect(lambda index, w=widget: self._log_tab_action(w, index))
                return
            if isinstance(widget, QListWidget) and widget.objectName() == "settings_nav":
                widget.currentTextChanged.connect(lambda text, w=widget: self._log_list_navigation_action(w, text))
                return
            if isinstance(widget, QAbstractButton):
                widget.clicked.connect(lambda _checked=False, w=widget: self._log_button_action(w))
                return
        except Exception as error:
            _log_ignored_error("LoggingMixin._attach_widget_logger", error)

    def _should_skip_action_logging(self, widget: QWidget) -> bool:
        if widget is None:
            return True
        if isinstance(widget, QPlainTextEdit):
            return True
        if isinstance(widget, QDialog):
            return True
        if getattr(widget, "objectName", lambda: "")() in {
            "qt_spinbox_lineedit",
        }:
            return True
        parent = widget.parent()
        while parent is not None:
            if parent is getattr(self, "logs_view", None):
                return True
            parent = parent.parent() if hasattr(parent, "parent") else None
        return False

    def _is_action_logging_ready(self) -> bool:
        return bool(getattr(self, "initial_load_complete", False)) and not bool(
            getattr(self, "_suspend_action_logging", False)
        )

    def _normalize_log_value(self, value) -> str:
        text = str(value or "").replace("\n", " ").replace("\r", " ").strip()
        if len(text) > 120:
            return text[:117] + "..."
        return text

    def _widget_caption(self, widget: QWidget) -> str:
        if widget is None:
            return "элемент"

        explicit = widget.property("log_label")
        if explicit:
            return str(explicit).strip()

        if isinstance(widget, QAbstractButton):
            text = self._normalize_log_value(widget.text())
            if text:
                return text

        for getter_name in ("placeholderText", "windowTitle", "objectName"):
            getter = getattr(widget, getter_name, None)
            if callable(getter):
                try:
                    value = self._normalize_log_value(getter())
                    if value:
                        return value
                except Exception as error:
                    _log_ignored_error("LoggingMixin._widget_caption", error)

        caption = self._find_caption_in_parent_layout(widget)
        if caption:
            return caption

        return widget.__class__.__name__

    def _find_caption_in_parent_layout(self, widget: QWidget) -> str:
        current = widget
        for _ in range(3):
            parent = current.parentWidget() if hasattr(current, "parentWidget") else None
            if parent is None:
                break
            layout = parent.layout() if hasattr(parent, "layout") else None
            if layout is not None:
                caption = self._find_caption_in_layout(layout, current)
                if caption:
                    return caption
            current = parent
        return ""

    def _find_caption_in_layout(self, layout, target: QWidget) -> str:
        target_index = -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            if item.widget() is target:
                target_index = i
                break
            child_layout = item.layout()
            if child_layout is not None:
                nested = self._find_caption_in_layout(child_layout, target)
                if nested:
                    return nested
        if target_index < 0:
            return ""

        for i in range(target_index - 1, -1, -1):
            item = layout.itemAt(i)
            if item is None:
                continue
            sibling = item.widget()
            if sibling is None:
                continue
            if isinstance(sibling, QAbstractButton):
                continue
            text = self._extract_widget_text(sibling)
            if text:
                return text
        return ""

    def _extract_widget_text(self, widget: QWidget) -> str:
        for attr in ("text", "title", "placeholderText"):
            getter = getattr(widget, attr, None)
            if callable(getter):
                try:
                    value = self._normalize_log_value(getter())
                    if value:
                        return value.rstrip(":")
                except Exception as error:
                    _log_ignored_error("LoggingMixin._extract_widget_text", error)
        return ""

    def _log_button_action(self, widget: QAbstractButton):
        if not self._is_action_logging_ready():
            return
        caption = self._widget_caption(widget)
        if caption:
            self.log_event(f"Нажата кнопка: {caption}")

    def _log_checkbox_action(self, widget: QCheckBox, checked: bool):
        if not self._is_action_logging_ready():
            return
        caption = self._widget_caption(widget)
        state = "включено" if checked else "выключено"
        self.log_event(f"Переключен флажок: {caption} -> {state}")

    def _log_combo_action(self, widget: QComboBox, text: str):
        if not self._is_action_logging_ready():
            return
        value = self._normalize_log_value(text)
        if not value:
            return
        last_value = self._normalize_log_value(widget.property("_last_logged_value"))
        if value == last_value:
            return
        widget.setProperty("_last_logged_value", text)
        caption = self._widget_caption(widget)
        self.log_event(f"Изменен список: {caption} -> {value}")

    def _log_line_edit_action(self, widget: QLineEdit):
        if not self._is_action_logging_ready():
            return
        value = self._normalize_log_value(widget.text())
        last_value = self._normalize_log_value(widget.property("_last_logged_value"))
        if value == last_value:
            return
        widget.setProperty("_last_logged_value", widget.text())
        caption = self._widget_caption(widget)
        self.log_event(f"Изменено поле: {caption} -> {value}")

    def _log_spin_action(self, widget: QSpinBox, value: int):
        if not self._is_action_logging_ready():
            return
        last_value = widget.property("_last_logged_value")
        if last_value == value:
            return
        widget.setProperty("_last_logged_value", value)
        caption = self._widget_caption(widget)
        self.log_event(f"Изменено числовое поле: {caption} -> {value}")

    def _log_tab_action(self, widget: QTabBar, index: int):
        if not self._is_action_logging_ready() or index < 0:
            return
        try:
            caption = self._normalize_log_value(widget.tabText(index))
        except Exception:
            caption = ""
        if caption:
            self.log_event(f"Открыта вкладка: {caption}")

    def _log_list_navigation_action(self, _widget: QListWidget, text: str):
        if not self._is_action_logging_ready():
            return
        value = self._normalize_log_value(text)
        if value:
            self.log_event(f"Открыт раздел настроек: {value}")

    @pyqtSlot(str)
    def _append_log_line(self, line: str):
        if not self.logs_view:
            return
        has_filters = hasattr(self, "logs_search_input") and self.logs_search_input is not None
        if has_filters:
            query = (self.logs_search_input.text() or "").strip()
            level_filter_active = False
            if hasattr(self, "_logs_level_actions") and self._logs_level_actions:
                all_levels = set(self._logs_level_actions.keys())
                selected = {k for k, a in self._logs_level_actions.items() if a.isChecked()}
                level_filter_active = bool(all_levels) and selected != all_levels
            if query or level_filter_active:
                try:
                    self._apply_logs_filters()
                    return
                except Exception as error:
                    _log_ignored_error("LoggingMixin._append_log_line", error)
        self.logs_view.appendPlainText(line)
        self.logs_view.moveCursor(QTextCursor.MoveOperation.End)

    def load_logs_into_view(self):
        if not self.logs_view:
            return
        log_path = self._log_file_path or self.get_log_file_path()
        lines = []
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
            except Exception:
                lines = []
        if self.max_log_lines and len(lines) > self.max_log_lines:
            lines = lines[-self.max_log_lines :]
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    if lines:
                        f.write("\n".join(lines) + "\n")
            except Exception as error:
                _log_ignored_error("LoggingMixin.load_logs_into_view", error)
        self._log_lines = list(lines)
        if hasattr(self, "_apply_logs_filters"):
            try:
                self._apply_logs_filters()
                return
            except Exception as error:
                _log_ignored_error("LoggingMixin.load_logs_into_view", error)
        self.logs_view.setPlainText("\n".join(lines))
        self.logs_view.moveCursor(QTextCursor.MoveOperation.End)

    def open_logs_file(self):
        log_path = self._log_file_path or self.get_log_file_path()
        try:
            if not os.path.exists(log_path):
                with open(log_path, "a", encoding="utf-8"):
                    pass
            os.startfile(log_path)
            self.log_event(f"Открыт файл логов: {log_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть логи: {str(exc)}")
            self.log_event(f"Ошибка открытия логов: {str(exc)}", "ERROR")
