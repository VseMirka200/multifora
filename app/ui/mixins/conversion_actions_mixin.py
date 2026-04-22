# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.core.models import FileItem


class ConversionActionsMixin:
    def update_to_combo_based_on_from(self):
        """Обновляет второе выпадающее меню на основе выбора в первом."""
        from_format = self.from_convert_combo.currentText()
        self.to_convert_combo.clear()
        self.to_convert_combo.addItem("Выберите целевой формат...")

        if from_format == "Выберите исходный формат..." or from_format == "Выберите исходный формат:":
            self.to_convert_combo.setEnabled(False)
            self.btn_convert.setEnabled(False)
            if callable(getattr(self, "refresh_conversion_preview", None)):
                self.refresh_conversion_preview(show_empty_warning=False)
            return

        self.to_convert_combo.setEnabled(True)

        # Определяем возможные целевые форматы на основе исходного
        format_mapping = {
            "DOC/DOCX": ["PDF", "ODT (OpenDocument)"],
            "PDF": ["DOC/DOCX", "ODT (OpenDocument)", "Изображения (JPG/PNG)"],
            "ODT (OpenDocument)": ["PDF", "DOC/DOCX"],
            "Изображения (JPG/PNG)": ["PDF"],
        }

        targets = format_mapping.get(from_format, [])
        for target in targets:
            self.to_convert_combo.addItem(target)

        # Подключаем обработчик изменения второго комбобокса
        if not hasattr(self, "to_combo_changed_connected"):
            self.to_convert_combo.currentIndexChanged.connect(self.update_convert_button_state)
            self.to_combo_changed_connected = True

        if callable(getattr(self, "refresh_conversion_preview", None)):
            self.refresh_conversion_preview(show_empty_warning=False)

    def update_convert_button_state(self):
        """Обновляет состояние кнопки конвертации."""
        from_selected = self.from_convert_combo.currentIndex() > 0
        to_selected = self.to_convert_combo.currentIndex() > 0

        self.btn_convert.setEnabled(from_selected and to_selected)
        if callable(getattr(self, "refresh_conversion_preview", None)):
            self.refresh_conversion_preview(show_empty_warning=False)

    def convert_files_dual_combo(self):
        """Конвертация файлов на основе выбора в двух комбобоксах."""
        from_format = self.from_convert_combo.currentText()
        to_format = self.to_convert_combo.currentText()

        if not from_format or not to_format:
            QMessageBox.warning(self, "Ошибка", "Выберите исходный и целевой форматы!")
            return

        # Определяем тип конвертации на основе выбора
        conversion_map = {
            ("DOC/DOCX", "PDF"): "word_to_pdf",
            ("PDF", "DOC/DOCX"): "pdf_to_word",
            ("DOC/DOCX", "ODT (OpenDocument)"): "word_to_odt",
            ("ODT (OpenDocument)", "DOC/DOCX"): "odt_to_word",
            ("ODT (OpenDocument)", "PDF"): "odt_to_pdf",
            ("PDF", "ODT (OpenDocument)"): "pdf_to_odt",
            ("PDF", "Изображения (JPG/PNG)"): "pdf_to_image",
            ("Изображения (JPG/PNG)", "PDF"): "image_to_pdf",
        }

        conversion_type = conversion_map.get((from_format, to_format))

        if not conversion_type:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Конвертация из {from_format} в {to_format} не поддерживается!",
            )
            return

        selected_items = self.list_files.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите файлы для конвертации!")
            return

        files = []
        for item in selected_items:
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if file_item and file_item.is_file:
                if self._check_file_compatibility_dual(file_item, from_format):
                    files.append(file_item)

        if not files:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Выберите файлы формата {from_format} для конвертации!",
            )
            return

        reply = self.show_russian_message_box(
            "Подтверждение",
            f"Конвертировать {len(files)} файлов из {from_format} в {to_format}?",
            QMessageBox.Icon.Question,
            True,
        )

        if reply:
            if not self.create_file_worker():
                return
            self.file_worker.set_conversion(files, conversion_type, to_format)
            self._last_operation = {
                "op": "convert",
                "conversion_type": conversion_type,
                "conversion_format": to_format,
                "file_paths": [f.path for f in files],
            }
            self.file_worker.start()
            if callable(getattr(self, "_show_progress_dialog", None)):
                self._show_progress_dialog(f"Конвертация {len(files)} файлов...")

    def _check_file_compatibility_dual(self, file_item: FileItem, from_format: str) -> bool:
        """Проверяет совместимость файла с выбранным исходным форматом."""
        if "DOC/DOCX" in from_format:
            return file_item.path.lower().endswith((".doc", ".docx"))
        if "PDF" in from_format:
            return file_item.path.lower().endswith(".pdf")
        if "ODT" in from_format:
            return file_item.path.lower().endswith(".odt")
        if "Изображения" in from_format:
            return file_item.path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"))
        return False

    def convert_word_files(self):
        """Конвертация Word файлов."""
        conversion_type = self.word_convert_combo.currentText()

        if conversion_type == "DOC/DOCX → PDF":
            self.convert_files("word_to_pdf")
        elif conversion_type == "PDF → DOCX":
            self.convert_files("pdf_to_word")

    def convert_pdf_files(self):
        """Конвертация PDF файлов."""
        conversion_type = self.pdf_convert_combo.currentText()

        if conversion_type == "PDF → Изображения":
            self.convert_files("pdf_to_image")
