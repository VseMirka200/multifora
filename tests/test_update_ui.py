import concurrent.futures
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from app.ui.mixins.settings_panel_mixin import SettingsPanelMixin


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.host = QWidget()
        self.host.btn_check_updates = QPushButton(self.host)
        self.host.btn_download_update = QPushButton(self.host)
        self.host.btn_download_update.setVisible(False)
        self.host.btn_install_update = QPushButton(self.host)
        self.host.btn_install_update.setVisible(False)
        self.host.update_status_label = QLabel(self.host)
        self.host.update_latest_label = QLabel(self.host)
        self.host._update_silent = True
        self.host._update_poll_timer = Mock()
        self.host._update_download_poll_timer = Mock()

    def tearDown(self):
        self.host.deleteLater()

    def test_update_buttons_follow_check_download_and_install_stages(self):
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

        SettingsPanelMixin._poll_update_future(self.host)

        self.assertFalse(self.host.btn_download_update.isHidden())
        self.assertTrue(self.host.btn_download_update.isEnabled())
        self.assertTrue(self.host.btn_install_update.isHidden())

        download_future = concurrent.futures.Future()
        download_future.set_result(
            {"path": "C:/Updates/Multifora-Setup-1.1.0.exe", "version": "1.1.0"}
        )
        self.host._update_download_future = download_future

        SettingsPanelMixin._poll_update_download_future(self.host)

        self.assertEqual(self.host.btn_download_update.text(), "Скачать заново")
        self.assertFalse(self.host.btn_install_update.isHidden())
        self.assertTrue(self.host.btn_install_update.isEnabled())

        self.host.file_worker = Mock()
        self.host.file_worker.isRunning.return_value = False
        self.host.close = Mock()
        self.host.log_event = Mock()
        with patch(
            "app.ui.mixins.settings_panel_mixin.launch_update_installer"
        ) as launch, patch(
            "app.ui.mixins.settings_panel_mixin.QTimer.singleShot"
        ) as single_shot:
            SettingsPanelMixin.install_downloaded_update(self.host)

        launch.assert_called_once_with("C:/Updates/Multifora-Setup-1.1.0.exe")
        single_shot.assert_called_once_with(500, self.host.close)
        self.assertFalse(self.host.btn_install_update.isEnabled())


if __name__ == "__main__":
    unittest.main()
