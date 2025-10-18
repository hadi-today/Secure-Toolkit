"""Gadgets exposed by the secure editor panel."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Dict

from plugins.secure_editor.editor_modules import config


def _query_note_stats() -> Dict[str, int | str | None]:
    connection = None
    try:
        connection = sqlite3.connect(config.DB_FILE_PATH)
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM notes")
        note_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM versions")
        version_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT notes.name, MAX(versions.timestamp)
            FROM notes
            LEFT JOIN versions ON versions.note_id = notes.id
            GROUP BY notes.id
            ORDER BY MAX(versions.timestamp) DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        latest_note = row[0] if row and row[1] else None
        latest_ts = row[1] if row and row[1] else None

        return {
            "note_count": note_count,
            "version_count": version_count,
            "latest_note": latest_note,
            "latest_timestamp": latest_ts,
        }
    except sqlite3.Error:
        return {
            "note_count": 0,
            "version_count": 0,
            "latest_note": None,
            "latest_timestamp": None,
        }
    finally:
        if connection is not None:
            connection.close()


def provide_gadgets(base_url: str) -> List[Dict[str, object]]:
    """Return gadget metadata for the secure editor."""

    stats = _query_note_stats()

    latest_display = "Never"
    if stats["latest_timestamp"]:
        try:
            dt = datetime.fromisoformat(stats["latest_timestamp"])
            latest_display = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            latest_display = stats["latest_timestamp"]

    latest_note = stats["latest_note"] or "No notes saved"

    content_html = f"""
        <strong>Encrypted notes overview</strong>
        <ul>
            <li>Total notes: <b>{stats['note_count']}</b></li>
            <li>Saved versions: <b>{stats['version_count']}</b></li>
            <li>Latest update: <b>{latest_display}</b></li>
            <li>Latest note: <b>{latest_note}</b></li>
        </ul>
        <p>Open the Secure Editor panel to browse note history and compare versions.</p>
    """

    return [
        {
            "id": "secure-editor-summary",
            "title": "Secure Editor activity",
            "description": "Quick stats for encrypted notes stored by the desktop editor.",
            "content_html": content_html,
            "order": 15,
            "plugin": "secure_editor",
        }
    ]
