import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from app.core.app_identity import APP_DISPLAY_NAME
from app.core.app_icons import _get_app_icon_qt_path, _set_app_user_model_id
from app.core.app_ipc import (
    _ensure_ipc_token,
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
        _debug_log(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0438\u043a\u043e\u043d\u043a\u0438 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f: {exc}")

    startup_files = collect_startup_files()
    first = is_first_instance()

    if not first:
        sent = send_files_to_running_instance(startup_files)
        if startup_files and not sent:
            _debug_log("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u0435\u0440\u0435\u0434\u0430\u0442\u044c \u0441\u0442\u0430\u0440\u0442\u043e\u0432\u044b\u0435 \u0444\u0430\u0439\u043b\u044b \u0443\u0436\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d\u043d\u043e\u043c\u0443 \u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440\u0443")
            QMessageBox.warning(
                None,
                APP_DISPLAY_NAME,
                "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u0435\u0440\u0435\u0434\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b \u0432 \u0443\u0436\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d\u043d\u044b\u0439 \u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f.",
            )
        sys.exit(0)

    _ensure_ipc_token()
    window = MultiforaMainWindow()
    window.show()

    if startup_files:
        QTimer.singleShot(0, lambda: window.add_files(startup_files))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
