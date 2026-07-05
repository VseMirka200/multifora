import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.ui.mixins.windows_integration_mixin import WindowsIntegrationMixin


class _ShortcutDummy(WindowsIntegrationMixin):
    def log_event(self, *_args, **_kwargs):
        return None


class WindowsShortcutIconPreservationTests(unittest.TestCase):
    def test_preserves_existing_shortcut_when_icon_is_unavailable(self):
        dummy = _ShortcutDummy()

        with tempfile.TemporaryDirectory() as tmpdir:
            shortcut_path = Path(tmpdir) / "Multifora.lnk"
            shortcut_path.write_text("existing shortcut", encoding="utf-8")

            with patch("app.ui.mixins.windows_integration_mixin._get_shortcut_icon_path", return_value=None), \
                 patch("app.ui.mixins.windows_integration_mixin.subprocess.run") as run_mock:
                result = dummy.create_windows_shortcut(str(shortcut_path), silent=True)

        self.assertTrue(result)
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
