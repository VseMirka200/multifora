import unittest
from pathlib import Path


class ConversionOutputWiringTests(unittest.TestCase):
    def test_conversion_ui_does_not_embed_output_destination_field(self):
        source = Path("app/ui/mixins/operations_tab_layout_mixin.py").read_text(encoding="utf-8")
        self.assertNotIn('"Сохранение:"', source)
        self.assertNotIn("convert_output_mode_combo", source)
        self.assertNotIn("input_convert_output_path", source)

    def test_conversion_action_asks_destination_at_run_time(self):
        source = Path("app/ui/mixins/conversion_actions_mixin.py").read_text(encoding="utf-8")
        self.assertIn("_ask_conversion_output_destination", source)
        self.assertIn('"Рядом с исходником"', source)
        self.assertIn('"Выбрать папку…"', source)
        self.assertIn("output_dir=output_dir", source)
        self.assertIn('"conversion_output_dir": output_dir', source)

    def test_retry_preserves_conversion_output_dir(self):
        source = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        self.assertIn('output_dir=self._last_operation.get("conversion_output_dir", "")', source)

    def test_last_custom_conversion_folder_is_persisted(self):
        source = Path("app/core/settings.py").read_text(encoding="utf-8")
        self.assertIn('"conversion_output_path"', source)


if __name__ == "__main__":
    unittest.main()
