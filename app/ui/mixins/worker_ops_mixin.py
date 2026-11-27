import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.core.app_utils import _debug_log
from app.ui.file_table import operation_file_items, selected_file_items
from app.ui.merge_pages import choose_merge_pages
from core.file_models import FileItem, OperationFile, OperationSource
from core.filesystem import normalized_path_key
from core.operation_requests import CompressionRequest, ConversionRequest, MergeRequest, RenameRequest
from core.operation_result import OperationResult


class WorkerOpsMixin:
    # Передаёт выбранные файлы рабочему потоку и обновляет UI по результатам операций.
    def _get_operation_file_items(self, *, files_only=False) -> list[FileItem]:
        visible = self._get_filtered_files() if hasattr(self, "_get_filtered_files") else self.files
        return operation_file_items(
            self.files, files_only=files_only, visible_files=visible, is_checked=self.list_files.model().is_checked
        )

    def _get_selected_or_all_file_items(self) -> list[FileItem]:
        return self._get_operation_file_items(files_only=True)

    def _should_auto_clear_after_operation(self) -> bool:
        enabled_checkbox = getattr(self, "auto_clear_enabled_checkbox", None)
        if enabled_checkbox is None or not enabled_checkbox.isChecked():
            return False
        request = self._last_operation_request
        if isinstance(request, ConversionRequest) and request.sample:
            return False
        operation = request.kind if request is not None else ""
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
        self, output_format: str, files: list[FileItem], *, allow_pdf=False
    ) -> str:
        extension = "docx" if output_format == "docx" else "pdf"
        filter_text = (
            "Документ DOCX (*.docx)"
            if extension == "docx"
            else "PDF Document (*.pdf)"
        )
        start_folder = os.path.dirname(files[0].path) if files else ""
        default_path = os.path.join(
            start_folder, f"Объединенный_документ.{extension}"
        )

        pdf_filter = "PDF Document (*.pdf)"
        filters = [filter_text]
        if allow_pdf:
            filters.append(pdf_filter)
        filters.append("Все файлы (*.*)")
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Куда сохранить объединенный документ",
            default_path,
            ";;".join(filters),
        )
        if not file_path:
            return ""

        if allow_pdf and selected_filter == pdf_filter:
            extension = "pdf"
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
        if hasattr(self, "list_files"):
            selected = selected_file_items(self.list_files, files_only=True)
            if selected:
                files = selected
        output_format = self._detect_merge_output_format(files)
        valid_files = len(files) >= 2 and output_format is not None
        panel = getattr(self, "merge_pages_panel", None)
        if panel is not None and self._active_operation_id() == "merge":
            sources = files
            panel.set_files(sources)
            valid_files = panel.ready and panel.pages.count() >= 2 and output_format is not None
        button.setEnabled(valid_files and not self._operation_start_block_reason())
        button.setToolTip(self._operation_start_block_reason() or (
            "Объединить выбранные документы" if valid_files
            else "Добавьте документы одного формата с двумя или более страницами"
        ))

    def _compression_files(self, candidates):
        if self.combo_compress_type.currentText() == "Изображения":
            return [item for item in candidates if item.file_type == "image"]
        return [item for item in candidates if item.path.lower().endswith(".pdf")]

    def compress_files(self):
        """Сжатие файлов."""
        if not self._ensure_operation_can_start():
            return
        selected_files = self._get_selected_or_all_file_items()
        if not selected_files:
            QMessageBox.warning(self, "Ошибка", "Добавьте файлы для сжатия!")
            return

        compress_type = self.combo_compress_type.currentText()
        files = self._compression_files(selected_files)

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

        replaces_source = replace_pdf or image_output_mode == "replace"
        if compress_type == "PDF документы":
            destination = "с заменой исходников" if replace_pdf else "с созданием копий"
            details = f"{method_info} · {destination}"
        else:
            destination_labels = {
                "replace": "с заменой исходников",
                "alongside": "рядом с исходниками",
                "custom": f"в папку {image_output_dir}",
            }
            quality = f"качество JPEG/WebP: {compression_level}%, " if self._image_quality_applies(files) else ""
            details = f" ({quality}{destination_labels[image_output_mode]})"
        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Сжать {len(files)} {file_type}{details}?",
            QMessageBox.Icon.Question,
            True,
            yes_text="Заменить исходники" if replaces_source else "Сжать файлы",
            no_text="Отмена",
            destructive=replaces_source,
        )
        if not reply:
            return

        compression_type = "image" if compress_type == "Изображения" else "pdf"
        show_starting = getattr(self, "_show_operation_starting", None)
        if callable(show_starting):
            show_starting(f"Подготовка сжатия {len(files)} файлов...")
        request = CompressionRequest(
            compression_level,
            compression_type,
            pdf_method,
            replace_pdf,
            image_output_mode,
            image_output_dir,
        )
        if not self._start_operation(request, files):
            return
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
        if not self._ensure_operation_can_start():
            return
        files = self._get_selected_or_all_file_items()
        panel = getattr(self, "merge_pages_panel", None)
        if panel is not None:
            self._update_merge_button_state()
            if not panel.ready:
                return
            files = list(panel.files)
            order = panel.page_order()
        else:
            order = ()
        kind = self._detect_merge_output_format(files)
        if len(files) < 2 or kind is None:
            QMessageBox.warning(self, "Объединение", "Выберите минимум два PDF или два DOCX.")
            return
        # Editable DOCX can be joined only as complete documents, in document order.
        full_order = not order or (panel is not None and len(order) == panel.pages.count() and list(order) == sorted(order))
        output_kind = kind if full_order else "pdf"
        output = self._select_merge_output_path_for_format(output_kind, files, allow_pdf=(kind == "docx" and full_order))
        if not output:
            return
        if os.path.exists(output):
            QMessageBox.warning(self, "Объединение", "Выберите новое имя: существующие файлы не перезаписываются.")
            return
        output_kind = "docx" if output.lower().endswith(".docx") else "pdf"
        warning = "\nПроверьте разделы, колонтитулы и разметку после объединения." if output_kind == "docx" else ""
        if not self.show_russian_message_box("Подтверждение", f"Объединить документы в {output_kind.upper()}?\n{output}{warning}", QMessageBox.Icon.Question, True):
            return
        if self._start_operation(MergeRequest(output_kind, output, () if output_kind == "docx" else order), files):
            self._show_progress_dialog("Объединение документов…")

    def on_operation_finished(self, result):
        """Завершение операции."""
        QTimer.singleShot(0, self, self._refresh_launch_button_states)
        if not isinstance(result, OperationResult):
            result = OperationResult(
                new_files=result.get("new_files", []) if hasattr(result, "get") else result,
                updated_files=result.get("updated_files", []) if hasattr(result, "get") else [],
                errors=result.get("errors", []) if hasattr(result, "get") else [],
                warnings=result.get("warnings", []) if hasattr(result, "get") else [],
                cancelled=bool(result.get("cancelled")) if hasattr(result, "get") else False,
            )
        if not result.errors and self._operation_errors:
            result.errors = self._operation_errors
        self._operation_errors = []
        new_files, updated_files = result.new_files, result.updated_files
        request = self._last_operation_request
        self.operation_result_panel.set_result(
            result,
            can_retry=request is not None and not isinstance(request, MergeRequest),
        )

        if self._is_undo_operation:
            if (result.errors or result.cancelled) and self._pending_undo_entry:
                moved = {normalized_path_key(source.path) for source, _ in updated_files}
                pending = self._pending_undo_entry
                pairs = [(path, target) for path, target in pending["pairs"] if normalized_path_key(path) not in moved]
                if pairs:
                    self._rename_history.append({**pending, "pairs": pairs, "count": len(pairs)})
            self._pending_undo_entry = None
        else:
            if (
                isinstance(self._last_operation_request, RenameRequest)
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

        self.progress_dialog.reset()
        if callable(getattr(self, "_update_compress_button", None)):
            self._update_compress_button()

        if (result.outcome == "success"
                and not isinstance(self._last_operation_request, MergeRequest)
                and self._should_auto_clear_after_operation()):
            self.files.clear()
            self.list_files.clear()
            self.update_file_info()
            self.status_bar.showMessage(
                "Операция завершена. Список очищен, файлы на диске сохранены."
            )
            self._close_after_operation()
            return

        changed = False
        if updated_files:
            self._apply_operation_updates(updated_files)
            changed = True

        if new_files and not isinstance(self._last_operation_request, MergeRequest):
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

        self.status_bar.clearMessage()

        self._close_after_operation()

    def _close_after_operation(self):
        if not self._pending_close:
            return
        if self._operation_is_running():
            QTimer.singleShot(50, self._close_after_operation)
            return
        self._pending_close = False
        QTimer.singleShot(0, self.close)

    def _apply_operation_updates(self, updates: list[tuple[OperationSource, str]]) -> None:
        # Пакет может обменять пути двух строк. Сопоставляем их до первого изменения.
        rows = {normalized_path_key(item.path): item for item in self.files}
        for source, new_path in updates:
            item = rows.get(normalized_path_key(source.path)) if isinstance(source, OperationFile) else source
            if item is None:
                continue
            try:
                item.path = new_path
                item.update_info()
            except Exception as exc:
                _debug_log(f"update_info error for {new_path}: {exc}")

    def on_operation_error(self, error_msg):
        """Аварийная ошибка: сообщаем при окончательном сигнале finished."""
        self._operation_errors.append({"message": str(error_msg)})
        self.log_event(f"Критическая ошибка операции: {error_msg}", "ERROR")
