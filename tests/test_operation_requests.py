"""Regression tests for immutable operation requests and dispatching."""

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
    def test_request_fields_are_immutable(self):
        request = RenameRequest(("source.txt",), ("target.txt",))

        with self.assertRaises(AttributeError):
            request.strict = True

    def test_dispatcher_reports_progress_and_cancellation(self):
        dispatcher = OperationDispatcher()
        events = []
        cancellation = CancellationToken()
        cancellation.cancel()

        def handle(_request, context):
            context.report_progress(150)
            if context.is_cancelled:
                return OperationResult(warnings=[{"message": "cancelled"}])
            return OperationResult()

        dispatcher.register(CompressionRequest, handle)
        result = dispatcher.dispatch(
            CompressionRequest(("source.png",), 85),
            cancellation=cancellation,
            event_listener=events.append,
        )

        self.assertEqual(result.warnings, [{"message": "cancelled"}])
        self.assertEqual(events[0].value, 100)

    def test_dispatcher_returns_error_result_for_missing_handler(self):
        result = OperationDispatcher().dispatch(
            MergeRequest(("first.pdf", "second.pdf"))
        )

        self.assertIn("No handler", result.errors[0]["message"])

    def test_all_request_types_keep_operation_configuration(self):
        self.assertTrue(ConversionRequest(("source.png",), "image"))
        self.assertTrue(CompressionRequest(("source.png",), 80))
        self.assertTrue(MergeRequest(("first.pdf", "second.pdf")))
