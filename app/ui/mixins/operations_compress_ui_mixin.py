
from PyQt6.QtCore import Qt

from app.core.app_utils import _log_ignored_error


class OperationsCompressUiMixin:
    # Согласует параметры сжатия с типами выбранных файлов и доступными средствами.
    def _auto_select_compress_type(self):
        if not hasattr(self, "list_files") or not hasattr(self, "combo_compress_type"):
            return

        selected_items = self.list_files.selectedItems()
        if not selected_items:
            return

        has_pdf = False
        has_image = False
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if not file_item or not file_item.is_file:
                continue
            if str(getattr(file_item, "path", "")).lower().endswith(".pdf"):
                has_pdf = True
            elif getattr(file_item, "file_type", "") == "image":
                has_image = True

        target_text = None
        if has_pdf and not has_image:
            target_text = "PDF документы"
        elif has_image and not has_pdf:
            target_text = "Изображения"

        if not target_text:
            return

        try:
            current_text = self.combo_compress_type.currentText()
        except Exception:
            current_text = ""
        if current_text == target_text:
            return

        try:
            self.combo_compress_type.blockSignals(True)
            self.combo_compress_type.setCurrentText(target_text)
        finally:
            self.combo_compress_type.blockSignals(False)
        self.on_compress_type_changed(target_text)

    def _has_selected_files_for_current_compress_type(self) -> bool:
        if not hasattr(self, "list_files"):
            return False
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            return False

        compress_type = self.combo_compress_type.currentText() if hasattr(self, "combo_compress_type") else ""
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if not file_item or not file_item.is_file:
                continue
            if compress_type == "PDF документы":
                if file_item.path.lower().endswith(".pdf"):
                    return True
            else:
                if file_item.file_type == "image":
                    return True
        return False

    def _update_compress_button(self):
        if not hasattr(self, "btn_compress"):
            return

        can_compress = self._has_selected_files_for_current_compress_type()

        if hasattr(self, "file_worker") and self.file_worker and self.file_worker.isRunning():
            can_compress = False

        # Не импортируем библиотеки конвертации при запуске интерфейса.
        # Наличие конкретного backend проверяется worker-ом только при старте операции.
        self.btn_compress.setEnabled(can_compress)

    def on_compress_type_changed(self, compress_type):
        # Пустые подсказки не должны увеличивать высоту панели сжатия.
        is_pdf_mode = "PDF" in str(compress_type)

        tips_text = ""
        if hasattr(self, "compress_tips_label") and self.compress_tips_label is not None:
            tips_text = self.compress_tips_label.text().strip()

        if hasattr(self, "compress_mode_stack") and self.compress_mode_stack is not None:
            target = (
            getattr(self, "pdf_mode_widget", None)
            if is_pdf_mode
            else getattr(self, "image_mode_widget", None)
        )
            if target is not None:
                self.compress_mode_stack.setCurrentWidget(target)
                try:
                    self.compress_mode_stack.setFixedHeight(target.sizeHint().height())
                except Exception as error:
                    _log_ignored_error("OperationsCompressUiMixin.on_compress_type_changed", error)

        if hasattr(self, "compress_tips_label") and self.compress_tips_label is not None:
            self.compress_tips_label.setVisible(bool(tips_text))
            self.compress_tips_label.setMaximumHeight(16777215 if tips_text else 0)

        if hasattr(self, "compress_info_label") and self.compress_info_label is not None:
            self.compress_info_label.setVisible(False)
            self.compress_info_label.setMaximumHeight(0)

        self._update_compress_button()
        if callable(getattr(self, "refresh_compression_preview", None)):
            self.refresh_compression_preview(show_empty_warning=False)

    def _refresh_compression_preview_if_available(self):
        refresh_preview = getattr(self, "refresh_compression_preview", None)
        if callable(refresh_preview):
            refresh_preview(show_empty_warning=False)

    def on_replace_pdf_checked(self, _state):
        self._refresh_compression_preview_if_available()

    def on_replace_image_checked(self, _state):
        self._refresh_compression_preview_if_available()

    def on_pdf_method_changed(self, method_text: str):
        if not hasattr(self, "pdf_method_warning_label"):
            return
        if "Максимальное сжатие" in method_text:
            self.pdf_method_warning_label.setVisible(True)
        else:
            self.pdf_method_warning_label.setVisible(False)
        self._refresh_compression_preview_if_available()

    def on_compression_level_changed(self, _index: int):
        self._refresh_compression_preview_if_available()
