# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QGroupBox, QMessageBox


class TemplateParamsBaseMixin:
    def apply_template_data(self, template_type, data):
        """Применяет данные шаблона к виджетам"""
        try:
            if template_type == "Добавить текст в начало":
                if hasattr(self, 'template_prefix'):
                    self.template_prefix.setText(data.get('prefix', ''))
                    
            elif template_type == "Добавить текст в конец":
                if hasattr(self, 'template_suffix'):
                    self.template_suffix.setText(data.get('suffix', ''))
                    
            elif template_type == "Удалить символы с начала":
                if hasattr(self, 'template_remove_start'):
                    self.template_remove_start.setValue(data.get('remove_start', 1))
                    
            elif template_type == "Удалить символы с конца":
                if hasattr(self, 'template_remove_end'):
                    self.template_remove_end.setValue(data.get('remove_end', 1))
                    
            elif template_type == "Удалить определенный текст":
                if hasattr(self, 'template_remove_text'):
                    self.template_remove_text.setText(data.get('remove_text', ''))
                    
            elif template_type == "Заменить текст другим":
                if hasattr(self, 'template_find') and hasattr(self, 'template_replace'):
                    self.template_find.setText(data.get('find', ''))
                    self.template_replace.setText(data.get('replace', ''))
                    
            elif template_type == "Простая нумерация":
                if hasattr(self, 'template_num_start'):
                    self.template_num_start.setValue(data.get('start', 1))
                    self.template_num_step.setValue(data.get('step', 1))
                    self.template_num_digits.setValue(data.get('digits', 3))
                    self.template_num_sep.setText(data.get('separator', '_'))
                    
            elif template_type == "Нумерация с префиксом":
                if hasattr(self, 'template_prefix_text'):
                    self.template_prefix_text.setText(data.get('prefix', 'фото_'))
                    self.template_prefix_start.setValue(data.get('start', 1))
                    self.template_prefix_step.setValue(data.get('step', 1))
                    self.template_prefix_digits.setValue(data.get('digits', 3))
                    
            elif template_type == "Нумерация с датой":
                if hasattr(self, 'template_date_format'):
                    self.template_date_format.setCurrentIndex(data.get('date_format', 0))
                    self.template_date_start.setValue(data.get('start', 1))
                    self.template_date_step.setValue(data.get('step', 1))
                    self.template_date_digits.setValue(data.get('digits', 3))
                    
            elif template_type == "Дата в начале названия":
                if hasattr(self, 'template_original_date_format'):
                    self.template_original_date_format.setCurrentIndex(data.get('date_format', 0))
                    
            elif template_type == "Пользовательский шаблон":
                if hasattr(self, 'template_custom'):
                    self.template_custom.setText(data.get('template', ''))
                    if hasattr(self, 'template_custom_use_numbering'):
                        self.template_custom_use_numbering.setChecked(data.get('use_numbering', True))
                        self.on_custom_numbering_toggled(self.template_custom_use_numbering.checkState())
                    if hasattr(self, 'template_custom_start'):
                        self.template_custom_start.setValue(data.get('start', 1))
                    if hasattr(self, 'template_custom_step'):
                        self.template_custom_step.setValue(data.get('step', 1))
                    
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось применить данные шаблона: {str(e)}")
    def adjust_rename_group_height(self):
        """Адаптирует высоту группы переименования под содержимое"""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget and widget.children():
                for child in widget.children():
                    if isinstance(child, QGroupBox) and child.title() == "Переименование файлов":
                        child.setMaximumHeight(16777215)
                        break
    def clear_template_params_container(self):
        """Очищает контейнер с параметрами шаблона"""
        while self.template_params_layout.count():
            item = self.template_params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
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
