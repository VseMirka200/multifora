import unittest
from pathlib import Path

from app.ui.mixins.appearance_mixin import AppearanceMixin
from app.ui.theme_styles import DARK_APPLICATION_STYLE, LIGHT_APPLICATION_STYLE
from app.ui.typography import BODY_PX
from app.ui.ui_styles import (
    build_drop_zone_surface_style,
    build_operations_help_button_style,
    build_operations_tab_bar_style,
    build_settings_navigation_style,
    build_standard_button_style,
    build_standard_field_style,
    build_template_table_style,
    standard_palette,
)


class _ThemeHost(AppearanceMixin):
    def __init__(self):
        self.theme_mode = "system"
        self.system_theme = "light"
        self.style_applications = []
        self.runtime_refreshes = 0

    def _get_system_theme_mode(self):
        return self.system_theme

    def _apply_application_style(self, theme: str) -> None:
        self.style_applications.append(theme)

    def _apply_theme_runtime_widgets(self):
        self.runtime_refreshes += 1


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
    def test_effective_theme_is_only_applied_when_it_changes(self):
        host = _ThemeHost()

        host.apply_theme_mode("system")
        host.apply_theme_mode("system")
        host.apply_theme_mode("light")

        self.assertEqual(host.style_applications, ["light"])
        self.assertEqual(host.runtime_refreshes, 1)
        self.assertEqual(host.theme_mode, "light")

        host.apply_theme_mode("dark")
        self.assertEqual(host.style_applications, ["light", "dark"])
        self.assertEqual(host.runtime_refreshes, 2)

        host.apply_theme_mode("system")
        self.assertEqual(host.style_applications, ["light", "dark", "light"])
        host.system_theme = "dark"
        host._on_system_theme_changed(None)
        self.assertEqual(
            host.style_applications, ["light", "dark", "light", "dark"]
        )
        self.assertEqual(host.runtime_refreshes, 4)

    def test_settings_hints_are_small_and_theme_aware(self):
        selector = 'QFrame#settings_card QLabel[settingsHint="true"] {'
        for style, color in (
            (DARK_APPLICATION_STYLE, standard_palette("dark")["disabled_fg"]),
            (LIGHT_APPLICATION_STYLE, standard_palette("light")["disabled_fg"]),
        ):
            self.assertIn(selector, style)
            hint_style = style.split(selector, 1)[1].split("}", 1)[0]
            self.assertIn(f"color: {color}", hint_style)
            self.assertIn("font-size: 12px", hint_style)

    def test_button_roles_have_distinct_styles_and_visible_focus(self):
        for theme in ("light", "dark"):
            styles = {
                build_standard_button_style(theme, role)
                for role in ("primary", "danger", "secondary")
            }
            self.assertEqual(len(styles), 3)
            for style in styles:
                self.assertIn("QAbstractButton:focus", style)

    def test_standard_field_text_contrast(self):
        for theme in ("light", "dark"):
            palette = standard_palette(theme)
            self.assertGreaterEqual(
                _contrast(palette["fg"], palette["bg"]), 4.5
            )
            self.assertGreaterEqual(
                _contrast(palette["disabled_fg"], palette["disabled_bg"]), 4.0
            )

    def test_primary_and_danger_colours_remain_legible_in_both_themes(self):
        for theme in ("dark", "light"):
            colors = standard_palette(theme)
            for background in ("accent", "accent_hover", "accent_pressed"):
                self.assertGreaterEqual(_contrast(colors["on_accent"], colors[background]), 4.5)
            for background in ("danger", "danger_hover", "danger_pressed"):
                self.assertGreaterEqual(_contrast(colors["on_danger"], colors[background]), 4.5)
            self.assertGreaterEqual(_contrast(colors["disabled_fg"], colors["disabled_bg"]), 4.5)

    def test_menu_disabled_items_have_theme_specific_color(self):
        self.assertIn("QMenu::item:disabled", LIGHT_APPLICATION_STYLE)
        self.assertIn(f"background-color: {standard_palette('light')['bg']}", LIGHT_APPLICATION_STYLE)
        self.assertIn(f"color: {standard_palette('light')['disabled_fg']}", LIGHT_APPLICATION_STYLE)
        self.assertIn("QMenu::item:disabled", DARK_APPLICATION_STYLE)
        self.assertIn(f"background-color: {standard_palette('dark')['bg']}", DARK_APPLICATION_STYLE)
        self.assertIn(f"color: {standard_palette('dark')['disabled_fg']}", DARK_APPLICATION_STYLE)

    def test_menu_items_have_an_explicit_theme_background(self):
        for style, background, hover in (
            (LIGHT_APPLICATION_STYLE, standard_palette("light")["bg"], standard_palette("light")["hover_bg"]),
            (DARK_APPLICATION_STYLE, standard_palette("dark")["bg"], standard_palette("dark")["hover_bg"]),
        ):
            shared_selector = "QMenu::item,\nQMenu QListWidget#scrollable_filter_list::item {"
            self.assertIn(shared_selector, style)
            menu_items = style.split(shared_selector, 1)[1].split("}", 1)[0]
            self.assertIn(f"background-color: {background}", menu_items)
            self.assertIn("margin: 0px", menu_items)
            self.assertNotIn("background-color: transparent", menu_items)
            menu_hover = style.split(
                "QMenu QListWidget#scrollable_filter_list::item:hover {", 1
            )[1].split("}", 1)[0]
            self.assertIn(f"background-color: {hover}", menu_hover)

    def test_header_dropdown_commands_use_compact_horizontal_padding(self):
        for style in (LIGHT_APPLICATION_STYLE, DARK_APPLICATION_STYLE):
            selector = "QMenu#header_dropdown_popup::item {"
            self.assertIn(selector, style)
            menu_items = style.split(selector, 1)[1].split("}", 1)[0]
            self.assertIn("padding-left: 4px", menu_items)
            self.assertIn("padding-right: 4px", menu_items)

    def test_help_menu_matches_compact_help_button(self):
        for style in (LIGHT_APPLICATION_STYLE, DARK_APPLICATION_STYLE):
            selector = "QMenu#help_menu_popup::item {"
            self.assertIn(selector, style)
            menu_items = style.split(selector, 1)[1].split("}", 1)[0]
            self.assertIn("min-height: 18px", menu_items)
            self.assertIn("max-height: 18px", menu_items)
            self.assertIn("padding: 0px 4px", menu_items)
            self.assertIn("font-size: 12px", menu_items)
            self.assertIn("font-weight: 500", menu_items)

    def test_help_button_uses_larger_text(self):
        for theme in ("light", "dark"):
            style = build_operations_help_button_style(theme)
            base_button = style.split("QPushButton {", 1)[1].split("}", 1)[0]
            self.assertIn("font-size: 12px", base_button)

    def test_scrollable_dropdown_has_vertical_arrow_buttons(self):
        for style, track, handle in (
            (LIGHT_APPLICATION_STYLE, standard_palette("light")["window_bg"], standard_palette("light")["hover_border"]),
            (DARK_APPLICATION_STYLE, standard_palette("dark")["window_bg"], standard_palette("dark")["hover_border"]),
        ):
            scrollbar = style.split(
                "QMenu QListWidget#scrollable_filter_list QScrollBar:vertical {",
                1,
            )[1].split("}", 1)[0]
            self.assertIn(f"background-color: {track}", scrollbar)
            scroll_handle = style.split(
                "QMenu QListWidget#scrollable_filter_list QScrollBar::handle:vertical {",
                1,
            )[1].split("}", 1)[0]
            self.assertIn(f"background-color: {handle}", scroll_handle)
            self.assertIn(
                "QMenu QListWidget#scrollable_filter_list QScrollBar::up-arrow:vertical",
                style,
            )
            self.assertIn(
                "QMenu QListWidget#scrollable_filter_list QScrollBar::down-arrow:vertical",
                style,
            )
            scoped_lines = style.split(
                "QMenu QListWidget#scrollable_filter_list QScrollBar::sub-line:vertical,",
                1,
            )[1].split("}", 1)[0]
            self.assertIn("height: 14px", scoped_lines)
            self.assertNotIn("height: 0px", scoped_lines)

    def test_operations_tabs_have_transparent_background(self):
        for theme, active in (
            ("light", standard_palette("light")["accent"]),
            ("dark", standard_palette("dark")["accent"]),
        ):
            style = build_operations_tab_bar_style(theme)
            self.assertIn("background: transparent", style)
            self.assertIn(f"color: {active}", style)
            self.assertIn(f"border-bottom: 3px solid {active}", style)

    def test_settings_navigation_uses_vertical_tab_selection_style(self):
        for theme, foreground, background, active in (
            ("light", standard_palette("light")["fg"], standard_palette("light")["bg"], standard_palette("light")["accent"]),
            ("dark", standard_palette("dark")["fg"], standard_palette("dark")["bg"], standard_palette("dark")["accent"]),
        ):
            style = build_settings_navigation_style(theme)
            button = style.split("QPushButton#settings_nav_item {", 1)[
                1
            ].split("}", 1)[0]
            selected_button = style.split(
                "QPushButton#settings_nav_item:checked {", 1
            )[1].split("}", 1)[0]
            self.assertIn(f"color: {foreground}", button)
            self.assertIn(f"font-size: {BODY_PX}px", button)
            self.assertIn("font-weight: 600", button)
            self.assertIn(f"background-color: {background}", button)
            self.assertIn("border-radius: 0px", button)
            self.assertIn(f"color: {active}", selected_button)
            self.assertIn("background-color: transparent", selected_button)
            self.assertNotIn("border-bottom", selected_button)

    def test_light_theme_does_not_reintroduce_dark_template_surface(self):
        light = "\n".join(
            (
                LIGHT_APPLICATION_STYLE,
                build_standard_field_style("light", "surface"),
                build_template_table_style("light"),
            )
        )
        self.assertNotIn(standard_palette("dark")["bg"], light)
        self.assertIn(f"alternate-background-color: {standard_palette('light')['window_bg']}", light)

    def test_template_manager_light_alternating_rows_are_light(self):
        light_style = build_template_table_style("light")
        self.assertIn(f"alternate-background-color: {standard_palette('light')['window_bg']}", light_style)
        self.assertNotIn("alternate-background-color: #454545", light_style)

    def test_runtime_refreshes_buttons_and_operation_tabs(self):
        source = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        self.assertIn("refresh_standard_button_styles(self)", source)
        self.assertIn("self._apply_operations_tab_bar_theme(mode)", source)

    def test_light_menu_popup_uses_white_surface(self):
        self.assertIn(f"background-color: {standard_palette('light')['bg']}", LIGHT_APPLICATION_STYLE)

    def test_dropdown_styles_are_global_instead_of_assigned_to_each_menu(self):
        components = Path("app/ui/ui_components.py").read_text(
            encoding="utf-8"
        )
        theme_source = Path("app/ui/theme_styles.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("QMenu {", DARK_APPLICATION_STYLE)
        self.assertIn("QComboBox QAbstractItemView", DARK_APPLICATION_STYLE)
        self.assertEqual(theme_source.count("QMenu {{"), 1)
        self.assertEqual(theme_source.count("QComboBox QAbstractItemView,"), 1)
        self.assertEqual(
            theme_source.count("QComboBox QAbstractItemView::item {{"), 1
        )
        self.assertNotIn("MENU_STYLE_DARK", components)
        self.assertNotIn("MENU_STYLE_LIGHT", components)
        self.assertNotIn("menu.setStyleSheet(", components)
        self.assertNotIn("view.setStyleSheet(", components)

    def test_dropdown_popup_has_rounded_bottom_without_extra_padding(self):
        for style in (LIGHT_APPLICATION_STYLE, DARK_APPLICATION_STYLE):
            popup = style.split("QMenu#menu_like_combo_popup,", 1)[1].split(
                "}", 1
            )[0]
            self.assertIn("QMenu#header_dropdown_popup", popup)
            self.assertIn("border-bottom-left-radius: 4px", popup)
            self.assertIn("border-bottom-right-radius: 4px", popup)
            self.assertIn("padding-bottom: 0px", popup)

    def test_light_file_panel_and_list_surface_stay_white(self):
        ui_main = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        self.assertIn(
            f"background-color: {standard_palette('light')['bg']}", build_drop_zone_surface_style("light")
        )
        self.assertNotIn(
            "background-color: #f3f3f3", build_drop_zone_surface_style("light")
        )
        self.assertNotIn("right_layout.addSpacing(SPACE_SM)", ui_main)


if __name__ == "__main__":
    unittest.main()
