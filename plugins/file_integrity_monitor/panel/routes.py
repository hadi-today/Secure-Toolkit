"""Flask blueprint that serves the file integrity monitor web view."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request

from plugins.web_panel.server.web_auth import token_required

from ..acknowledgements import acknowledge as acknowledge_signature
from ..history import fetch_recent_scans
from ..persistence import (
    initialize_database,
    load_baseline,
    load_baseline_timestamp,
    load_config,
)


file_integrity_bp = Blueprint(
    "file_integrity_panel",
    __name__,
    template_folder="templates",
    static_folder="static",
)


def _collect_status() -> dict[str, object]:
    initialize_database()
    directories, interval, auto_scan = load_config()
    baseline = load_baseline()
    baseline_timestamp = load_baseline_timestamp()
    history = fetch_recent_scans()

    last_scan = history[0] if history else None
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return {
        "directories": directories,
        "interval_minutes": interval,
        "auto_scan": auto_scan,
        "baseline": {
            "count": len(baseline),
            "captured_at": baseline_timestamp,
            "has_baseline": bool(baseline),
        },
        "history": history,
        "last_scan": last_scan,
        "generated_at": generated_at,
    }


@file_integrity_bp.route("/")
@token_required
def panel_home():
    """Render the main dashboard view."""

    return render_template("file_integrity.html")


@file_integrity_bp.route("/api/status")
@token_required
def api_status():
    """Expose the latest scan information as JSON."""

    return jsonify(_collect_status())


@file_integrity_bp.route("/api/acknowledge", methods=["POST"])
@token_required
def api_acknowledge():
    payload = request.get_json(silent=True) or {}
    signature = payload.get("signature")
    if not isinstance(signature, str) or not signature:
        return jsonify({"status": "error", "message": "Missing signature"}), 400
    initialize_database()
    acknowledge_signature(signature)
    return jsonify({"status": "ok", "signature": signature})


__all__ = ["file_integrity_bp"]
