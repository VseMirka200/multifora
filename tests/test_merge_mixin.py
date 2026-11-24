import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.workers.merge_worker import MergeMixin, MergeWorker
from core.file_models import FileItem
from core.operation_result import OperationResult


def test_merge_selected_docx_pages_keeps_editable_content(tmp_path):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Inches
    from PIL import Image

    first = tmp_path / "first.docx"
    second = tmp_path / "second.docx"
    output = tmp_path / "merged.docx"
    picture = tmp_path / "picture.png"
    Image.new("RGB", (20, 20), "blue").save(picture)

    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Inches(11), Inches(8.5)
    section.header.paragraphs[0].text = "Landscape header"
    document.add_paragraph("Excluded")
    paragraph = document.add_paragraph("Selected ")
    paragraph.paragraph_format.page_break_before = True
    paragraph.add_run("bold").bold = True
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Editable cell"
    document.add_picture(str(picture))
    document.save(first)
    document = Document()
    document.add_paragraph("First in result")
    document.save(second)

    worker = _DummyMergeWorker()
    worker.files = [FileItem(str(first)), FileItem(str(second))]
    worker.merge_output_path = str(output)
    worker.page_order = ((1, 0), (0, 1))
    worker._merge_files_to_target()

    merged = Document(output)
    paragraphs = [paragraph for paragraph in merged.paragraphs if paragraph.text]
    assert [paragraph.text for paragraph in paragraphs] == ["First in result", "Selected bold"]
    assert any(run.bold and run.text == "bold" for run in paragraphs[-1].runs)
    assert merged.tables[0].cell(0, 0).text == "Editable cell"
    assert len(merged.inline_shapes) == 1
    assert merged.sections[0].orientation == WD_ORIENT.PORTRAIT
    assert merged.sections[1].orientation == WD_ORIENT.LANDSCAPE
    assert merged.sections[1].header.paragraphs[0].text == "Landscape header"


class _SignalStub:
    def __init__(self):
        self.emitted = []

    def emit(self, value):
        self.emitted.append(value)


class _DummyMergeWorker(MergeMixin):
    def __init__(self):
        self.files = []
        self.errors = []
        self.merge_output_format = "docx"
        self.merge_output_path = ""
        self.status = _SignalStub()
        self.progress = _SignalStub()
        self.finished = _SignalStub()
        self.error = _SignalStub()
        self._cancel_requested = False

    def _should_cancel(self):
        return self._cancel_requested

    def _record_error(self, file_item, message):
        self.errors.append({"file": file_item, "message": message})

    def _emit_finished(self, new_files=None, updated_files=None):
        self.finished.emit(
            OperationResult(
                new_files or [], updated_files or [], list(self.errors)
            )
        )

    def _get_unique_path(self, path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        return f"{base}_1{ext}"


def test_merge_worker_preserves_sections_and_header_relationships(tmp_path):
    from docx import Document
    from docx.enum.section import WD_ORIENT, WD_SECTION_START
    from docx.shared import Inches
    from PIL import Image

    picture = tmp_path / "image.png"
    with Image.new("RGB", (8, 8), "blue") as image:
        image.save(picture)
    first, second, third = (tmp_path / f"{name}.docx" for name in ("first", "second", "third"))
    document = Document()
    document.sections[0].header.paragraphs[0].text = "First header"
    document.add_paragraph("First body")
    document.save(first)

    document = Document()
    document.settings.odd_and_even_pages_header_footer = True
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Inches(11), Inches(8.5)
    section.header.paragraphs[0].text = "Second header"
    section.header.paragraphs[0].add_run().add_picture(str(picture))
    section.even_page_header.paragraphs[0].text = "Second even header"
    section.footer.paragraphs[0].text = "Second footer"
    document.add_paragraph("Second body")
    document.add_section(WD_SECTION_START.CONTINUOUS)
    document.add_paragraph("Next section of second body")
    document.save(second)

    document = Document()
    document.add_paragraph("Third body")
    document.save(third)

    output = tmp_path / "merged.docx"
    worker = MergeWorker([FileItem(str(path)) for path in (first, second, third)], "docx", str(output))
    worker.run()
    merged = Document(output)
    first_section, second_section, continuation, third_section = merged.sections
    assert first_section.header.paragraphs[0].text == "First header"
    assert first_section.even_page_header.paragraphs[0].text == "First header"
    assert second_section.header.paragraphs[0].text == "Second header"
    assert second_section.even_page_header.paragraphs[0].text == "Second even header"
    assert second_section.footer.paragraphs[0].text == "Second footer"
    assert second_section.orientation == WD_ORIENT.LANDSCAPE
    assert continuation.start_type == WD_SECTION_START.CONTINUOUS
    assert continuation.header.is_linked_to_previous
    assert any(rel.reltype.endswith("/image") for rel in second_section.header.part.rels.values())
    assert third_section.header.paragraphs[0].text == ""


def test_merge_worker_cancellation_during_docx_write_keeps_destination_absent(tmp_path):
    from docx import Document
    from docx.document import Document as DocumentType

    sources = [tmp_path / "first.docx", tmp_path / "second.docx"]
    for source in sources:
        Document().save(source)
    original = [source.read_bytes() for source in sources]
    output = tmp_path / "merged.docx"
    worker = MergeWorker([FileItem(str(path)) for path in sources], "docx", str(output))
    results, progress = [], []
    worker.finished.connect(results.append)
    worker.progress.connect(progress.append)
    save = DocumentType.save

    def cancel_after_write(document, path):
        save(document, path)
        worker.request_cancel()

    with patch.object(DocumentType, "save", cancel_after_write):
        worker.run()
    assert results[0].cancelled
    assert 100 not in progress
    assert sorted(tmp_path.iterdir()) == sources
    assert [source.read_bytes() for source in sources] == original


class MergeMixinTests(unittest.TestCase):
    def test_dedicated_merge_worker_keeps_its_own_operation_state(self):
        worker = MergeWorker([], "pdf", "output.pdf")
        self.assertEqual(worker.merge_output_format, "pdf")
        self.assertFalse(worker._should_cancel())
        worker.request_cancel()
        self.assertTrue(worker._should_cancel())

    def test_pdf_output_rejects_word_and_mixed_inputs(self):
        worker = _DummyMergeWorker()
        worker.merge_output_format = "pdf"

        for paths in (
            ("first.docx", "second.docx"),
            ("first.pdf", "second.docx"),
        ):
            worker.files = [Mock(path=path, is_file=True) for path in paths]
            with self.assertRaisesRegex(Exception, "только файлы PDF"):
                worker._merge_files_to_target()

    def test_merge_rejects_source_removed_after_it_was_queued(self):
        worker = _DummyMergeWorker()
        worker.merge_output_format = "pdf"
        worker.files = [
            Mock(path="first.pdf", is_file=True),
            Mock(path="second.pdf", is_file=True),
        ]

        with (
            patch("core.merge_documents.os.path.isfile", return_value=False),
            self.assertRaisesRegex(FileNotFoundError, "Не найдены или недоступны"),
        ):
            worker._merge_files_to_target()

    def test_merge_docx_files(self):
        from docx import Document

        worker = _DummyMergeWorker()
        with tempfile.TemporaryDirectory() as tmpdir:
            first = os.path.join(tmpdir, "first.docx")
            second = os.path.join(tmpdir, "second.docx")

            doc = Document()
            doc.add_paragraph("First")
            doc.save(first)

            doc = Document()
            doc.add_paragraph("Second")
            doc.save(second)

            worker.files = [FileItem(first), FileItem(second)]
            output = worker._merge_files_to_target()

            self.assertTrue(os.path.exists(output))
            merged = Document(output)
            text = "\n".join(paragraph.text for paragraph in merged.paragraphs)
            self.assertIn("First", text)
            self.assertIn("Second", text)
            self.assertLess(text.index("First"), text.index("Second"))

    def test_merge_pdf_preserves_queue_order(self):
        from tests.pdf_engine_fixtures import create_pdf, read_pdf_text

        worker = _DummyMergeWorker()
        worker.merge_output_format = "pdf"
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for index in (2, 1):
                path = os.path.join(tmpdir, f"{index}.pdf")
                create_pdf(path, [f"Document {index}"])
                files.append(FileItem(path))
            worker.files = files
            output = worker._merge_files_to_target()
            from pathlib import Path
            text = read_pdf_text(output, Path(tmpdir) / "result.txt")
            self.assertLess(text.index("Document 2"), text.index("Document 1"))

    def test_merge_uses_requested_output_path(self):
        from docx import Document

        worker = _DummyMergeWorker()
        with tempfile.TemporaryDirectory() as tmpdir:
            first = os.path.join(tmpdir, "first.docx")
            second = os.path.join(tmpdir, "second.docx")
            requested = os.path.join(tmpdir, "custom-name.docx")

            for path, value in ((first, "First"), (second, "Second")):
                doc = Document()
                doc.add_paragraph(value)
                doc.save(path)

            worker.files = [FileItem(first), FileItem(second)]
            worker.merge_output_path = requested

            self.assertEqual(worker._merge_files_to_target(), requested)
            self.assertTrue(os.path.exists(requested))


if __name__ == "__main__":
    unittest.main()
