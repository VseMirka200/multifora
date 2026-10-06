import concurrent.futures
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton, QWidget

from app.ui.mixins.settings_panel_mixin import SettingsPanelMixin


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.host = QWidget()
        self.host.btn_check_updates = QPushButton(self.host)
        self.host._update_silent = False
        self.host._update_poll_timer = Mock()

    def tearDown(self):
        self.host.deleteLater()

    def test_manual_update_check_shows_result(self):
        check_future = concurrent.futures.Future()
        check_future.set_result(
            {
                "current_version": "1.0.0",
                "latest_version": "1.1.0",
                "comparison": -1,
                "has_update": True,
                "installer": {"name": "Multifora-Setup-1.1.0.exe"},
            }
        )
        self.host._update_future = check_future

        with patch(
            "app.ui.mixins.settings_panel_mixin.QMessageBox.information"
        ) as information:
            SettingsPanelMixin._poll_update_future(self.host)

        information.assert_called_once_with(
            self.host,
            "Проверка обновлений",
            "Доступно обновление: 1.0.0 → 1.1.0.",
        )
        self.assertTrue(self.host.btn_check_updates.isEnabled())


if __name__ == "__main__":
    unittest.main()
