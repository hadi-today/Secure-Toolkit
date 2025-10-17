"""Utility helpers that assemble the reusable sections of the web panel UI."""

import socket

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


def create_settings_group(ip_combo: QComboBox, port_input: QLineEdit) -> QGroupBox:
    """Return a form group that captures host and port configuration."""

    settings_group = QGroupBox('Server Settings')
    form_layout = QFormLayout()
    form_layout.addRow(QLabel('Listen on IP:'), ip_combo)
    form_layout.addRow(QLabel('Port:'), port_input)
    settings_group.setLayout(form_layout)
    return settings_group


def create_control_group(start_stop_button: QPushButton, status_label: QLabel) -> QGroupBox:
    """Return the control group that holds the lifecycle toggle and status."""

    control_group = QGroupBox('Server Control')
    control_layout = QVBoxLayout()
    control_layout.addWidget(start_stop_button)
    control_layout.addWidget(status_label)
    control_group.setLayout(control_layout)
    return control_group


def create_log_group(log_output: QTextEdit) -> QGroupBox:
    """Return the log view group so the caller can display streamed output."""

    log_group = QGroupBox('Server Log')
    log_layout = QVBoxLayout()
    log_layout.addWidget(log_output)
    log_group.setLayout(log_layout)
    return log_group


def populate_ip_addresses(ip_combo: QComboBox) -> None:
    """Fill the combo box with local interface addresses for convenience."""

    ip_combo.addItem('127.0.0.1 (Local Only)')
    ip_combo.addItem('0.0.0.0 (All Networks)')
    try:
        hostname = socket.gethostname()
        for ip_address in socket.gethostbyname_ex(hostname)[2]:
            if ip_address != '127.0.0.1':
                ip_combo.addItem(f'{ip_address} (Local Network)')
    except socket.gaierror:
        # DNS resolution can fail in sandboxed or offline environments.  The
        # dialog still works with the default options, so we ignore the error.
        pass
