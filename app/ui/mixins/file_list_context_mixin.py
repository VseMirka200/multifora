
import os

from PyQt6.QtCore import QPoint, QItemSelectionModel, QMimeData, Qt, QUrl
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox

from app.ui.ui_components import apply_standard_menu_style, get_russian_text_input


class FileListContextMixin:
    def _get_selected_file_items(self):
        selected_items = self.list_files.selectedItems()
        file_items = []
        for item in selected_items:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                file_items.append(data)
        return file_items

    def show_file_context_menu(self, pos: QPoint):
        if not self.files:
            return
        index = self.list_files.indexAt(pos)
        if index.isValid() and not self.list_files.selectionModel().isSelected(index):
            self.list_files.clearSelection()
            self.list_files.selectionModel().select(index, QItemSelectionModel.SelectionFlag.Select)

        selected_items = self._get_selected_file_items()
        if not selected_items:
            return

        menu = QMenu(self)
        apply_standard_menu_style(menu)
        action_open = menu.addAction("Открыть")
        action_copy = menu.addAction("Скопировать")
        action_rename = menu.addAction("Переименовать")
        menu.addSeparator()
        action_remove = menu.addAction("Удалить из списка")

        if len(selected_items) != 1:
            action_rename.setEnabled(False)

        action = menu.exec(self.list_files.viewport().mapToGlobal(pos))
        if action == action_open:
            self.open_selected_items()
        elif action == action_copy:
            self.copy_selected_files_to_clipboard()
        elif action == action_rename:
            self.rename_selected_item()
        elif action == action_remove:
            self.remove_selected_files_from_list()
    def open_file(self, item):
        """Открытие файла"""
        file_item = item.data(Qt.ItemDataRole.UserRole)
        if file_item and file_item.is_file:
            try:
                if os.path.exists(file_item.path):
                    os.startfile(file_item.path)
                    self.log_event(f"Открыт файл: {file_item.path}")
                else:
                    QMessageBox.information(self, "Информация", 
                        f"Файл не найден: {file_item.name}")
            except Exception as e:
                QMessageBox.information(self, "Информация", 
                    f"Не удалось открыть файл: {file_item.name}\nОшибка: {str(e)}")
    def open_selected_items(self):
        selected = self._get_selected_file_items()
        if not selected:
            return
        opened = 0
        for file_item in selected:
            try:
                if os.path.exists(file_item.path):
                    os.startfile(file_item.path)
                    opened += 1
                else:
                    self.log_event(f"Файл не найден: {file_item.path}", "WARN")
            except Exception as e:
                self.log_event(f"Ошибка открытия: {file_item.path} ({e})", "ERROR")
        if opened:
            self.status_bar.showMessage(f"Открыто: {opened}")
    def copy_selected_files_to_clipboard(self):
        selected = self._get_selected_file_items()
        if not selected:
            return
        urls = []
        for file_item in selected:
            if os.path.exists(file_item.path):
                urls.append(QUrl.fromLocalFile(file_item.path))
        if not urls:
            QMessageBox.information(self, "Информация", "Не удалось скопировать: файлы не найдены")
            return
        mime = QMimeData()
        mime.setUrls(urls)
        QApplication.clipboard().setMimeData(mime)
        self.status_bar.showMessage(f"Скопировано: {len(urls)}")
    def rename_selected_item(self):
        selected = self._get_selected_file_items()
        if len(selected) != 1:
            QMessageBox.information(self, "Информация", "Выберите один файл для переименования")
            return
        file_item = selected[0]
        if not os.path.exists(file_item.path):
            QMessageBox.information(self, "Информация", "Файл не найден")
            return
        current_name = os.path.basename(file_item.path)
        new_name, ok = get_russian_text_input(
            self,
            title="Переименование",
            label="Новое имя:",
            text=current_name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "Ошибка", "Имя не может быть пустым")
            return
        if new_name == current_name:
            return
        new_path = os.path.join(os.path.dirname(file_item.path), new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Ошибка", "Файл с таким именем уже существует")
            return
        try:
            os.rename(file_item.path, new_path)
            file_item.path = new_path
            file_item.update_info()
            file_item.preview_name = file_item.name
            self.list_files.refresh()
            self.update_file_info()
            self.status_bar.showMessage("Переименовано")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось переименовать: {e}")
    def remove_selected_files_from_list(self):
        selected = self._get_selected_file_items()
        if not selected:
            return
        selected_paths = set()
        for item in selected:
            try:
                selected_paths.add(os.path.normcase(os.path.abspath(item.path)))
            except Exception:
                selected_paths.add(os.path.normcase(item.path))
        kept_files = []
        for f in self.files:
            try:
                abs_path = os.path.normcase(os.path.abspath(f.path))
            except Exception:
                abs_path = os.path.normcase(f.path)
            if abs_path not in selected_paths:
                kept_files.append(f)
        self.files = kept_files
        self.list_files.set_files(self.files)
        self.update_file_info()
        self.status_bar.showMessage("Удалено из списка")

    def open_selected_folder(self):
        """Открытие папки с выбранным файлом"""
        selected = self.list_files.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите файл")
            return

        file_item = selected[0].data(Qt.ItemDataRole.UserRole)
        if file_item:
            try:
                os.startfile(file_item.folder)
                self.log_event(f"Открыта папка: {file_item.folder}")
            except Exception as e:
                QMessageBox.information(self, "Информация",
                    f"Не удалось открыть папку: {file_item.folder}")
                self.log_event(f"Ошибка открытия папки: {e}", "ERROR")

    def select_all(self):
        """Выделить все файлы"""
        self.list_files.clearSelection()
        self.list_files.select_paths([f.path for f in self.files])
        self.log_event(f"Выбраны все файлы ({len(self.files)})")

    def deselect_all(self):
        """Снять выделение со всех файлов"""
        self.list_files.clearSelection()
        self.log_event("Снято выделение со всех файлов")
