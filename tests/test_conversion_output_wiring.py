import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.core.models import FileItem, OperationFile
from app.ui.operation_controller import OperationController
from app.ui.ui_main import MultiforaMainWindow
from core.operation_requests import ConversionRequest


class ConversionOutputWiringTests(unittest.TestCase):
    def test_conversion_ui_embeds_output_destination_controls(self):
        source = Path(
            "app/ui/mixins/operations_tab_layout_mixin.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"Способ сохранения:"', source)
        self.assertIn("combo_conversion_output_mode", source)
        self.assertIn("input_conversion_output_path", source)
        self.assertIn("btn_select_conversion_output_folder", source)

    def test_conversion_destination_is_not_duplicated_in_settings(self):
        source = Path("app/ui/mixins/settings_panel_mixin.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("conversion_output_mode_combo", source)
        self.assertNotIn("conversion_output_path_row", source)
        self.assertNotIn('"Конвертация"', source)

    def test_conversion_action_supports_inline_and_prompt_destinations(self):
        source = Path("app/ui/mixins/conversion_actions_mixin.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("on_conversion_output_mode_changed", source)
        self.assertIn("input_conversion_output_path", source)
        self.assertIn("_ask_conversion_output_destination", source)
        self.assertIn('"Рядом с файлом"', source)
        self.assertIn('"В папку «Конвертированные»"', source)
        self.assertIn('"Выбрать папку…"', source)
        self.assertIn("output_dir=output_dir", source)

    def test_retry_preserves_conversion_output_dir(self):
        request = ConversionRequest("auto_document", "PDF", "custom", "chosen-folder")
        file = FileItem("failed.docx")
        controller = OperationController()
        window = SimpleNamespace(
            _last_operation_request=request,
            _collect_file_items_by_paths=Mock(return_value=[file]),
            _show_operation_starting=Mock(),
            _show_progress_dialog=Mock(),
            create_file_worker=Mock(return_value=True),
            file_worker=Mock(),
        )
        window._start_operation = lambda request, files: controller.start(window, request, files)
        MultiforaMainWindow._retry_failed_operation(window, [{"path": file.path}, {"message": "Other error"}])
        window._collect_file_items_by_paths.assert_called_once_with([file.path])
        window.create_file_worker.assert_called_once_with(operation="convert_document")
        window.file_worker.set_conversion.assert_called_once_with(
            [OperationFile.from_item(file)], "auto_document", "PDF", output_mode="custom", output_dir="chosen-folder"
        )
        window.file_worker.start.assert_called_once_with()

    def test_last_custom_conversion_folder_is_persisted(self):
        source = Path("app/core/settings.py").read_text(encoding="utf-8")
        self.assertIn('"conversion_output_path"', source)
        self.assertIn('"conversion_output_mode"', source)


if __name__ == "__main__":
    unittest.main()
