from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from app.core.conversion_formats import (
    CONVERSION_CATEGORIES,
    DOCUMENT_CATEGORY,
    category_for_file_type,
    compatible_targets_for_source,
    is_mixed_source_label,
    matches_format,
    target_formats_for_category,
)
from app.core.models import FileItem

_CATEGORY_PLACEHOLDER = "Выберите тип файла:"
_TARGET_PLACEHOLDER = "Выберите целевой формат:"

_OPTIMIZED_DOCUMENT_ROUTES: dict[tuple[str, str], str] = {
    ("DOC", "PDF"): "word_to_pdf",
    ("DOCX", "PDF"): "word_to_pdf",
    ("PDF", "DOCX"): "pdf_to_word",
    ("DOCX", "ODT"): "word_to_odt",
    ("ODT", "DOCX"): "odt_to_word",
    ("ODT", "PDF"): "odt_to_pdf",
    ("PDF", "ODT"): "pdf_to_odt",
}


class ConversionActionsMixin:
    """Содержит UI-логику запуска конвертации файлов."""

    def _schedule_conversion_settings_save(self) -> None:
        callback = getattr(self, "_schedule_settings_save", None)
        if callable(callback):
            callback()

    def _conversion_custom_output_path(self) -> str:
        return str(getattr(self, "conversion_output_path", "") or "").strip()

    def _selected_file_items(self) -> list[FileItem]:
        list_widget = getattr(self, "list_files", None)
        if list_widget is None:
            return []

        selected_files: list[FileItem] = []
        for item in list_widget.selectedItems():
            file_item = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(file_item, FileItem) and file_item.is_file:
                selected_files.append(file_item)
        return selected_files

    def _initial_conversion_folder(self) -> str:
        current_path = self._conversion_custom_output_path()
        if current_path and os.path.isdir(current_path):
            return current_path

        selected_files = self._selected_file_items()
        if selected_files:
            return os.path.dirname(selected_files[0].path)

        files = getattr(self, "files", []) or []
        if not files:
            return ""
        return os.path.dirname(str(getattr(files[0], "path", "") or ""))

    def select_conversion_output_folder(self) -> str:
        """Запрашивает общую папку результата; пустая строка означает отмену."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сконвертированных файлов",
            self._initial_conversion_folder(),
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return ""

        normalized_folder = os.path.normpath(folder)
        self.conversion_output_path = normalized_folder
        self._schedule_conversion_settings_save()
        return normalized_folder

    def _ask_conversion_output_destination(
        self,
        *,
        file_count: int,
        source_label: str,
        target_label: str,
    ) -> tuple[bool, str]:
        """Запрашивает место сохранения результатов конвертации.

        Возвращает пару ``(подтверждено, папка)``. Пустая папка означает режим
        ``Конвертированные`` рядом с каждым исходным файлом.
        """
        while True:
            box = QMessageBox(self)
            box.setWindowTitle("Сохранение конвертации")
            box.setIcon(QMessageBox.Icon.Question)
            box.setText("Куда сохранить сконвертированные файлы?")
            box.setInformativeText(
                f"Файлов: {file_count}\n"
                f"Конвертация: {source_label} → {target_label}\n\n"
                "Можно создать папку «Конвертированные» рядом с каждым "
                "исходным файлом или выбрать общую папку."
            )

            source_button = box.addButton(
                "Рядом с исходником",
                QMessageBox.ButtonRole.AcceptRole,
            )
            custom_button = box.addButton(
                "Выбрать папку…",
                QMessageBox.ButtonRole.ActionRole,
            )
            cancel_button = box.addButton(
                "Отмена",
                QMessageBox.ButtonRole.RejectRole,
            )
            box.setDefaultButton(source_button)
            box.setEscapeButton(cancel_button)
            box.exec()

            clicked_button = box.clickedButton()
            if clicked_button is source_button:
                self.conversion_output_mode = "source_subfolder"
                self._schedule_conversion_settings_save()
                return True, ""

            if clicked_button is custom_button:
                folder = self.select_conversion_output_folder()
                if folder:
                    self.conversion_output_mode = "custom"
                    self._schedule_conversion_settings_save()
                    return True, folder
                # Возвращаемся к выбору назначения, чтобы отмена системного
                # диалога папки не запускала и не отменяла конвертацию сама.
                continue

            return False, ""

    @staticmethod
    def _display_category_for_file(file_item: FileItem) -> str:
        return category_for_file_type(file_item.file_type) or ""

    def _selected_convert_category(self) -> str:
        combo = getattr(self, "convert_file_type_combo", None)
        if combo is None:
            return ""
        return str(combo.currentText() or "").strip()

    def _file_matches_convert_category(
        self,
        file_item: FileItem,
        category_label: str,
    ) -> bool:
        normalized_category = str(category_label or "").strip()
        if not normalized_category or normalized_category == _CATEGORY_PLACEHOLDER:
            return True
        return self._display_category_for_file(file_item) == normalized_category

    def update_to_combo_based_on_from(self) -> None:
        """Обновляет список целей для точного или смешанного источника."""
        category_label = self._selected_convert_category()
        source_combo = getattr(self, "from_convert_combo", None)
        target_combo = getattr(self, "to_convert_combo", None)
        if source_combo is None or target_combo is None:
            return

        source_label = str(source_combo.currentText() or "").strip()
        target_combo.blockSignals(True)
        try:
            target_combo.clear()
            target_combo.addItem(_TARGET_PLACEHOLDER)

            valid_source = (
                category_label in CONVERSION_CATEGORIES
                and source_combo.currentIndex() > 0
                and bool(source_label)
            )
            if not valid_source:
                target_combo.setEnabled(False)
                return

            targets = compatible_targets_for_source(category_label, source_label)
            for target in targets:
                target_combo.addItem(target)
            target_combo.setEnabled(bool(targets))
        finally:
            target_combo.blockSignals(False)
            self.update_convert_button_state()

    def update_convert_button_state(self) -> None:
        """Синхронизирует доступность кнопки с текущим выбором пользователя."""
        source_combo = getattr(self, "from_convert_combo", None)
        target_combo = getattr(self, "to_convert_combo", None)
        list_widget = getattr(self, "list_files", None)

        category_selected = self._selected_convert_category()
        source_selected = source_combo is not None and source_combo.currentIndex() > 0
        target_selected = target_combo is not None and target_combo.currentIndex() > 0
        has_files = bool(list_widget is not None and list_widget.selectedItems())

        self.btn_convert.setEnabled(
            has_files
            and category_selected in CONVERSION_CATEGORIES
            and source_selected
            and target_selected
        )

        refresh_preview = getattr(self, "refresh_conversion_preview", None)
        if callable(refresh_preview):
            refresh_preview(show_empty_warning=False)

    def _validate_conversion_selection(
        self,
        category_label: str,
        source_label: str,
        target_label: str,
    ) -> bool:
        if category_label not in CONVERSION_CATEGORIES:
            QMessageBox.warning(self, "Ошибка", "Выберите тип файла для конвертации!")
            return False

        source_combo = getattr(self, "from_convert_combo", None)
        target_combo = getattr(self, "to_convert_combo", None)
        if (
            source_combo is None
            or target_combo is None
            or source_combo.currentIndex() <= 0
            or target_combo.currentIndex() <= 0
        ):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Выберите исходный и целевой форматы!",
            )
            return False

        if target_label not in target_formats_for_category(category_label):
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Целевой формат {target_label} не поддерживается.",
            )
            return False

        return bool(source_label)

    def _collect_compatible_conversion_files(
        self,
        category_label: str,
        source_label: str,
        target_label: str,
    ) -> tuple[list[FileItem], int]:
        files: list[FileItem] = []
        skipped_same_target = 0
        mixed_mode = is_mixed_source_label(category_label, source_label)

        for file_item in self._selected_file_items():
            if not self._file_matches_convert_category(file_item, category_label):
                continue
            if not self._check_file_compatibility_dual(file_item, source_label):
                continue
            if mixed_mode and matches_format(file_item.path, target_label):
                skipped_same_target += 1
                continue
            files.append(file_item)

        return files, skipped_same_target

    def _show_empty_conversion_selection_message(
        self,
        *,
        source_label: str,
        target_label: str,
        skipped_same_target: int,
    ) -> None:
        if skipped_same_target:
            QMessageBox.information(
                self,
                "Конвертация",
                f"Все выбранные файлы уже имеют формат {target_label}.",
            )
            return

        QMessageBox.warning(
            self,
            "Ошибка",
            f"Среди выбранных файлов нет совместимых с режимом «{source_label}».",
        )

    @staticmethod
    def _resolve_conversion_type(
        category_label: str,
        source_label: str,
        target_label: str,
    ) -> str:
        if category_label != DOCUMENT_CATEGORY:
            return "auto_image"
        if is_mixed_source_label(category_label, source_label):
            return "auto_document"
        return _OPTIMIZED_DOCUMENT_ROUTES.get(
            (source_label, target_label),
            "auto_document",
        )

    def convert_files_dual_combo(self) -> None:
        """Конвертирует один или несколько исходных форматов в общий целевой."""
        source_combo = getattr(self, "from_convert_combo", None)
        target_combo = getattr(self, "to_convert_combo", None)
        if source_combo is None or target_combo is None:
            return

        category_label = self._selected_convert_category()
        source_label = str(source_combo.currentText() or "").strip()
        target_label = str(target_combo.currentText() or "").strip()

        if not self._validate_conversion_selection(
            category_label,
            source_label,
            target_label,
        ):
            return

        selected_files = self._selected_file_items()
        if not selected_files:
            QMessageBox.warning(self, "Ошибка", "Выберите файлы для конвертации!")
            return

        files, skipped_same_target = self._collect_compatible_conversion_files(
            category_label,
            source_label,
            target_label,
        )
        if not files:
            self._show_empty_conversion_selection_message(
                source_label=source_label,
                target_label=target_label,
                skipped_same_target=skipped_same_target,
            )
            return

        accepted, output_dir = self._ask_conversion_output_destination(
            file_count=len(files),
            source_label=source_label,
            target_label=target_label,
        )
        if not accepted or not self.create_file_worker():
            return

        conversion_type = self._resolve_conversion_type(
            category_label,
            source_label,
            target_label,
        )
        self.file_worker.set_conversion(
            files,
            conversion_type,
            target_label,
            output_dir=output_dir,
        )
        self._last_operation = {
            "op": "convert",
            "file_category": category_label,
            "conversion_type": conversion_type,
            "conversion_format": target_label,
            "conversion_output_dir": output_dir,
            "file_paths": [file_item.path for file_item in files],
        }
        self.file_worker.start()

        show_progress = getattr(self, "_show_progress_dialog", None)
        if callable(show_progress):
            skipped_suffix = (
                f" (пропущено уже готовых: {skipped_same_target})"
                if skipped_same_target
                else ""
            )
            show_progress(
                f"Конвертация {len(files)} файлов в {target_label}{skipped_suffix}..."
            )

    def _check_file_compatibility_dual(
        self,
        file_item: FileItem,
        from_format: str,
    ) -> bool:
        """Проверяет файл для точного или смешанного режима источника."""
        category_label = self._selected_convert_category()
        if is_mixed_source_label(category_label, from_format):
            return self._display_category_for_file(file_item) == category_label
        return matches_format(file_item.path, from_format)
