# -*- coding: utf-8 -*-
import os
from datetime import datetime

from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHeaderView,
    QMenu,
    QMessageBox,
    QTabBar,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

import app.core.settings as app_settings
from app.ui.ui_components import (
    build_bookmark_icon,
    apply_standard_menu_style,
    get_russian_text_input,
    setup_standard_dialog,
)
from app.ui.ui_spacing import MARGINS_NONE, SPACE_NONE, SPACE_SM, SPACE_MD


class TemplateCrudMixin:
    def get_template_session_state(self):
        """Возвращает текущее состояние выбранного шаблона для восстановления сессии."""
        template_name = ""
        if hasattr(self, "combo_templates") and self.combo_templates is not None:
            try:
                template_name = self.combo_templates.currentText().strip()
            except Exception:
                template_name = ""
        if not template_name or template_name == "Выберите шаблон...":
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
        if not template_name or template_name == "Выберите шаблон...":
            return
        if not hasattr(self, "combo_templates") or self.combo_templates is None:
            return

        index = self.combo_templates.findText(template_name)
        if index < 0:
            try:
                normalized_name = template_name.strip().casefold()
                for idx, (item_text, _item_data) in enumerate(getattr(self.combo_templates, "_items", [])):
                    if str(item_text).strip().casefold() == normalized_name:
                        index = idx
                        break
            except Exception:
                pass
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
        if self._get_effective_theme_mode_for_templates() == "light":
            return """
            QTableWidget {
                background-color: transparent;
                alternate-background-color: #3d74b3;
                border: 1px solid #c7cfda;
                color: #1f2328;
                selection-background-color: #3d74b3;
                selection-color: #1f2328;
            }
            QTableWidget::item {
                border-right: 1px solid #d6dbe2;
                border-bottom: none;
                padding: 3px;
            }
            QTableWidget::item:alternate {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #3d74b3;
                color: #1f2328;
            }
            QTableWidget::item:selected:!active {
                background-color: #3d74b3;
                color: #1f2328;
            }
            QHeaderView::section {
                background-color: #eef1f5;
                color: #1f2328;
                border-top: none;
                border-left: none;
                border-bottom: none;
                border-right: 1px solid #d6dbe2;
                padding: 4px;
            }
            QTableCornerButton::section {
                background-color: #eef1f5;
                border: none;
            }
            """
        return """
            QTableWidget {
                background-color: transparent;
                alternate-background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                color: #f0f0f0;
                selection-background-color: #3d74b3;
                selection-color: #ffffff;
            }
            QTableWidget::item {
                border-right: 1px solid rgba(255, 255, 255, 0.55);
                border-bottom: none;
                padding: 3px;
            }
            QTableWidget::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QTableWidget::item:selected:!active {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #f0f0f0;
                border-top: none;
                border-left: none;
                border-bottom: none;
                border-right: 1px solid rgba(255, 255, 255, 0.55);
                padding: 4px;
            }
            QTableCornerButton::section {
                background-color: #2b2b2b;
                border: none;
            }
            """

    def _get_selected_template_name(self):
        if not hasattr(self, "templates_table") or self.templates_table is None:
            return ""
        try:
            row = self.templates_table.currentRow()
            if row < 0:
                return ""
            item = self.templates_table.item(row, 1)
            return item.text().strip() if item is not None else ""
        except Exception:
            return ""

    def _rename_selected_template(self, parent_window=None):
        template_name = self._get_selected_template_name()
        if not template_name:
            QMessageBox.warning(self, "Ошибка", "Выберите шаблон для переименования!")
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
            QMessageBox.warning(self, "Ошибка", f"Шаблон '{new_name}' уже существует!")
            return

        template_payload = self.custom_templates.get(template_name)
        if template_payload is None:
            QMessageBox.warning(self, "Ошибка", f"Шаблон '{template_name}' не найден!")
            return

        reordered_templates = {}
        for name, data in self.custom_templates.items():
            reordered_templates[new_name if name == template_name else name] = data
        self.custom_templates = reordered_templates
        self.save_settings()
        self.update_templates_table(parent_window)

        try:
            for row in range(self.templates_table.rowCount()):
                item = self.templates_table.item(row, 1)
                if item is not None and item.text() == new_name:
                    self.templates_table.selectRow(row)
                    self.templates_table.setCurrentCell(row, 1)
                    break
        except Exception:
            pass
        self.status_bar.showMessage(f"Шаблон переименован: {template_name} -> {new_name}")

    def _show_templates_context_menu(self, pos, parent_window=None):
        index = self.templates_table.indexAt(pos)
        if index.isValid():
            self.templates_table.selectRow(index.row())
            self.templates_table.setCurrentCell(index.row(), 1)

        template_name = self._get_selected_template_name()
        if not template_name:
            return

        menu = QMenu(self.templates_table)
        try:
            menu._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
        except Exception:
            pass
        apply_standard_menu_style(menu)

        action_apply = menu.addAction("Применить")
        action_rename = menu.addAction("Переименовать")
        action_delete = menu.addAction("Удалить")

        selected_action = menu.exec(self.templates_table.viewport().mapToGlobal(pos))
        if selected_action == action_apply:
            self.load_selected_template(parent_window)
        elif selected_action == action_rename:
            self._rename_selected_template(parent_window)
        elif selected_action == action_delete:
            self.delete_selected_template(parent_window)

    def _on_templates_table_section_resized(self, logical_index, _old_size, new_size):
        if not hasattr(self, "templates_table") or self.templates_table is None:
            return
        min_widths = getattr(self, "_templates_table_min_widths", {})
        min_width = min_widths.get(logical_index)
        if min_width is None or new_size >= min_width:
            return
        header = self.templates_table.horizontalHeader()
        header.blockSignals(True)
        self.templates_table.setColumnWidth(logical_index, min_width)
        header.blockSignals(False)

    def save_current_template(self):
        """Сохранение текущего шаблона как пользовательского"""
        if not self.current_template:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите и настройте шаблон!")
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
                'type': self.current_template,
                'data': template_data,
                'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.save_settings()
            QMessageBox.information(self, "Успех", f"Шаблон '{name}' сохранен!")
    def get_current_template_data(self):
        """Получает данные текущего шаблона"""
        template_data = {}
        
        if self.current_template == "Добавить текст в начало":
            if hasattr(self, 'template_prefix'):
                template_data['prefix'] = self.template_prefix.text()
            else:
                return None
                
        elif self.current_template == "Добавить текст в конец":
            if hasattr(self, 'template_suffix'):
                template_data['suffix'] = self.template_suffix.text()
            else:
                return None
                
        elif self.current_template == "Удалить символы с начала":
            if hasattr(self, 'template_remove_start'):
                template_data['remove_start'] = self.template_remove_start.value()
            else:
                return None
                
        elif self.current_template == "Удалить символы с конца":
            if hasattr(self, 'template_remove_end'):
                template_data['remove_end'] = self.template_remove_end.value()
            else:
                return None
                
        elif self.current_template == "Удалить определенный текст":
            if hasattr(self, 'template_remove_text'):
                template_data['remove_text'] = self.template_remove_text.text()
            else:
                return None
                
        elif self.current_template == "Заменить текст другим":
            if hasattr(self, 'template_find') and hasattr(self, 'template_replace'):
                template_data['find'] = self.template_find.text()
                template_data['replace'] = self.template_replace.text()
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
                    template_data["digits"] = self.template_prefix_digits.value()
                else:
                    return None
            elif mode == "Нумерация с датой":
                if hasattr(self, "template_date_format"):
                    template_data["date_format"] = self.template_date_format.currentIndex()
                    template_data["start"] = self.template_date_start.value()
                    template_data["step"] = self.template_date_step.value()
                    template_data["digits"] = self.template_date_digits.value()
                else:
                    return None
                
        elif self.current_template == "Дата в начале названия":
            if hasattr(self, 'template_original_date_format'):
                template_data['date_format'] = self.template_original_date_format.currentIndex()
            else:
                return None
                
        elif self.current_template == "Пользовательский шаблон":
            if hasattr(self, 'template_custom'):
                template_data['template'] = self.template_custom.text()
            else:
                return None
                
        return template_data
    def load_selected_template(self, parent_window=None):
        """Загрузка выбранного шаблона из таблицы"""
        selected_rows = self.templates_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите шаблон для загрузки!")
            return
            
        row = selected_rows[0].row()
        template_name = self.templates_table.item(row, 1).text()
        self.load_template(template_name)
        if parent_window:
            parent_window.accept()
    def load_template(self, template_name):
        """Загрузка шаблона по имени"""
        if template_name not in self.custom_templates:
            QMessageBox.warning(self, "Ошибка", f"Шаблон '{template_name}' не найден!")
            return
            
        template_data = self.custom_templates[template_name]
        template_type = template_data['type']
        index = self.combo_templates.findText(template_type)
        if index >= 0:
            self.combo_templates.setCurrentIndex(index)
            
            QTimer.singleShot(100, lambda: self.apply_template_data(template_type, template_data['data']))
            
            self.status_bar.showMessage(f"Загружен шаблон: {template_name}")
        else:
            QMessageBox.warning(self, "Ошибка", f"Тип шаблона '{template_type}' не поддерживается!")
    def delete_selected_template(self, parent_window=None):
        """Удаление выбранного шаблона"""
        selected_rows = self.templates_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите шаблон для удаления!")
            return
            
        row = selected_rows[0].row()
        template_name = self.templates_table.item(row, 1).text()
        
        reply = self.show_russian_message_box(
            "Подтверждение", 
            f"Удалить шаблон '{template_name}'?",
            QMessageBox.Icon.Question,
            True
        )
        
        if reply:
            del self.custom_templates[template_name]
            self.update_templates_table(parent_window)
            self.save_settings()
            self.status_bar.showMessage(f"Шаблон '{template_name}' удален")
    def update_templates_table(self, parent_window=None):
        """Обновление таблицы шаблонов"""
        if hasattr(self, 'templates_table') and self.templates_table:
            current_name = self._get_selected_template_name()
            self.templates_table.clearContents()
            self.templates_table.setRowCount(len(self.custom_templates))
            
            row = 0
            for name, template_data in self.custom_templates.items():
                number_item = QTableWidgetItem(str(row + 1))
                number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                number_item.setFlags(number_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.templates_table.setItem(row, 0, number_item)

                name_item = QTableWidgetItem(name)
                name_item.setData(Qt.ItemDataRole.UserRole, name)
                name_item.setIcon(build_bookmark_icon(theme=self._get_effective_theme_mode_for_templates()))
                self.templates_table.setItem(row, 1, name_item)
                row += 1
                
            self.templates_table.horizontalHeader().setStretchLastSection(False)
            self.templates_table.setColumnWidth(0, 46)
            self.templates_table.setColumnWidth(1, 390)
            if current_name:
                for row in range(self.templates_table.rowCount()):
                    item = self.templates_table.item(row, 1)
                    if item is not None and item.text() == current_name:
                        self.templates_table.selectRow(row)
                        self.templates_table.setCurrentCell(row, 1)
                        break
    def delete_template_from_manager(self, template_name, parent_window):
        """Удаление шаблона из менеджера"""
        if template_name not in self.custom_templates:
            return
        
        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Удалить шаблон '{template_name}'?",
            QMessageBox.Icon.Question,
            True
        )
        
        if reply:
            del self.custom_templates[template_name]
            self.update_templates_table(parent_window)
            self.save_settings()
            self.status_bar.showMessage(f"Шаблон '{template_name}' удален")
    def load_template_from_manager(self, template_name, parent_window):
        """Загрузка шаблона из менеджера и закрытие окна"""
        self.load_template(template_name)
        if parent_window:
            parent_window.accept()

    def _build_template_manager_action_tabs(self, dialog):
        action_tabs = QTabBar()
        action_tabs.setObjectName("template_manager_action_tabs")
        action_tabs.setExpanding(False)
        action_tabs.setMovable(False)
        action_tabs.setUsesScrollButtons(False)
        action_tabs.setDocumentMode(True)
        action_tabs.setDrawBase(False)
        action_tabs.setElideMode(Qt.TextElideMode.ElideRight)
        action_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        action_tabs.addTab("Экспорт шаблонов")
        action_tabs.addTab("Импорт шаблонов")

        def _trigger_action(index):
            if index == 0:
                self.export_templates()
            elif index == 1:
                self.import_templates(dialog)

        action_tabs.tabBarClicked.connect(_trigger_action)
        return action_tabs

    def show_template_manager(self):
        """Показывает модальное окно управления шаблонами"""
        dialog = QDialog(self)
        dialog._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
        setup_standard_dialog(dialog, title="Управление шаблонами")
        try:
            dialog.setStyleSheet(self.styleSheet())
        except Exception:
            pass
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_NONE)
        
        card = QFrame()
        card.setObjectName("settings_card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, SPACE_MD, 0, SPACE_MD)
        card_layout.setSpacing(SPACE_SM)

        action_tabs = self._build_template_manager_action_tabs(dialog)
        card_layout.addWidget(action_tabs)
        
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(2)
        self.templates_table.setHorizontalHeaderLabels(["№", "Название шаблона"])
        self.templates_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.templates_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.templates_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.templates_table.setAlternatingRowColors(True)
        self.templates_table.setShowGrid(False)
        self.templates_table.setIconSize(QSize(16, 16))
        self.templates_table.verticalHeader().setVisible(False)
        self.templates_table.horizontalHeader().setVisible(False)
        self.templates_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.templates_table.setStyleSheet(self._templates_table_stylesheet())
        header = self.templates_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(36)
        self._templates_table_min_widths = {0: 46, 1: 220}
        header.sectionResized.connect(self._on_templates_table_section_resized)
        self.templates_table.cellDoubleClicked.connect(lambda *_args: self.load_selected_template(dialog))
        self.templates_table.customContextMenuRequested.connect(
            lambda pos: self._show_templates_context_menu(pos, dialog)
        )
        card_layout.addWidget(self.templates_table)

        self._templates_apply_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), dialog)
        self._templates_apply_shortcut.activated.connect(lambda: self.load_selected_template(dialog))
        self._templates_apply_shortcut_enter = QShortcut(QKeySequence(Qt.Key.Key_Enter), dialog)
        self._templates_apply_shortcut_enter.activated.connect(lambda: self.load_selected_template(dialog))
        self._templates_delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), dialog)
        self._templates_delete_shortcut.activated.connect(lambda: self.delete_selected_template(dialog))
        self._templates_rename_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F2), dialog)
        self._templates_rename_shortcut.activated.connect(lambda: self._rename_selected_template(dialog))

        layout.addWidget(card)
        
        self.update_templates_table(dialog)
        dialog.adjustSize()
        table_width = self.templates_table.frameWidth() * 2
        table_width += sum(self.templates_table.columnWidth(i) for i in range(self.templates_table.columnCount()))
        card_margins = card_layout.contentsMargins()
        root_margins = layout.contentsMargins()
        required_width = (
            table_width
            + card_margins.left()
            + card_margins.right()
            + root_margins.left()
            + root_margins.right()
        )
        dialog.setMinimumWidth(required_width)
        dialog.resize(required_width, dialog.sizeHint().height())
        self.templates_table.setFocus()
        
        dialog.exec()
    def update_template_combo(self):
        """Обновляет комбобокс с шаблонами - теперь только стандартные шаблоны"""
        self.combo_templates.clear()
        
        standard_templates = [
            "Выберите шаблон...",
            "Добавить текст в начало",
            "Добавить текст в конец",
            "Удалить символы с начала",
            "Удалить символы с конца",
            "Удалить определенный текст",
            "Заменить текст другим",
            "Нумерация",
            "Дата в начале названия",
            "Пользовательский шаблон"
        ]
        
        self.combo_templates.addItems(standard_templates)
