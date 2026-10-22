import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from app.core.app_utils import _debug_log
from app.core.models import FileItem
from app.ui.ui_components import selected_file_items


class WorkerOpsMixin:
    # Передаёт выбранные файлы рабочему потоку и обновляет UI по результатам операций.
    def _get_selected_or_all_file_items(self) -> list[FileItem]:
        files = selected_file_items(self.list_files, files_only=True)
        if files:
            return files
        return [
            file_item
            for file_item in self.files
            if getattr(file_item, "is_file", False)
        ]

    def _should_auto_clear_after_operation(self) -> bool:
        enabled_checkbox = getattr(self, "auto_clear_enabled_checkbox", None)
        if enabled_checkbox is None or not enabled_checkbox.isChecked():
            return False
        operation = str((self._last_operation or {}).get("op", ""))
        checkbox_names = {
            "rename": "auto_clear_rename_checkbox",
            "convert": "auto_clear_convert_checkbox",
            "merge": "auto_clear_merge_checkbox",
            "compress": "auto_clear_compress_checkbox",
        }
        checkbox = getattr(self, checkbox_names.get(operation, ""), None)
        return bool(checkbox is not None and checkbox.isChecked())

    @staticmethod
    def _detect_merge_output_format(files: list[FileItem]) -> str | None:
        extensions = {
            os.path.splitext(str(getattr(file, "path", "")))[1].lower()
            for file in files
        }
        if extensions == {".pdf"}:
            return "pdf"
        if extensions == {".docx"}:
            return "docx"
        return None

    def _select_merge_output_path_for_format(
        self, output_format: str, files: list[FileItem]
    ) -> str:
        extension = "docx" if output_format == "docx" else "pdf"
        filter_text = (
            "Word Document (*.docx)"
            if extension == "docx"
            else "PDF Document (*.pdf)"
        )
        start_folder = os.path.dirname(files[0].path) if files else ""
        default_path = os.path.join(
            start_folder, f"Объединенный_документ.{extension}"
        )

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
            file_path = (
                f"{base}.{extension}" if base else f"{file_path}.{extension}"
            )
        return file_path

    def _update_merge_button_state(self, *_args):
        button = getattr(self, "btn_merge", None)
        if button is None:
            return

        files = (
            self._get_selected_or_all_file_items()
            if hasattr(self, "list_files")
            else []
        )
        output_format = self._detect_merge_output_format(files)
        valid_files = len(files) >= 2 and output_format is not None
        button.setEnabled(valid_files)

    def compress_files(self):
        """Сжатие файлов."""
        if not self._ensure_operation_can_start():
            return
        selected_files = self._get_selected_or_all_file_items()
        if not selected_files:
            QMessageBox.warning(self, "Ошибка", "Добавьте файлы для сжатия!")
            return

        compress_type = self.combo_compress_type.currentText()
        if compress_type == "Изображения":
            files = [
                file_item
                for file_item in selected_files
                if file_item.file_type == "image"
            ]
        else:
            files = [
                file_item
                for file_item in selected_files
                if file_item.path.lower().endswith(".pdf")
            ]

        if not files:
            file_type = (
                "изображения (JPG/PNG)"
                if compress_type == "Изображения"
                else "PDF документы"
            )
            QMessageBox.warning(
                self, "Ошибка", f"В списке нет подходящих файлов: {file_type}."
            )
            return

        pdf_method = "auto"
        replace_pdf = False
        image_output_mode = "alongside"
        image_output_dir = ""
        method_text = ""
        if compress_type == "PDF документы":
            method_text = self.combo_pdf_method.currentText()
            if method_text == "Максимальное сжатие":
                pdf_method = "max"
            elif method_text == "Сохранить качество":
                pdf_method = "quality"
            elif method_text == "Только оптимизация":
                pdf_method = "optimize"
            replace_pdf = (
                self.checkbox_replace_pdf.isChecked()
                if hasattr(self, "checkbox_replace_pdf")
                else False
            )
        elif compress_type == "Изображения":
            image_output_mode = self._image_output_mode()
            if image_output_mode == "custom":
                image_output_dir = self._image_output_path()
                if not image_output_dir:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Выберите папку для сжатых изображений.",
                    )
                    return

        compression_level = 85
        if compress_type == "Изображения" and hasattr(
            self, "combo_compression_level"
        ):
            try:
                selected_level = self.combo_compression_level.currentData()
                if isinstance(selected_level, int):
                    compression_level = selected_level
            except Exception:
                compression_level = 85
        file_type = (
            "изображения"
            if compress_type == "Изображения"
            else "PDF документы"
        )
        method_info = (
            f" ({method_text})" if compress_type == "PDF документы" else ""
        )

        if compress_type == "PDF документы":
            details = method_info
        else:
            destination_labels = {
                "replace": "с заменой исходников",
                "alongside": "рядом с исходниками",
                "custom": f"в папку {image_output_dir}",
            }
            details = f" (уровень: {compression_level}%, {destination_labels[image_output_mode]})"
        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Сжать {len(files)} {file_type}{details}?",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            return

        compression_type = "image" if compress_type == "Изображения" else "pdf"
        show_starting = getattr(self, "_show_operation_starting", None)
        if callable(show_starting):
            show_starting(f"Подготовка сжатия {len(files)} файлов...")
        if not self.create_file_worker():
            hide_progress = getattr(self, "_hide_progress_dialog", None)
            if callable(hide_progress):
                hide_progress()
            return

        self.file_worker.set_compression(
            files,
            compression_level,
            compression_type,
            pdf_method,
            replace_pdf,
            image_output_mode,
            image_output_dir,
        )
        self._last_operation = {
            "op": "compress",
            "compression_level": compression_level,
            "compression_type": compression_type,
            "pdf_method": pdf_method,
            "replace_pdf": replace_pdf,
            "image_output_mode": image_output_mode,
            "image_output_dir": image_output_dir,
            "file_paths": [f.path for f in files],
        }
        self.file_worker.start()
        if compress_type == "PDF документы":
            self.log_event(
                f"Сжатие: {len(files)} файлов ({file_type}{method_info})"
            )
        else:
            self.log_event(f"Сжатие: {len(files)} файлов{details}")
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(f"Сжатие {len(files)} файлов...")
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()
        self.status_bar.showMessage(f"Сжатие {len(files)} файлов...")

    def merge_files(self):
        """Объединение документов одинакового формата в один файл."""
        if not self._ensure_operation_can_start():
            return
        files = self._get_selected_or_all_file_items()
        if len(files) < 2:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Добавьте или выберите минимум два документа для объединения!",
            )
            return

        missing_paths = [
            file.path for file in files if not os.path.isfile(file.path)
        ]
        if missing_paths:
            for file in files:
                if file.path in missing_paths:
                    file.update_info()
            self.update_file_list()
            QMessageBox.warning(
                self,
                "Исходный файл недоступен",
                "Эти документы больше не существуют по указанному пути "
                "или недоступны:\n\n"
                + "\n".join(f"• {path}" for path in missing_paths)
                + "\n\nУдалите их из списка или добавьте снова.",
            )
            return

        output_format = self._detect_merge_output_format(files)
        if output_format is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Можно объединять только файлы одного формата: PDF с PDF или DOCX с DOCX.",
            )
            return

        if output_format == "docx":
            if not all(file.path.lower().endswith(".docx") for file in files):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Для результата DOCX выберите только файлы DOCX.",
                )
                return
            format_label = "DOCX"
        else:
            if not all(file.path.lower().endswith(".pdf") for file in files):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Для результа PDF выберите только файлы PDF.",
                )
                return
            format_label = "PDF"

        output_path = self._select_merge_output_path_for_format(
            output_format, files
        )
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

        show_starting = getattr(self, "_show_operation_starting", None)
        if callable(show_starting):
            show_starting(f"Подготовка объединения {len(files)} документов...")
        # У объединения свой лёгкий воркер. Не создаём здесь FileWorker:
        # его стек конвертации и сжатия импортирует необязательные backend'ы,
        # из-за чего окно подготовки может выглядеть зависшим до старта потока.
        from core.workers.merge.merge_worker import MergeWorker

        self.file_worker = MergeWorker(files, output_format, output_path)
        self.file_worker.progress.connect(self.progress_bar.setValue)
        self.file_worker.status.connect(self.on_worker_status)
        self.file_worker.finished.connect(self.on_operation_finished)
        self.file_worker.error.connect(self.on_operation_error)
        self._last_operation = {
            "op": "merge",
            "output_format": output_format,
            "output_path": output_path,
            "file_paths": [f.path for f in files],
        }
        self.file_worker.start()
        self.log_event(
            f"Объединение: {len(files)} документов в {format_label}"
        )
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(
                f"Объединение {len(files)} документов..."
            )
        self.status_bar.showMessage(f"Объединение {len(files)} документов...")

    def on_operation_finished(self, result):
        """Завершение операции."""
        errors = []
        warnings = []
        if hasattr(result, "get"):
            new_files = result.get("new_files", [])
            updated_files = result.get("updated_files", [])
            errors = result.get("errors", [])
            warnings = result.get("warnings", [])
        else:
            new_files = result
            updated_files = []

        if not errors and self._operation_errors:
            errors = self._operation_errors
        self._operation_errors = []

        if self._is_undo_operation:
            if errors and self._pending_undo_entry:
                self._rename_history.append(self._pending_undo_entry)
            self._pending_undo_entry = None
        else:
            if (
                self._last_operation
                and self._last_operation.get("op") == "rename"
                and updated_files
            ):
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

        if (
            not errors
            and not warnings
            and self._should_auto_clear_after_operation()
        ):
            self.files.clear()
            self.list_files.clear()
            self.update_file_info()
            self.status_bar.showMessage(
                "Операция завершена. Список очищен, файлы на диске сохранены."
            )
            if self._pending_close and not (
                self.file_worker and self.file_worker.isRunning()
            ):
                self._pending_close = False
                QTimer.singleShot(0, self.close)
            return

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

        if warnings:
            lines = [f"• {entry.get('message', '')}" for entry in warnings[:8]]
            extra = (
                f"\n…и ещё {len(warnings) - 8}" if len(warnings) > 8 else ""
            )
            QMessageBox.warning(
                self,
                "Предупреждения о результате",
                "Некоторые документы преобразованы только как текст.\n"
                + "\n".join(lines)
                + extra,
            )
        if errors:
            self._offer_retry_for_errors(errors)

        if self._pending_close and not (
            self.file_worker and self.file_worker.isRunning()
        ):
            self._pending_close = False
            QTimer.singleShot(0, self.close)

    def on_operation_error(self, error_msg):
        """Аварийная ошибка: сообщаем при окончательном сигнале finished."""
        self._operation_errors.append({"message": str(error_msg)})
        self.log_event(f"Критическая ошибка операции: {error_msg}", "ERROR")

    def _offer_retry_for_errors(self, errors: list[dict]) -> None:
        grouped_errors: dict[str, list[dict]] = {}
        for entry in errors:
            error_message = str(entry.get("message", ""))
            grouped_errors.setdefault(error_message, []).append(entry)

        lines = []
        for error_message, entries in list(grouped_errors.items())[:8]:
            count = len(entries)
            suffix = f"\n  Затронуто файлов: {count}." if count > 1 else ""
            lines.append(f"• {error_message}{suffix}")
        remaining = len(grouped_errors) - 8
        more = f"\n• …и ещё {remaining} причин" if remaining > 0 else ""
        non_retryable_markers = ("недопустимый символ", "ошибка плана")
        retryable_errors = [
            entry
            for entry in errors
            if entry.get("path")
            and not any(
                marker in str(entry.get("message", "")).casefold()
                for marker in non_retryable_markers
            )
        ]
        can_retry = bool(
            self._last_operation
            and self._last_operation.get("op")
            in {"rename", "convert", "compress"}
            and retryable_errors
        )
        message = (
            f"Не удалось обработать {self._ru_files_label(len(errors))}.\n\n"
            "Причина:\n"
            + "\n".join(lines)
            + more
        )
        if can_retry:
            message += "\n\nПовторить только файлы с временными ошибками?"
        reply = self.show_russian_message_box(
            "Не удалось завершить операцию",
            message,
            QMessageBox.Icon.Warning,
            can_retry,
        )
        if can_retry and reply:
            self._retry_failed_operation(retryable_errors)
