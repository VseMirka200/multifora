"""Tests for framework-neutral typed file operation dispatching."""

import unittest

from core.operations import (
    CancellationToken,
    CompressionRequest,
    ConversionRequest,
    MergeRequest,
    OperationDispatcher,
    RenameRequest,
)
from core.workers.result import OperationResult


class OperationRequestTests(unittest.TestCase):
    def test_requests_are_immutable(self):
        request = RenameRequest(("one.txt",), ("renamed.txt",), strict=True)

        with self.assertRaises(AttributeError):
            request.strict = False

    def test_request_validation_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            RenameRequest(("one.txt",), ())
        with self.assertRaises(ValueError):
            ConversionRequest(("one.txt",), "image", output_mode="unknown")
        with self.assertRaises(ValueError):
            CompressionRequest(("one.png",), 101)
        with self.assertRaises(ValueError):
            MergeRequest(("one.pdf",), output_format="txt")


class OperationDispatcherTests(unittest.TestCase):
    def test_dispatch_passes_events_and_returns_handler_result(self):
        dispatcher = OperationDispatcher()
        events = []

        def handle(request, context):
            self.assertIsInstance(request, MergeRequest)
            context.report_status("Merging")
            context.report_progress(125)
            return OperationResult(new_files=["merged.pdf"])

        dispatcher.register(MergeRequest, handle)
        result = dispatcher.dispatch(
            MergeRequest(("one.pdf", "two.pdf")),
            event_listener=events.append,
        )

        self.assertEqual(result.new_files, ["merged.pdf"])
        self.assertEqual(
            [(event.kind, event.value) for event in events],
            [("status", "Merging"), ("progress", 100)],
        )

    def test_dispatcher_exposes_cancellation_to_the_handler(self):
        dispatcher = OperationDispatcher()
        cancellation = CancellationToken()
        cancellation.cancel()

        def handle(_request, context):
            if context.is_cancelled:
                return OperationResult(warnings=[{"message": "Cancelled"}])
            return OperationResult()

        dispatcher.register(CompressionRequest, handle)
        result = dispatcher.dispatch(
            CompressionRequest(("one.png",), 85),
            cancellation=cancellation,
        )

        self.assertEqual(result.warnings, [{"message": "Cancelled"}])

    def test_dispatcher_returns_error_result_for_failures_or_missing_handler(
        self,
    ):
        dispatcher = OperationDispatcher()
        events = []

        missing_result = dispatcher.dispatch(
            ConversionRequest(("one.png",), "image"),
            event_listener=events.append,
        )
        self.assertIn("No handler", missing_result.errors[0]["message"])

        def fail(_request, _context):
            raise RuntimeError("conversion failed")

        dispatcher.register(ConversionRequest, fail)
        failed_result = dispatcher.dispatch(
            ConversionRequest(("one.png",), "image"),
            event_listener=events.append,
        )

        self.assertEqual(
            failed_result.errors, [{"message": "conversion failed"}]
        )
        self.assertEqual(events[-1].kind, "error")


if __name__ == "__main__":
    unittest.main()
