"""Flush deferred Qt cleanup when tests do not run the application event loop."""

import pytest
from PySide6.QtCore import QCoreApplication, QEvent


@pytest.fixture(autouse=True)
def flush_deferred_qt_deletes():
    yield
    # processEvents() alone does not flush DeferredDelete outside app.exec().
    # Keeping old windows alive makes each subsequent global QSS change slower.
    if QCoreApplication.instance() is not None:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
