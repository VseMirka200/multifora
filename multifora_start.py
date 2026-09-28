import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.core.app_identity import APP_DISPLAY_NAME
from app.core.app_icons import _get_app_icon_qt_path, _set_app_user_model_id
from app.core.app_ipc import (
    _ensure_ipc_token,
    _enqueue_files,
    collect_startup_files,
    is_first_instance,
    send_files_to_running_instance,
)
from app.core.app_utils import _debug_log
from app.ui.ui_main import MultiforaMainWindow


def main():
    _set_app_user_model_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setStyle("Fusion")
    try:
        icon_path = _get_app_icon_qt_path()
        if icon_path:
            app.setWindowIcon(QIcon(icon_path))
    except Exception as exc:
        _debug_log(f"Ошибка иконки приложения: {exc}")

    startup_files = collect_startup_files()
    first = is_first_instance()

    if not first:
        sent = send_files_to_running_instance(startup_files)
        if startup_files and not sent:
            _debug_log(
                "Не удалось передать стартовые файлы уже запущенному экземпляру"
            )
            _enqueue_files(startup_files)
        sys.exit(0)

    _ensure_ipc_token()
    window = MultiforaMainWindow()
    window.show()

    if startup_files:
        QTimer.singleShot(0, lambda: window.add_files(startup_files))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()