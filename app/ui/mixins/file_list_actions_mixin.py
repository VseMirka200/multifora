# -*- coding: utf-8 -*-

import os
import re
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
)

from app.core.models import FileItem
from app.core.app_utils import _debug_log
from app.ui.ui_components import (
    setup_standard_dialog,
    setup_standard_secondary_button,
)


class FileListActionsMixin:
    def _manual_sort_mode_text(self) -> str:
        return "Без сортировки (ручной порядок)"

    def _get_sort_mode(self) -> str:
        if hasattr(self, "get_sort_mode"):
            try:
                return self.get_sort_mode()
            except Exception:
                pass
        if hasattr(self, "combo_sort") and self.combo_sort is not None and hasattr(self.combo_sort, "currentText"):
            return self.combo_sort.currentText()
        return self._manual_sort_mode_text()

    def _get_sort_mode_index(self) -> int:
        if hasattr(self, "get_sort_mode_index"):
            try:
                return int(self.get_sort_mode_index())
            except Exception:
                pass
        if hasattr(self, "combo_sort") and self.combo_sort is not None and hasattr(self.combo_sort, "currentIndex"):
            return int(self.combo_sort.currentIndex())
        return 0

    def _set_sort_mode(self, mode: str, notify: bool = False):
        if hasattr(self, "set_sort_mode"):
            try:
                self.set_sort_mode(mode, notify=notify)
                return
            except Exception:
                pass
        if hasattr(self, "combo_sort") and self.combo_sort is not None and hasattr(self.combo_sort, "setCurrentText"):
            if hasattr(self.combo_sort, "blockSignals"):
                self.combo_sort.blockSignals(True)
            self.combo_sort.setCurrentText(mode)
            if hasattr(self.combo_sort, "blockSignals"):
                self.combo_sort.blockSignals(False)
            if notify:
                self.on_sort_changed()

    def _selected_type_filter(self) -> set[str]:
        if not hasattr(self, "_type_filter_actions") or not self._type_filter_actions:
            return {"document", "image", "archive", "folder", "other"}
        selected = {k for k, a in self._type_filter_actions.items() if a.isChecked()}
        return selected
    def _current_search_query(self) -> str:
        if hasattr(self, "input_search") and self.input_search is not None:
            return self.input_search.text().strip().casefold()
        return ""

    def _is_search_active(self) -> bool:
        return bool(self._current_search_query())

    def _is_type_filter_active(self) -> bool:
        all_types = {"document", "image", "archive", "folder", "other"}
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
        known_ext = {
            ".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico",
            ".zip", ".rar", ".7z", ".tar", ".gz",
        }
        for file_item in self.files:
            ftype = str(getattr(file_item, "file_type", "other")).lower()
            if type_filter and ftype not in type_filter:
                continue

            ext = os.path.splitext(str(getattr(file_item, "name", "")))[1].lower()
            ext_key = ext
            if ftype == "folder":
                ext_key = "__folder__"
            elif not ext:
                ext_key = "__noext__"
            elif ext not in known_ext:
                ext_key = "__otherext__"

            if self._is_extension_filter_active() and ext_key not in ext_filter:
                continue

            if query and query not in str(getattr(file_item, "name", "")).casefold():
                continue
            result.append(file_item)
        return result

    def on_search_text_changed(self, _text):
        if self._is_any_filter_active() and self._get_sort_mode_index() == 0:
            self.list_files.set_manual_sorting(False)
        self.update_file_list()

    def on_file_type_filter_changed(self, _checked=False):
        if hasattr(self, "_update_type_filter_button_text"):
            self._update_type_filter_button_text()
        if self._is_any_filter_active() and self._get_sort_mode_index() == 0:
            self.list_files.set_manual_sorting(False)
        self.update_file_list()

    def on_extension_filter_changed(self, _checked=False):
        if hasattr(self, "_update_ext_filter_button_text"):
            self._update_ext_filter_button_text()
        if self._is_any_filter_active() and self._get_sort_mode_index() == 0:
            self.list_files.set_manual_sorting(False)
        self.update_file_list()

    def add_files_dialog(self):
        """Открытие диалога для добавления файлов"""
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы", "", "Все файлы (*.*)")
        if files:
            self.add_files(files)
    def _ask_folder_add_mode(self):
        dialog = QDialog(self)
        setup_standard_dialog(dialog, title="Добавление папки", min_width=520)
        try:
            dialog._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
            dialog.setStyleSheet(self.styleSheet())
        except Exception:
            pass

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        try:
            icon = dialog.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
            icon_label.setPixmap(icon.pixmap(32, 32))
        except Exception:
            pass
        content_row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        text_label = QLabel("Выберите способ добавления:\nдобавить папку целиком или только её содержимое?")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        content_row.addWidget(text_label, 1)
        layout.addLayout(content_row)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(6)

        btn_folder = QPushButton("Добавить папку")
        btn_contents = QPushButton("Добавить содержимое")
        btn_cancel = QPushButton("Отмена")
        setup_standard_secondary_button(btn_folder, height=22)
        setup_standard_secondary_button(btn_contents, height=22)
        setup_standard_secondary_button(btn_cancel, height=22)
        buttons_row.addWidget(btn_folder)
        buttons_row.addWidget(btn_contents)
        buttons_row.addWidget(btn_cancel)
        layout.addLayout(buttons_row)

        selected_mode = {"value": None}

        def _accept_with(mode: str):
            selected_mode["value"] = mode
            dialog.accept()

        btn_folder.clicked.connect(lambda: _accept_with("folder"))
        btn_contents.clicked.connect(lambda: _accept_with("contents"))
        btn_cancel.clicked.connect(dialog.reject)

        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            return selected_mode["value"]
        return None
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
                    # if canceled, skip folder
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
            mode = self._get_sort_mode()
            if not mode.startswith("Без сортировки"):
                self.sort_files(mode)
            else:
                self.update_file_list()
        
        if added_count > 0:
            self.update_file_info()
            try:
                if callable(getattr(self, "refresh_active_file_preview", None)):
                    self.refresh_active_file_preview()
                elif getattr(self, "current_template", None):
                    self.refresh_rename_preview()
            except Exception:
                pass
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
    def on_sort_changed(self):
        mode = self._get_sort_mode()
        if self._get_sort_mode_index() == 0:
            if self._is_any_filter_active():
                self.list_files.set_manual_sorting(False)
                self.status_bar.showMessage("Ручная сортировка недоступна при активных фильтрах.")
                return
            self.list_files.set_manual_sorting(True)
            return
        self.list_files.set_manual_sorting(False)
        self.sort_files(mode)
    def sort_files(self, mode: str):
        if not self.files:
            return
        selected_paths = []
        for item in self.list_files.selectedItems():
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and getattr(data, "path", None):
                selected_paths.append(data.path)

        def natural_key(text: str):
            parts = re.split(r"(\d+)", text)
            key = []
            for part in parts:
                if part.isdigit():
                    key.append(int(part))
                else:
                    key.append(part.casefold())
            return key

        reverse = False
        if mode == "Имя A→Z":
            key_func = lambda f: (natural_key(f.name), f.path.casefold())
        elif mode == "Имя Z→A":
            key_func = lambda f: (natural_key(f.name), f.path.casefold())
            reverse = True
        elif mode == "Расширение A→Z":
            key_func = lambda f: (os.path.splitext(f.name)[1].lower(), natural_key(f.name))
        elif mode == "Размер ↑":
            key_func = lambda f: (f.size, natural_key(f.name))
        elif mode == "Размер ↓":
            key_func = lambda f: (f.size, natural_key(f.name))
            reverse = True
        else:
            return

        self.files.sort(key=key_func, reverse=reverse)
        self.update_file_list()
        self.list_files.clearSelection()
        self.list_files.select_paths(selected_paths)
    def on_list_order_changed(self):
        if self._is_any_filter_active():
            self.status_bar.showMessage("Отключите фильтры, чтобы менять порядок перетаскиванием.")
            self.update_file_list()
            return
        self.files = self.list_files.model().files()
        if self._get_sort_mode() != self._manual_sort_mode_text():
            self._set_sort_mode(self._manual_sort_mode_text(), notify=False)
        self.list_files.set_manual_sorting(True)
    def clear_files(self):
        """Очистка списка файлов"""
        if not self.files:
            return
            
        reply = self.show_russian_message_box(
            "Подтверждение",
            "Очистить список файлов? (файлы на диске не удаляются)",
            QMessageBox.Icon.Question,
            True
        )
        
        if reply:
            self.files.clear()
            self.list_files.clear()
            self.update_file_info()
            self.status_bar.showMessage("Список очищен")
