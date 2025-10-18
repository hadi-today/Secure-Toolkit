"""Persistence helpers for the port monitor plugin."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional


class PortActivityRepository:
    """SQLite-backed repository that stores port availability events."""

    def __init__(self, database_path: str):
        self._database_path = database_path
        os.makedirs(os.path.dirname(self._database_path), exist_ok=True)
        self._initialise_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _initialise_schema(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS port_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    protocol TEXT NOT NULL,
                    address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    pid INTEGER,
                    process_name TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_open
                ON port_activity(end_time)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_port
                ON port_activity(port)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    is_running INTEGER NOT NULL DEFAULT 0,
                    desired_state TEXT,
                    poll_interval REAL NOT NULL DEFAULT 2.0,
                    updated_at TEXT NOT NULL,
                    last_heartbeat TEXT,
                    last_error TEXT
                )
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO monitor_state (
                    id, is_running, desired_state, poll_interval, updated_at, last_heartbeat, last_error
                ) VALUES (1, 0, NULL, 2.0, ?, NULL, NULL)
                """,
                (self._now_iso(),),
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def record_start(
        self,
        *,
        protocol: str,
        address: str,
        port: int,
        pid: int | None,
        process_name: str,
        start_time: str,
    ) -> int:
        """Insert a new port availability record and return its identifier."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO port_activity (
                    protocol, address, port, pid, process_name, start_time
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (protocol, address, port, pid, process_name, start_time),
            )
            connection.commit()
            return cursor.lastrowid

    def record_stop(self, record_id: int, end_time: str) -> None:
        """Update an existing availability record with an end timestamp."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE port_activity
                   SET end_time = ?
                 WHERE id = ? AND end_time IS NULL
                """,
                (end_time, record_id),
            )
            connection.commit()

    def close_all_active(self, end_time: str) -> None:
        """Mark any open records as closed at ``end_time``."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE port_activity
                   SET end_time = ?
                 WHERE end_time IS NULL
                """,
                (end_time,),
            )
            connection.commit()

    def fetch_open_ports(self) -> List[Dict[str, object]]:
        """Return port records that do not yet have an ``end_time``."""

        with self._connect() as connection:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT id, protocol, address, port, pid, process_name, start_time
                  FROM port_activity
                 WHERE end_time IS NULL
              ORDER BY start_time ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_recent_history(self, limit: int = 200) -> List[Dict[str, object]]:
        """Return the most recent availability events up to ``limit`` rows."""

        with self._connect() as connection:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT id, protocol, address, port, pid, process_name,
                       start_time, end_time
                  FROM port_activity
              ORDER BY COALESCE(end_time, start_time) DESC, id DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def purge(self, keep_latest: int = 1000) -> None:
        """Keep only the ``keep_latest`` most recent rows to bound storage."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                DELETE FROM port_activity
                 WHERE id NOT IN (
                       SELECT id FROM port_activity
                       ORDER BY id DESC
                       LIMIT ?
                 )
                """,
                (keep_latest,),
            )
            connection.commit()

    def set_service_state(self, *, is_running: bool, poll_interval: float) -> None:
        """Persist the current service state for consumption by the web panel."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE monitor_state
                   SET is_running = ?,
                       poll_interval = ?,
                       updated_at = ?,
                       desired_state = CASE WHEN ? THEN desired_state ELSE NULL END
                 WHERE id = 1
                """,
                (
                    1 if is_running else 0,
                    float(poll_interval),
                    self._now_iso(),
                    1 if is_running else 0,
                ),
            )
            connection.commit()

    def update_heartbeat(self, timestamp: Optional[str] = None) -> None:
        """Store the last successful polling timestamp."""

        heartbeat = timestamp or self._now_iso()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE monitor_state
                   SET last_heartbeat = ?,
                       updated_at = ?
                 WHERE id = 1
                """,
                (heartbeat, self._now_iso()),
            )
            connection.commit()

    def set_error_state(self, message: Optional[str], timestamp: Optional[str] = None) -> None:
        """Record or clear the latest error message surfaced by the monitor."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE monitor_state
                   SET last_error = ?,
                       updated_at = ?
                 WHERE id = 1
                """,
                (message, timestamp or self._now_iso()),
            )
            connection.commit()

    def request_stop(self) -> None:
        """Flag that the running worker should stop as soon as practical."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE monitor_state
                   SET desired_state = 'stop',
                       updated_at = ?
                 WHERE id = 1
                """,
                (self._now_iso(),),
            )
            connection.commit()

    def clear_stop_request(self) -> None:
        """Remove any outstanding stop request flag."""

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE monitor_state
                   SET desired_state = NULL,
                       updated_at = ?
                 WHERE id = 1
                """,
                (self._now_iso(),),
            )
            connection.commit()

    def should_stop(self) -> bool:
        """Return ``True`` when a remote stop request has been issued."""

        with self._connect() as connection:
            cursor = connection.cursor()
            row = cursor.execute(
                "SELECT desired_state FROM monitor_state WHERE id = 1"
            ).fetchone()
        if not row:
            return False
        return row[0] == "stop"

    def get_service_state(self) -> Dict[str, object]:
        """Return the last recorded service state snapshot."""

        with self._connect() as connection:
            cursor = connection.cursor()
            row = cursor.execute(
                """
                SELECT is_running, desired_state, poll_interval, updated_at,
                       last_heartbeat, last_error
                  FROM monitor_state
                 WHERE id = 1
                """
            ).fetchone()

        if not row:
            return {
                "is_running": False,
                "desired_state": None,
                "poll_interval": 2.0,
                "updated_at": None,
                "last_heartbeat": None,
                "last_error": None,
            }

        return {
            "is_running": bool(row[0]),
            "desired_state": row[1],
            "poll_interval": float(row[2]) if row[2] is not None else 2.0,
            "updated_at": row[3],
            "last_heartbeat": row[4],
            "last_error": row[5],
        }

    def append_log(self, message: str, timestamp: Optional[str] = None) -> None:
        """Persist a log entry and trim the log table to a reasonable size."""

        log_timestamp = timestamp or self._now_iso()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO monitor_log (timestamp, message)
                VALUES (?, ?)
                """,
                (log_timestamp, message),
            )
            cursor.execute(
                """
                DELETE FROM monitor_log
                 WHERE id NOT IN (
                       SELECT id FROM monitor_log
                       ORDER BY id DESC
                       LIMIT 1000
                 )
                """
            )
            connection.commit()

    def fetch_recent_logs(self, limit: int = 200) -> List[Dict[str, object]]:
        """Return the most recent log lines recorded by the monitor."""

        with self._connect() as connection:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT id, timestamp, message
                  FROM monitor_log
              ORDER BY id DESC
                 LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]


__all__ = ["PortActivityRepository"]
