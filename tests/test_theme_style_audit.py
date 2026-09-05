import re
import unittest
from pathlib import Path

from app.ui.theme_styles import LIGHT_APPLICATION_STYLE

from app.ui.ui_styles import (
    MENU_STYLE_DARK,
    MENU_STYLE_LIGHT,
    build_operations_tab_bar_style,
    standard_palette,
)


def _hex_luminance(value: str) -> float:
    value = value.lstrip("#")
    rgb = [int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_hex_luminance(a), _hex_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class ThemeStyleAuditTests(unittest.TestCase):
    def test_standard_field_text_contrast(self):
        for theme in ("light", "dark"):
            palette = standard_palette(theme)
            self.assertGreaterEqual(_contrast(palette["fg"], palette["bg"]), 4.5)
            self.assertGreaterEqual(_contrast(palette["disabled_fg"], palette["disabled_bg"]), 4.0)

    def test_menu_disabled_items_have_theme_specific_color(self):
        self.assertIn("QMenu::item:disabled", MENU_STYLE_LIGHT)
        self.assertIn("color: #6f7785", MENU_STYLE_LIGHT)
        self.assertIn("QMenu::item:disabled", MENU_STYLE_DARK)
        self.assertIn("color: #a8a8a8", MENU_STYLE_DARK)

    def test_operations_tabs_keep_selected_underline_without_hover_override(self):
        light = build_operations_tab_bar_style("light")
        dark = build_operations_tab_bar_style("dark")
        for style in (light, dark):
            self.assertIn("border-bottom: 1px solid #3d74b3", style)
            self.assertNotIn("QTabBar#operations_tab_bar::tab:hover", style)

    def test_light_theme_does_not_reintroduce_dark_template_surface(self):
        light = LIGHT_APPLICATION_STYLE
        self.assertNotIn("#383838", light)
        self.assertTrue("alternate-background-color: #eef1f5" in light or "alternate-background-color: #f8fafc" in light)

    def test_template_manager_light_alternating_rows_are_light(self):
        source = Path("app/ui/mixins/template_crud_mixin.py").read_text(encoding="utf-8")
        start = source.index('if self._get_effective_theme_mode_for_templates() == "light"')
        dark_return = source.index('        return """', source.index('            """', start) + 1)
        light_block = source[start:dark_return]
        self.assertIn("alternate-background-color: #eef1f5", light_block)
        self.assertNotIn("alternate-background-color: #454545", light_block)

    def test_disclosure_icon_uses_current_theme(self):
        source = Path("app/ui/ui_components.py").read_text(encoding="utf-8")
        self.assertRegex(source, re.compile(r'QColor\("#1f2328" if theme == "light" else "#f0f0f0"\)'))
        self.assertIn("def refresh_theme_icon", source)

    def test_runtime_refreshes_buttons_and_operation_tabs(self):
        source = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        self.assertIn("refresh_standard_button_styles(self)", source)
        self.assertIn("self._apply_operations_tab_bar_theme(mode)", source)


    def test_light_menu_popup_uses_white_surface(self):
        self.assertIn("background-color: #ffffff", MENU_STYLE_LIGHT)

    def test_light_file_panel_and_list_surface_stay_white(self):
        ui_main = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        self.assertIn('background-color: #ffffff;', ui_main)
        self.assertNotIn('background-color: #f3f3f3;\n                        border: none;\n                        border-radius: 4px;', ui_main)
        self.assertNotIn('right_layout.addSpacing(SPACE_SM)', ui_main)


if __name__ == "__main__":
    unittest.main()
