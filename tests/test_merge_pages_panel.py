import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from pypdf import PdfReader, PdfWriter

from app.ui.merge_pages import MergePagesPanel
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
