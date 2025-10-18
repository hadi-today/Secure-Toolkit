"""Shared actions for the file integrity monitor dialog."""

from __future__ import annotations

from .acknowledgements import is_acknowledged
from .formatting import summarize, timestamped
from .history import record_scan


def handle_scan(widget, trigger: str) -> None:
    result = widget._controller.perform_scan()
    signature = result.signature() if result.has_findings else None
    if result.has_findings:
        if is_acknowledged(signature):
            widget._last_reported_result = result
            widget._set_ack_state(None, False)
            return
        if widget._last_reported_result == result:
            return
        message = summarize(trigger, result)
        widget._last_reported_result = result
        widget._set_ack_state(signature, True)
    else:
        message = timestamped(f"{trigger} found no changes.")
        widget._set_ack_state(None, False, True)
    record_scan(trigger, len(result.changed), len(result.deleted), len(result.new), message, signature)
    widget._append_log(message)


__all__ = ["handle_scan"]
