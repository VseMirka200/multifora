import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.core import settings


class _DummyWindow:
    def apply_theme_mode(self, mode="system"):
        self.applied_theme_mode = mode

    def apply_shortcut_settings(self, silent=False):
        self.shortcut_settings_silent = silent


class _DummyCheckbox:
    def isChecked(self):
        return False


class SettingsResilienceTests(unittest.TestCase):
    def test_load_settings_handles_corrupted_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.json")
            with open(settings_path, "w", encoding="utf-8") as f:
                f.write("{not-json")

            window = _DummyWindow()
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path):
                settings.load_settings(window)

        self.assertEqual(window.theme_mode, "system")
        self.assertFalse(window.windows_context_menu_enabled)
        self.assertTrue(window.auto_update_check_enabled)
        self.assertTrue(window.shortcut_settings_silent)

    def test_load_settings_ignores_persisted_rename_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.json")
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "rename_history": {
                            "history": [{"pairs": [["new.txt", "old.txt"]]}],
                            "redo_history": [{"pairs": [["old.txt", "new.txt"]]}],
                        }
                    },
                    f,
                )

            window = _DummyWindow()
            with patch("app.core.settings.get_settings_file_path", return_value=settings_path):
                settings.load_settings(window)

        self.assertEqual(window._rename_history, [])

    def test_collected_settings_exclude_rename_history(self):
        window = _DummyWindow()
        settings._initialize_settings_defaults(window)
        window.custom_templates = {}
        window.auto_clear_checkbox = _DummyCheckbox()
        window.ghostscript_path_override = None
        window._rename_history = [{"pairs": [["new.txt", "old.txt"]]}]

        data = settings._collect_settings_data(window)

        self.assertNotIn("rename_history", data)

    def test_image_compression_destination_is_persisted(self):
        window = _DummyWindow()
        settings._initialize_settings_defaults(window)
        settings._apply_settings_data(
            window,
            {
                "image_compression_output_mode": "custom",
                "image_compression_output_path": r"C:\output",
            },
        )
        self.assertEqual(window.image_compression_output_mode, "custom")
        self.assertEqual(window.image_compression_output_path, r"C:\output")

        window.custom_templates = {}
        window.auto_clear_checkbox = _DummyCheckbox()
        window.ghostscript_path_override = None
        data = settings._collect_settings_data(window)
        self.assertEqual(data["image_compression_output_mode"], "custom")
        self.assertEqual(data["image_compression_output_path"], r"C:\output")

    def test_conversion_destination_is_persisted(self):
        window = _DummyWindow()
        settings._initialize_settings_defaults(window)
        settings._apply_settings_data(
            window,
            {
                "conversion_output_mode": "custom",
                "conversion_output_path": r"C:\converted",
            },
        )
        self.assertEqual(window.conversion_output_mode, "custom")
        self.assertEqual(window.conversion_output_path, r"C:\converted")

        window.custom_templates = {}
        window.auto_clear_checkbox = _DummyCheckbox()
        window.ghostscript_path_override = None
        data = settings._collect_settings_data(window)
        self.assertEqual(data["conversion_output_mode"], "custom")
        self.assertEqual(data["conversion_output_path"], r"C:\converted")
