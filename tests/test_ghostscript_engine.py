import io
import unittest
from unittest.mock import Mock, patch

from core.workers.ghostscript_engine import GhostscriptUnavailableError, run_ghostscript


class GhostscriptEngineTests(unittest.TestCase):
    def test_missing_engine_is_classified_as_common_failure(self):
        with patch("core.workers.ghostscript_engine.deps.ensure_ghostscript_detected", return_value=(False, None)):
            with self.assertRaises(GhostscriptUnavailableError):
                run_ghostscript([], lambda: False)

    def test_engine_start_failure_is_classified_as_common_failure(self):
        with (
            patch(
                "core.workers.ghostscript_engine.deps.ensure_ghostscript_detected", return_value=(True, "ghostscript")
            ),
            patch("core.workers.ghostscript_engine.tempfile.TemporaryFile", return_value=io.StringIO()),
            patch("core.workers.ghostscript_engine.subprocess.Popen", side_effect=FileNotFoundError("missing")),
        ):
            with self.assertRaises(GhostscriptUnavailableError):
                run_ghostscript([], lambda: False)

    def test_unavailable_temp_directory_is_classified_as_common_failure(self):
        with (
            patch(
                "core.workers.ghostscript_engine.deps.ensure_ghostscript_detected", return_value=(True, "ghostscript")
            ),
            patch("core.workers.ghostscript_engine.tempfile.TemporaryFile", side_effect=PermissionError("denied")),
        ):
            with self.assertRaises(GhostscriptUnavailableError):
                run_ghostscript([], lambda: False)

    def test_calls_engine_with_safe_batch_arguments(self):
        process = Mock(returncode=0)
        process.poll.return_value = 0
        with (
            patch(
                "core.workers.ghostscript_engine.deps.ensure_ghostscript_detected", return_value=(True, "ghostscript")
            ),
            patch("core.workers.ghostscript_engine.tempfile.TemporaryFile", return_value=io.StringIO()),
            patch("core.workers.ghostscript_engine.subprocess.Popen", return_value=process) as launch,
        ):
            run_ghostscript(["-sDEVICE=docxwrite", "source.pdf"], lambda: False)
        self.assertEqual(
            launch.call_args.args[0],
            ["ghostscript", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=docxwrite", "source.pdf"],
        )

    def test_reports_process_error(self):
        process = Mock(returncode=1)
        process.poll.return_value = 1
        with (
            patch(
                "core.workers.ghostscript_engine.deps.ensure_ghostscript_detected", return_value=(True, "ghostscript")
            ),
            patch("core.workers.ghostscript_engine.tempfile.TemporaryFile", return_value=io.StringIO("bad PDF")),
            patch("core.workers.ghostscript_engine.subprocess.Popen", return_value=process),
        ):
            with self.assertRaisesRegex(RuntimeError, "bad PDF"):
                run_ghostscript([], lambda: False)

    def test_cancellation_stops_running_engine(self):
        process = Mock(returncode=None)
        process.poll.return_value = None
        with (
            patch(
                "core.workers.ghostscript_engine.deps.ensure_ghostscript_detected", return_value=(True, "ghostscript")
            ),
            patch("core.workers.ghostscript_engine.tempfile.TemporaryFile", return_value=io.StringIO()),
            patch("core.workers.ghostscript_engine.subprocess.Popen", return_value=process),
        ):
            with self.assertRaises(InterruptedError):
                run_ghostscript([], Mock(side_effect=[False, True]))
        process.terminate.assert_called_once()
        process.wait.assert_called_once()
