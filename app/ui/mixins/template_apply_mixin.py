import os
from datetime import datetime

from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QSpinBox,
)

import app.core.rename_templates as rt
from app.core.app_utils import _log_ignored_error
from app.ui.ui_components import setup_standard_dropdown
from app.ui.ui_styles import DROPDOWN_HEIGHT


class TemplateApplyMixin:
    # Применяет параметры шаблона к именам для предпросмотра и последующего переименования.
    def on_template_selected(self, template_name):
        """Обработчик выбора шаблона"""
        self.current_template = template_name

        self.clear_template_params_container()

        if template_name == "Добавить текст":
            self.create_add_text_params()
        elif template_name == "Удалить символы":
            self.create_remove_chars_params()
        elif template_name == "Удалить определенный текст":
            self.create_remove_text_params()
        elif template_name == "Заменить текст другим":
            self.create_replace_text_params()
        elif template_name == "Изменить регистр":
            self.create_case_params()
        elif template_name == "Нумерация":
            self.create_numbering_params()
        elif template_name == "Дата в начале названия":
            self.create_date_original_params()

        for spinbox in self.template_params_widget.findChildren(QSpinBox):
            spinbox.setFixedHeight(DROPDOWN_HEIGHT)
        for field in self.template_params_widget.findChildren(QLineEdit):
            if field.property("renameTemplateField"):
                field.setFixedHeight(DROPDOWN_HEIGHT)
                field.setTextMargins(5, 0, 5, 0)

        self.template_params_widget.setVisible(True)
        self._apply_template_params_theme()
        self._connect_template_param_preview_signals()
        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(self.template_params_widget)
        self.refresh_rename_preview()
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()

    def apply_template_logic(self):
        """Логика применения шаблона"""
        self._rename_template_error = ""
        current_num = 1
        step = 1
        num_digits = 3

        numbering_mode = self.current_template
        if self.current_template == "Нумерация":
            numbering_mode = (
                self.get_numbering_mode()
                if hasattr(self, "get_numbering_mode")
                else "Простая нумерация"
            )

        if numbering_mode == "Простая нумерация":
            current_num = (
                self.template_num_start.value()
                if hasattr(self, "template_num_start")
                else 1
            )
            step = (
                self.template_num_step.value()
                if hasattr(self, "template_num_step")
                else 1
            )
            num_digits = (
                self.template_num_digits.value()
                if hasattr(self, "template_num_digits")
                else 3
            )
        elif numbering_mode == "Нумерация с префиксом":
            current_num = (
                self.template_prefix_start.value()
                if hasattr(self, "template_prefix_start")
                else 1
            )
            step = (
                self.template_prefix_step.value()
                if hasattr(self, "template_prefix_step")
                else 1
            )
            num_digits = (
                self.template_prefix_digits.value()
                if hasattr(self, "template_prefix_digits")
                else 3
            )
        elif numbering_mode == "Нумерация с датой":
            current_num = (
                self.template_date_start.value()
                if hasattr(self, "template_date_start")
                else 1
            )
            step = (
                self.template_date_step.value()
                if hasattr(self, "template_date_step")
                else 1
            )
            num_digits = (
                self.template_date_digits.value()
                if hasattr(self, "template_date_digits")
                else 3
            )
        for file_item in self.files:
            self.list_files.model().preview_for(file_item).preview_name = file_item.name
        resolver = getattr(self, "_preview_operation_items", None)
        files = resolver() if callable(resolver) else self.files
        for file_item in files:
            old_name = file_item.name
            name_without_ext, ext = os.path.splitext(old_name)
            new_name = old_name

            if self.current_template == "Добавить текст":
                text = self.template_add_text.text()
                if self.template_add_position.currentData() == "end":
                    new_name = f"{name_without_ext}{text}{ext}"
                else:
                    new_name = f"{text}{old_name}"

            elif self.current_template == "Удалить символы":
                count = self.template_remove_count.value()
                if len(name_without_ext) > count:
                    if self.template_remove_position.currentData() == "end":
                        new_name = f"{name_without_ext[:-count]}{ext}"
                    else:
                        new_name = f"{name_without_ext[count:]}{ext}"

            elif self.current_template == "Удалить определенный текст":
                text_to_remove = getattr(
                    self, "template_remove_text", QLineEdit("")
                ).text()
                new_name = (
                    old_name.replace(text_to_remove, "")
                    if text_to_remove
                    else old_name
                )

            elif self.current_template == "Заменить текст другим":
                find_text = getattr(
                    self, "template_find", QLineEdit("")
                ).text()
                replace_text = getattr(
                    self, "template_replace", QLineEdit("")
                ).text()
                new_name = (
                    old_name.replace(find_text, replace_text)
                    if find_text
                    else old_name
                )

            elif self.current_template == "Изменить регистр":
                mode_widget = getattr(self, "template_case_mode", None)
                mode = (
                    str(mode_widget.currentData() or "")
                    if mode_widget is not None
                    else ""
                )
                new_name = f"{rt.apply_case_mode(name_without_ext, mode)}{ext}"

            elif numbering_mode == "Простая нумерация":
                num_str = f"{current_num:0{num_digits}d}"
                sep = getattr(self, "template_num_sep", QLineEdit("_")).text()
                new_name = f"{num_str}{sep}{old_name}"
                current_num += step

            elif numbering_mode == "Нумерация с префиксом":
                prefix = getattr(
                    self, "template_prefix_text", QLineEdit("фото_")
                ).text()
                num_str = f"{current_num:0{num_digits}d}"
                new_name = f"{prefix}{num_str}{ext}"
                current_num += step

            elif numbering_mode == "Нумерация с датой":
                date_format_name = getattr(
                    self, "template_date_format", QComboBox()
                ).currentText()
                date_str = datetime.now().strftime(
                    rt.get_date_format(date_format_name)
                )
                num_str = f"{current_num:0{num_digits}d}"
                new_name = f"{date_str}_{num_str}{ext}"
                current_num += step

            elif self.current_template == "Дата в начале названия":
                date_format_name = getattr(
                    self, "template_original_date_format", QComboBox()
                ).currentText()
                date_str = datetime.now().strftime(
                    rt.get_date_format(date_format_name)
                )
                new_name = f"{date_str}{old_name}"

            self.list_files.model().preview_for(file_item).preview_name = new_name

        self.status_bar.showMessage(
            f"Применено правило: {self.current_template}"
        )

    def _connect_template_param_preview_signals(self):
        """Подключает автопредпросмотр для динамических параметров шаблона."""
        container = getattr(self, "template_params_widget", None)
        if container is None:
            return

        for field in container.findChildren(QLineEdit):
            field.textChanged.connect(
                lambda _value, self=self: self.refresh_rename_preview()
            )
            field.textChanged.connect(
                lambda _value, self=self: self._schedule_settings_save()
            )
        for field in container.findChildren(QSpinBox):
            field.valueChanged.connect(
                lambda _value, self=self: self.refresh_rename_preview()
            )
            field.valueChanged.connect(
                lambda _value, self=self: self._schedule_settings_save()
            )
        for field in container.findChildren(QComboBox):
            field.currentIndexChanged.connect(
                lambda _value, self=self: self.refresh_rename_preview()
            )
            field.currentIndexChanged.connect(
                lambda _value, self=self: self._schedule_settings_save()
            )

    def _apply_template_params_theme(self):
        """Применяет текущую тему к динамически созданным полям шаблона."""
        container = getattr(self, "template_params_widget", None)
        if container is None:
            return

        mode = getattr(self, "_effective_theme_mode", "dark")
        for combo in container.findChildren(QComboBox):
            try:
                combo._effective_theme_mode = mode
            except Exception as error:
                _log_ignored_error(
                    "TemplateApplyMixin._apply_template_params_theme", error
                )
            try:
                setup_standard_dropdown(combo)
            except Exception as error:
                _log_ignored_error(
                    "TemplateApplyMixin._apply_template_params_theme", error
                )
