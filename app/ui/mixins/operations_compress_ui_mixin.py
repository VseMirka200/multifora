
import os

from PyQt6.QtWidgets import QFileDialog

from app.core.app_utils import _log_ignored_error
from app.ui.ui_components import selected_file_items


class OperationsCompressUiMixin:
    # Согласует параметры сжатия с типами выбранных файлов и доступными средствами.
    def _auto_select_compress_type(self):
        if not hasattr(self, "list_files") or not hasattr(self, "combo_compress_type"):
            return

        candidates = selected_file_items(self.list_files, files_only=True)
        if not candidates:
            candidates = [
                file_item
                for file_item in getattr(self, "files", [])
                if getattr(file_item, "is_file", False)
            ]

        has_pdf = False
        has_image = False
        for file_item in candidates:
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
        selected_files = selected_file_items(self.list_files, files_only=True)
        if not selected_files:
            return False

        compress_type = self.combo_compress_type.currentText() if hasattr(self, "combo_compress_type") else ""
        for file_item in selected_files:
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

        if (
            hasattr(self, "combo_compress_type")
            and self.combo_compress_type.currentText() == "Изображения"
            and self._image_output_mode() == "custom"
        ):
            can_compress = can_compress and bool(self._image_output_path())

        # Не импортируем библиотеки конвертации при запуске интерфейса.
        # Наличие конкретного backend проверяется worker-ом только при старте операции.
        self.btn_compress.setEnabled(can_compress)

    def _image_output_mode(self) -> str:
        combo = getattr(self, "combo_image_output_mode", None)
        mode = str(combo.currentData() or "alongside") if combo is not None else "alongside"
        return mode if mode in {"replace", "alongside", "custom"} else "alongside"

    def _image_output_path(self) -> str:
        field = getattr(self, "input_image_output_path", None)
        if field is not None:
            return str(field.text() or "").strip()
        return str(getattr(self, "image_compression_output_path", "") or "").strip()

    def _sync_compress_mode_stack_height(self, target=None) -> None:
        """Fits the mode stack to dynamic controls of the currently shown page."""
        stack = getattr(self, "compress_mode_stack", None)
        if stack is None:
            return
        target = target or stack.currentWidget()
        if target is None:
            return

        try:
            target_layout = target.layout()
            if target_layout is not None:
                target_layout.invalidate()
                target_layout.activate()
            target.updateGeometry()
            stack.setFixedHeight(target.sizeHint().height())
            stack.updateGeometry()
        except Exception as error:
            _log_ignored_error(
                "OperationsCompressUiMixin._sync_compress_mode_stack_height",
                error,
            )

    def on_image_output_mode_changed(self, *_args):
        mode = self._image_output_mode()
        self.image_compression_output_mode = mode
        custom_enabled = mode == "custom"

        path_section = getattr(self, "image_output_path_section", None)
        if path_section is not None:
            path_section.setVisible(custom_enabled)
        path_field = getattr(self, "input_image_output_path", None)
        if path_field is not None:
            path_field.setEnabled(custom_enabled)
        select_button = getattr(self, "btn_select_image_output_path", None)
        if select_button is not None:
            select_button.setEnabled(custom_enabled)

        self._sync_compress_mode_stack_height(
            getattr(self, "image_mode_widget", None)
        )

        self._update_compress_button()
        callback = getattr(self, "_schedule_settings_save", None)
        if callable(callback):
            callback()
        self._refresh_compression_preview_if_available()

    def select_image_output_folder(self):
        initial_path = self._image_output_path()
        if not initial_path or not os.path.isdir(initial_path):
            selected_files = selected_file_items(getattr(self, "list_files", None))
            if selected_files:
                file_item = selected_files[0]
                initial_path = os.path.dirname(str(getattr(file_item, "path", "") or ""))

        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сжатых изображений",
            initial_path,
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return

        normalized_path = os.path.normpath(folder)
        self.image_compression_output_path = normalized_path
        self.input_image_output_path.setText(normalized_path)
        self._update_compress_button()
        callback = getattr(self, "_schedule_settings_save", None)
        if callable(callback):
            callback()

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
                self._sync_compress_mode_stack_height(target)

        if hasattr(self, "compress_tips_label") and self.compress_tips_label is not None:
            self.compress_tips_label.setVisible(bool(tips_text))
            self.compress_tips_label.setMaximumHeight(16777215 if tips_text else 0)

        if hasattr(self, "compress_info_label") and self.compress_info_label is not None:
            self.compress_info_label.setVisible(False)
            self.compress_info_label.setMaximumHeight(0)

        self._update_compress_button()
        if callable(getattr(self, "refresh_compression_preview", None)):
            self.refresh_compression_preview(show_empty_warning=False)

    def _refresh_compression_preview_if_available(self, *_args):
        refresh_preview = getattr(self, "refresh_compression_preview", None)
        if callable(refresh_preview):
            refresh_preview(show_empty_warning=False)

    def on_pdf_method_changed(self, method_text: str):
        if not hasattr(self, "pdf_method_warning_label"):
            return
        if "Максимальное сжатие" in method_text:
            self.pdf_method_warning_label.setVisible(True)
        else:
            self.pdf_method_warning_label.setVisible(False)
        self._refresh_compression_preview_if_available()
