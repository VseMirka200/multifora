from PySide6.QtWidgets import QMessageBox

from app.core.app_utils import _log_ignored_error


class TemplateParamsBaseMixin:
    def update_template_combo(self):
        """Заполняет список правил переименования."""
        self.combo_templates.clear()

        standard_templates = [
            "Добавить текст",
            "Удалить символы",
            "Удалить определенный текст",
            "Заменить текст другим",
            "Изменить регистр",
            "Нумерация",
            "Дата в начале названия",
        ]

        self.combo_templates.addItems(standard_templates)
        metrics = self.combo_templates.menu().fontMetrics()
        self.combo_templates.setFixedWidth(max(metrics.horizontalAdvance(name) for name in standard_templates) + 64)

    def get_template_session_state(self):
        """Возвращает текущее состояние выбранного шаблона для восстановления сессии."""
        template_name = ""
        if (
            hasattr(self, "combo_templates")
            and self.combo_templates is not None
        ):
            try:
                template_name = self.combo_templates.currentText().strip()
            except Exception:
                template_name = ""
        if not template_name:
            return {"selected_template": "", "template_data": {}}

        template_data = self.get_current_template_data() or {}
        return {
            "selected_template": template_name,
            "template_data": template_data,
        }

    def restore_template_session_state(self, state):
        """Восстанавливает выбранный шаблон и его параметры после запуска."""
        if not isinstance(state, dict):
            return

        template_name = str(state.get("selected_template") or "").strip()
        if not template_name:
            return
        if (
            not hasattr(self, "combo_templates")
            or self.combo_templates is None
        ):
            return

        template_data = state.get("template_data")
        if not isinstance(template_data, dict):
            template_data = {}

        legacy_rule = {
            "добавить текст в начало": ("Добавить текст", "start", "text", "prefix", "префикс_"),
            "добавить текст в конец": ("Добавить текст", "end", "text", "suffix", "_суффикс"),
            "удалить символы с начала": ("Удалить символы", "start", "count", "remove_start", 1),
            "удалить символы с конца": ("Удалить символы", "end", "count", "remove_end", 1),
        }.get(template_name.casefold())
        if legacy_rule is not None:
            template_name, position, field, old_field, default = legacy_rule
            template_data = {"position": position, field: template_data.get(old_field, default)}

        index = self.combo_templates.findText(template_name)
        if index < 0:
            try:
                normalized_name = template_name.strip().casefold()
                for idx, (item_text, _item_data) in enumerate(
                    getattr(self.combo_templates, "_items", [])
                ):
                    if str(item_text).strip().casefold() == normalized_name:
                        index = idx
                        break
            except Exception as error:
                _log_ignored_error(
                    "TemplateParamsBaseMixin.restore_template_session_state", error
                )
        if index < 0:
            return

        self.combo_templates.setCurrentIndex(index)
        if template_data:
            self.apply_template_data(self.combo_templates.currentText(), template_data)
        if callable(getattr(self, "refresh_rename_preview", None)):
            self.refresh_rename_preview()

    def get_current_template_data(self):
        """Получает данные текущего шаблона"""
        template_data = {}

        if self.current_template == "Добавить текст":
            if hasattr(self, "template_add_text"):
                template_data["position"] = self.template_add_position.currentData()
                template_data["text"] = self.template_add_text.text()
            else:
                return None

        elif self.current_template == "Удалить символы":
            if hasattr(self, "template_remove_count"):
                template_data["position"] = self.template_remove_position.currentData()
                template_data["count"] = self.template_remove_count.value()
            else:
                return None

        elif self.current_template == "Удалить определенный текст":
            if hasattr(self, "template_remove_text"):
                template_data["remove_text"] = self.template_remove_text.text()
            else:
                return None

        elif self.current_template == "Заменить текст другим":
            if hasattr(self, "template_find") and hasattr(
                self, "template_replace"
            ):
                template_data["find"] = self.template_find.text()
                template_data["replace"] = self.template_replace.text()
            else:
                return None

        elif self.current_template == "Изменить регистр":
            if hasattr(self, "template_case_mode"):
                template_data["case_mode"] = (
                    self.template_case_mode.currentData() or "lower"
                )
            else:
                return None

        elif self.current_template == "Нумерация":
            if hasattr(self, "get_numbering_mode"):
                template_data["numbering_mode"] = self.get_numbering_mode()
            else:
                template_data["numbering_mode"] = "Простая нумерация"

            mode = template_data["numbering_mode"]
            if mode == "Простая нумерация":
                if hasattr(self, "template_num_start"):
                    template_data["start"] = self.template_num_start.value()
                    template_data["step"] = self.template_num_step.value()
                    template_data["digits"] = self.template_num_digits.value()
                    template_data["separator"] = self.template_num_sep.text()
                else:
                    return None
            elif mode == "Нумерация с префиксом":
                if hasattr(self, "template_prefix_text"):
                    template_data["prefix"] = self.template_prefix_text.text()
                    template_data["start"] = self.template_prefix_start.value()
                    template_data["step"] = self.template_prefix_step.value()
                    template_data["digits"] = (
                        self.template_prefix_digits.value()
                    )
                else:
                    return None
            elif mode == "Нумерация с датой":
                if hasattr(self, "template_date_format"):
                    template_data["date_format"] = (
                        self.template_date_format.currentIndex()
                    )
                    template_data["start"] = self.template_date_start.value()
                    template_data["step"] = self.template_date_step.value()
                    template_data["digits"] = self.template_date_digits.value()
                else:
                    return None

        elif self.current_template == "Дата в начале названия":
            if hasattr(self, "template_original_date_format"):
                template_data["date_format"] = (
                    self.template_original_date_format.currentIndex()
                )
            else:
                return None

        return template_data

    def apply_template_data(self, template_type, data):
        """Применяет данные шаблона к виджетам"""
        try:
            if template_type == "Добавить текст":
                index = self.template_add_position.findData(data.get("position", "start"))
                self.template_add_position.setCurrentIndex(max(0, index))
                text = data.get("text")
                if isinstance(text, str):
                    self.template_add_text.setText(text)

            elif template_type == "Удалить символы":
                index = self.template_remove_position.findData(data.get("position", "start"))
                self.template_remove_position.setCurrentIndex(max(0, index))
                count = data.get("count", 1)
                if isinstance(count, int):
                    field = self.template_remove_count
                    field.setValue(max(field.minimum(), min(count, field.maximum())))

            elif template_type == "Удалить определенный текст":
                if hasattr(self, "template_remove_text"):
                    self.template_remove_text.setText(
                        data.get("remove_text", "")
                    )

            elif template_type == "Заменить текст другим":
                if hasattr(self, "template_find") and hasattr(
                    self, "template_replace"
                ):
                    self.template_find.setText(data.get("find", ""))
                    self.template_replace.setText(data.get("replace", ""))

            elif template_type == "Изменить регистр":
                if hasattr(self, "template_case_mode"):
                    index = self.template_case_mode.findData(
                        data.get("case_mode", "lower")
                    )
                    self.template_case_mode.setCurrentIndex(max(0, index))

            elif template_type in (
                "Нумерация",
                "Простая нумерация",
                "Нумерация с префиксом",
                "Нумерация с датой",
            ):
                numbering_mode = data.get("numbering_mode", template_type)
                if hasattr(self, "set_numbering_mode"):
                    self.set_numbering_mode(numbering_mode)

                if numbering_mode == "Простая нумерация":
                    if hasattr(self, "template_num_start"):
                        self.template_num_start.setValue(data.get("start", 1))
                        self.template_num_step.setValue(data.get("step", 1))
                        self.template_num_digits.setValue(
                            data.get("digits", 3)
                        )
                        self.template_num_sep.setText(
                            data.get("separator", "_")
                        )

                elif numbering_mode == "Нумерация с префиксом":
                    if hasattr(self, "template_prefix_text"):
                        self.template_prefix_text.setText(
                            data.get("prefix", "фото_")
                        )
                        self.template_prefix_start.setValue(
                            data.get("start", 1)
                        )
                        self.template_prefix_step.setValue(data.get("step", 1))
                        self.template_prefix_digits.setValue(
                            data.get("digits", 3)
                        )

                elif numbering_mode == "Нумерация с датой" and hasattr(
                    self, "template_date_format"
                ):
                    self.template_date_format.setCurrentIndex(
                        data.get("date_format", 0)
                    )
                    self.template_date_start.setValue(data.get("start", 1))
                    self.template_date_step.setValue(data.get("step", 1))
                    self.template_date_digits.setValue(data.get("digits", 3))

            elif template_type == "Дата в начале названия" and hasattr(
                self, "template_original_date_format"
            ):
                self.template_original_date_format.setCurrentIndex(
                    data.get("date_format", 0)
                )

        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка", f"Не удалось восстановить параметры правила: {e!s}"
            )

    def clear_template_params_container(self):
        """Очищает контейнер с параметрами шаблона"""
        while self.template_params_layout.count():
            item = self.template_params_layout.takeAt(0)
            if widget := item.widget():
                widget.hide()
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        """Рекурсивно очищает layout и все его виджеты"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())
                    item.layout().deleteLater()
