import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from app.core.app_utils import _debug_log
from app.core.models import FileItem


class WorkerOpsMixin:
    def _get_selected_or_all_file_items(self) -> list[FileItem]:
        selected_items = self.list_files.selectedItems()
        if selected_items:
            files = []
            for item in selected_items:
                file_item = item.data(Qt.ItemDataRole.UserRole)
                if file_item and file_item.is_file:
                    files.append(file_item)
            return files
        return [file_item for file_item in self.files if getattr(file_item, "is_file", False)]

    def _resolve_merge_output_format(self, files: list[FileItem], selected_format: str) -> str:
        if selected_format == "auto":
            if all(file.path.lower().endswith(".docx") for file in files):
                return "docx"
            return "pdf"
        return selected_format or "pdf"

    def _select_merge_output_path_for_format(self, output_format: str, files: list[FileItem]) -> str:
        extension = "docx" if output_format == "docx" else "pdf"
        filter_text = "Word Document (*.docx)" if extension == "docx" else "PDF Document (*.pdf)"
        start_folder = os.path.dirname(files[0].path) if files else ""
        default_path = os.path.join(start_folder, f"Объединенный_документ.{extension}")

        current_path = ""
        if hasattr(self, "input_merge_output_path") and self.input_merge_output_path is not None:
            current_path = self.input_merge_output_path.text().strip()
        if current_path:
            default_path = current_path

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Куда сохранить объединенный документ",
            default_path,
            f"{filter_text};;Все файлы (*.*)",
        )
        if not file_path:
            return ""

        base, ext = os.path.splitext(file_path)
        if ext.lower() != f".{extension}":
            file_path = f"{base}.{extension}" if base else f"{file_path}.{extension}"
        if hasattr(self, "input_merge_output_path") and self.input_merge_output_path is not None:
            self.input_merge_output_path.setText(file_path)
        return file_path

    def select_merge_output_path(self):
        files = self._get_selected_or_all_file_items()
        selected_format = "pdf"
        if hasattr(self, "combo_merge_format") and self.combo_merge_format is not None:
            selected_format = str(self.combo_merge_format.currentData() or "pdf")
        output_format = self._resolve_merge_output_format(files, selected_format)
        self._select_merge_output_path_for_format(output_format, files)

    def on_merge_format_changed(self):
        if not hasattr(self, "input_merge_output_path") or self.input_merge_output_path is None:
            return
        current_path = self.input_merge_output_path.text().strip()
        if not current_path:
            return
        selected_format = "pdf"
        if hasattr(self, "combo_merge_format") and self.combo_merge_format is not None:
            selected_format = str(self.combo_merge_format.currentData() or "pdf")
        if selected_format == "auto":
            self.input_merge_output_path.clear()
            return
        extension = ".docx" if selected_format == "docx" else ".pdf"
        base, _ext = os.path.splitext(current_path)
        if base:
            self.input_merge_output_path.setText(f"{base}{extension}")

    def convert_files(self, conversion_type: str, target_format: str = ""):
        """Конвертация файлов."""
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите файлы для конвертации!")
            return

        files = []
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if file_item and file_item.is_file:
                if self._check_file_compatibility(file_item, conversion_type):
                    files.append(file_item)

        if not files:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Выберите файлы совместимого формата для конвертации {conversion_type}!",
            )
            return

        operation_name = self.get_conversion_operation_name(conversion_type)
        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Конвертировать {len(files)} файлов в {operation_name}?",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            return

        if not self.create_file_worker():
            return
        self.file_worker.set_conversion(files, conversion_type, target_format)
        self._last_operation = {
            "op": "convert",
            "conversion_type": conversion_type,
            "conversion_format": target_format,
            "file_paths": [f.path for f in files],
        }
        self.file_worker.start()
        self.log_event(f"Конвертация: {len(files)} файлов в {operation_name}")
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(f"Конвертация {len(files)} файлов...")

    def get_conversion_operation_name(self, conversion_type: str) -> str:
        names = {
            "word_to_pdf": "PDF",
            "pdf_to_word": "DOCX",
            "word_to_odt": "ODT",
            "odt_to_word": "DOCX",
            "odt_to_pdf": "PDF",
            "pdf_to_odt": "ODT",
            "pdf_to_image": "изображения",
            "image_to_image": "изображения",
            "media_to_media": "медиафайлы",
        }
        return names.get(conversion_type, conversion_type)

    def compress_files(self):
        """Сжатие файлов."""
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите файлы для сжатия!")
            return

        compress_type = self.combo_compress_type.currentText()
        files = []
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if file_item and file_item.is_file:
                if compress_type == "Изображения":
                    if file_item.file_type == "image":
                        files.append(file_item)
                elif compress_type == "PDF документы":
                    if file_item.path.lower().endswith(".pdf"):
                        files.append(file_item)

        if not files:
            file_type = "изображения (JPG/PNG)" if compress_type == "Изображения" else "PDF документы"
            QMessageBox.warning(self, "Ошибка", f"Выберите {file_type} для сжатия!")
            return

        pdf_method = "auto"
        replace_pdf = False
        replace_image = False
        method_text = ""
        if compress_type == "PDF документы":
            method_text = self.combo_pdf_method.currentText()
            if method_text == "Максимальное сжатие":
                pdf_method = "max"
            elif method_text == "Сохранить качество":
                pdf_method = "quality"
            elif method_text == "Только оптимизация":
                pdf_method = "optimize"
            replace_pdf = self.checkbox_replace_pdf.isChecked() if hasattr(self, "checkbox_replace_pdf") else False
        elif compress_type == "Изображения":
            replace_image = self.checkbox_replace_image.isChecked() if hasattr(self, "checkbox_replace_image") else False

        compression_level = 85
        if compress_type == "Изображения" and hasattr(self, "combo_compression_level"):
            try:
                selected_level = self.combo_compression_level.currentData()
                if isinstance(selected_level, int):
                    compression_level = selected_level
            except Exception:
                compression_level = 85
        file_type = "изображения" if compress_type == "Изображения" else "PDF документы"
        method_info = f" ({method_text})" if compress_type == "PDF документы" else ""

        if compress_type == "PDF документы":
            details = method_info
        else:
            replace_note = ", с заменой оригинала" if replace_image else ", с копией"
            details = f" (уровень: {compression_level}%{replace_note})"
        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Сжать {len(files)} {file_type}{details}?",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            return

        compression_type = "image" if compress_type == "Изображения" else "pdf"
        if not self.create_file_worker():
            return

        self.file_worker.set_compression(
            files,
            compression_level,
            compression_type,
            pdf_method,
            replace_pdf,
            replace_image,
        )
        self._last_operation = {
            "op": "compress",
            "compression_level": compression_level,
            "compression_type": compression_type,
            "pdf_method": pdf_method,
            "replace_pdf": replace_pdf,
            "replace_image": replace_image,
            "file_paths": [f.path for f in files],
        }
        self.file_worker.start()
        if compress_type == "PDF документы":
            self.log_event(f"Сжатие: {len(files)} файлов ({file_type}{method_info})")
        else:
            replace_note = "с заменой оригинала" if replace_image else "с копией"
            self.log_event(f"Сжатие: {len(files)} файлов ({file_type}, {compression_level}%, {replace_note})")
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(f"Сжатие {len(files)} файлов...")
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()
        self.status_bar.showMessage(f"Сжатие {len(files)} файлов...")

    def merge_files(self):
        """Объединение Word/PDF документов в один файл."""
        files = self._get_selected_or_all_file_items()
        if len(files) < 2:
            QMessageBox.warning(self, "Ошибка", "Добавьте или выберите минимум два документа для объединения!")
            return

        selected_format = "pdf"
        if hasattr(self, "combo_merge_format") and self.combo_merge_format is not None:
            selected_data = self.combo_merge_format.currentData()
            if selected_data:
                selected_format = str(selected_data)
        output_format = self._resolve_merge_output_format(files, selected_format)

        if output_format == "docx":
            if not all(file.path.lower().endswith(".docx") for file in files):
                QMessageBox.warning(self, "Ошибка", "Для результата DOCX выберите только файлы DOCX.")
                return
            format_label = "DOCX"
        else:
            if not all(file.path.lower().endswith((".doc", ".docx", ".pdf")) for file in files):
                QMessageBox.warning(self, "Ошибка", "Для объединения выберите документы Word или PDF.")
                return
            format_label = "PDF"

        output_path = ""
        if hasattr(self, "input_merge_output_path") and self.input_merge_output_path is not None:
            output_path = self.input_merge_output_path.text().strip()
        if not output_path:
            output_path = self._select_merge_output_path_for_format(output_format, files)
            if not output_path:
                return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Объединить {len(files)} документов в один {format_label}?\n\nСохранить:\n{output_path}",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            return

        if not self.create_file_worker():
            return

        self.file_worker.set_merge(files, output_format, output_path)
        self._last_operation = {
            "op": "merge",
            "output_format": output_format,
            "output_path": output_path,
            "file_paths": [f.path for f in files],
        }
        self.file_worker.start()
        self.log_event(f"Объединение: {len(files)} документов в {format_label}")
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(f"Объединение {len(files)} документов...")
        self.status_bar.showMessage(f"Объединение {len(files)} документов...")

    def _check_file_compatibility(self, file_item: FileItem, conversion_type: str) -> bool:
        if conversion_type == "word_to_pdf":
            return file_item.path.lower().endswith((".doc", ".docx"))
        if conversion_type == "pdf_to_word":
            return file_item.path.lower().endswith(".pdf")
        if conversion_type == "odt_to_pdf":
            return file_item.path.lower().endswith(".odt")
        if conversion_type == "pdf_to_odt":
            return file_item.path.lower().endswith(".pdf")
        if conversion_type == "pdf_to_image":
            return file_item.path.lower().endswith(".pdf")
        return False

    def on_operation_finished(self, result):
        """Завершение операции."""
        errors = []
        if isinstance(result, dict):
            new_files = result.get("new_files", [])
            updated_files = result.get("updated_files", [])
            errors = result.get("errors", [])
        else:
            new_files = result
            updated_files = []

        if not errors and self._operation_errors:
            errors = self._operation_errors
        self._operation_errors = []

        if self._is_undo_operation:
            if errors:
                if self._pending_undo_entry:
                    self._rename_history.append(self._pending_undo_entry)
            else:
                if self._pending_undo_entry:
                    self._push_rename_redo(self._pending_undo_entry)
            self._pending_undo_entry = None
        elif self._is_redo_operation:
            if errors:
                if self._pending_redo_entry:
                    self._rename_redo_history.append(self._pending_redo_entry)
            else:
                if self._pending_redo_entry:
                    self._push_rename_history(self._pending_redo_entry)
            self._pending_redo_entry = None
        else:
            if self._last_operation and self._last_operation.get("op") == "rename" and updated_files:
                undo_pairs = []
                for file_item, new_path in updated_files:
                    old_path = getattr(file_item, "path", None)
                    if old_path:
                        undo_pairs.append((new_path, old_path))
                if undo_pairs:
                    self._push_rename_history(
                        {
                            "op": "rename",
                            "pairs": undo_pairs,
                            "label": f"Переименовано {len(undo_pairs)} файлов",
                        }
                    )
        self._is_undo_operation = False
        self._is_redo_operation = False

        self.log_event(
            f"Операция завершена. Получено {self._ru_files_label(len(new_files))} новых, "
            f"обновлено {self._ru_files_label(len(updated_files))}.",
            "INFO",
        )

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel_operation.setVisible(False)
        self.btn_cancel_operation.setEnabled(True)
        if callable(getattr(self, "_hide_progress_dialog", None)):
            self._hide_progress_dialog()
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()

        auto_clear = self.auto_clear_checkbox.isChecked()
        if auto_clear:
            self.files.clear()
            self.list_files.clear()
            self.update_file_info()
            self.status_bar.showMessage("Операция завершена. Список файлов очищен.")
        else:
            changed = False
            if updated_files:
                for file_item, new_path in updated_files:
                    try:
                        file_item.path = new_path
                        file_item.update_info()
                    except Exception as exc:
                        _debug_log(f"update_info error for {new_path}: {exc}")
                changed = True

            if new_files:
                _debug_log(f"Добавляю {len(new_files)} новых файлов в список")
                for file_item in new_files:
                    if file_item not in self.files:
                        self.files.append(file_item)
                changed = True

            if changed:
                self.update_file_list()
                self.update_file_info()
                if callable(getattr(self, "refresh_active_file_preview", None)):
                    self.refresh_active_file_preview()

            if updated_files and new_files:
                self.status_bar.showMessage(
                    "Операция завершена. "
                    f"Создано {self._ru_files_label(len(new_files))}, "
                    f"обновлено {self._ru_files_label(len(updated_files))}."
                )
            elif updated_files:
                self.status_bar.showMessage(
                    f"Операция завершена. Обновлено {self._ru_files_label(len(updated_files))}."
                )
            else:
                self.status_bar.showMessage(
                    f"Операция завершена. Создано {self._ru_files_label(len(new_files))}."
                )

        persist_history = getattr(self, "_persist_rename_history_state", None)
        if callable(persist_history):
            persist_history()

        if self._pending_close and not (self.file_worker and self.file_worker.isRunning()):
            self._pending_close = False
            QTimer.singleShot(0, self.close)

    def on_operation_error(self, error_msg):
        """Ошибка операции."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel_operation.setVisible(False)
        self.btn_cancel_operation.setEnabled(True)
        if callable(getattr(self, "_hide_progress_dialog", None)):
            self._hide_progress_dialog()
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()
        self._operation_errors.append({"message": error_msg})
        self.log_event(f"Ошибка операции: {error_msg}", "ERROR")
        self.status_bar.showMessage("Ошибка при выполнении операции")
        if self._pending_close and not (self.file_worker and self.file_worker.isRunning()):
            self._pending_close = False
            QTimer.singleShot(0, self.close)

        errors = self._operation_errors
        if errors:
            lines = []
            for entry in errors[:5]:
                msg = entry.get("message", "")
                name = entry.get("name")
                if name and name not in msg:
                    msg = f"{name}: {msg}"
                lines.append(f"• {msg}")
            more = ""
            if len(errors) > 5:
                more = f"\n...и еще {len(errors) - 5}"
            text = (
                "Обнаружены ошибки в некоторых файлах:\n"
                + "\n".join(lines)
                + more
                + "\n\nПовторить только ошибки?"
            )
            reply = self.show_russian_message_box(
                "Ошибки операции",
                text,
                QMessageBox.Icon.Warning,
                True,
            )
            if reply:
                self._retry_failed_operation(errors)
