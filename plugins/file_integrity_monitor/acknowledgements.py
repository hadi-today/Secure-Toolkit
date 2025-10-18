"""Persistence helpers for acknowledged scan findings."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .paths import DATABASE_PATH


def is_acknowledged(signature: str | None) -> bool:
    if not signature:
        return False
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            "SELECT 1 FROM acknowledged_findings WHERE signature = ?",
            (signature,),
        ).fetchone()
    return row is not None


def acknowledge(signature: str | None) -> None:
    if not signature:
        return
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(DATABASE_PATH) as connection:
        with connection:
            connection.execute(
                "INSERT INTO acknowledged_findings(signature, acknowledged_at) VALUES (?, ?)"
                " ON CONFLICT(signature) DO UPDATE SET acknowledged_at=excluded.acknowledged_at",
                (signature, timestamp),
            )
            connection.execute(
                "UPDATE scan_history SET acknowledged = 1 WHERE signature = ?",
                (signature,),
            )


def clear_acknowledgements() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        with connection:
            connection.execute("DELETE FROM acknowledged_findings")
            connection.execute("UPDATE scan_history SET acknowledged = 0")


__all__ = ["acknowledge", "clear_acknowledgements", "is_acknowledged"]
