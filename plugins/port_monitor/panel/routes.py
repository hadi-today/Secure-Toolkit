"""Flask blueprint that powers the Port Monitor web panel."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict

from flask import Blueprint, jsonify, render_template

from plugins.web_panel.server.web_auth import token_required

from ..storage import PortActivityRepository


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_PATH = os.path.join(BASE_DIR, "port_monitor.db")


def _get_repository() -> PortActivityRepository:
    return PortActivityRepository(DATABASE_PATH)


port_monitor_bp = Blueprint(
    "port_monitor_panel",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@port_monitor_bp.route("/")
@token_required
def panel_home():
    """Render the main Port Monitor dashboard."""

    return render_template("port_monitor.html")


@port_monitor_bp.route("/api/status", methods=["GET"])
@token_required
def api_status():
    """Return a JSON snapshot describing the current port activity."""

    repository = _get_repository()
    service_state = repository.get_service_state()
    open_ports = repository.fetch_open_ports()
    history = repository.fetch_recent_history(100)
    logs = repository.fetch_recent_logs(200)

    payload: Dict[str, object] = {
        "service": service_state,
        "open_ports": open_ports,
        "history": history,
        "logs": logs,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return jsonify(payload)


@port_monitor_bp.route("/api/stop", methods=["POST"])
@token_required
def api_request_stop():
    """Request that the running monitor thread stop after its next poll."""

    repository = _get_repository()
    state = repository.get_service_state()

    if not state.get("is_running"):
        message = "Monitor is not currently running."
        return jsonify({"message": message, "running": False}), 200

    repository.request_stop()
    message = "Stop signal sent. The monitor will stop after its next polling cycle."
    return jsonify({"message": message, "running": True}), 202


__all__ = ["port_monitor_bp"]
