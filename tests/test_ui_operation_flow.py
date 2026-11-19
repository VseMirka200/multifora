from unittest.mock import patch

import pytest
from docx import Document
from PIL import Image
from pypdf import PdfReader, PdfWriter
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.ui.ui_main import MultiforaMainWindow
from app.workers.operation_worker import OperationWorker
from core.file_models import FileItem
from core.operation_requests import ConversionRequest
from core.operation_result import OperationResult


@pytest.fixture
def window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("app.core.settings.get_settings_file_path", lambda: str(tmp_path / "settings.json"))
    for name in (
        "apply_shortcut_settings", "ensure_context_menu_registration", "process_startup_queue",
        "check_updates_on_startup", "create_ipc_server", "init_logging",
    ):
        monkeypatch.setattr(MultiforaMainWindow, name, lambda *_args, **_kwargs: None)
    main = MultiforaMainWindow()
    main.show()
    app.processEvents()
    yield main
    main.queue_timer.stop()
    main._queue_paths_refresh_timer.stop()
    main._settings_save_timer.stop()
    if main.file_worker and main.file_worker.isRunning():
        main.file_worker.request_cancel()
        assert main.file_worker.wait(5000)
    main.deleteLater()


def test_queue_distinguishes_filters_highlight_and_work_marks(window, tmp_path):
    assert window._list_header_layout.count() == 3
    assert window.operation_scope_label.isHidden()
    assert not window.drop_zone_controls.isHidden()
    source = tmp_path / "first.txt"
    source.write_bytes(b"a" * 1024)
    other = tmp_path / "second.txt"
    other.write_bytes(b"b" * 2_097_152)
    window.add_files([str(source), str(other)])
    assert window.drop_zone_controls.isHidden()
    QApplication.processEvents()
    assert not window.operation_scope_label.isHidden()

    window.list_files.selectRow(1)
    assert "2.00 МБ" in window.label_item_size.text()
    assert len(window._get_operation_file_items()) == 2
    model = window.list_files.model()
    model.setData(model.index(0, model.COLUMN_CHECK), Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    window.input_search.setText("second")
    QApplication.processEvents()
    assert window._get_operation_file_items() == []
    assert "Скрыто отмеченных: 1" in window.operation_scope_label.text()

    window.input_search.setText("unmatched")
    assert window.drop_zone_hint_label.text() == "Ничего не найдено"
    assert not window.btn_reset_queue_filters.isHidden()
    window.btn_reset_queue_filters.click()
    assert len(model.files()) == 2
    assert window.drop_zone_controls.isHidden()


def test_cancelled_result_keeps_queue_and_published_file(window, tmp_path):
    source = tmp_path / "first.docx"
    source.write_bytes(b"source")
    output = tmp_path / "first.pdf"
    output.write_bytes(b"example")
    window.add_files([str(source)])
    window.auto_clear_enabled_checkbox.setChecked(True)
    window.auto_clear_convert_checkbox.setChecked(True)
    window._operations.last_request = ConversionRequest("docx_to_pdf", "PDF", "alongside", "")
    worker = OperationWorker()
    worker.finished.connect(window.on_operation_finished)
    worker.request_cancel()
    worker._emit_finished([FileItem(str(output))])

    assert {item.path for item in window.files} == {str(source), str(output)}
    assert "Операция отменена" in window.operation_result_panel.summary.text()
    assert not window.operation_result_panel.open_result.isHidden()
    assert window.operation_result_panel.result.outcome == "cancelled"


def test_conversion_sample_uses_highlighted_docx_and_keeps_queue(window, tmp_path):
    sources = [tmp_path / f"{name}.docx" for name in ("first", "second")]
    for source in sources:
        document = Document()
        document.add_paragraph(source.stem)
        document.save(source)
    window.add_files(list(map(str, sources)))
    window.operations_tab_bar.setCurrentIndex(1)
    window.convert_file_type_combo.setCurrentText("Документы")
    window.from_convert_combo.setCurrentText("DOCX")
    window.to_convert_combo.setCurrentText("PDF")
    mode = window.combo_conversion_output_mode
    mode.setCurrentIndex(mode.findData("alongside"))
    window.auto_clear_enabled_checkbox.setChecked(True)
    window.auto_clear_convert_checkbox.setChecked(True)
    assert not window.conversion_panel.btn_sample.isEnabled()
    window.list_files.selectRow(1)
    assert window.conversion_panel.btn_sample.isEnabled()
    window.conversion_panel.btn_sample.click()
    assert window.file_worker.wait(5000)
    QApplication.processEvents()

    assert not sources[0].with_suffix(".pdf").exists()
    assert "second" in PdfReader(sources[1].with_suffix(".pdf")).pages[0].extract_text()
    assert len(window.files) == 3
    assert window.from_convert_combo.currentText() == "DOCX"
    assert window.to_convert_combo.currentText() == "PDF"


def test_merge_keyboard_order_matches_output(window, tmp_path):
    sources = [tmp_path / f"{index}.pdf" for index in range(3)]
    for index, source in enumerate(sources):
        with PdfWriter() as writer:
            writer.add_blank_page(width=200 + index * 10, height=300)
            writer.write(source)
    window.add_files(list(map(str, sources)))
    window.operations_tab_bar.setCurrentIndex(3)
    assert window.list_files.verticalHeader().isHidden()
    window.list_files.selectRow(2)
    QTest.keyClick(window.list_files, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    output = tmp_path / "combined.pdf"
    with (
        patch.object(window, "_select_merge_output_path_for_format", return_value=str(output)),
        patch.object(window, "show_russian_message_box", return_value=True),
    ):
        window.btn_merge.click()
    assert window.file_worker.wait(5000)
    QApplication.processEvents()
    assert [int(page.mediabox.width) for page in PdfReader(output).pages] == [200, 220, 210]
    assert window.operation_result_panel.result.outcome == "success"


def test_partial_result_retries_only_explicitly_retryable_errors(window, tmp_path):
    output = tmp_path / "created.pdf"
    output.write_bytes(b"test")
    window._operations.last_request = ConversionRequest("docx_to_pdf", "PDF", "alongside", "")
    window.on_operation_finished(OperationResult(
        new_files=[FileItem(str(output))],
        errors=[
            {"path": "document.docx", "message": "LayoutError"},
            {"path": "locked.docx", "message": "PermissionError", "retryable": True},
        ],
    ))
    panel = window.operation_result_panel
    assert "Обработана часть файлов" in panel.summary.text()
    assert len(panel.retryable) == 1 and panel.retryable[0]["path"] == "locked.docx"


def test_compression_result_reports_measured_sizes(window, tmp_path):
    source = tmp_path / "source.jpg"
    Image.effect_noise((600, 400), 90).save(source, quality=100)
    original_size = source.stat().st_size
    window.add_files([str(source)])
    window.operations_tab_bar.setCurrentIndex(2)
    with patch.object(window, "show_russian_message_box", return_value=True):
        window.btn_compress.click()
    assert window.file_worker.wait(5000)
    QApplication.processEvents()

    result = window.operation_result_panel.result
    size, = result.compression_sizes
    target, = result.new_files
    assert size.before == original_size
    assert size.after == target.size < original_size
    assert "Экономия" in window.operation_result_panel.summary.text()
