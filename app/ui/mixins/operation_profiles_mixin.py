from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import QMessageBox

from app.ui.ui_components import get_russian_text_input


class OperationProfilesMixin:
    """Сохраняет и восстанавливает параметры любой вкладки операций."""

    def _current_operation_label(self) -> str:
        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is None or tab_bar.currentIndex() < 0:
            return ""
        return str(tab_bar.tabText(tab_bar.currentIndex()) or "").strip()

    def _collect_operation_profile(self) -> dict:
        operation = self._current_operation_label()
        data: dict[str, object] = {}
        if operation == "Переименование":
            data = {
                "template": getattr(self, "current_template", ""),
                "template_data": self.get_current_template_data() or {},
                "conflict_policy": self.rename_conflict_policy.currentData() or "unique",
            }
        elif operation == "Конвертация":
            data = {
                "category": self.convert_file_type_combo.currentText(),
                "source": self.from_convert_combo.currentText(),
                "target": self.to_convert_combo.currentText(),
                "output_mode": getattr(self, "conversion_output_mode", "source_subfolder"),
                "output_path": getattr(self, "conversion_output_path", ""),
            }
        elif operation == "Объединение":
            data = {
                "format": self.combo_merge_format.currentData() or "pdf",
                "output_path": self.input_merge_output_path.text(),
            }
        elif operation == "Метаданные":
            data = {
                "fields": sorted(
                    key
                    for key, checkbox in self.metadata_field_checkboxes.items()
                    if checkbox.isChecked()
                )
            }
        elif operation == "Сжатие":
            data = {
                "type": self.combo_compress_type.currentText(),
                "image_quality": self.combo_compression_level.currentData(),
                "pdf_method": self.combo_pdf_method.currentText(),
                "replace_pdf": self.checkbox_replace_pdf.isChecked(),
                "replace_image": self.checkbox_replace_image.isChecked(),
            }
        return {"operation": operation, "data": data}

    def _refresh_operation_profiles_combo(self, selected_name: str = "") -> None:
        combo = getattr(self, "operation_profile_combo", None)
        if combo is None:
            return
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Профили операций", "")
        profiles = getattr(self, "operation_profiles", {})
        if isinstance(profiles, dict):
            for name in sorted(profiles, key=str.casefold):
                combo.addItem(str(name), str(name))
        index = combo.findData(selected_name) if selected_name else 0
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def save_current_operation_profile(self) -> None:
        profile = self._collect_operation_profile()
        if not profile.get("operation"):
            return
        default_name = f"{profile['operation']} {len(self.operation_profiles) + 1}"
        name, accepted = get_russian_text_input(
            self,
            title="Сохранение профиля",
            label="Название профиля:",
            text=default_name,
        )
        name = str(name or "").strip()
        if not accepted or not name:
            return
        if name in self.operation_profiles:
            replace = self.show_russian_message_box(
                "Профиль уже существует",
                f"Заменить профиль «{name}»?",
                QMessageBox.Icon.Question,
                True,
            )
            if not replace:
                return
        profile["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.operation_profiles[name] = profile
        self._refresh_operation_profiles_combo(name)
        self.save_settings()
        self.status_bar.showMessage(f"Профиль сохранён: {name}")

    def delete_selected_operation_profile(self) -> None:
        combo = getattr(self, "operation_profile_combo", None)
        name = str(combo.currentData() or "") if combo is not None else ""
        if not name or name not in self.operation_profiles:
            return
        accepted = self.show_russian_message_box(
            "Удаление профиля",
            f"Удалить профиль «{name}»?",
            QMessageBox.Icon.Question,
            True,
        )
        if not accepted:
            return
        del self.operation_profiles[name]
        self._refresh_operation_profiles_combo()
        self.save_settings()
        self.status_bar.showMessage(f"Профиль удалён: {name}")

    def apply_selected_operation_profile(self, *_args) -> None:
        combo = getattr(self, "operation_profile_combo", None)
        name = str(combo.currentData() or "") if combo is not None else ""
        profile = self.operation_profiles.get(name) if name else None
        if not isinstance(profile, dict):
            return
        operation = str(profile.get("operation") or "")
        data = profile.get("data")
        if not isinstance(data, dict):
            return

        tab_bar = getattr(self, "operations_tab_bar", None)
        if tab_bar is not None:
            for index in range(tab_bar.count()):
                if tab_bar.tabText(index) == operation:
                    tab_bar.setCurrentIndex(index)
                    break

        if operation == "Переименование":
            template = str(data.get("template") or "")
            index = self.combo_templates.findText(template)
            if index >= 0:
                self.combo_templates.setCurrentIndex(index)
                self.apply_template_data(template, data.get("template_data") or {})
            policy_index = self.rename_conflict_policy.findData(data.get("conflict_policy", "unique"))
            self.rename_conflict_policy.setCurrentIndex(max(0, policy_index))
            self.refresh_rename_preview(show_empty_warning=False)
        elif operation == "Конвертация":
            self.convert_file_type_combo.setCurrentText(str(data.get("category") or ""))
            self.from_convert_combo.setCurrentText(str(data.get("source") or ""))
            self.to_convert_combo.setCurrentText(str(data.get("target") or ""))
            self.conversion_output_mode = str(data.get("output_mode") or "source_subfolder")
            self.conversion_output_path = str(data.get("output_path") or "")
        elif operation == "Объединение":
            index = self.combo_merge_format.findData(data.get("format", "pdf"))
            self.combo_merge_format.setCurrentIndex(max(0, index))
            self.input_merge_output_path.setText(str(data.get("output_path") or ""))
        elif operation == "Метаданные":
            fields = {str(value) for value in data.get("fields", [])}
            for key, checkbox in self.metadata_field_checkboxes.items():
                checkbox.setChecked(key in fields)
        elif operation == "Сжатие":
            self.combo_compress_type.setCurrentText(str(data.get("type") or "Изображения"))
            index = self.combo_compression_level.findData(data.get("image_quality", 85))
            self.combo_compression_level.setCurrentIndex(max(0, index))
            self.combo_pdf_method.setCurrentText(str(data.get("pdf_method") or "Авто (рекомендуется)"))
            self.checkbox_replace_pdf.setChecked(bool(data.get("replace_pdf", False)))
            self.checkbox_replace_image.setChecked(bool(data.get("replace_image", False)))
        self.status_bar.showMessage(f"Профиль применён: {name}")
