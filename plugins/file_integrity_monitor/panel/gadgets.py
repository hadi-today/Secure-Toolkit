"""Dashboard gadgets exposed by the file integrity monitor."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from ..history import fetch_recent_scans
from ..persistence import load_baseline_timestamp, load_config


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "Never"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def provide_gadgets(base_url: str) -> List[Dict[str, object]]:
    """Return a concise overview for the launcher dashboard."""

    directories, interval, auto_scan = load_config()
    baseline_time = load_baseline_timestamp()
    recent = fetch_recent_scans(1)
    last_scan = recent[0] if recent else None

    baseline_status = "Ready" if baseline_time else "Missing"
    auto_label = "enabled" if auto_scan else "disabled"
    last_run = _format_timestamp(last_scan.get("run_at") if last_scan else None)
    changed = last_scan.get("changed_count") if last_scan else 0
    deleted = last_scan.get("deleted_count") if last_scan else 0
    new = last_scan.get("new_count") if last_scan else 0

    content_html = f"""
        <strong>Configuration</strong>
        <ul>
            <li>Baseline: <b>{baseline_status}</b></li>
            <li>Auto scan: <b>{auto_label}</b></li>
            <li>Folders: <b>{len(directories)}</b></li>
            <li>Interval: <b>{interval} min</b></li>
        </ul>
        <p class=\"small\">Last scan {last_run} — Δ {changed} / -{deleted} / +{new}</p>
    """

    return [
        {
            "id": "file-integrity-monitor",
            "title": "File integrity overview",
            "description": "Quick health summary for the monitored folders.",
            "content_html": content_html,
            "order": 35,
            "plugin": "file_integrity_monitor",
            "link": {
                "label": "Open detailed view",
                "url": f"{base_url}/",
            },
        }
    ]


__all__ = ["provide_gadgets"]
