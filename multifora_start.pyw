import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

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
    app.setStyle("Fusion")
    try:
        icon_path = _get_app_icon_qt_path()
        if icon_path:
            app.setWindowIcon(QIcon(icon_path))
    except Exception as exc:
        _debug_log(f"РћС€РёР±РєР° РёРєРѕРЅРєРё РїСЂРёР»РѕР¶РµРЅРёСЏ: {exc}")

    startup_files = collect_startup_files()
    first = is_first_instance()

    if not first:
        sent = send_files_to_running_instance(startup_files)
        if startup_files and not sent:
            _debug_log("РќРµ СѓРґР°Р»РѕСЃСЊ РїРµСЂРµРґР°С‚СЊ СЃС‚Р°СЂС‚РѕРІС‹Рµ С„Р°Р№Р»С‹ СѓР¶Рµ Р·Р°РїСѓС‰РµРЅРЅРѕРјСѓ СЌРєР·РµРјРїР»СЏСЂСѓ")
            QMessageBox.warning(
                None,
                "Multifora",
                "РќРµ СѓРґР°Р»РѕСЃСЊ РїРµСЂРµРґР°С‚СЊ С„Р°Р№Р»С‹ РІ СѓР¶Рµ Р·Р°РїСѓС‰РµРЅРЅС‹Р№ СЌРєР·РµРјРїР»СЏСЂ РїСЂРёР»РѕР¶РµРЅРёСЏ.",
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
