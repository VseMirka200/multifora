import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QListWidget
from pypdf import PdfReader, PdfWriter

from app.ui.merge_pages import MergePagesPanel, PageList
from core.file_models import FileItem
from core.pdf_engine.merge import combine_pdfs


def test_inline_pages_reorder_and_refresh(tmp_path):
    app = QApplication.instance() or QApplication([])
    sources = []
    for name, widths in (("a", (100, 200)), ("b", (300, 400))):
        path = tmp_path / f"{name}.pdf"
        writer = PdfWriter()
        for width in widths:
            writer.add_blank_page(width=width, height=100)
        writer.write(path)
        writer.close()
        sources.append(FileItem(str(path)))
    panel = MergePagesPanel()
    try:
        panel.set_files(sources)
        deadline = time.monotonic() + 10
        while not panel.ready and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert panel.ready
        assert panel.pages.count() == 4
        panel.pages.setCurrentRow(3)
        panel.pages.move_current(0)
        order = panel.page_order()
        panel.set_files(sources)
        assert panel.page_order() == order
        output = tmp_path / "merged.pdf"
        combine_pdfs([f.path for f in sources], output, lambda: False, page_order=order)
        assert [int(p.mediabox.width) for p in PdfReader(output).pages] == [400, 100, 200, 300]
        panel.set_files([])
        assert not panel.ready
        assert panel.pages.count() == 0
    finally:
        panel.stop()
        panel.close()


def test_page_list_supports_two_dimensional_internal_drag_drop():
    app = QApplication.instance() or QApplication([])
    pages = PageList(None)
    try:
        assert pages.dragEnabled()
        assert pages.acceptDrops()
        assert pages.showDropIndicator()
        assert pages.dragDropMode() == QListWidget.DragDropMode.DragDrop
        assert pages.flow() == QListWidget.Flow.LeftToRight
        assert pages.isWrapping()
        assert pages.movement() == QListWidget.Movement.Snap
        assert pages.selectionMode() == QListWidget.SelectionMode.ExtendedSelection
        assert pages.viewport().acceptDrops()
    finally:
        pages.close()


def test_merge_panel_rejects_unsupported_or_mixed_formats_without_loading(tmp_path):
    app = QApplication.instance() or QApplication([])
    pdf = tmp_path / "one.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    panel = MergePagesPanel()
    try:
        panel.set_files([FileItem(str(pdf)), FileItem(str(text))])
        app.processEvents()
        assert panel.loader is None
        assert not panel.ready
        assert "одного формата: PDF или DOCX" in panel.hint.text()
    finally:
        panel.stop()
        panel.close()


def test_invalid_docx_error_identifies_source_file(tmp_path):
    app = QApplication.instance() or QApplication([])
    first = tmp_path / "broken-one.docx"
    second = tmp_path / "broken-two.docx"
    first.write_text("not a docx archive", encoding="utf-8")
    second.write_text("not a docx archive", encoding="utf-8")
    panel = MergePagesPanel()
    try:
        panel.set_files([FileItem(str(first)), FileItem(str(second))])
        deadline = time.monotonic() + 5
        while panel.loader is not None and panel.loader.isRunning() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert "broken-one.docx" in panel.hint.text()
        assert "Ожидается настоящий документ DOCX" in panel.hint.text()
    finally:
        panel.stop()
        panel.close()
