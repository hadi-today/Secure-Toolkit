# plugins/web_panel/ui_builder.py

import socket
from PyQt6.QtWidgets import (QLabel, QLineEdit, QComboBox, QTextEdit, 
                             QPushButton, QGroupBox, QFormLayout, QVBoxLayout)

def create_settings_group(ip_combo, port_input):
    settings_group = QGroupBox("Server Settings")
    form_layout = QFormLayout()
    form_layout.addRow(QLabel("Listen on IP:"), ip_combo)
    form_layout.addRow(QLabel("Port:"), port_input)
    settings_group.setLayout(form_layout)
    return settings_group

def create_control_group(start_stop_button, status_label):
    control_group = QGroupBox("Server Control")
    control_layout = QVBoxLayout()
    control_layout.addWidget(start_stop_button)
    control_layout.addWidget(status_label)
    control_group.setLayout(control_layout)
    return control_group

def create_log_group(log_output):
    log_group = QGroupBox("Server Log")
    log_layout = QVBoxLayout()
    log_layout.addWidget(log_output)
    log_group.setLayout(log_layout)
    return log_group

def populate_ip_addresses(ip_combo):
    ip_combo.addItem("127.0.0.1 (Local Only)")
    ip_combo.addItem("0.0.0.0 (All Networks)")
    try:
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            if ip != '127.0.0.1':
                ip_combo.addItem(f"{ip} (Local Network)")
    except socket.gaierror:
        pass