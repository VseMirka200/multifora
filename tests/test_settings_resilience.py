import json
import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt

from app.core import settings


class _DummyWindow:
    def apply_theme_mode(self, mode="system"):
        self.applied_theme_mode = mode

    def apply_shortcut_settings(self, silent=False):
        self.shortcut_settings_silent = silent


class _DummyCheckbox:
    def __init__(self, checked=False):
        self.checked = bool(checked)

    def blockSignals(self, _blocked):
        return False

    def setChecked(self, checked):
        self.checked = bool(checked)

    def isChecked(self):
        return self.checked


class _DummyNavigation:
    def __init__(self, count=5):
        self._count = count
        self.current_row = -1

    def count(self):
        return self._count

    def setCurrentRow(self, row):
        self.current_row = row


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
        self.assertFalse(hasattr(window, "auto_update_check_enabled"))
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

    def test_auto_clear_has_master_switch_and_operation_choices(self):
        window = _DummyWindow()
        window.auto_clear_enabled_checkbox = _DummyCheckbox()
        for attribute_name in (
            "auto_clear_rename_checkbox",
            "auto_clear_convert_checkbox",
            "auto_clear_merge_checkbox",
            "auto_clear_compress_checkbox",
            "auto_clear_metadata_checkbox",
        ):
            setattr(window, attribute_name, _DummyCheckbox())
        settings._initialize_settings_defaults(window)

        self.assertFalse(window.auto_clear_enabled_checkbox.isChecked())
        self.assertTrue(window.auto_clear_convert_checkbox.isChecked())

        settings._apply_settings_data(
            window,
            {
                "auto_clear_enabled": True,
                "auto_clear_by_operation": {
                    "rename": True,
                    "convert": False,
                    "merge": False,
                    "compress": True,
                    "metadata": False,
                },
            },
        )
        window.custom_templates = {}
        window.ghostscript_path_override = None

        data = settings._collect_settings_data(window)

        self.assertTrue(data["auto_clear_enabled"])
        self.assertEqual(
            data["auto_clear_by_operation"],
            {
                "rename": True,
                "convert": False,
                "merge": False,
                "compress": True,
                "metadata": False,
            },
        )

    def test_removed_auto_clear_navigation_page_is_migrated_to_main(self):
        window = _DummyWindow()
        window.settings_nav = _DummyNavigation()

        settings._restore_navigation_state(
            window,
            {
                "settings_nav_current_row": 3,
                "auto_clear_by_operation": {},
            },
        )

        self.assertEqual(window._pending_settings_nav_row, 0)
        self.assertEqual(window.settings_nav.current_row, 0)

    def test_old_settings_navigation_rows_are_migrated_to_merged_layout(self):
        expected_rows = {
            0: 0,  # Основное
            1: 2,  # Обновления -> О программе
            2: 1,  # Логи
            3: 0,  # Удалённая отдельная Автоочистка
            4: 2,  # О программе
        }
        for saved_row, expected_row in expected_rows.items():
            with self.subTest(saved_row=saved_row):
                window = _DummyWindow()
                window.settings_nav = _DummyNavigation(count=3)

                settings._restore_navigation_state(
                    window,
                    {
                        "settings_nav_current_row": saved_row,
                        "auto_clear_by_operation": {},
                    },
                )

                self.assertEqual(window._pending_settings_nav_row, expected_row)
                self.assertEqual(window.settings_nav.current_row, expected_row)

    def test_current_settings_navigation_row_is_not_migrated(self):
        window = _DummyWindow()
        window.settings_nav = _DummyNavigation(count=3)

        settings._restore_navigation_state(
            window,
            {
                "settings_nav_current_row": 2,
                "settings_nav_layout_version": 2,
            },
        )

        self.assertEqual(window._pending_settings_nav_row, 2)
        self.assertEqual(window.settings_nav.current_row, 2)

    def test_auto_update_check_uses_checkbox_as_single_source_of_truth(self):
        window = _DummyWindow()
        settings._initialize_settings_defaults(window)
        window.auto_update_check_checkbox = _DummyCheckbox(True)

        settings._apply_settings_data(
            window,
            {
                "auto_check_updates": False,
                "current_tab_index": 4,
            },
        )

        self.assertFalse(window.auto_update_check_checkbox.isChecked())
        self.assertFalse(hasattr(window, "auto_update_check_enabled"))

        window.custom_templates = {}
        window.auto_clear_checkbox = _DummyCheckbox()
        window.ghostscript_path_override = None
        data = settings._collect_settings_data(window)

        self.assertFalse(data["auto_check_updates"])
        self.assertNotIn("current_tab_index", data)

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

    def test_removed_rename_options_are_ignored(self):
        window = _DummyWindow()
        settings._initialize_settings_defaults(window)
        settings._apply_settings_data(
            window,
            {
                "rename_folder_mode": "parallel_by_folder",
                "rename_numbering_scope": "per_folder",
            },
        )

        self.assertFalse(hasattr(window, "rename_folder_mode"))
        self.assertFalse(hasattr(window, "rename_numbering_scope"))

        window.custom_templates = {}
        window.auto_clear_checkbox = _DummyCheckbox()
        window.ghostscript_path_override = None
        data = settings._collect_settings_data(window)
        self.assertNotIn("rename_folder_mode", data)
        self.assertNotIn("rename_numbering_scope", data)

    def test_column_sort_state_is_persisted(self):
        window = _DummyWindow()
        settings._initialize_settings_defaults(window)
        settings._apply_settings_data(
            window,
            {
                "file_list_view_state": {
                    "sort_column": 3,
                    "sort_order": "descending",
                }
            },
        )
        self.assertEqual(window._column_sort_section, 3)
        self.assertEqual(window._column_sort_order, Qt.SortOrder.DescendingOrder)

        window.custom_templates = {}
        window.auto_clear_checkbox = _DummyCheckbox()
        window.ghostscript_path_override = None
        data = settings._collect_settings_data(window)
        self.assertEqual(
            data["file_list_view_state"],
            {"sort_column": 3, "sort_order": "descending"},
        )
