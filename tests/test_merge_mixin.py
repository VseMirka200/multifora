import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.core.models import FileItem
from core.workers.merge.merge_mixin import MergeMixin
from core.workers.merge.merge_worker import MergeWorker
from core.workers.result import OperationResult


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
            patch("core.workers.merge.merge_mixin.os.path.isfile", return_value=False),
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
        import pymupdf

        worker = _DummyMergeWorker()
        worker.merge_output_format = "pdf"
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for index in (2, 1):
                path = os.path.join(tmpdir, f"{index}.pdf")
                with pymupdf.open() as document:
                    document.new_page().insert_text((72, 72), f"Document {index}")
                    document.save(path)
                files.append(FileItem(path))
            worker.files = files
            output = worker._merge_files_to_target()
            with pymupdf.open(output) as document:
                self.assertEqual(len(document), 2)
                self.assertIn("Document 2", document[0].get_text())
                self.assertIn("Document 1", document[1].get_text())

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
