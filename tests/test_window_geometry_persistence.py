import json
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.ui.ui_main import MultiforaMainWindow


class WindowGeometryPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_geometry_is_saved_and_restored(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")

            with patch("app.core.settings.get_settings_file_path", return_value=settings_path), \
                patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None), \
                patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None), \
                patch.object(MultiforaMainWindow, "create_file_worker", return_value=True):
                window = MultiforaMainWindow()
                try:
                    window.setGeometry(321, 245, 1111, 633)
                    if hasattr(window, "_settings_save_timer") and window._settings_save_timer is not None:
                        window._settings_save_timer.stop()
                    window._force_settings_save = True
                    window.save_settings()
                    window._force_settings_save = False

                    with open(settings_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    self.assertEqual(data["window_pos"], [321, 245])
                    self.assertEqual(data["window_size"], [1111, 633])
                    self.assertFalse(data["window_maximized"])

                    restored = MultiforaMainWindow()
                    try:
                        restored._restore_window_geometry_from_pending()
                        self.assertEqual(restored.geometry().x(), 321)
                        self.assertEqual(restored.geometry().y(), 245)
                        self.assertEqual(restored.geometry().width(), 1111)
                        self.assertEqual(restored.geometry().height(), 633)
                    finally:
                        if hasattr(restored, "queue_timer"):
                            restored.queue_timer.stop()
                        if hasattr(restored, "_settings_save_timer"):
                            restored._settings_save_timer.stop()
                        restored.deleteLater()
                finally:
                    if hasattr(window, "queue_timer"):
                        window.queue_timer.stop()
                    if hasattr(window, "_settings_save_timer"):
                        window._settings_save_timer.stop()
                    window.deleteLater()


if __name__ == "__main__":
    unittest.main()
