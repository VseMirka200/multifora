import pytest
from PySide6.QtCore import QObject

from app.core.qt_utils import signals_blocked


@pytest.mark.parametrize("initially_blocked", [False, True])
def test_signal_guard_restores_previous_state_after_error(initially_blocked):
    widget = QObject()
    widget.blockSignals(initially_blocked)

    with pytest.raises(ValueError, match="failed update"), signals_blocked(widget):
        assert widget.signalsBlocked()
        raise ValueError("failed update")

    assert widget.signalsBlocked() == initially_blocked


def test_nested_signal_guards_do_not_unblock_outer_update():
    widget = QObject()
    with signals_blocked(widget):
        with signals_blocked(widget):
            assert widget.signalsBlocked()
        assert widget.signalsBlocked()
    assert not widget.signalsBlocked()
