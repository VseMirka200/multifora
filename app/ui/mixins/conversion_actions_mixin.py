# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.core.models import FileItem
from app.core.conversion_formats import (
    CONVERSION_CATEGORIES,
    category_for_file_type,
    format_for_path,
    formats_for_category,
    matches_format,
    suffix_for_format,
)


class ConversionActionsMixin:
    @staticmethod
    def _convert_formats_for_category(category: str) -> list[str]:
        return formats_for_category(category)

    @staticmethod
    def _convert_source_format_label(file_item) -> str | None:
        return format_for_path(getattr(file_item, "path", ""))

    @staticmethod
    def _convert_target_suffix(format_label: str) -> str:
        return suffix_for_format(format_label)

    @staticmethod
    def _file_category_label(file_item) -> str:
        return str(getattr(file_item, "file_type", "")).lower()

    @staticmethod
    def _display_category_for_file(file_item) -> str:
        return category_for_file_type(getattr(file_item, "file_type", "")) or ""

    def _selected_convert_category(self) -> str:
        combo = getattr(self, "convert_file_type_combo", None)
        if combo is None:
            return ""
        try:
            return str(combo.currentText() or "").strip()
        except Exception:
            return ""

    def _file_matches_convert_category(self, file_item, category_label: str) -> bool:
        category_label = str(category_label or "").strip()
        if not category_label or category_label == "Выберите тип файла:":
            return True
        return self._display_category_for_file(file_item) == category_label

    def _same_category_target_options(self, category_label: str, source_label: str) -> list[str]:
        source_label = str(source_label or "").strip()
        formats = self._convert_formats_for_category(category_label)
        return [fmt for fmt in formats if fmt != source_label]

    def _populate_combo_items(self, combo, placeholder: str, values: list[str]) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(placeholder)
        for value in values:
            combo.addItem(value)
        combo.blockSignals(False)

    def update_to_combo_based_on_from(self):
        """Обновляет второе выпадающее меню на основе выбора в первом и типа файла."""
        category_label = self._selected_convert_category()
        source_combo = getattr(self, "from_convert_combo", None)
        target_combo = getattr(self, "to_convert_combo", None)
        if source_combo is None or target_combo is None:
            return

        source_label = str(source_combo.currentText() or "").strip()
        allowed_formats = self._convert_formats_for_category(category_label)

        target_combo.blockSignals(True)
        target_combo.clear()
        target_combo.addItem("Выберите целевой формат:")

        if not category_label or not allowed_formats or source_combo.currentIndex() <= 0:
            target_combo.setEnabled(False)
            target_combo.blockSignals(False)
            if callable(getattr(self, "update_convert_button_state", None)):
                self.update_convert_button_state()
            return

        target_formats = self._same_category_target_options(category_label, source_label)
        for target in target_formats:
            target_combo.addItem(target)
        target_combo.setEnabled(True)
        target_combo.blockSignals(False)

        if callable(getattr(self, "update_convert_button_state", None)):
            self.update_convert_button_state()

    def update_convert_button_state(self):
        """Обновляет состояние кнопки конвертации."""
        category_selected = self._selected_convert_category()
        from_selected = getattr(self, "from_convert_combo", None) is not None and self.from_convert_combo.currentIndex() > 0
        to_selected = getattr(self, "to_convert_combo", None) is not None and self.to_convert_combo.currentIndex() > 0
        has_files = bool(getattr(self, "list_files", None) and self.list_files.selectedItems())

        self.btn_convert.setEnabled(
            has_files
            and bool(category_selected)
            and category_selected in CONVERSION_CATEGORIES
            and from_selected
            and to_selected
        )
        if callable(getattr(self, "refresh_conversion_preview", None)):
            self.refresh_conversion_preview(show_empty_warning=False)

    def convert_files_dual_combo(self):
        """Конвертация файлов по категории и выбранным форматам."""
        category_label = self._selected_convert_category()
        source_combo = getattr(self, "from_convert_combo", None)
        target_combo = getattr(self, "to_convert_combo", None)
        if source_combo is None or target_combo is None:
            return

        source_label = str(source_combo.currentText() or "").strip()
        target_label = str(target_combo.currentText() or "").strip()

        if not category_label:
            QMessageBox.warning(self, "Ошибка", "Выберите тип файла для конвертации!")
            return
        if source_combo.currentIndex() <= 0 or target_combo.currentIndex() <= 0:
            QMessageBox.warning(self, "Ошибка", "Выберите исходный и целевой форматы!")
            return

        if category_label not in CONVERSION_CATEGORIES:
            QMessageBox.warning(self, "Ошибка", f"Тип «{category_label}» пока не поддерживается.")
            return

        conversion_type = None
        if category_label == "Документы":
            doc_map = {
                ("DOCX", "PDF"): "word_to_pdf",
                ("PDF", "DOCX"): "pdf_to_word",
                ("DOCX", "ODT"): "word_to_odt",
                ("ODT", "DOCX"): "odt_to_word",
                ("ODT", "PDF"): "odt_to_pdf",
                ("PDF", "ODT"): "pdf_to_odt",
            }
            conversion_type = doc_map.get((source_label, target_label))
        elif category_label == "Фотографии":
            conversion_type = "image_to_image"
        elif category_label in ("Видео", "Звуки"):
            conversion_type = "media_to_media"

        if not conversion_type:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Конвертация из {source_label} в {target_label} пока не поддерживается.",
            )
            return

        selected_items = self.list_files.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите файлы для конвертации!")
            return

        files = []
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if not file_item or not file_item.is_file:
                continue
            if not self._file_matches_convert_category(file_item, category_label):
                continue
            if not self._check_file_compatibility_dual(file_item, source_label):
                continue
            files.append(file_item)

        if not files:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Выберите файлы типа «{category_label}» и формата {source_label} для конвертации!",
            )
            return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Конвертировать {len(files)} файлов типа «{category_label}» из {source_label} в {target_label}?",
            QMessageBox.Icon.Question,
            True,
        )
        if not reply:
            return

        if not self.create_file_worker():
            return

        self.file_worker.set_conversion(files, conversion_type, target_label)
        self._last_operation = {
            "op": "convert",
            "file_category": category_label,
            "conversion_type": conversion_type,
            "conversion_format": target_label,
            "file_paths": [f.path for f in files],
        }
        self.file_worker.start()
        if callable(getattr(self, "_show_progress_dialog", None)):
            self._show_progress_dialog(f"Конвертация {len(files)} файлов...")

    def _check_file_compatibility_dual(self, file_item: FileItem, from_format: str) -> bool:
        """Проверяет соответствие файла выбранному исходному формату."""
        return matches_format(file_item.path, from_format)
