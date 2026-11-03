"""Capture clean, local UI screenshots for the documentation site."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app.ui.ui_main import MultiforaMainWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    output = Path("docs/assets/screenshots")
    output.mkdir(parents=True, exist_ok=True)
    temporary_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    try:
        temporary = temporary_dir.name
        with (
            patch(
                "app.core.settings.get_settings_file_path",
                return_value=f"{temporary}/settings.json",
            ),
            patch.object(
                MultiforaMainWindow,
                "apply_shortcut_settings",
                return_value=None,
            ),
            patch.object(
                MultiforaMainWindow,
                "ensure_context_menu_registration",
                return_value=None,
            ),
            patch.object(
                MultiforaMainWindow, "create_ipc_server", return_value=None
            ),
            patch.object(
                MultiforaMainWindow, "create_file_worker", return_value=True
            ),
            patch.object(
                MultiforaMainWindow,
                "check_updates_on_startup",
                return_value=None,
            ),
        ):
            window = MultiforaMainWindow()
        window.resize(1280, 780)
        window.show()
        app.processEvents()
        for index, name in enumerate(
            ("rename", "conversion", "compression", "merge")
        ):
            window.operations_tab_bar.setCurrentIndex(index)
            app.processEvents()
            window.grab().save(str(output / f"{name}.png"), "PNG")
        window.close()
    finally:
        try:
            temporary_dir.cleanup()
        except PermissionError:
            # Некоторые оболочки Windows кратковременно удерживают дескриптор
            # Qt.
            pass


if __name__ == "__main__":
    main()
