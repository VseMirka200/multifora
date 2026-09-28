import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import app.core.deps as deps
from core.workers.compression.compression_mixin import CompressionMixin
from core.workers.result import OperationResult


class _SignalStub:
    def __init__(self):
        self.emitted = []

    def emit(self, value):
        self.emitted.append(value)


class _DummyCompressionWorker(CompressionMixin):
    def __init__(self):
        self.files = []
        self.errors = []
        self._last_pdf_error = ""
        self.status = _SignalStub()
        self.progress = _SignalStub()
        self.finished = _SignalStub()
        self.error = _SignalStub()
        self._cancel_requested = False

    def _should_cancel(self):
        return self._cancel_requested

    def _emit_finished(self, new_files=None, updated_files=None):
        self.finished.emit(OperationResult(new_files or [], updated_files or [], list(self.errors)))


class GhostscriptDetectionTests(unittest.TestCase):
    def test_ensure_ghostscript_detected_invokes_detection_when_state_is_empty(self):
        original_has = deps.HAS_GHOSTSCRIPT
        original_path = deps.GHOSTSCRIPT_PATH
        try:
            deps.HAS_GHOSTSCRIPT = False
            deps.GHOSTSCRIPT_PATH = None

            def _fake_detect(custom_path=None):
                deps.HAS_GHOSTSCRIPT = True
                deps.GHOSTSCRIPT_PATH = custom_path or r"C:\fake\gswin64c.exe"

            with patch.object(deps, "_detect_ghostscript", side_effect=_fake_detect) as detect_mock:
                has_gs, path = deps.ensure_ghostscript_detected()

            self.assertEqual(detect_mock.call_count, 1)
            self.assertTrue(has_gs)
            self.assertTrue(path.endswith("gswin64c.exe"))
        finally:
            deps.HAS_GHOSTSCRIPT = original_has
            deps.GHOSTSCRIPT_PATH = original_path

    def test_compression_mixin_calls_dynamic_ghostscript_detection(self):
        worker = _DummyCompressionWorker()
        with patch("core.workers.compression.compression_mixin.deps.ensure_ghostscript_detected") as ensure_mock:
            worker._compress_pdf_files()
        self.assertEqual(ensure_mock.call_count, 1)
        self.assertEqual(len(worker.finished.emitted), 1)

    def test_detect_ghostscript_prefers_bundled_x64(self):
        original_has = deps.HAS_GHOSTSCRIPT
        original_path = deps.GHOSTSCRIPT_PATH
        original_argv0 = sys.argv[0]
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                bundled_dir = os.path.join(tmpdir, "bin", "gswin64")
                os.makedirs(bundled_dir)
                bundled_exe = os.path.join(bundled_dir, "gswin64c.exe")
                with open(bundled_exe, "wb") as f:
                    f.write(b"")

                sys.argv[0] = os.path.join(tmpdir, "Multifora.exe")
                with patch.dict(os.environ, {}, clear=True):
                    with patch.object(deps, "_find_ghostscript_in_registry", return_value=None):
                        with patch("app.core.deps.shutil.which", return_value=None):
                            deps._detect_ghostscript()

                self.assertTrue(deps.HAS_GHOSTSCRIPT)
                self.assertEqual(os.path.normcase(deps.GHOSTSCRIPT_PATH), os.path.normcase(bundled_exe))
        finally:
            deps.HAS_GHOSTSCRIPT = original_has
            deps.GHOSTSCRIPT_PATH = original_path
            sys.argv[0] = original_argv0

    def test_compression_emits_result_when_cancelled(self):
        worker = _DummyCompressionWorker()
        worker._cancel_requested = True
        with patch("core.workers.compression.compression_mixin.deps.ensure_ghostscript_detected"):
            worker._compress_pdf_files()
        self.assertEqual(len(worker.finished.emitted), 1)
        self.assertEqual(worker.finished.emitted[0].get("updated_files"), [])


if __name__ == "__main__":
    unittest.main()
