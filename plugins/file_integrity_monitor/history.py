"""Scan history storage helpers for the file integrity monitor."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List

from .acknowledgements import is_acknowledged
from .paths import DATABASE_PATH


def record_scan(
    trigger: str,
    changed: int,
    deleted: int,
    new: int,
    message: str,
    signature: str | None = None,
) -> None:
    """Persist a scan summary while trimming old entries."""

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(DATABASE_PATH) as connection:
        with connection:
            connection.execute(
                (
                    "INSERT INTO scan_history(trigger, run_at, changed_count, deleted_count,"
                    " new_count, message, signature, acknowledged)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    trigger,
                    timestamp,
                    changed,
                    deleted,
                    new,
                    message,
                    signature,
                    1 if is_acknowledged(signature) else 0,
                ),
            )
            connection.execute(
                "DELETE FROM scan_history WHERE id NOT IN ("
                " SELECT id FROM scan_history ORDER BY id DESC LIMIT 200"
                ")"
            )


def fetch_recent_scans(limit: int = 50) -> List[dict[str, object]]:
    """Return the most recent scan entries ordered from newest to oldest."""

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT trigger, run_at, changed_count, deleted_count, new_count, message, signature, acknowledged"
            " FROM scan_history ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    result: List[dict[str, object]] = []
    for row in rows:
        record = dict(row)
        record["acknowledged"] = bool(record.get("acknowledged"))
        result.append(record)
    return result


__all__ = ["record_scan", "fetch_recent_scans"]
