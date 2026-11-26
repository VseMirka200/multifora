import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.models import FileItem
from core.workers.merge.merge_mixin import MergeMixin
from core.workers.merge.merge_worker import MergeWorker


class _Signal:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class _Worker(MergeMixin):
    def __init__(self, files, output_path=""):
        self.files = files
        self.merge_output_format = "pdf"
        self.merge_output_path = output_path
        self.status = _Signal()
        self.progress = _Signal()
        self.finished = _Signal()
        self.error = _Signal()
        self.errors = []

    def _should_cancel(self):
        return False

    def _record_error(self, file_item, message):
        self.errors.append((file_item, message))

    def _emit_finished(self, new_files=None, updated_files=None):
        self.finished.emit((new_files or [], updated_files or []))

    def _get_unique_path(self, path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        return f"{base}_1{ext}"


class MergeMixinTests(unittest.TestCase):
    def test_merge_worker_keeps_operation_state(self):
        worker = MergeWorker([], "pdf", "output.pdf")
        self.assertEqual(worker.merge_output_format, "pdf")
        self.assertFalse(worker._should_cancel())
        worker.request_cancel()
        self.assertTrue(worker._should_cancel())

    def test_docx_and_mixed_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name in ("first.docx", "second.pdf"):
                path = os.path.join(directory, name)
                with open(path, "wb") as stream:
                    stream.write(b"input")
                paths.append(path)
            worker = _Worker([FileItem(paths[0]), FileItem(paths[0])])
            with self.assertRaisesRegex(ValueError, "Объединение DOCX удалено"):
                worker._merge_files_to_target()
            worker.files = [FileItem(paths[0]), FileItem(paths[1])]
            with self.assertRaisesRegex(ValueError, "Объединяет PDF с PDF"):
                worker._merge_files_to_target()

    def test_missing_source_is_reported_before_engine_invocation(self):
        worker = _Worker([
            SimpleNamespace(path="missing-a.pdf", is_file=True, name="missing-a.pdf"),
            SimpleNamespace(path="missing-b.pdf", is_file=True, name="missing-b.pdf"),
        ])
        with patch("core.workers.merge.merge_mixin.native_engines.merge_pdfs") as engine:
            with self.assertRaisesRegex(FileNotFoundError, "Не найдены исходные PDF"):
                worker._merge_files_to_target()
        engine.assert_not_called()

    def test_pdf_merge_delegates_to_pdfcraft_and_respects_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name in ("a.pdf", "b.pdf"):
                path = os.path.join(directory, name)
                with open(path, "wb") as stream:
                    stream.write(b"%PDF-1.7 placeholder")
                paths.append(path)
            requested = os.path.join(directory, "merged-custom.pdf")
            worker = _Worker([FileItem(path) for path in paths], requested)

            def merge(_owner, files, output):
                self.assertEqual([file.path for file in files], paths)
                with open(output, "wb") as stream:
                    stream.write(b"%PDF-1.7 merged")
                return output

            with patch("core.workers.merge.merge_mixin.native_engines.merge_pdfs", side_effect=merge) as engine:
                result = worker._merge_files_to_target()
            self.assertEqual(result, requested)
            engine.assert_called_once()
            self.assertTrue(os.path.isfile(requested))

    def test_only_pdf_merge_is_exposed(self):
        source = open("app/ui/mixins/worker_ops_mixin.py", encoding="utf-8").read()
        self.assertIn('if extensions == {".pdf"}:', source)
        self.assertNotIn('if extensions == {".docx"}:', source)


if __name__ == "__main__":
    unittest.main()
