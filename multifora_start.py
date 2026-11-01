import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

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
from app.core.runtime_logging import install_runtime_logging
from app.ui.ui_main import MultiforaMainWindow


def _run_build_smoke_test() -> int:
    """Check the *frozen* bundle without performing file operations.

    The report is written to MULTIFORA_SMOKE_REPORT, because a windowed
    PyInstaller executable does not have a console on Windows.
    """
    import importlib
    import json
    import os
    import time
    import traceback
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from unittest.mock import patch

    from app.core.pdf_compat import import_pymupdf_with_legacy_alias

    report_path = os.environ.get("MULTIFORA_SMOKE_REPORT")
    report = {"status": "failed", "imports": [], "window_visible": False}
    application = None
    window = None
    try:
        for module in (
            "PySide6.QtCore",
            "PySide6.QtGui",
            "PySide6.QtWidgets",
            "PySide6.QtNetwork",
            "pymupdf",
            "docx",
            "docxcompose.composer",
        ):
            if module == "pymupdf":
                import_pymupdf_with_legacy_alias()
            else:
                importlib.import_module(module)
            report["imports"].append(module)

        # Exercise native PDF code and DOCX package data, not only imports.
        from io import BytesIO

        import pymupdf
        from docx import Document
        from docxcompose.composer import Composer

        from app.core import deps

        report["lazy_backends"] = all(
            module not in sys.modules
            for module in ("pdf2docx", "PIL.Image", "pillow_heif", "odf")
        )
        if not report["lazy_backends"]:
            raise RuntimeError("Optional backends were imported before use")

        image_buffer = BytesIO()
        with deps.Image.new("RGB", (2, 2), "white") as image:
            image.save(image_buffer, "PNG")
        image_buffer.seek(0)
        with deps.Image.open(image_buffer) as image:
            image.load()
            if image.size != (2, 2):
                raise RuntimeError("Pillow image roundtrip failed")
        if deps.HAS_HEIF and ".heic" not in deps.Image.registered_extensions():
            raise RuntimeError("HEIF image opener was not registered")
        report["image_roundtrip"] = True
        report["imports"].extend(("PIL.Image", "pillow_heif"))

        with TemporaryDirectory(prefix="multifora-odf-") as directory:
            odf_path = Path(directory, "roundtrip.odt")
            odf_document = deps.OpenDocumentText()
            odf_document.text.addElement(deps.text.P(text="Multifora ODF check"))
            odf_document.save(str(odf_path))
            loaded_odf = deps.load(str(odf_path))
            loaded_text = "\n".join(
                deps.teletype.extractText(element)
                for element in loaded_odf.getElementsByType(deps.text.P)
            )
            if "Multifora ODF check" not in loaded_text:
                raise RuntimeError("ODF roundtrip failed")
        report["odf_roundtrip"] = True
        report["imports"].append("odf.opendocument")

        with pymupdf.open() as document:
            document.new_page().insert_text((72, 72), "Multifora PDF check")
            pdf_bytes = document.tobytes()
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if "Multifora PDF check" not in document[0].get_text():
                raise RuntimeError("PDF roundtrip failed")
            document[0].get_pixmap()
        report["pdf_roundtrip"] = True

        # Exercise the real pdf2docx backend inside the frozen process.  A
        # successful import alone does not prove that its native dependencies
        # and package hooks are complete.
        with TemporaryDirectory(prefix="multifora-pdf2docx-") as directory:
            source_pdf = Path(directory, "source.pdf")
            output_docx = Path(directory, "result.docx")
            source_pdf.write_bytes(pdf_bytes)
            converter = deps.pdf2docx.Converter(str(source_pdf))
            try:
                converter.convert(str(output_docx))
            finally:
                converter.close()
            converted_text = "\n".join(
                paragraph.text for paragraph in Document(output_docx).paragraphs
            )
            if "Multifora PDF check" not in converted_text:
                raise RuntimeError("PDF to DOCX conversion failed")
        report["pdf_to_docx"] = True
        report["imports"].append("pdf2docx")

        first = Document()
        first.add_paragraph("First document")
        second = Document()
        second.add_paragraph("Second document")
        composer = Composer(first)
        composer.append(second)
        merged = BytesIO()
        composer.save(merged)
        merged.seek(0)
        if [p.text for p in Document(merged).paragraphs] != [
            "First document", "Second document"
        ]:
            raise RuntimeError("DOCX merge failed")
        report["docx_merge"] = True

        application = QApplication([sys.argv[0]])
        application.setApplicationName(APP_DISPLAY_NAME)
        application.setApplicationDisplayName(APP_DISPLAY_NAME)
        application.setStyle("Fusion")
        from app.ui.ui_main import MultiforaMainWindow

        # Smoke-проверка не должна менять ярлыки, реестр, IPC-файлы и настройки
        # рабочей установки или обращаться к сети.
        with (
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
                MultiforaMainWindow, "process_startup_queue", return_value=None
            ),
            patch.object(
                MultiforaMainWindow,
                "check_updates_on_startup",
                return_value=None,
            ),
        ):
            window_started = time.perf_counter()
            window = MultiforaMainWindow()
            report["window_create_seconds"] = round(
                time.perf_counter() - window_started, 6
            )
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
                # closeEvent сохраняет настройки и удаляет IPC-токен, поэтому
                # здесь достаточно уничтожить тестовое окно через цикл Qt.
                window.hide()
                window.deleteLater()
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
                destination.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                pass
    return return_code


def main():
    install_runtime_logging()
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
    if sys.argv[1:] == ["--build-smoke-test"]:
        sys.exit(_run_build_smoke_test())
    main()
