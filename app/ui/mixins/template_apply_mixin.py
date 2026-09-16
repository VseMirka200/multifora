import os
import re
from datetime import datetime

from PyQt6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QSpinBox, QTextEdit

import app.core.rename_templates as rt
from app.ui.ui_components import setup_standard_dropdown
from app.core.app_utils import _log_ignored_error


class TemplateApplyMixin:
    # Применяет параметры шаблона к именам для предпросмотра и последующего переименования.
    def on_template_selected(self, template_name):
        """Обработчик выбора шаблона"""
        if template_name == "Выберите шаблон...":
            self.template_params_widget.setVisible(False)
            if hasattr(self, "btn_apply_rename"):
                self.btn_apply_rename.setEnabled(False)
            self.status_bar.showMessage("")
            if callable(getattr(self, "_schedule_settings_save", None)):
                self._schedule_settings_save()
            return

        self.current_template = template_name

        self.clear_template_params_container()

        if template_name == "Добавить текст в начало":
            self.create_add_prefix_params()
        elif template_name == "Добавить текст в конец":
            self.create_add_suffix_params()
        elif template_name == "Удалить символы с начала":
            self.create_remove_start_params()
        elif template_name == "Удалить символы с конца":
            self.create_remove_end_params()
        elif template_name == "Удалить определенный текст":
            self.create_remove_text_params()
        elif template_name == "Заменить текст другим":
            self.create_replace_text_params()
        elif template_name == "Регулярное выражение":
            self.create_regex_replace_params()
        elif template_name == "Изменить регистр":
            self.create_case_params()
        elif template_name == "Нумерация":
            self.create_numbering_params()
        elif template_name == "Дата в начале названия":
            self.create_date_original_params()
        elif template_name == "Пользовательский шаблон":
            self.create_custom_template_params()

        self.template_params_widget.setVisible(True)
        self._apply_template_params_theme()
        self._connect_template_param_preview_signals()
        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(self.template_params_widget)
        self.refresh_rename_preview()
        self.status_bar.showMessage(f"Выбран шаблон: {template_name}")
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()

        self.adjust_rename_group_height()

    def apply_template_logic(self):
        """Логика применения шаблона"""
        self._rename_template_error = ""
        current_num = 1
        step = 1
        use_numbering = True
        num_digits = 3

        numbering_mode = self.current_template
        if self.current_template == "Нумерация":
            numbering_mode = self.get_numbering_mode() if hasattr(self, "get_numbering_mode") else "Простая нумерация"

        if numbering_mode == "Простая нумерация":
            current_num = self.template_num_start.value() if hasattr(self, "template_num_start") else 1
            step = self.template_num_step.value() if hasattr(self, "template_num_step") else 1
            num_digits = self.template_num_digits.value() if hasattr(self, "template_num_digits") else 3
        elif numbering_mode == "Нумерация с префиксом":
            current_num = self.template_prefix_start.value() if hasattr(self, "template_prefix_start") else 1
            step = self.template_prefix_step.value() if hasattr(self, "template_prefix_step") else 1
            num_digits = self.template_prefix_digits.value() if hasattr(self, "template_prefix_digits") else 3
        elif numbering_mode == "Нумерация с датой":
            current_num = self.template_date_start.value() if hasattr(self, "template_date_start") else 1
            step = self.template_date_step.value() if hasattr(self, "template_date_step") else 1
            num_digits = self.template_date_digits.value() if hasattr(self, "template_date_digits") else 3
        elif self.current_template == "Пользовательский шаблон":
            template = self.template_custom.text() if hasattr(self, "template_custom") else ""
            custom_settings = rt.parse_custom_template_settings(template)
            use_numbering = bool(custom_settings.get("use_numbering", False))
            current_num = int(custom_settings.get("start", 1))
            step = int(custom_settings.get("step", 1))
            num_digits = int(custom_settings.get("digits", 3))

        initial_num = current_num
        numbering_active = numbering_mode in {
            "Простая нумерация",
            "Нумерация с префиксом",
            "Нумерация с датой",
        } or (self.current_template == "Пользовательский шаблон" and use_numbering)
        scope_widget = getattr(self, "rename_numbering_scope_combo", None)
        numbering_scope = (
            str(scope_widget.currentData() or "global")
            if scope_widget is not None
            else "global"
        )
        folder_counters: dict[str, int] = {}

        for i, file_item in enumerate(self.files):
            folder_key = os.path.normcase(
                os.path.abspath(str(getattr(file_item, "folder", "")))
            )
            if numbering_active and numbering_scope == "per_folder":
                current_num = folder_counters.get(folder_key, initial_num)

            old_name = file_item.name
            name_without_ext, ext = os.path.splitext(old_name)
            new_name = old_name

            if self.current_template == "Добавить текст в начало":
                prefix = getattr(self, "template_prefix", QLineEdit("")).text()
                new_name = f"{prefix}{old_name}"

            elif self.current_template == "Добавить текст в конец":
                suffix = getattr(self, "template_suffix", QLineEdit("")).text()
                new_name = f"{name_without_ext}{suffix}{ext}"

            elif self.current_template == "Удалить символы с начала":
                remove_chars = getattr(self, "template_remove_start", QSpinBox()).value()
                new_name = (
                    f"{name_without_ext[remove_chars:]}{ext}"
                    if len(name_without_ext) > remove_chars
                    else old_name
                )

            elif self.current_template == "Удалить символы с конца":
                remove_chars = getattr(self, "template_remove_end", QSpinBox()).value()
                new_name = (
                    f"{name_without_ext[:-remove_chars]}{ext}"
                    if len(name_without_ext) > remove_chars
                    else old_name
                )

            elif self.current_template == "Удалить определенный текст":
                text_to_remove = getattr(self, "template_remove_text", QLineEdit("")).text()
                new_name = old_name.replace(text_to_remove, "") if text_to_remove else old_name

            elif self.current_template == "Заменить текст другим":
                find_text = getattr(self, "template_find", QLineEdit("")).text()
                replace_text = getattr(self, "template_replace", QLineEdit("")).text()
                new_name = old_name.replace(find_text, replace_text) if find_text else old_name

            elif self.current_template == "Регулярное выражение":
                pattern = getattr(self, "template_regex_pattern", QLineEdit("")).text()
                replacement = getattr(self, "template_regex_replace", QLineEdit("")).text()
                ignore_case = bool(
                    getattr(
                        getattr(self, "template_regex_ignore_case", None),
                        "isChecked",
                        lambda: False,
                    )()
                )
                if pattern:
                    try:
                        new_stem = rt.regex_replace(
                            name_without_ext,
                            pattern,
                            replacement,
                            ignore_case=ignore_case,
                        )
                        new_name = f"{new_stem}{ext}"
                    except re.error as error:
                        self._rename_template_error = f"Ошибка регулярного выражения: {error}"

            elif self.current_template == "Изменить регистр":
                mode_widget = getattr(self, "template_case_mode", None)
                mode = str(mode_widget.currentData() or "") if mode_widget is not None else ""
                new_name = f"{rt.apply_case_mode(name_without_ext, mode)}{ext}"

            elif numbering_mode == "Простая нумерация":
                num_str = f"{current_num:0{num_digits}d}"
                sep = getattr(self, "template_num_sep", QLineEdit("_")).text()
                new_name = f"{num_str}{sep}{old_name}"
                current_num += step

            elif numbering_mode == "Нумерация с префиксом":
                prefix = getattr(self, "template_prefix_text", QLineEdit("фото_")).text()
                num_str = f"{current_num:0{num_digits}d}"
                new_name = f"{prefix}{num_str}{ext}"
                current_num += step

            elif numbering_mode == "Нумерация с датой":
                date_format_name = getattr(self, "template_date_format", QComboBox()).currentText()
                date_str = datetime.now().strftime(rt.get_date_format(date_format_name))
                num_str = f"{current_num:0{num_digits}d}"
                new_name = f"{date_str}_{num_str}{ext}"
                current_num += step

            elif self.current_template == "Дата в начале названия":
                date_format_name = getattr(self, "template_original_date_format", QComboBox()).currentText()
                date_str = datetime.now().strftime(rt.get_date_format(date_format_name))
                new_name = f"{date_str}{old_name}"

            elif self.current_template == "Пользовательский шаблон":
                if hasattr(self, "template_custom"):
                    template = self.template_custom.text()
                    if template:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                        new_name, current_num = rt.apply_custom_template(
                            template,
                            name_without_ext,
                            ext,
                            current_num,
                            date_str,
                            step,
                            use_numbering,
                            num_digits,
                            file_path=file_item.path,
                        )

            file_item.preview_name = new_name
            if numbering_active and numbering_scope == "per_folder":
                folder_counters[folder_key] = current_num

        self.list_files.refresh()

        self.status_bar.showMessage(f"Применен шаблон: {self.current_template}")

    def _connect_template_param_preview_signals(self):
        """Подключает автопредпросмотр для динамических параметров шаблона."""
        container = getattr(self, "template_params_widget", None)
        if container is None:
            return

        for field in container.findChildren(QLineEdit):
            field.textChanged.connect(lambda _value, self=self: self.refresh_rename_preview())
            field.textChanged.connect(lambda _value, self=self: self._schedule_settings_save())
        for field in container.findChildren(QTextEdit):
            field.textChanged.connect(lambda *_args, self=self: self.refresh_rename_preview())
            field.textChanged.connect(lambda *_args, self=self: self._schedule_settings_save())
        for field in container.findChildren(QSpinBox):
            field.valueChanged.connect(lambda _value, self=self: self.refresh_rename_preview())
            field.valueChanged.connect(lambda _value, self=self: self._schedule_settings_save())
        for field in container.findChildren(QComboBox):
            field.currentIndexChanged.connect(lambda _value, self=self: self.refresh_rename_preview())
            field.currentIndexChanged.connect(lambda _value, self=self: self._schedule_settings_save())
        for field in container.findChildren(QCheckBox):
            field.stateChanged.connect(lambda _value, self=self: self.refresh_rename_preview())
            field.stateChanged.connect(lambda _value, self=self: self._schedule_settings_save())

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
                _log_ignored_error("TemplateApplyMixin._apply_template_params_theme", error)
            try:
                setup_standard_dropdown(combo)
            except Exception as error:
                _log_ignored_error("TemplateApplyMixin._apply_template_params_theme", error)
