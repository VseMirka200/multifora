import importlib.util
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


def _load_windows_integration_module():
    module_name = "windows_integration_mixin_under_test"
    loader = SourceFileLoader(
        module_name,
        str(Path("app/ui/mixins/windows_integration_mixin.py")),
    )
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


windows_integration = _load_windows_integration_module()
WindowsIntegrationMixin = windows_integration.WindowsIntegrationMixin


class _ShortcutDummy(WindowsIntegrationMixin):
    def log_event(self, *_args, **_kwargs):
        return None


class WindowsShortcutIconPreservationTests(unittest.TestCase):
    def test_preserves_existing_shortcut_when_icon_is_unavailable(self):
        dummy = _ShortcutDummy()

        with tempfile.TemporaryDirectory() as tmpdir:
            shortcut_path = Path(tmpdir) / "Multifora.lnk"
            shortcut_path.write_text("existing shortcut", encoding="utf-8")

            with patch.object(windows_integration, "_get_shortcut_icon_path", return_value=None), \
                 patch.object(windows_integration.subprocess, "run") as run_mock:
                result = dummy.create_windows_shortcut(str(shortcut_path), silent=True)

        self.assertTrue(result)
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
