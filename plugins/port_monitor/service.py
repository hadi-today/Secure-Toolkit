"""Background monitoring service for the port monitor plugin."""

from __future__ import annotations

import socket
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Dict, Tuple

import psutil
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .storage import PortActivityRepository


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalise_address(address) -> Tuple[str, int]:
    """Return ``(host, port)`` for a ``psutil`` connection address."""

    if not address:
        return ("0.0.0.0", 0)
    host = getattr(address, "ip", None)
    port = getattr(address, "port", None)
    if host is None and isinstance(address, tuple):
        host = address[0]
    if port is None and isinstance(address, tuple):
        port = address[1] if len(address) > 1 else 0
    if not host:
        host = "0.0.0.0"
    return host, int(port or 0)


def _protocol_name(conn_type: int) -> str:
    if conn_type == socket.SOCK_STREAM:
        return "TCP"
    if conn_type == socket.SOCK_DGRAM:
        return "UDP"
    return str(conn_type)


_service_state = {"running": False}


def is_monitor_running() -> bool:
    """Return ``True`` when the background monitor thread is active."""

    return _service_state["running"]


def _set_service_running(value: bool) -> None:
    _service_state["running"] = value


class PortMonitorWorker(QObject):
    """Worker object that polls ``psutil`` for listening sockets."""

    current_ports = pyqtSignal(list)
    port_opened = pyqtSignal(dict)
    port_closed = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    state_changed = pyqtSignal(bool)
    finished = pyqtSignal()

    def __init__(self, repository: PortActivityRepository, poll_interval: float = 2.0):
        super().__init__()
        self._repository = repository
        self._poll_interval = max(0.5, float(poll_interval))
        self._running = False
        self._active_ports: Dict[Tuple[str, str, int, int], Dict[str, object]] = {}
        self._last_error_signature: str | None = None

    def run(self) -> None:
        """Entry point executed inside the worker thread."""

        self._running = True
        _set_service_running(True)
        self.state_changed.emit(True)
        self._repository.set_service_state(
            is_running=True, poll_interval=self._poll_interval
        )
        start_timestamp = _now_iso()
        self._repository.clear_stop_request()
        self._log(
            f"[{start_timestamp}] Port monitoring started (interval {self._poll_interval:.1f}s).",
            start_timestamp,
        )

        try:
            while self._running:
                self._poll_once()
                if not self._running:
                    break
                time.sleep(self._poll_interval)
        finally:
            self._shutdown_active_ports()
            self.state_changed.emit(False)
            stop_timestamp = _now_iso()
            self._repository.set_service_state(
                is_running=False, poll_interval=self._poll_interval
            )
            self._repository.clear_stop_request()
            self._log(f"[{stop_timestamp}] Port monitoring stopped.", stop_timestamp)
            _set_service_running(False)
            self.finished.emit()

    def stop(self) -> None:
        """Signal the worker loop to exit."""

        self._running = False

    def _poll_once(self) -> None:
        if self._repository.should_stop():
            timestamp = _now_iso()
            self._log(
                f"[{timestamp}] Stop requested via web panel; shutting down monitor.",
                timestamp,
            )
            self._repository.update_heartbeat(timestamp)
            self._repository.clear_stop_request()
            self.stop()
            return

        timestamp = _now_iso()
        connections = self._gather_connections(timestamp)
        if connections is None:
            return

        current_snapshot: Dict[Tuple[str, str, int, int], Dict[str, object]] = {}
        for conn in connections:
            protocol = _protocol_name(conn.type)
            if protocol == "TCP" and conn.status != psutil.CONN_LISTEN:
                continue

            address, port = _normalise_address(conn.laddr)
            if port == 0:
                continue

            pid = getattr(conn, "pid", None) or 0
            process_name = self._resolve_process_name(pid)
            key = (protocol, address, port, pid)

            current_snapshot[key] = {
                "protocol": protocol,
                "address": address,
                "port": port,
                "pid": pid,
                "process_name": process_name,
            }

        self._handle_new_ports(timestamp, current_snapshot)
        self._handle_closed_ports(timestamp, current_snapshot)
        self._emit_current_ports()
        self._repository.update_heartbeat(timestamp)
        self._repository.purge()

    def _gather_connections(self, timestamp: str):
        try:
            connections = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:  # pragma: no cover - depends on host permissions
            self._log_error_once(
                "access_denied",
                (
                    f"[{timestamp}] psutil.net_connections requires elevated privileges; "
                    "falling back to per-process scanning (results may be incomplete)."
                ),
                timestamp,
            )
            return self._collect_connections_from_processes()
        except Exception as error:  # pragma: no cover - psutil errors are environment-specific
            self._log_error_once(
                f"unexpected:{error.__class__.__name__}",
                f"[{timestamp}] Failed to query network connections: {error}",
                timestamp,
            )
            return []

        self._reset_error_state()
        return connections

    def _collect_connections_from_processes(self):
        connections = []
        for process in psutil.process_iter(["pid"]):
            try:
                proc_connections = process.connections(kind="inet")
            except (psutil.NoSuchProcess, psutil.ZombieProcess):  # pragma: no cover - process churn
                continue
            except psutil.AccessDenied:  # pragma: no cover - depends on OS policy
                continue

            for conn in proc_connections:
                if hasattr(conn, "pid"):
                    connections.append(conn)
                    continue

                data = conn._asdict()
                data["pid"] = process.pid
                connections.append(SimpleNamespace(**data))

        return connections

    def _log_error_once(self, signature: str, message: str, timestamp: str | None = None) -> None:
        if self._last_error_signature == signature:
            return
        self._last_error_signature = signature
        self._repository.set_error_state(message, timestamp)
        self._log(message, timestamp)

    def _reset_error_state(self) -> None:
        if self._last_error_signature is None:
            return
        self._last_error_signature = None
        self._repository.set_error_state(None)

    def _handle_new_ports(self, timestamp: str, snapshot: Dict[Tuple[str, str, int, int], Dict[str, object]]) -> None:
        for key, info in snapshot.items():
            if key in self._active_ports:
                continue

            record_id = self._repository.record_start(
                protocol=info["protocol"],
                address=info["address"],
                port=info["port"],
                pid=info["pid"],
                process_name=info["process_name"],
                start_time=timestamp,
            )

            entry = dict(info)
            entry.update({"id": record_id, "start_time": timestamp})
            self._active_ports[key] = entry
            self.port_opened.emit(dict(entry))
            self._log(
                "[{timestamp}] Port {port}/{protocol} opened by PID {pid} ({process}).".format(
                    timestamp=timestamp,
                    port=info["port"],
                    protocol=info["protocol"],
                    pid=info["pid"],
                    process=info["process_name"],
                ),
                timestamp,
            )

    def _handle_closed_ports(self, timestamp: str, snapshot: Dict[Tuple[str, str, int, int], Dict[str, object]]) -> None:
        for key, entry in list(self._active_ports.items()):
            if key in snapshot:
                continue

            record_id = int(entry["id"])
            self._repository.record_stop(record_id, timestamp)
            closed_entry = dict(entry)
            closed_entry["end_time"] = timestamp
            self.port_closed.emit(closed_entry)
            self._log(
                "[{timestamp}] Port {port}/{protocol} closed (PID {pid}).".format(
                    timestamp=timestamp,
                    port=entry["port"],
                    protocol=entry["protocol"],
                    pid=entry["pid"],
                ),
                timestamp,
            )
            self._active_ports.pop(key)

    def _emit_current_ports(self) -> None:
        snapshot = [
            {
                "id": entry["id"],
                "protocol": entry["protocol"],
                "address": entry["address"],
                "port": entry["port"],
                "pid": entry["pid"],
                "process_name": entry["process_name"],
                "start_time": entry["start_time"],
            }
            for entry in self._active_ports.values()
        ]
        self.current_ports.emit(snapshot)

    def _shutdown_active_ports(self) -> None:
        if not self._active_ports:
            return

        timestamp = _now_iso()
        for entry in list(self._active_ports.values()):
            record_id = int(entry["id"])
            self._repository.record_stop(record_id, timestamp)
            closed_entry = dict(entry)
            closed_entry["end_time"] = timestamp
            self.port_closed.emit(closed_entry)
            self._log(
                "[{timestamp}] Port {port}/{protocol} closed when monitoring stopped.".format(
                    timestamp=timestamp,
                    port=entry["port"],
                    protocol=entry["protocol"],
                ),
                timestamp,
            )
        self._active_ports.clear()

    def _resolve_process_name(self, pid: int) -> str:
        if pid <= 0:
            return "System"
        try:
            return psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):  # pragma: no cover - depends on OS state
            return "Unknown"

    def _log(self, message: str, timestamp: str | None = None) -> None:
        self.log_message.emit(message)
        self._repository.append_log(message, timestamp)


class PortMonitorServiceController:
    """Facade responsible for coordinating the worker thread."""

    def __init__(self, service_host, database_path: str):
        self._service_host = service_host
        self._database_path = database_path
        self._service_name = "port_monitor_service"

    def is_running(self) -> bool:
        entry = self._service_host.background_services.get(self._service_name)
        thread = entry.get("thread") if entry else None
        return bool(thread and thread.isRunning())

    def get_worker(self) -> PortMonitorWorker | None:
        entry = self._service_host.background_services.get(self._service_name)
        return entry.get("worker") if entry else None

    def get_repository(self) -> PortActivityRepository:
        entry = self._service_host.background_services.get(self._service_name)
        if entry and "repository" in entry:
            return entry["repository"]
        return PortActivityRepository(self._database_path)

    def get_poll_interval(self) -> float:
        entry = self._service_host.background_services.get(self._service_name)
        if entry and "interval" in entry:
            try:
                return float(entry["interval"])
            except (TypeError, ValueError):  # pragma: no cover - defensive fallback
                return 2.0
        return 2.0

    def start(self, poll_interval: float = 2.0) -> PortMonitorWorker:
        if self.is_running():
            worker = self.get_worker()
            if worker is not None:
                return worker

        repository = PortActivityRepository(self._database_path)
        worker = PortMonitorWorker(repository, poll_interval=poll_interval)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        service_host = self._service_host
        service_name = self._service_name

        def remove_from_registry():
            entry = service_host.background_services.get(service_name)
            if entry and entry.get("thread") is thread:
                service_host.background_services.pop(service_name, None)

        worker.finished.connect(remove_from_registry)
        thread.finished.connect(remove_from_registry)
        thread.finished.connect(lambda: _set_service_running(False))
        thread.start()

        self._service_host.background_services[self._service_name] = {
            "thread": thread,
            "worker": worker,
            "repository": repository,
            "interval": float(poll_interval),
        }
        return worker

    def stop(self) -> None:
        entry = self._service_host.background_services.get(self._service_name)
        if not entry:
            repository = PortActivityRepository(self._database_path)
            state = repository.get_service_state()
            repository.set_service_state(
                is_running=False,
                poll_interval=state.get("poll_interval", 2.0) if isinstance(state, dict) else 2.0,
            )
            repository.clear_stop_request()
            return

        worker: PortMonitorWorker | None = entry.get("worker")
        thread: QThread | None = entry.get("thread")

        if worker:
            worker.stop()
        if thread:
            thread.quit()
            thread.wait()
        _set_service_running(False)
        self._service_host.background_services.pop(self._service_name, None)


__all__ = [
    "PortMonitorServiceController",
    "PortMonitorWorker",
    "is_monitor_running",
]
