import importlib.util
import sys
import types
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import Mock, patch


def _load_startup_module():
    module_name = "multifora_start"
    loader = SourceFileLoader(module_name, str(Path("multifora_start.py")))
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)

    ui_module_name = "app.ui.ui_main"
    previous_ui_module = sys.modules.get(ui_module_name)
    ui_module = types.ModuleType(ui_module_name)
    ui_module.MultiforaMainWindow = type("MultiforaMainWindow", (), {})
    sys.modules[ui_module_name] = ui_module
    sys.modules[module_name] = module
    try:
        loader.exec_module(module)
    finally:
        if previous_ui_module is None:
            sys.modules.pop(ui_module_name, None)
        else:
            sys.modules[ui_module_name] = previous_ui_module
    return module


startup = _load_startup_module()


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
    @patch("multifora_start._enqueue_files")
    @patch("multifora_start.sys.exit", side_effect=SystemExit)
    def test_no_enqueue_when_send_succeeds(
        self,
        exit_mock: Mock,
        enqueue_mock: Mock,
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
        enqueue_mock.assert_not_called()
        exit_mock.assert_called_once_with(0)

    @patch("multifora_start._set_app_user_model_id")
    @patch("multifora_start._get_app_icon_qt_path", return_value=None)
    @patch("multifora_start.QApplication", return_value=_DummyApp())
    @patch("multifora_start.collect_startup_files", return_value=[r"C:\tmp\a.pdf"])
    @patch("multifora_start.is_first_instance", return_value=False)
    @patch("multifora_start.send_files_to_running_instance", return_value=False)
    @patch("multifora_start._enqueue_files")
    @patch("multifora_start._debug_log")
    @patch("multifora_start.sys.exit", side_effect=SystemExit)
    def test_enqueue_when_send_fails(
        self,
        exit_mock: Mock,
        debug_log_mock: Mock,
        enqueue_mock: Mock,
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
        enqueue_mock.assert_called_once_with([r"C:\tmp\a.pdf"])
        exit_mock.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
