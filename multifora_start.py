import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.core.app_icons import _get_app_icon_qt_path, _set_app_user_model_id
from app.core.app_identity import APP_DISPLAY_NAME
from app.core.app_ipc import (
    _enqueue_files,
    _ensure_ipc_token,
    collect_startup_files,
    is_first_instance,
    send_files_to_running_instance,
)
from app.core.app_utils import _debug_log
from app.ui.ui_main import MultiforaMainWindow


def _run_build_smoke_test() -> int:
    """Check the *frozen* bundle without performing file operations.

    The report is written to MULTIFORA_SMOKE_REPORT, because a windowed
    PyInstaller executable does not have a console on Windows.
    """
    import importlib
    import json
    import os
    from pathlib import Path
    import traceback

    report_path = os.environ.get("MULTIFORA_SMOKE_REPORT")
    report = {"status": "failed", "imports": [], "window_visible": False}
    application = None
    window = None
    try:
        for module in (
            "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
            "PyQt6.QtNetwork", "fitz", "pdf2docx", "PIL.Image",
            "pillow_heif", "docx", "docxcompose.composer",
            "odf.opendocument", "pythoncom", "win32com.client",
        ):
            importlib.import_module(module)
            report["imports"].append(module)

        application = QApplication([sys.argv[0]])
        application.setApplicationName(APP_DISPLAY_NAME)
        application.setApplicationDisplayName(APP_DISPLAY_NAME)
        application.setStyle("Fusion")
        from app.ui.ui_main import MultiforaMainWindow

        window = MultiforaMainWindow()
        window.show()
        application.processEvents()
        report["window_visible"] = window.isVisible()
        if not report["window_visible"]:
            raise RuntimeError("Main window did not become visible")
        report["status"] = "ok"
        return_code = 0
    except Exception:
        report["error"] = traceback.format_exc()
        return_code = 1
    finally:
        if window is not None:
            try:
                window.close()
            except Exception:
                report["cleanup_error"] = traceback.format_exc()
        if application is not None:
            try:
                application.processEvents()
            except Exception:
                report["cleanup_error"] = traceback.format_exc()
                return_code = 1
        if report_path:
            try:
                destination = Path(report_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass
    return return_code


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
            _debug_log("Не удалось передать стартовые файлы уже запущенному экземпляру")
            _enqueue_files(startup_files)
        sys.exit(0)

    _ensure_ipc_token()
    window = MultiforaMainWindow()
    window.show()

    if startup_files:
        QTimer.singleShot(0, lambda: window.add_files(startup_files))

    sys.exit(app.exec())


if __name__ == "__main__":
    if sys.argv[1:] == ["--build-smoke-test"]:
        sys.exit(_run_build_smoke_test())
    main()
