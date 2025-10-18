"""Output formatting helpers for scan results."""

from __future__ import annotations

import time
from typing import Iterable

from .scanner import ScanResult


def summarize(trigger: str, result: ScanResult) -> str:
    parts = [
        timestamped(f"{trigger} detected changes:"),
        _section("Modified", result.changed),
        _section("Deleted", result.deleted),
        _section("New", result.new),
    ]
    return "\n".join(filter(None, parts))


def timestamped(message: str) -> str:
    return f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"


def _section(label: str, entries: Iterable[str]) -> str:
    entries = list(entries)
    if not entries:
        return ""
    lines = [f"  {label} files ({len(entries)}):"]
    lines.extend(f"    • {path}" for path in entries)
    return "\n".join(lines)
