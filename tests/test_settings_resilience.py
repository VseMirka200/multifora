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
