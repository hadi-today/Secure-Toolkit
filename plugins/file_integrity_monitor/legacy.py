"""Migration helpers that import legacy JSON data into SQLite."""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Iterable

from .paths import LEGACY_BASELINE_PATH, LEGACY_CONFIG_PATH


def migrate(connection: sqlite3.Connection) -> None:
    try:
        has_directories = (
            connection.execute("SELECT COUNT(*) FROM directories").fetchone()[0] > 0
        )
        has_baseline = (
            connection.execute("SELECT COUNT(*) FROM baseline").fetchone()[0] > 0
        )
    except sqlite3.Error:
        return

    if os.path.exists(LEGACY_CONFIG_PATH) and not has_directories:
        _import_config(connection)
        _remove(LEGACY_CONFIG_PATH)

    if os.path.exists(LEGACY_BASELINE_PATH) and not has_baseline:
        _import_baseline(connection)
        _remove(LEGACY_BASELINE_PATH)


def _import_config(connection: sqlite3.Connection) -> None:
    try:
        with open(LEGACY_CONFIG_PATH, "r", encoding="utf-8") as file:
            config = json.load(file)
    except Exception:
        return

    directories = config.get("directories", []) if isinstance(config, dict) else []
    valid = [path for path in directories if isinstance(path, str) and os.path.isdir(path)]
    interval = config.get("interval_minutes") if isinstance(config, dict) else None
    auto = config.get("auto_scan") if isinstance(config, dict) else None

    with connection:
        connection.execute("DELETE FROM directories")
        connection.executemany(
            "INSERT INTO directories(path) VALUES (?)",
            ((path,) for path in valid),
        )
        if interval is not None:
            _upsert(connection, "interval_minutes", str(interval))
        if auto is not None:
            _upsert(connection, "auto_scan", "1" if auto else "0")


def _import_baseline(connection: sqlite3.Connection) -> None:
    try:
        with open(LEGACY_BASELINE_PATH, "r", encoding="utf-8") as file:
            baseline_data = json.load(file)
    except Exception:
        return

    if not isinstance(baseline_data, dict):
        return

    entries: list[Iterable[object]] = []
    for path, info in baseline_data.items():
        if not isinstance(path, str) or not isinstance(info, dict):
            continue
        try:
            entries.append(
                (
                    path,
                    str(info.get("hash", "")),
                    int(info.get("size", 0)),
                    float(info.get("mtime", 0.0)),
                )
            )
        except (TypeError, ValueError):
            continue

    if not entries:
        return

    with connection:
        connection.execute("DELETE FROM baseline")
        connection.executemany(
            "INSERT INTO baseline(path, hash, size, mtime) VALUES (?, ?, ?, ?)",
            entries,
        )


def _upsert(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
