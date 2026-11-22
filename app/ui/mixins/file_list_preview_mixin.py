import os

from PySide6.QtWidgets import QMessageBox

from app.core.conversion_formats import suffix_for_format
from app.ui.file_table import operation_file_items
from core.filesystem import compressed_name, conversion_directory, converted_name
from core.operation_requests import RenameRequest
from core.rename_plan import resolve_rename_targets
from core.rename_validation import analyze_rename_plan, format_rename_plan_issues


class FileListPreviewMixin:
    # Показывает будущие имена файлов без изменения исходных файлов на диске.
    _SOURCE_FOLDER_HEADER = "Исходная папка"

    def _set_preview_folder_header(self, text: str) -> None:
        file_list = getattr(self, "list_files", None)
        model = file_list.model() if file_list is not None else None
        setter = getattr(model, "set_folder_header", None)
        if callable(setter):
            setter(text)

    def _preview_operation_items(self):
        resolver = getattr(self, "_get_operation_file_items", None)
        return resolver() if callable(resolver) else operation_file_items(self.files)

    def _set_preview_names_to_original(self):
        for file_item in getattr(self, "files", []) or []:
            preview = self.list_files.model().preview_for(file_item)
            preview.rename_status = ""
            preview.preview_name = file_item.name
            preview.estimated_compressed_size = None
            preview.conversion_target_format = ""
            preview.preview_folder = str(
                getattr(file_item, "folder", "")
                or os.path.dirname(str(getattr(file_item, "path", "")))
            )
        self._set_preview_folder_header(self._SOURCE_FOLDER_HEADER)

    def _refresh_list_preview(self):
        if hasattr(self, "list_files") and self.list_files is not None:
            self.list_files.refresh()
        if callable(getattr(self, "refresh_preview_panel", None)):
            self.refresh_preview_panel()
        if callable(getattr(self, "_schedule_filter_button_refresh", None)):
            self._schedule_filter_button_refresh()

    def _active_operation_id(self) -> str:
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is None:
            return ""
        index = tab_bar.currentIndex()
        if index in (getattr(self, "_settings_tab_index", None), getattr(self, "_help_tab_index", None)):
            index = self.operations_stack.currentIndex()
        if index < 0:
            return ""
        return str(tab_bar.tabData(index) or "")

    def sync_file_preview_columns(self) -> None:
        """Показывает нужные для текущей операции имена и размеры."""
        file_list = getattr(self, "list_files", None)
        if file_list is None:
            return
        model = file_list.model()
        operation = self._active_operation_id()
        size_setter = getattr(model, "set_compression_sizes_visible", None)
        if callable(size_setter):
            size_setter(operation == "compress")
        format_setter = getattr(model, "set_conversion_formats_visible", None)
        if callable(format_setter):
            format_setter(operation == "convert")
        if hasattr(model, "COLUMN_ORDER"):
            model.set_merge_order_visible(operation == "merge")
            file_list.setColumnHidden(model.COLUMN_ORDER, not model.merge_order_visible)
        new_name_column = getattr(model, "COLUMN_NEW_NAME", None)
        if new_name_column is None:
            return
        should_hide = operation != "rename"
        if file_list.isColumnHidden(new_name_column) != should_hide:
            file_list.setColumnHidden(new_name_column, should_hide)

    def refresh_active_file_preview(self):
        """Обновляет предпросмотр независимо от пользовательского языка интерфейса."""
        operation = self._active_operation_id()
        self.sync_file_preview_columns()
        if operation == "rename":
            self.refresh_rename_preview(show_empty_warning=False)
        elif operation == "convert":
            self.refresh_conversion_preview(show_empty_warning=False)
        elif operation == "compress":
            self.refresh_compression_preview(show_empty_warning=False)
        else:
            self._set_preview_names_to_original()
            self._refresh_list_preview()

    def refresh_rename_preview(self, show_empty_warning=False):
        """Автоматически обновляет предпросмотр переименования."""
        label = getattr(self, "rename_validation_label", None)
        if label is not None:
            label.setToolTip("")
        issue_button = getattr(self, "btn_locate_rename_issue", None)
        if issue_button is not None:
            issue_button.hide()
        if not getattr(self, "files", None):
            if label is not None:
                label.setText("Нет файлов")
            if hasattr(self, "btn_apply_rename"):
                self.btn_apply_rename.setEnabled(False)
                self.btn_apply_rename.setToolTip("Переименовать")
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            if show_empty_warning:
                QMessageBox.warning(
                    self, "Ошибка", "Добавьте файлы для переименования"
                )
                self.log_event(
                    "Предпросмотр: нет файлов для переименования", "WARN"
                )
            return

        if not getattr(self, "current_template", None):
            if label is not None:
                label.setText("Выберите правило")
            if hasattr(self, "btn_apply_rename"):
                self.btn_apply_rename.setEnabled(False)
                self.btn_apply_rename.setToolTip("Переименовать")
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        self.apply_template_logic()
        if getattr(self, "_rename_template_error", ""):
            self._rename_plan_issues = []
            self.btn_apply_rename.setEnabled(False)
            self.btn_apply_rename.setToolTip("Переименовать")
            if label is not None:
                label.setText("Ошибка правила")
                label.setToolTip(self._rename_template_error)
            self.status_bar.showMessage(self._rename_template_error)
            self._refresh_list_preview()
            return

        changed_pairs = self._rename_preview_pairs()
        has_changes = bool(changed_pairs)
        self._rename_plan_issues = analyze_rename_plan(
            [item for item, _name in changed_pairs],
            [name for _item, name in changed_pairs],
        )
        issues_by_path = {issue.source: issue for issue in self._rename_plan_issues}
        blocking = any(issue.blocking for issue in self._rename_plan_issues)
        if issue_button is not None:
            issue_button.setVisible(bool(self._rename_plan_issues))
        if has_changes and not blocking:
            try:
                actual_paths = resolve_rename_targets(
                    [item for item, _name in changed_pairs],
                    [name for _item, name in changed_pairs],
                )
                for (item, _name), target in zip(
                    changed_pairs, actual_paths, strict=True
                ):
                    self.list_files.model().preview_for(item).preview_name = os.path.basename(target)
            except ValueError as error:
                blocking = True
                self._rename_template_error = str(error)
        self.btn_apply_rename.setEnabled(has_changes and not blocking)
        self.btn_apply_rename.setToolTip(
            f"Переименовать ({len(changed_pairs)})" if has_changes and not blocking else "Переименовать"
        )
        model = self.list_files.model()
        touched = {id(item) for item, _ in changed_pairs}
        for item in self.files:
            preview = model.preview_for(item)
            issue = issues_by_path.get(item.path)
            if issue is not None:
                preview.rename_status = issue.message if blocking else "Конфликт разрешён"
            else:
                preview.rename_status = "Новое имя" if id(item) in touched else "Без изменений"
        self._refresh_list_preview()
        if label is not None:
            if blocking:
                label.setText("Ошибка имени")
                label.setToolTip(self._rename_template_error or format_rename_plan_issues(self._rename_plan_issues, limit=3))
            elif self._rename_plan_issues:
                label.setText(f"Конфликты: {len(self._rename_plan_issues)}")
                label.setToolTip("Свободные имена показаны в предпросмотре.")
            else:
                label.setText("Имена проверены" if has_changes else "Без изменений")
        if has_changes:
            self.status_bar.showMessage("Предпросмотр обновлен автоматически.")
        else:
            self.status_bar.showMessage(
                "Шаблон не изменяет текущие имена файлов."
            )

    def _build_conversion_preview_name(
        self, file_name: str, to_format: str
    ) -> str:
        return converted_name(file_name, suffix_for_format(to_format))

    def _conversion_preview_folder(self, file_item) -> str:
        """Возвращает папку, в которой появится результат конвертации."""
        source_folder = str(
            getattr(file_item, "folder", "")
            or os.path.dirname(str(getattr(file_item, "path", "")))
        )
        mode_combo = getattr(self, "combo_conversion_output_mode", None)
        mode = str(
            mode_combo.currentData()
            if mode_combo is not None
            else getattr(self, "conversion_output_mode", "ask")
        )
        if mode in {"alongside", "source_subfolder"}:
            return conversion_directory(source_folder, mode, "")
        if mode == "custom":
            custom_path = ""
            resolver = getattr(self, "_conversion_custom_output_path", None)
            if callable(resolver):
                custom_path = str(resolver() or "").strip()
            return custom_path or "Выберите папку сохранения"
        return "Будет выбрана при запуске"

    def refresh_conversion_preview(self, show_empty_warning=False):
        """Обновляет предпросмотр целевого имени/формата для конвертации."""
        if not getattr(self, "files", None):
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            if show_empty_warning:
                QMessageBox.warning(
                    self, "Ошибка", "Добавьте файлы для конвертации"
                )
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
        from_idx = (
            from_combo.currentIndex()
            if hasattr(from_combo, "currentIndex")
            else 0
        )
        to_idx = (
            to_combo.currentIndex() if hasattr(to_combo, "currentIndex") else 0
        )
        type_idx = (
            type_combo.currentIndex()
            if type_combo is not None and hasattr(type_combo, "currentIndex")
            else 0
        )

        if (
            from_idx <= 0
            or to_idx <= 0
            or (type_combo is not None and type_idx <= 0)
        ):
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        self._set_preview_folder_header(self._SOURCE_FOLDER_HEADER)

        active_files, _ = self._collect_compatible_conversion_files(category_label, from_format, to_format)
        active_ids = {id(item) for item in active_files}
        for file_item in self.files:
            preview = self.list_files.model().preview_for(file_item)
            preview.preview_name = file_item.name
            preview.estimated_compressed_size = None
            preview.conversion_target_format = ""
            preview.preview_folder = str(
                getattr(file_item, "folder", "")
                or os.path.dirname(str(getattr(file_item, "path", "")))
            )
            if id(file_item) not in active_ids:
                continue
            preview.conversion_target_format = str(to_format).strip().upper()
            preview.preview_name = self._build_conversion_preview_name(file_item.name, to_format)
            preview.preview_folder = self._conversion_preview_folder(file_item)

        self._refresh_list_preview()

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
            ext = (
                file_item.name.rsplit(".", 1)[1].lower()
                if "." in file_item.name
                else ""
            )
        except Exception:
            ext = ""

        # Грубая оценка: JPEG/WebP обычно сжимаются сильнее PNG.
        mapping = (
            {40: 55, 65: 35, 85: 18, 95: 8}
            if ext in ("jpg", "jpeg", "webp")
            else {40: 35, 65: 22, 85: 12, 95: 5}
        )
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
                QMessageBox.warning(
                    self, "Ошибка", "Добавьте файлы для сжатия"
                )
            return

        compress_type_combo = getattr(self, "combo_compress_type", None)
        if compress_type_combo is None:
            self._set_preview_names_to_original()
            self._refresh_list_preview()
            return

        compress_type = str(compress_type_combo.currentText() or "")
        replace_pdf = bool(
            getattr(
                getattr(self, "checkbox_replace_pdf", None),
                "isChecked",
                lambda: False,
            )()
        )
        replace_image = (
            callable(getattr(self, "_image_output_mode", None))
            and self._image_output_mode() == "replace"
        )
        image_output_folder = ""
        if not replace_image and callable(
            getattr(self, "_image_output_mode", None)
        ) and self._image_output_mode() == "custom":
            image_output_folder = str(
                getattr(self, "_image_output_path", lambda: "")() or ""
            ).strip() or "Выберите папку сохранения"

        self._set_preview_folder_header(self._SOURCE_FOLDER_HEADER)

        active_ids = {id(item) for item in self._preview_operation_items()}
        for file_item in self.files:
            preview = self.list_files.model().preview_for(file_item)
            preview.preview_name = file_item.name
            preview.preview_folder = str(
                getattr(file_item, "folder", "")
                or os.path.dirname(str(getattr(file_item, "path", "")))
            )
            preview.estimated_compressed_size = None
            if id(file_item) not in active_ids or not getattr(file_item, "is_file", False):
                continue

            if "PDF" in compress_type and str(
                getattr(file_item, "path", "")
            ).lower().endswith(".pdf"):
                reduction = self._estimate_pdf_reduction_percent()
                preview.estimated_compressed_size = round(
                    max(0, getattr(file_item, "size", 0)) * (100 - reduction) / 100
                )
                if not replace_pdf:
                    new_name = compressed_name(file_item.name, ".pdf")
                    preview.preview_name = self._with_reduction_label(
                        new_name, reduction
                    )
                else:
                    preview.preview_name = self._with_reduction_label(
                        file_item.name, reduction
                    )
                continue

            if (
                "Изображения" in compress_type
                and getattr(file_item, "file_type", "") == "image"
            ):
                reduction = self._estimate_image_reduction_percent(file_item)
                preview.estimated_compressed_size = round(
                    max(0, getattr(file_item, "size", 0)) * (100 - reduction) / 100
                )
                if not replace_image:
                    ext = (
                        file_item.name.rsplit(".", 1)[1]
                        if "." in file_item.name
                        else ""
                    )
                    new_name = compressed_name(file_item.name, ext)
                    preview.preview_name = self._with_reduction_label(
                        new_name, reduction
                    )
                    if image_output_folder:
                        preview.preview_folder = image_output_folder
                else:
                    preview.preview_name = self._with_reduction_label(
                        file_item.name, reduction
                    )

        self._refresh_list_preview()

    def _rename_preview_pairs(self):
        model = self.list_files.model()
        return [
            (item, name) for item in self._preview_operation_items()
            if (name := model.preview_for(item).preview_name) != item.name
        ]

    def _locate_rename_issue(self):
        issues = self._rename_plan_issues
        if not issues:
            return
        issue = next((item for item in issues if item.blocking), issues[0])
        table = self.list_files
        model = table.model()
        for row, item in enumerate(model.files()):
            if item.path == issue.source:
                table.scrollTo(model.index(row, model.COLUMN_NEW_NAME))
                table.setFocus()
                break

    def apply_rename(self):
        """Применение переименования"""
        if not self._ensure_operation_can_start():
            return
        if not self.files:
            return

        pairs = self._rename_preview_pairs()
        if not pairs:
            QMessageBox.information(
                self, "Информация", "Нет изменений для применения"
            )
            self.log_event(
                "Переименование: нет изменений для применения", "INFO"
            )
            return
        files_to_rename, new_names = zip(*pairs, strict=True)

        issues = analyze_rename_plan(files_to_rename, new_names)
        blocking_issues = [issue for issue in issues if issue.blocking]
        if blocking_issues:
            QMessageBox.warning(
                self,
                "Некорректные имена",
                format_rename_plan_issues(blocking_issues),
            )
            return

        conflict_details = ""
        if issues:
            conflict_details = (
                f"\n\n{format_rename_plan_issues(issues)}"
                "\nКонфликтующие файлы получат свободный номер."
            )

        reply = self.show_russian_message_box(
            "Переименование исходников",
            f"Изменятся имена {len(files_to_rename)} файлов или папок в их исходных папках.{conflict_details}",
            QMessageBox.Icon.Question,
            True,
            yes_text="Переименовать",
            no_text="Отмена",
            destructive=True,
        )

        if reply:
            show_starting = getattr(self, "_show_operation_starting", None)
            if callable(show_starting):
                show_starting(
                    f"Подготовка переименования {len(files_to_rename)} файлов..."
                )
            request = RenameRequest(tuple(
                (file.path, name) for file, name in zip(files_to_rename, new_names, strict=True)
            ))
            if not self._start_operation(request, files_to_rename):
                return
            self.log_event(f"Переименование: {len(files_to_rename)} файлов")
            if callable(getattr(self, "_show_progress_dialog", None)):
                self._show_progress_dialog(
                    f"Переименование {len(files_to_rename)} файлов..."
                )

    def _remove_missing_files_from_queue(self) -> bool:
        """Удаляет из очереди файлы, которых больше нет на диске."""
        is_running = getattr(self, "_operation_is_running", None)
        if callable(is_running) and is_running():
            return False

        remaining_files = [
            file_item
            for file_item in self.files
            if not getattr(file_item, "is_file", False)
            or os.path.isfile(getattr(file_item, "path", ""))
        ]
        if len(remaining_files) == len(self.files):
            return False

        self.files = remaining_files
        return True

    def refresh_queue_paths(self) -> None:
        """Синхронизирует очередь с текущим состоянием файловой системы."""
        if self._remove_missing_files_from_queue():
            self.update_file_list()
            self.update_file_info()

    def update_file_list(self):
        """Обновление отображения списка"""
        if not self.files:
            self.list_files.clear()
            if callable(getattr(self, "on_file_selection_changed", None)):
                self.on_file_selection_changed()
                return
            if callable(getattr(self, "update_convert_button_state", None)):
                self.update_convert_button_state()
            if callable(getattr(self, "_update_compress_button", None)):
                self._update_compress_button()
            if callable(getattr(self, "_update_merge_button_state", None)):
                self._update_merge_button_state()
            return

        filtered_files = (
            self._get_filtered_files()
            if hasattr(self, "_get_filtered_files")
            else self.files
        )
        self.list_files.set_files(filtered_files)
        if callable(getattr(self, "on_file_selection_changed", None)):
            self.on_file_selection_changed()
            return
        if callable(getattr(self, "_auto_select_compress_type", None)):
            self._auto_select_compress_type()
        if callable(getattr(self, "_update_merge_button_state", None)):
            self._update_merge_button_state()
