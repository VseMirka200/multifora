import unittest
from pathlib import Path


class ConversionOutputWiringTests(unittest.TestCase):
    def test_conversion_ui_embeds_output_destination_controls(self):
        source = Path("app/ui/mixins/operations_tab_layout_mixin.py").read_text(encoding="utf-8")
        self.assertIn('"Способ сохранения:"', source)
        self.assertIn("combo_conversion_output_mode", source)
        self.assertIn("input_conversion_output_path", source)
        self.assertIn("btn_select_conversion_output_folder", source)

    def test_conversion_destination_is_not_duplicated_in_settings(self):
        source = Path("app/ui/mixins/settings_panel_mixin.py").read_text(encoding="utf-8")
        self.assertNotIn("conversion_output_mode_combo", source)
        self.assertNotIn("conversion_output_path_row", source)
        self.assertNotIn('"Конвертация"', source)

    def test_conversion_action_supports_inline_and_prompt_destinations(self):
        source = Path("app/ui/mixins/conversion_actions_mixin.py").read_text(encoding="utf-8")
        self.assertIn("on_conversion_output_mode_changed", source)
        self.assertIn("input_conversion_output_path", source)
        self.assertIn("_ask_conversion_output_destination", source)
        self.assertIn('"Рядом с файлом"', source)
        self.assertIn('"В папку «Конвертированные»"', source)
        self.assertIn('"Выбрать папку…"', source)
        self.assertIn("output_dir=output_dir", source)
        self.assertIn('"conversion_output_dir": output_dir', source)

    def test_retry_preserves_conversion_output_dir(self):
        source = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        self.assertIn('output_dir=self._last_operation.get("conversion_output_dir", "")', source)
        self.assertIn('"conversion_output_mode", "source_subfolder"', source)

    def test_last_custom_conversion_folder_is_persisted(self):
        source = Path("app/core/settings.py").read_text(encoding="utf-8")
        self.assertIn('"conversion_output_path"', source)
        self.assertIn('"conversion_output_mode"', source)


if __name__ == "__main__":
    unittest.main()
