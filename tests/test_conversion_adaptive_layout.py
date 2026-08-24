import unittest
from pathlib import Path


class ConversionAdaptiveLayoutTests(unittest.TestCase):
    def test_menu_like_combo_elides_long_selected_text(self):
        source = Path("app/ui/ui_components.py").read_text(encoding="utf-8")
        self.assertIn("metrics.elidedText", source)
        self.assertIn("Qt.TextElideMode.ElideRight", source)
        self.assertIn("self.setToolTip(text)", source)

    def test_menu_like_combo_can_shrink_with_operations_panel(self):
        source = Path("app/ui/ui_components.py").read_text(encoding="utf-8")
        self.assertIn("QSizePolicy.Policy.Ignored", source)
        self.assertIn("def minimumSizeHint(self):", source)

    def test_conversion_destination_is_prompted_instead_of_embedded(self):
        layout_source = Path("app/ui/mixins/operations_tab_layout_mixin.py").read_text(encoding="utf-8")
        action_source = Path("app/ui/mixins/conversion_actions_mixin.py").read_text(encoding="utf-8")
        self.assertNotIn('"Сохранение:"', layout_source)
        self.assertIn('"Куда сохранить сконвертированные файлы?"', action_source)
        self.assertIn('"Рядом с исходником"', action_source)
        self.assertIn('"Выбрать папку…"', action_source)


if __name__ == "__main__":
    unittest.main()
