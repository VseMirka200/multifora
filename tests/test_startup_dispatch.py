import unittest
from unittest.mock import Mock, patch

import multifora_start as startup


class _DummyApp:
    def setApplicationName(self, _name):
        return None

    def setApplicationDisplayName(self, _name):
        return None

    def setStyle(self, _style):
        return None

    def setWindowIcon(self, _icon):
        return None

    def exec(self):
        return 0


class StartupDispatchTests(unittest.TestCase):
    @patch("multifora_start._set_app_user_model_id")
    @patch("multifora_start._get_app_icon_qt_path", return_value=None)
    @patch("multifora_start.QApplication", return_value=_DummyApp())
    @patch("multifora_start.collect_startup_files", return_value=[r"C:\tmp\a.pdf"])
    @patch("multifora_start.is_first_instance", return_value=False)
    @patch("multifora_start.send_files_to_running_instance", return_value=True)
    @patch("multifora_start.QMessageBox.warning")
    @patch("multifora_start.sys.exit", side_effect=SystemExit)
    def test_no_enqueue_when_send_succeeds(
        self,
        exit_mock: Mock,
        warn_mock: Mock,
        send_mock: Mock,
        _first_mock: Mock,
        _collect_mock: Mock,
        _qapp_mock: Mock,
        _icon_mock: Mock,
        _aumid_mock: Mock,
    ):
        with self.assertRaises(SystemExit):
            startup.main()
        send_mock.assert_called_once()
        warn_mock.assert_not_called()
        exit_mock.assert_called_once_with(0)

    @patch("multifora_start._set_app_user_model_id")
    @patch("multifora_start._get_app_icon_qt_path", return_value=None)
    @patch("multifora_start.QApplication", return_value=_DummyApp())
    @patch("multifora_start.collect_startup_files", return_value=[r"C:\tmp\a.pdf"])
    @patch("multifora_start.is_first_instance", return_value=False)
    @patch("multifora_start.send_files_to_running_instance", return_value=False)
    @patch("multifora_start.QMessageBox.warning")
    @patch("multifora_start._debug_log")
    @patch("multifora_start.sys.exit", side_effect=SystemExit)
    def test_log_when_send_fails(
        self,
        exit_mock: Mock,
        debug_log_mock: Mock,
        warn_mock: Mock,
        send_mock: Mock,
        _first_mock: Mock,
        _collect_mock: Mock,
        _qapp_mock: Mock,
        _icon_mock: Mock,
        _aumid_mock: Mock,
    ):
        with self.assertRaises(SystemExit):
            startup.main()
        send_mock.assert_called_once()
        debug_log_mock.assert_called_once_with("Не удалось передать стартовые файлы уже запущенному экземпляру")
        warn_mock.assert_called_once_with(
            None,
            "Мультифора",
            "Не удалось передать файлы в уже запущенный экземпляр приложения.",
        )
        exit_mock.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
