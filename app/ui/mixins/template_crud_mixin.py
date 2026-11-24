from datetime import datetime

from PySide6.QtCore import QModelIndex, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.app_utils import _log_ignored_error
from app.ui.ui_components import (
    IconButton,
    StandardPopupMenu,
    get_russian_text_input,
    setup_standard_dialog,
    setup_standard_primary_button,
    setup_standard_secondary_button,
)
from app.ui.ui_icons import UI_ICON_SIZE
from app.ui.ui_styles import DIALOG_MARGINS, MARGINS_NONE, SPACE_SM, build_template_table_style


class TemplateCrudMixin:
    # Управляет пользовательскими шаблонами и их отображением в менеджере.
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
        if not template_name or template_name in ("Выбрать правило", "Выберите шаблон..."):
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
        if not template_name or template_name in ("Выбрать правило", "Выберите шаблон..."):
            return
        if (
            not hasattr(self, "combo_templates")
            or self.combo_templates is None
        ):
            return

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
                    "TemplateCrudMixin.restore_template_session_state", error
                )
        if index < 0:
            return

        template_data = state.get("template_data")
        if not isinstance(template_data, dict):
            template_data = {}

        self.combo_templates.setCurrentIndex(index)
        if template_data:
            self.apply_template_data(template_name, template_data)
        if callable(getattr(self, "refresh_rename_preview", None)):
            self.refresh_rename_preview()

    def _get_effective_theme_mode_for_templates(self):
        mode = getattr(self, "theme_mode", "system")
        effective = mode
        if mode == "system":
            try:
                effective = self._get_system_theme_mode()
            except Exception:
                effective = getattr(self, "_effective_theme_mode", "dark")
        return "light" if str(effective).lower() == "light" else "dark"

    def _templates_table_stylesheet(self):
        return build_template_table_style(
            self._get_effective_theme_mode_for_templates()
        )

    def _get_selected_template_name(self):
        if (
            not hasattr(self, "templates_table")
            or self.templates_table is None
        ):
            return ""
        try:
            row = self.templates_table.currentRow()
            if row < 0:
                return ""
            item = self.templates_table.item(row, 0)
            if item is None:
                return ""
            stored_name = item.data(Qt.ItemDataRole.UserRole)
            if stored_name:
                return str(stored_name).strip()
            return item.text().strip()
        except Exception:
            return ""

    def _rename_selected_template(self, parent_window=None):
        template_name = self._get_selected_template_name()
        if not template_name:
            QMessageBox.warning(
                self, "Ошибка", "Выберите шаблон для переименования!"
            )
            return

        new_name, ok = get_russian_text_input(
            self,
            title="Переименование шаблона",
            label="Новое имя шаблона:",
            text=template_name,
        )
        new_name = str(new_name or "").strip()
        if not ok or not new_name or new_name == template_name:
            return
        if new_name in self.custom_templates:
            QMessageBox.warning(
                self, "Ошибка", f"Шаблон '{new_name}' уже существует!"
            )
            return

        template_payload = self.custom_templates.get(template_name)
        if template_payload is None:
            QMessageBox.warning(
                self, "Ошибка", f"Шаблон '{template_name}' не найден!"
            )
            return

        reordered_templates = {}
        for name, data in self.custom_templates.items():
            reordered_templates[
                new_name if name == template_name else name
            ] = data
        self.custom_templates = reordered_templates
        self.save_settings()
        self.update_templates_table(parent_window)

        try:
            for row in range(self.templates_table.rowCount()):
                item = self.templates_table.item(row, 0)
                if (
                    item is not None
                    and item.data(Qt.ItemDataRole.UserRole) == new_name
                ):
                    self.templates_table.selectRow(row)
                    self.templates_table.setCurrentCell(row, 0)
                    break
        except Exception as error:
            _log_ignored_error(
                "TemplateCrudMixin._rename_selected_template", error
            )
        self.status_bar.showMessage(
            f"Шаблон переименован: {template_name} -> {new_name}"
        )

    def _show_templates_context_menu(self, pos, parent_window=None):
        index = self.templates_table.indexAt(pos)
        if index.isValid():
            self.templates_table.selectRow(index.row())
            self.templates_table.setCurrentCell(index.row(), 0)

        template_name = self._get_selected_template_name()
        if not template_name:
            return

        menu = StandardPopupMenu(theme_widget=self)
        action_apply = menu.add_command("Применить", icon_name="check-document")
        action_rename = menu.add_command("Переименовать", icon_name="rename")
        action_delete = menu.add_command("Удалить", icon_name="remove")

        selected_action = menu.exec(
            self.templates_table.viewport().mapToGlobal(pos)
        )
        if selected_action == action_apply:
            self.load_selected_template(parent_window)
        elif selected_action == action_rename:
            self._rename_selected_template(parent_window)
        elif selected_action == action_delete:
            self.delete_selected_template(parent_window)

    def save_current_template(self):
        """Сохранение текущего шаблона как пользовательского"""
        if not self.current_template:
            QMessageBox.warning(
                self, "Ошибка", "Сначала выберите и настройте шаблон!"
            )
            return

        template_data = self.get_current_template_data()
        if not template_data:
            return

        name, ok = get_russian_text_input(
            self,
            title="Сохранение шаблона",
            label="Введите имя для шаблона:",
            text=f"Мой шаблон {len(self.custom_templates) + 1}",
        )

        if ok and name:
            self.custom_templates[name] = {
                "type": self.current_template,
                "data": template_data,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.save_settings()
            QMessageBox.information(
                self, "Успех", f"Шаблон '{name}' сохранен!"
            )

    def get_current_template_data(self):
        """Получает данные текущего шаблона"""
        template_data = {}

        if self.current_template == "Добавить текст в начало":
            if hasattr(self, "template_prefix"):
                template_data["prefix"] = self.template_prefix.text()
            else:
                return None

        elif self.current_template == "Добавить текст в конец":
            if hasattr(self, "template_suffix"):
                template_data["suffix"] = self.template_suffix.text()
            else:
                return None

        elif self.current_template == "Удалить символы с начала":
            if hasattr(self, "template_remove_start"):
                template_data["remove_start"] = (
                    self.template_remove_start.value()
                )
            else:
                return None

        elif self.current_template == "Удалить символы с конца":
            if hasattr(self, "template_remove_end"):
                template_data["remove_end"] = self.template_remove_end.value()
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

        elif self.current_template == "Пользовательский шаблон":
            if hasattr(self, "template_custom"):
                template_data["template"] = self.template_custom.text()
            else:
                return None

        return template_data

    def load_selected_template(self, parent_window=None):
        """Загрузка выбранного шаблона из таблицы"""
        selected_rows = self.templates_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "Ошибка", "Выберите шаблон для загрузки!"
            )
            return

        row = selected_rows[0].row()
        template_item = self.templates_table.item(row, 0)
        template_name = (
            template_item.data(Qt.ItemDataRole.UserRole)
            if template_item is not None
            else ""
        )
        template_name = str(template_name).strip() if template_name else ""
        self.load_template(template_name)
        if parent_window:
            parent_window.accept()

    def load_template(self, template_name):
        """Загрузка шаблона по имени"""
        if template_name not in self.custom_templates:
            QMessageBox.warning(
                self, "Ошибка", f"Шаблон '{template_name}' не найден!"
            )
            return

        template_data = self.custom_templates[template_name]
        template_type = template_data["type"]
        index = self.combo_templates.findText(template_type)
        if index >= 0:
            self.combo_templates.setCurrentIndex(index)

            QTimer.singleShot(
                100,
                lambda: self.apply_template_data(
                    template_type, template_data["data"]
                ),
            )

            self.status_bar.showMessage(f"Загружен шаблон: {template_name}")
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Тип шаблона '{template_type}' не поддерживается!",
            )

    def delete_selected_template(self, parent_window=None):
        """Удаление выбранного шаблона"""
        selected_rows = self.templates_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "Ошибка", "Выберите шаблон для удаления!"
            )
            return

        row = selected_rows[0].row()
        template_item = self.templates_table.item(row, 0)
        template_name = (
            template_item.data(Qt.ItemDataRole.UserRole)
            if template_item is not None
            else ""
        )
        template_name = str(template_name).strip() if template_name else ""

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Удалить шаблон '{template_name}'?",
            QMessageBox.Icon.Question,
            True,
            yes_text="Удалить",
            no_text="Отмена",
            destructive=True,
        )

        if reply:
            del self.custom_templates[template_name]
            self.update_templates_table(parent_window)
            self.save_settings()
            self.status_bar.showMessage(f"Шаблон '{template_name}' удален")

    def update_templates_table(self, parent_window=None):
        """Обновление таблицы шаблонов"""
        if hasattr(self, "templates_table") and self.templates_table:
            current_name = self._get_selected_template_name()
            self.templates_table.clearContents()
            self.templates_table.setRowCount(len(self.custom_templates))
            for row, (name, template) in enumerate(self.custom_templates.items()):
                name_item = QTableWidgetItem(name)
                name_item.setData(Qt.ItemDataRole.UserRole, name)
                name_item.setFlags(
                    name_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                )
                self.templates_table.setItem(row, 0, name_item)
                if self.templates_table.columnCount() > 1:
                    kind = template.get("type", "") if isinstance(template, dict) else ""
                    self.templates_table.setItem(row, 1, QTableWidgetItem(kind))
            empty_hint = getattr(self, "template_empty_hint", None)
            if empty_hint is not None:
                empty_hint.setVisible(not self.custom_templates)
            if current_name:
                for row in range(self.templates_table.rowCount()):
                    item = self.templates_table.item(row, 0)
                    if (
                        item is not None
                        and item.data(Qt.ItemDataRole.UserRole) == current_name
                    ):
                        self.templates_table.selectRow(row)
                        self.templates_table.setCurrentCell(row, 0)
                        break
                else:
                    self.templates_table.clearSelection()
                    self.templates_table.setCurrentIndex(QModelIndex())
            else:
                self.templates_table.clearSelection()
                self.templates_table.setCurrentIndex(QModelIndex())

    def _build_template_manager_action_buttons(self, dialog):
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(*MARGINS_NONE)
        actions_layout.setSpacing(SPACE_SM)

        export_btn = IconButton("Экспорт шаблонов", dialog)
        setup_standard_secondary_button(export_btn, expand=True, icon_name="export")
        export_btn.clicked.connect(self.export_templates)
        actions_layout.addWidget(export_btn, 1)

        import_btn = IconButton("Импорт шаблонов", dialog)
        setup_standard_secondary_button(import_btn, expand=True, icon_name="import")
        import_btn.clicked.connect(lambda: self.import_templates(dialog))
        actions_layout.addWidget(import_btn, 1)

        apply_btn = IconButton("Применить", dialog)
        setup_standard_primary_button(apply_btn, expand=True, icon_name="check-document")
        apply_btn.setEnabled(False)
        apply_btn.clicked.connect(lambda: self.load_selected_template(dialog))
        actions_layout.addWidget(apply_btn, 1)

        self.btn_apply_template = apply_btn

        return actions_layout

    def show_template_manager(self):
        """Показывает модальное окно управления шаблонами"""
        dialog = QDialog(self)
        setup_standard_dialog(
            dialog,
            title="Управление шаблонами",
            min_width=520,
            min_height=320,
        )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(SPACE_SM)

        description = QLabel("Сохранённые пользовательские шаблоны", dialog)
        description.setWordWrap(True)
        layout.addWidget(description)
        self.template_empty_hint = QLabel("Сохраните параметры на вкладке «Переименование» или импортируйте шаблон.")
        self.template_empty_hint.setWordWrap(True)
        layout.addWidget(self.template_empty_hint)

        self.templates_table = QTableWidget(dialog)
        self.templates_table.setObjectName("template_manager_table")
        self.templates_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.templates_table.setColumnCount(2)
        self.templates_table.setHorizontalHeaderLabels(["Шаблон", "Тип"])
        self.templates_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.templates_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.templates_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.templates_table.setAlternatingRowColors(True)
        self.templates_table.setShowGrid(False)
        self.templates_table.setAutoFillBackground(False)
        self.templates_table.setIconSize(UI_ICON_SIZE)
        self.templates_table.verticalHeader().setVisible(False)
        self.templates_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.templates_table.setStyleSheet(self._templates_table_stylesheet())
        header = self.templates_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(36)
        header.setFixedHeight(header.fontMetrics().height() + 4)
        self.templates_table.cellDoubleClicked.connect(
            lambda *_args: self.load_selected_template(dialog)
        )
        self.templates_table.customContextMenuRequested.connect(
            lambda pos: self._show_templates_context_menu(pos, dialog)
        )
        layout.addWidget(self.templates_table, 1)

        actions_layout = self._build_template_manager_action_buttons(dialog)
        layout.addLayout(actions_layout)

        def sync_actions():
            selected = bool(self.templates_table.selectionModel().selectedRows())
            self.btn_apply_template.setEnabled(selected)

        self.templates_table.itemSelectionChanged.connect(sync_actions)

        self._templates_apply_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Return), dialog
        )
        self._templates_apply_shortcut.activated.connect(
            lambda: self.load_selected_template(dialog)
        )
        self._templates_apply_shortcut_enter = QShortcut(
            QKeySequence(Qt.Key.Key_Enter), dialog
        )
        self._templates_apply_shortcut_enter.activated.connect(
            lambda: self.load_selected_template(dialog)
        )
        self._templates_delete_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Delete), dialog
        )
        self._templates_delete_shortcut.activated.connect(
            lambda: self.delete_selected_template(dialog)
        )
        self._templates_rename_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_F2), dialog
        )
        self._templates_rename_shortcut.activated.connect(
            lambda: self._rename_selected_template(dialog)
        )

        self.update_templates_table(dialog)
        dialog.exec()

    def update_template_combo(self):
        """Обновляет комбобокс с шаблонами - теперь только стандартные шаблоны"""
        self.combo_templates.clear()

        standard_templates = [
            "Выбрать правило",
            "Добавить текст в начало",
            "Добавить текст в конец",
            "Удалить символы с начала",
            "Удалить символы с конца",
            "Удалить определенный текст",
            "Заменить текст другим",
            "Изменить регистр",
            "Нумерация",
            "Дата в начале названия",
            "Пользовательский шаблон",
        ]

        self.combo_templates.addItems(standard_templates)
        metrics = self.combo_templates.menu().fontMetrics()
        self.combo_templates.setFixedWidth(max(metrics.horizontalAdvance(name) for name in standard_templates) + 64)
