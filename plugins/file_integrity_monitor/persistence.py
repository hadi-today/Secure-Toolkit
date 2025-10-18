"""SQLite persistence helpers for the file integrity monitor."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Iterable, Tuple

from .legacy import migrate
from .paths import DATABASE_PATH, PLUGIN_DIR
from .types import DEFAULT_INTERVAL_MINUTES, Inventory


def initialize_database() -> None:
    os.makedirs(PLUGIN_DIR, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        with connection:
            statements = [
                "CREATE TABLE IF NOT EXISTS directories (path TEXT PRIMARY KEY)",
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS baseline ( path TEXT PRIMARY KEY, hash TEXT NOT NULL, size INTEGER NOT NULL, mtime REAL NOT NULL )",
                "CREATE TABLE IF NOT EXISTS scan_history ( id INTEGER PRIMARY KEY AUTOINCREMENT, trigger TEXT NOT NULL, run_at TEXT NOT NULL, changed_count INTEGER NOT NULL, deleted_count INTEGER NOT NULL, new_count INTEGER NOT NULL, message TEXT NOT NULL, signature TEXT, acknowledged INTEGER NOT NULL DEFAULT 0 )",
                "CREATE TABLE IF NOT EXISTS acknowledged_findings ( signature TEXT PRIMARY KEY, acknowledged_at TEXT NOT NULL )",
            ]
            for statement in statements:
                connection.execute(statement)
            _ensure_column(connection, "scan_history", "signature TEXT")
            _ensure_column(
                connection,
                "scan_history",
                "acknowledged INTEGER NOT NULL DEFAULT 0",
            )
        migrate(connection)


def load_config() -> Tuple[list[str], int, bool]:
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            directory_rows = connection.execute(
                "SELECT path FROM directories ORDER BY path"
            ).fetchall()
            settings = dict(
                connection.execute("SELECT key, value FROM settings").fetchall()
            )
    except sqlite3.Error:
        return [], DEFAULT_INTERVAL_MINUTES, False

    directories = [
        path for (path,) in directory_rows if isinstance(path, str) and os.path.isdir(path)
    ]
    interval = _clamp_interval(_safe_int(settings.get("interval_minutes")))
    auto_scan = str(settings.get("auto_scan")) == "1"
    return directories, interval, auto_scan


def save_config(directories: Iterable[str], interval: int, auto_scan: bool) -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        with connection:
            connection.execute("DELETE FROM directories")
            connection.executemany(
                "INSERT INTO directories(path) VALUES (?)",
                ((os.path.abspath(path),) for path in directories),
            )
            _upsert_setting(connection, "interval_minutes", str(interval))
            _upsert_setting(connection, "auto_scan", "1" if auto_scan else "0")


def load_baseline() -> Inventory:
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            rows = connection.execute(
                "SELECT path, hash, size, mtime FROM baseline"
            ).fetchall()
    except sqlite3.Error:
        return {}

    baseline: Inventory = {}
    for path, hash_value, size, mtime in rows:
        if not isinstance(path, str):
            continue
        baseline[path] = {
            "hash": hash_value,
            "size": size,
            "mtime": mtime,
        }
    return baseline


def save_baseline(inventory: Inventory) -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        with connection:
            connection.execute("DELETE FROM baseline")
            connection.executemany(
                "INSERT INTO baseline(path, hash, size, mtime) VALUES (?, ?, ?, ?)",
                (
                    (
                        path,
                        str(metadata.get("hash", "")),
                        int(metadata.get("size", 0)),
                        float(metadata.get("mtime", 0.0)),
                    )
                    for path, metadata in inventory.items()
                ),
            )
            _upsert_setting(
                connection,
                "baseline_captured_at",
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )

def load_baseline_timestamp() -> str | None:
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = 'baseline_captured_at'"
            ).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def _ensure_column(connection: sqlite3.Connection, table: str, definition: str) -> None:
    try:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
    except sqlite3.OperationalError:
        pass


def _upsert_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _safe_int(value, default: int = DEFAULT_INTERVAL_MINUTES) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_interval(value: int) -> int:
    return min(max(1, value), 24 * 60)
