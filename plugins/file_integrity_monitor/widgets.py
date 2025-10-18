"""UI helper functions for the file integrity monitor dialog."""

from __future__ import annotations

from typing import Callable, Tuple

from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)


def build_directory_group(add_callback: Callable[[], None], remove_callback: Callable[[], None]) -> Tuple[QGroupBox, QListWidget]:
    group = QGroupBox("Monitored folders")
    layout = QVBoxLayout(group)
    directory_list = QListWidget()
    directory_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    layout.addWidget(directory_list)

    buttons = QHBoxLayout()
    add_button = QPushButton("Add folder…")
    add_button.clicked.connect(add_callback)
    remove_button = QPushButton("Remove selected")
    remove_button.clicked.connect(remove_callback)
    buttons.addWidget(add_button)
    buttons.addWidget(remove_button)
    buttons.addStretch()
    layout.addLayout(buttons)
    return group, directory_list


def build_control_group(
    baseline_callback: Callable[[], None],
    scan_callback: Callable[[], None],
    interval_callback: Callable[[], None],
    toggle_callback: Callable[[], None],
) -> Tuple[QGroupBox, QCheckBox, QSpinBox, QLabel]:
    group = QGroupBox("Monitoring controls")
    layout = QVBoxLayout(group)

    info = QLabel(
        "Create a baseline to snapshot the selected folders. Later scans report"
        " modified, removed, or newly created files."
    )
    info.setWordWrap(True)

    action_row = QHBoxLayout()
    baseline_button = QPushButton("Create baseline")
    baseline_button.clicked.connect(baseline_callback)
    scan_button = QPushButton("Scan now")
    scan_button.clicked.connect(scan_callback)
    action_row.addWidget(baseline_button)
    action_row.addWidget(scan_button)
    action_row.addStretch()

    auto_scan_checkbox = QCheckBox("Enable automatic scanning")
    auto_scan_checkbox.stateChanged.connect(lambda _: toggle_callback())

    interval_row = QHBoxLayout()
    interval_row.addWidget(QLabel("Scan interval (minutes):"))
    interval_input = QSpinBox()
    interval_input.setRange(1, 24 * 60)
    interval_input.valueChanged.connect(lambda _: interval_callback())
    interval_row.addWidget(interval_input)
    interval_row.addStretch()

    status_label = QLabel()

    layout.addWidget(info)
    layout.addLayout(action_row)
    layout.addWidget(auto_scan_checkbox)
    layout.addLayout(interval_row)
    layout.addWidget(status_label)
    return group, auto_scan_checkbox, interval_input, status_label


def build_log_group(ack_callback: Callable[[], None]) -> Tuple[QGroupBox, QTextEdit, QPushButton]:
    group = QGroupBox("Scan activity")
    layout = QVBoxLayout(group)
    log_output = QTextEdit()
    log_output.setReadOnly(True)
    log_output.setMinimumHeight(220)
    layout.addWidget(log_output)
    button_row = QHBoxLayout()
    button_row.addStretch()
    ack_button = QPushButton("Acknowledge changes")
    ack_button.clicked.connect(ack_callback)
    ack_button.setEnabled(False)
    button_row.addWidget(ack_button)
    layout.addLayout(button_row)
    return group, log_output, ack_button
