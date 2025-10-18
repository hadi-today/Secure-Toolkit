"""Qt widget that exposes the port monitor controls."""

from __future__ import annotations

import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from .service import PortMonitorServiceController, is_monitor_running as _service_is_running


class PortMonitorWidget(QDialog):
    """Dialog that allows the operator to manage the monitoring service."""

    def __init__(self, keyring_data, save_callback, parent=None):
        self._service_host = (
            parent
            if parent is not None and hasattr(parent, "background_services")
            else self._create_service_host()
        )

        super().__init__(parent)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("Port Monitor")
        self.resize(800, 600)

        self._database_path = os.path.join(os.path.dirname(__file__), "port_monitor.db")
        self.service_controller = PortMonitorServiceController(
            self._service_host, self._database_path
        )

        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("color: red;")
        self.interval_input = QDoubleSpinBox()
        self.interval_input.setRange(0.5, 30.0)
        self.interval_input.setSingleStep(0.5)
        self.interval_input.setValue(2.0)
        self.interval_input.setValue(self.service_controller.get_poll_interval())

        self.start_stop_button = QPushButton("Start Monitoring")
        self.active_table = self._create_table(
            ["Protocol", "Address", "Port", "PID", "Process", "Since"]
        )
        self.history_table = self._create_table(
            ["Protocol", "Address", "Port", "PID", "Process", "Started", "Ended"]
        )
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self._init_layout()
        self._bind_signals()
        self._sync_with_service_state()
        self._refresh_tables()
        self._load_existing_logs()

    @staticmethod
    def _create_service_host():
        class _ServiceHost:  # pragma: no cover - simple data container
            def __init__(self):
                self.background_services = {}

        return _ServiceHost()

    def _create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        return table

    def _init_layout(self):
        layout = QVBoxLayout(self)

        controls_box = QGroupBox("Service Controls")
        controls_layout = QGridLayout(controls_box)
        controls_layout.addWidget(QLabel("Polling interval (seconds)"), 0, 0)
        controls_layout.addWidget(self.interval_input, 0, 1)
        controls_layout.addWidget(self.start_stop_button, 1, 0, 1, 2)
        controls_layout.addWidget(self.status_label, 2, 0, 1, 2)
        layout.addWidget(controls_box)

        active_box = QGroupBox("Currently listening ports")
        active_layout = QVBoxLayout(active_box)
        active_layout.addWidget(self.active_table)
        layout.addWidget(active_box)

        history_box = QGroupBox("Recent port availability")
        history_layout = QVBoxLayout(history_box)
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_box)

        log_box = QGroupBox("Monitor log")
        log_layout = QVBoxLayout(log_box)
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_box)

    def _bind_signals(self):
        self.start_stop_button.clicked.connect(self._toggle_service)

        worker = self.service_controller.get_worker()
        if worker is not None:
            self._connect_worker_signals(worker)

    def _toggle_service(self):
        if self.service_controller.is_running():
            self.service_controller.stop()
            self._update_ui_for_stop()
        else:
            worker = self.service_controller.start(self.interval_input.value())
            self._connect_worker_signals(worker)
            self._update_ui_for_start()

    def _sync_with_service_state(self):
        if self.service_controller.is_running():
            self._update_ui_for_start()
        else:
            self._update_ui_for_stop()

    def _refresh_tables(self):
        repository = self.service_controller.get_repository()
        self._populate_active_table(repository.fetch_open_ports())
        self._populate_history_table(repository.fetch_recent_history())

    def _load_existing_logs(self):
        repository = self.service_controller.get_repository()
        entries = repository.fetch_recent_logs()
        self.log_output.clear()
        for entry in entries:
            message = entry.get("message")
            if not isinstance(message, str):
                continue
            self.log_output.append(message)
        if entries:
            self.log_output.verticalScrollBar().setValue(
                self.log_output.verticalScrollBar().maximum()
            )

    def _connect_worker_signals(self, worker):
        worker.current_ports.connect(self._populate_active_table)
        worker.port_opened.connect(self._on_port_event)
        worker.port_closed.connect(self._on_port_event)
        worker.log_message.connect(self._append_log)
        worker.state_changed.connect(self._handle_state_change)

    def _update_ui_for_start(self):
        self.start_stop_button.setText("Stop Monitoring")
        self.interval_input.setEnabled(False)
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("color: green;")

    def _update_ui_for_stop(self):
        self.start_stop_button.setText("Start Monitoring")
        self.interval_input.setEnabled(True)
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("color: red;")

    def _handle_state_change(self, running: bool):
        if running:
            self._update_ui_for_start()
        else:
            self._update_ui_for_stop()
            self._refresh_tables()

    def _populate_active_table(self, rows=None):
        if rows is None:
            repository = self.service_controller.get_repository()
            rows = repository.fetch_open_ports()

        self.active_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._set_table_item(self.active_table, row_index, 0, row.get("protocol", ""))
            self._set_table_item(self.active_table, row_index, 1, row.get("address", ""))
            self._set_table_item(self.active_table, row_index, 2, str(row.get("port", "")))
            self._set_table_item(
                self.active_table,
                row_index,
                3,
                self._format_pid(row.get("pid")),
            )
            self._set_table_item(
                self.active_table,
                row_index,
                4,
                row.get("process_name", ""),
            )
            since = row.get("start_time")
            self._set_table_item(self.active_table, row_index, 5, self._format_timestamp(since))

        self.active_table.resizeColumnsToContents()

    def _populate_history_table(self, rows=None):
        if rows is None:
            repository = self.service_controller.get_repository()
            rows = repository.fetch_recent_history()

        self.history_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._set_table_item(self.history_table, row_index, 0, row.get("protocol", ""))
            self._set_table_item(self.history_table, row_index, 1, row.get("address", ""))
            self._set_table_item(self.history_table, row_index, 2, str(row.get("port", "")))
            self._set_table_item(
                self.history_table,
                row_index,
                3,
                self._format_pid(row.get("pid")),
            )
            self._set_table_item(
                self.history_table,
                row_index,
                4,
                row.get("process_name", ""),
            )
            self._set_table_item(
                self.history_table,
                row_index,
                5,
                self._format_timestamp(row.get("start_time")),
            )
            self._set_table_item(
                self.history_table,
                row_index,
                6,
                self._format_timestamp(row.get("end_time")),
            )

        self.history_table.resizeColumnsToContents()

    def _append_log(self, message: str):
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def _on_port_event(self, _event):
        self._populate_history_table()

    def _set_table_item(self, table: QTableWidget, row: int, column: int, text: str):
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, column, item)

    def _format_timestamp(self, value):
        if not value:
            return "—"
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError:
            return str(value)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

    def _format_pid(self, value):
        if value in (None, "", 0):
            return "—"
        return str(value)


def is_monitor_running() -> bool:
    return _service_is_running()


__all__ = ["PortMonitorWidget", "is_monitor_running"]
