from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.core.conversion_formats import CATEGORY_FILE_TYPES, suffix_for_format


class FileListPreviewMixin:
    # Показывает будущие имена файлов без изменения исходных файлов на диске.
    def _set_preview_names_to_original(self):
        for file_item in getattr(self, "files", []) or []:
            file_item.preview_name = file_item.name

    def _refresh_list_preview(self):
        if hasattr(self, "list_files") and self.list_files is not None:
            self.list_files.refresh()
        if callable(getattr(self, "refresh_preview_panel", None)):
            self.refresh_preview_panel()

    def _active_operations_tab_label(self) -> str:
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is None:
            return ""
        try:
            idx = tab_bar.currentIndex()
            if idx < 0:
                return ""
            return str(tab_bar.tabText(idx)).strip().casefold()
        except Exception:
            return ""

    def refresh_active_file_preview(self):
        """Обновляет предпросмотр в списке в зависимости от активного режима."""
        tab_label = self._active_operations_tab_label()
        if "переимен" in tab_label:
            self.refresh_rename_preview(show_empty_warning=False)
            return
        if "конверта" in tab_label:
            self.refresh_conversion_preview(show_empty_warning=False)
            return
        if "сжат" in tab_label:
            self.refresh_compression_preview(show_empty_warning=False)
            return
        self._set_preview_names_to_original()
        self._refresh_list_preview()

    def refresh_rename_preview(self, show_empty_warning=False):
        """Автоматически обновляет предпросмотр переименования."""
        if not getattr(self, "files", None):
            if hasattr(self, "btn_apply_rename"):
                self.btn_apply_rename.setEnabled(False)
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            if show_empty_warning:
                QMessageBox.warning(self, "Ошибка", "Добавьте файлы для переименования")
                self.log_event("Предпросмотр: нет файлов для переименования", "WARN")
            return

        if not getattr(self, "current_template", None):
            if hasattr(self, "btn_apply_rename"):
                self.btn_apply_rename.setEnabled(False)
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        self.apply_template_logic()
        self._refresh_list_preview()
        has_changes = any(
            hasattr(file_item, "preview_name") and file_item.name != file_item.preview_name
            for file_item in self.files
        )
        self.btn_apply_rename.setEnabled(has_changes)
        if has_changes:
            self.status_bar.showMessage("Предпросмотр обновлен автоматически.")
        else:
            self.status_bar.showMessage("Шаблон не изменяет текущие имена файлов.")

    @staticmethod
    def _conversion_target_suffix(to_format: str) -> str:
        return suffix_for_format(to_format)

    def _build_conversion_preview_name(self, file_name: str, to_format: str) -> str:
        suffix = self._conversion_target_suffix(to_format)
        if not suffix:
            return file_name
        base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        return f"{base_name}{suffix}"

    def refresh_conversion_preview(self, show_empty_warning=False):
        """Обновляет предпросмотр целевого имени/формата для конвертации."""
        if not getattr(self, "files", None):
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            if show_empty_warning:
                QMessageBox.warning(self, "Ошибка", "Добавьте файлы для конвертации")
            return

        from_combo = getattr(self, "from_convert_combo", None)
        to_combo = getattr(self, "to_convert_combo", None)
        type_combo = getattr(self, "convert_file_type_combo", None)
        if from_combo is None or to_combo is None:
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        from_format = from_combo.currentText()
        to_format = to_combo.currentText()
        category_label = ""
        if type_combo is not None:
            try:
                category_label = str(type_combo.currentText() or "").strip()
            except Exception:
                category_label = ""
        from_idx = from_combo.currentIndex() if hasattr(from_combo, "currentIndex") else 0
        to_idx = to_combo.currentIndex() if hasattr(to_combo, "currentIndex") else 0
        type_idx = (
            type_combo.currentIndex()
            if type_combo is not None and hasattr(type_combo, "currentIndex")
            else 0
        )

        if from_idx <= 0 or to_idx <= 0 or (type_combo is not None and type_idx <= 0):
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        for file_item in self.files:
            file_item.preview_name = file_item.name
            if not getattr(file_item, "is_file", False):
                continue
            if category_label:
                file_type = str(getattr(file_item, "file_type", "")).lower()
                expected = CATEGORY_FILE_TYPES.get(category_label, "")
                if expected and file_type != expected:
                    continue
            if callable(getattr(self, "_check_file_compatibility_dual", None)):
                if self._check_file_compatibility_dual(file_item, from_format):
                    file_item.preview_name = self._build_conversion_preview_name(file_item.name, to_format)

        self._refresh_list_preview()

    @staticmethod
    def _build_compressed_name(file_name: str, ext: str) -> str:
        dot_ext = str(ext or "")
        if dot_ext and not dot_ext.startswith("."):
            dot_ext = f".{dot_ext}"
        base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        return f"{base_name}_compressed{dot_ext}"

    def _estimate_image_reduction_percent(self, file_item) -> int:
        level_combo = getattr(self, "combo_compression_level", None)
        level = 85
        if level_combo is not None:
            try:
                selected_level = level_combo.currentData()
                if isinstance(selected_level, int):
                    level = selected_level
            except Exception:
                level = 85

        ext = ""
        try:
            ext = file_item.name.rsplit(".", 1)[1].lower() if "." in file_item.name else ""
        except Exception:
            ext = ""

        # Грубая оценка: JPEG/WebP обычно сжимаются сильнее PNG.
        if ext in ("jpg", "jpeg", "webp"):
            mapping = {40: 55, 65: 35, 85: 18, 95: 8}
        else:
            mapping = {40: 35, 65: 22, 85: 12, 95: 5}
        return int(mapping.get(level, 18))

    def _estimate_pdf_reduction_percent(self) -> int:
        method_combo = getattr(self, "combo_pdf_method", None)
        method_text = ""
        if method_combo is not None:
            try:
                method_text = str(method_combo.currentText() or "")
            except Exception:
                method_text = ""

        if "Максимальное сжатие" in method_text:
            return 55
        if "Сохранить качество" in method_text:
            return 18
        if "Только оптимизация" in method_text:
            return 10
        return 30

    @staticmethod
    def _with_reduction_label(name: str, reduction_percent: int) -> str:
        return f"{name} (≈-{max(0, int(reduction_percent))}%)"

    def refresh_compression_preview(self, show_empty_warning=False):
        """Обновляет предпросмотр имени файла для режима сжатия."""
        if not getattr(self, "files", None):
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            if show_empty_warning:
                QMessageBox.warning(self, "Ошибка", "Добавьте файлы для сжатия")
            return

        compress_type_combo = getattr(self, "combo_compress_type", None)
        if compress_type_combo is None:
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        compress_type = str(compress_type_combo.currentText() or "")
        replace_pdf = bool(getattr(getattr(self, "checkbox_replace_pdf", None), "isChecked", lambda: False)())
        replace_image = bool(getattr(getattr(self, "checkbox_replace_image", None), "isChecked", lambda: False)())

        for file_item in self.files:
            file_item.preview_name = file_item.name
            if not getattr(file_item, "is_file", False):
                continue

            if "PDF" in compress_type and str(getattr(file_item, "path", "")).lower().endswith(".pdf"):
                reduction = self._estimate_pdf_reduction_percent()
                if not replace_pdf:
                    new_name = self._build_compressed_name(file_item.name, ".pdf")
                    file_item.preview_name = self._with_reduction_label(new_name, reduction)
                else:
                    file_item.preview_name = self._with_reduction_label(file_item.name, reduction)
                continue

            if "Изображения" in compress_type and getattr(file_item, "file_type", "") == "image":
                reduction = self._estimate_image_reduction_percent(file_item)
                if not replace_image:
                    ext = file_item.name.rsplit(".", 1)[1] if "." in file_item.name else ""
                    new_name = self._build_compressed_name(file_item.name, ext)
                    file_item.preview_name = self._with_reduction_label(new_name, reduction)
                else:
                    file_item.preview_name = self._with_reduction_label(file_item.name, reduction)

        self._refresh_list_preview()

    def apply_rename(self):
        """Применение переименования"""
        if not self.files:
            return

        files_to_rename = []
        new_names = []

        for file_item in self.files:
            if hasattr(file_item, 'preview_name') and file_item.name != file_item.preview_name:
                files_to_rename.append(file_item)
                new_names.append(file_item.preview_name)

        if not files_to_rename:
            QMessageBox.information(self, "Информация", "Нет изменений для применения")
            self.log_event("Переименование: нет изменений для применения", "INFO")
            return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Переименовать {len(files_to_rename)} файлов?",
            QMessageBox.Icon.Question,
            True
        )

        if reply:
            if not self.create_file_worker():
                return
            self.file_worker.set_rename(files_to_rename, new_names)
            self._last_operation = {
                "op": "rename",
                "new_names_by_path": {f.path: name for f, name in zip(files_to_rename, new_names)},
            }
            self.file_worker.start()
            self.log_event(f"Переименование: {len(files_to_rename)} файлов")
            if callable(getattr(self, "_show_progress_dialog", None)):
                self._show_progress_dialog(f"Переименование {len(files_to_rename)} файлов...")
            self.btn_apply_rename.setEnabled(False)

    def update_file_list(self):
        """Обновление отображения списка"""
        if not self.files:
            self.list_files.clear()
            return

        selected_paths = []
        for item in self.list_files.selectedItems():
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if file_item and getattr(file_item, "path", None):
                selected_paths.append(file_item.path)

        filtered_files = self._get_filtered_files() if hasattr(self, "_get_filtered_files") else self.files
        self.list_files.set_files(filtered_files)
        self.list_files.clearSelection()
        self.list_files.select_paths(selected_paths)
