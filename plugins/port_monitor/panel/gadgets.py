"""Dashboard gadgets exposed by the Port Monitor plugin."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

from ..storage import PortActivityRepository


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_PATH = os.path.join(BASE_DIR, "port_monitor.db")


def _get_repository() -> PortActivityRepository:
    return PortActivityRepository(DATABASE_PATH)


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "Never"
    try:
        dt = datetime.fromisoformat(value)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def provide_gadgets(base_url: str) -> List[Dict[str, object]]:
    """Return gadget metadata summarising recent port activity."""

    repository = _get_repository()
    service = repository.get_service_state()
    open_ports = repository.fetch_open_ports()
    history = repository.fetch_recent_history(5)
    logs = repository.fetch_recent_logs(1)

    running = "Running" if service.get("is_running") else "Stopped"
    heartbeat = _format_timestamp(service.get("last_heartbeat"))
    last_event: str
    if history:
        candidate = history[0]
        last_event = _format_timestamp(candidate.get("end_time") or candidate.get("start_time"))
    else:
        last_event = "Never"

    last_log = logs[0]["message"] if logs else "No log entries recorded yet."

    content_html = f"""
        <strong>Background monitor</strong>
        <ul>
            <li>Status: <b>{running}</b></li>
            <li>Active listening ports: <b>{len(open_ports)}</b></li>
            <li>Last heartbeat: <b>{heartbeat}</b></li>
            <li>Most recent change: <b>{last_event}</b></li>
        </ul>
        <p class="small">{last_log}</p>
    """

    return [
        {
            "id": "port-monitor-summary",
            "title": "Port monitor overview",
            "description": "Quick status for the background port listener tracker.",
            "content_html": content_html,
            "order": 25,
            "plugin": "port_monitor",
            "link": {
                "label": "Open detailed view",
                "url": f"{base_url}/",
            },
        }
    ]


__all__ = ["provide_gadgets"]
