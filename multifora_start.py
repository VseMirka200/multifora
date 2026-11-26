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
    """Smoke-test the bundled ArtCraft CLI engines and frozen Qt application."""
    import base64
    import json
    import os
    import time
    import traceback
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from unittest.mock import patch

    from core.workers.native_engines import engine_path, run_engine

    report_path = os.environ.get("MULTIFORA_SMOKE_REPORT")
    report = {"status": "failed", "window_visible": False}
    application = None
    window = None
    try:
        for engine in ("pdf", "photo", "deck"):
            executable = engine_path(engine)
            run_engine(engine, ["--version"])
            report[f"{engine}_engine"] = str(Path(executable).name)

        with TemporaryDirectory(prefix="multifora-artcraft-smoke-") as directory:
            root = Path(directory)
            first_text = root / "first.txt"
            second_text = root / "second.txt"
            first_text.write_text("Multifora PdfCraft first page", encoding="utf-8")
            second_text.write_text("Multifora PdfCraft second page", encoding="utf-8")
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            for source in (first_text, second_text):
                run_engine("pdf", ["batch", str(source), "--steps", "convert", "--out-dir", str(pdf_dir)])
            first_pdf = pdf_dir / "first.pdf"
            second_pdf = pdf_dir / "second.pdf"
            if not first_pdf.is_file() or not second_pdf.is_file():
                raise RuntimeError("PdfCraft text-to-PDF conversion failed")

            info = json.loads(run_engine("pdf", ["info", str(first_pdf)]))
            pages = info.get("pages")
            if isinstance(pages, list):
                page_count = len(pages)
            else:
                page_count = pages or info.get("page_count") or info.get("pageCount")
            if not isinstance(page_count, int) or page_count < 1:
                raise RuntimeError("PdfCraft info did not return page count")
            rendered = root / "page.png"
            run_engine("pdf", ["render", str(first_pdf), "--page", "1", "--dpi", "96", "--out", str(rendered)])
            if not rendered.is_file() or rendered.stat().st_size == 0:
                raise RuntimeError("PdfCraft PDF rendering failed")
            report["pdf_roundtrip"] = True

            merged = root / "merged.pdf"
            run_engine("pdf", ["combine", str(first_pdf), str(second_pdf), "--out", str(merged)])
            merged_info = json.loads(run_engine("pdf", ["info", str(merged)]))
            merged_pages = merged_info.get("pages")
            merged_count = len(merged_pages) if isinstance(merged_pages, list) else merged_pages
            if not isinstance(merged_count, int) or merged_count < 2:
                raise RuntimeError("PdfCraft PDF merge failed")
            report["pdf_merge"] = True

            script = root / "export.json"
            output_docx = root / "result.docx"
            script.write_text(json.dumps([
                {"tool": "doc_open", "args": {"path": str(first_pdf)}},
                {"tool": "doc_export_office", "args": {"doc": 1, "path": str(output_docx)}},
            ]), encoding="utf-8")
            run_engine("pdf", ["run", "--script", str(script), "--report"])
            if not output_docx.is_file() or output_docx.stat().st_size == 0:
                raise RuntimeError("PdfCraft PDF-to-DOCX export failed")
            report["pdf_to_docx"] = True

            # A tiny known PNG exercises PhotoCraft's real decoder and encoder.
            png = root / "tiny.png"
            png.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p7sAAAAASUVORK5CYII="
            ))
            webp = root / "tiny.webp"
            png_again = root / "tiny-again.png"
            run_engine("photo", ["convert", str(png), str(webp), "--quality", "90"])
            run_engine("photo", ["convert", str(webp), str(png_again)])
            if not webp.is_file() or not png_again.is_file() or png_again.stat().st_size == 0:
                raise RuntimeError("PhotoCraft image roundtrip failed")
            report["image_roundtrip"] = True

        report["deck_engine"] = engine_path("deck")
        application = QApplication([sys.argv[0]])
        application.setApplicationName(APP_DISPLAY_NAME)
        application.setApplicationDisplayName(APP_DISPLAY_NAME)
        application.setStyle("Fusion")
        with (
            patch.object(MultiforaMainWindow, "apply_shortcut_settings", return_value=None),
            patch.object(MultiforaMainWindow, "ensure_context_menu_registration", return_value=None),
            patch.object(MultiforaMainWindow, "create_ipc_server", return_value=None),
            patch.object(MultiforaMainWindow, "process_startup_queue", return_value=None),
            patch.object(MultiforaMainWindow, "check_updates_on_startup", return_value=None),
        ):
            started = time.perf_counter()
            window = MultiforaMainWindow()
            report["window_create_seconds"] = round(time.perf_counter() - started, 6)
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
                destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
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
