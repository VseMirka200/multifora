
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.core.models import (
    FileItem,
    file_item_source_folder,
    file_item_type_label,
    natural_sort_key,
)
from app.core.conversion_formats import KNOWN_FILE_EXTENSIONS
from app.core.message_boxes import show_app_choice
from app.core.app_utils import _log_ignored_error


class FileListActionsMixin:
    # Добавляет и удаляет файлы, сохраняя согласованность списка и предпросмотра.
    _FILTERABLE_FILE_TYPES = frozenset(("document", "image", "archive", "folder", "other"))

    def _selected_type_filter(self) -> set[str]:
        if not hasattr(self, "_type_filter_actions") or not self._type_filter_actions:
            return set(self._FILTERABLE_FILE_TYPES)
        selected = {k for k, a in self._type_filter_actions.items() if a.isChecked()}
        return selected
    def _current_search_query(self) -> str:
        if hasattr(self, "input_search") and self.input_search is not None:
            return self.input_search.text().strip().casefold()
        return ""

    def _is_search_active(self) -> bool:
        return bool(self._current_search_query())

    def _is_type_filter_active(self) -> bool:
        all_types = self._FILTERABLE_FILE_TYPES
        return self._selected_type_filter() != all_types

    def _is_any_filter_active(self) -> bool:
        return self._is_search_active() or self._is_type_filter_active() or self._is_extension_filter_active()

    def _selected_extension_filter(self) -> set[str]:
        if not hasattr(self, "_ext_filter_actions") or not self._ext_filter_actions:
            return set()
        return {k for k, a in self._ext_filter_actions.items() if a.isChecked()}

    def _is_extension_filter_active(self) -> bool:
        if not hasattr(self, "_ext_filter_actions") or not self._ext_filter_actions:
            return False
        all_ext = set(self._ext_filter_actions.keys())
        return self._selected_extension_filter() != all_ext


    def _get_filtered_files(self):
        type_filter = self._selected_type_filter()
        ext_filter = self._selected_extension_filter()
        query = self._current_search_query()
        if not query and not self._is_type_filter_active() and not self._is_extension_filter_active():
            return list(self.files)

        result = []
        for file_item in self.files:
            ftype = str(getattr(file_item, "file_type", "other")).lower()
            if ftype not in type_filter:
                continue

            ext = os.path.splitext(str(getattr(file_item, "name", "")))[1].lower()
            ext_key = ext
            if ftype == "folder":
                ext_key = "__folder__"
            elif not ext:
                ext_key = "__noext__"
            elif ext not in KNOWN_FILE_EXTENSIONS:
                ext_key = "__otherext__"

            if self._is_extension_filter_active() and ext_key not in ext_filter:
                continue

            if query and query not in str(getattr(file_item, "name", "")).casefold():
                continue
            result.append(file_item)
        return result

    def on_search_text_changed(self, _text):
        self.list_files.set_manual_sorting(True)
        self.update_file_list()

    def on_file_type_filter_changed(self, _checked=False):
        if hasattr(self, "_update_type_filter_button_text"):
            self._update_type_filter_button_text()
        self.list_files.set_manual_sorting(True)
        self.update_file_list()

    def on_extension_filter_changed(self, _checked=False):
        if hasattr(self, "_update_ext_filter_button_text"):
            self._update_ext_filter_button_text()
        self.list_files.set_manual_sorting(True)
        self.update_file_list()

    def _ask_folder_add_mode(self):
        selected = show_app_choice(
            self,
            "Добавление папки",
            "Выберите способ добавления:\n"
            "добавить папку целиком или только её содержимое?",
            (
                ("folder", "Добавить папку", "secondary"),
                ("contents", "Добавить содержимое", "secondary"),
                ("cancel", "Отмена", "secondary"),
            ),
            icon=QMessageBox.Icon.Question,
            default_key="folder",
            cancel_key="cancel",
        )
        return None if selected == "cancel" else selected

    def add_files(self, file_paths):
        """Добавление файлов в список"""
        if not isinstance(file_paths, list):
            if isinstance(file_paths, str):
                file_paths = [file_paths]
            elif hasattr(file_paths, '__iter__'):
                file_paths = list(file_paths)
            else:
                QMessageBox.warning(self, "Ошибка", f"Неправильный формат файлов: {type(file_paths)}")
                return

        folder_mode = None
        expanded_paths = []
        for path in list(file_paths):
            try:
                if os.path.isdir(path):
                    if folder_mode is None:
                        folder_mode = self._ask_folder_add_mode()
                    if folder_mode == "contents":
                        for root, _, files in os.walk(path):
                            for name in files:
                                expanded_paths.append(os.path.join(root, name))
                    elif folder_mode == "folder":
                        expanded_paths.append(path)
                    elif folder_mode is None:
                        folder_mode = "cancel"
                else:
                    expanded_paths.append(path)
            except Exception:
                expanded_paths.append(path)
        file_paths = expanded_paths
        
        added_count = 0
        existing_paths = set()
        for f in self.files:
            try:
                existing_paths.add(os.path.normcase(os.path.abspath(f.path)))
            except Exception:
                existing_paths.add(os.path.normcase(f.path))
        
        new_items = []
        for file_path in file_paths:
            try:
                abs_path = os.path.normcase(os.path.abspath(file_path))
            except Exception:
                abs_path = os.path.normcase(file_path)
            if abs_path in existing_paths:
                continue
                
            try:
                file_item = FileItem(file_path)
                self.files.append(file_item)
                added_count += 1
                existing_paths.add(abs_path)
                new_items.append(file_item)
                
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось добавить файл {os.path.basename(file_path)}: {e}")

        if new_items:
            column = getattr(self, "_column_sort_section", None)
            if column is not None:
                self.sort_files_by_column(
                    column,
                    getattr(self, "_column_sort_order", Qt.SortOrder.AscendingOrder),
                )
            else:
                self.update_file_list()
        
        if added_count > 0:
            self.update_file_info()
            try:
                if callable(getattr(self, "refresh_active_file_preview", None)):
                    self.refresh_active_file_preview()
                elif getattr(self, "current_template", None):
                    self.refresh_rename_preview()
            except Exception as error:
                _log_ignored_error("FileListActionsMixin.add_files", error)
            if callable(getattr(self, "log_event", None)):
                self.log_event(f"Добавлены файлы в список: {self._ru_files_label(added_count)}")
            self.status_bar.showMessage(f"Добавлено {self._ru_files_label(added_count)}")
    def update_file_info(self):
        """Обновление информации о файлах"""
        total_files = len(self.files)
        total_size = sum(f.size for f in self.files) / (1024*1024)
        item_size = self.files[0].size / (1024*1024) if self.files else 0.0
        
        self.label_count.setText(f"Файлов: {total_files}")
        self.label_item_size.setText(f"Размер: {item_size:.2f} MB")
        self.label_total_size.setText(f"Общий объем: {total_size:.2f} MB")
    def on_file_header_clicked(self, section: int):
        """Сортирует общий список по выбранной колонке таблицы."""
        current_section = getattr(self, "_column_sort_section", None)
        current_order = getattr(
            self,
            "_column_sort_order",
            Qt.SortOrder.AscendingOrder,
        )
        if current_section == section and current_order == Qt.SortOrder.DescendingOrder:
            self._column_sort_section = None
            self.list_files.horizontalHeader().setSortIndicatorShown(False)
            self.list_files.set_manual_sorting(True)
            if callable(getattr(self, "_schedule_settings_save", None)):
                self._schedule_settings_save()
            return
        order = (
            Qt.SortOrder.DescendingOrder
            if current_section == section
            else Qt.SortOrder.AscendingOrder
        )
        self.sort_files_by_column(section, order)

    def sort_files_by_column(self, section: int, order=Qt.SortOrder.AscendingOrder):
        if not hasattr(self, "list_files"):
            return
        model = self.list_files.model()
        valid_columns = {
            model.COLUMN_OLD_NAME,
            model.COLUMN_NEW_NAME,
            model.COLUMN_TYPE,
            model.COLUMN_PATH,
        }
        if section not in valid_columns:
            return

        selected_paths = [
            file_item.path
            for file_item in self.list_files.selected_file_items()
            if getattr(file_item, "path", None)
        ]

        if section == model.COLUMN_OLD_NAME:
            key_func = lambda f: (natural_sort_key(getattr(f, "name", "")), str(f.path).casefold())
        elif section == model.COLUMN_NEW_NAME:
            key_func = lambda f: (
                natural_sort_key(getattr(f, "preview_name", None) or getattr(f, "name", "")),
                str(f.path).casefold(),
            )
        elif section == model.COLUMN_TYPE:
            key_func = lambda f: (
                natural_sort_key(file_item_type_label(f)),
                natural_sort_key(getattr(f, "name", "")),
            )
        else:
            key_func = lambda f: (
                natural_sort_key(file_item_source_folder(f)),
                natural_sort_key(getattr(f, "name", "")),
            )

        self.files.sort(
            key=key_func,
            reverse=order == Qt.SortOrder.DescendingOrder,
        )
        self._column_sort_section = section
        self._column_sort_order = order
        self.list_files.set_manual_sorting(True)
        header = self.list_files.horizontalHeader()
        header.setSortIndicator(section, order)
        header.setSortIndicatorShown(True)
        self.update_file_list()
        self.list_files.clearSelection()
        self.list_files.select_paths(selected_paths)
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()
    def on_list_order_changed(self):
        visible_files = self.list_files.model().files()
        if self._is_any_filter_active():
            visible_ids = {id(file_item) for file_item in visible_files}
            visible_iterator = iter(visible_files)
            self.files = [
                next(visible_iterator) if id(file_item) in visible_ids else file_item
                for file_item in self.files
            ]
        else:
            self.files = visible_files
        self._column_sort_section = None
        self.list_files.horizontalHeader().setSortIndicatorShown(False)
        self.list_files.set_manual_sorting(True)
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()
