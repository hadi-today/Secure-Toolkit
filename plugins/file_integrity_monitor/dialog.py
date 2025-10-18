from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox, QVBoxLayout

from .acknowledgements import acknowledge
from .controller import MonitorController
from .dialog_actions import handle_scan
from .dialog_state import MonitorDialogStateMixin
from .formatting import timestamped
from .scanner import ScanResult
from .widgets import build_control_group, build_directory_group, build_log_group


class FileIntegrityMonitorWidget(MonitorDialogStateMixin, QDialog):
    def __init__(self, keyring_data, save_callback, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("File Integrity Monitor")
        self.resize(720, 560)
        self._controller = MonitorController()
        self._is_scanning = False
        self._last_reported_result: ScanResult | None = None
        self._pending_signature: str | None = None
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(lambda: self._perform_scan("Scheduled scan"))
        self._build_ui()
        self._load_state()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        directory_group, self.directory_list = build_directory_group(self._add_directory, self._remove_selected)
        control_group, self.auto_scan_checkbox, self.interval_input, self.status_label = build_control_group(
            self._create_baseline, lambda: self._perform_scan("Manual scan"), self._handle_interval_change, self._toggle_auto_scan
        )
        log_group, self.log_output, self.ack_button = build_log_group(self._acknowledge_changes)
        layout.addWidget(directory_group)
        layout.addWidget(control_group)
        layout.addWidget(log_group)

    def _add_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select folder")
        if directory and self._controller.add_directory(directory):
            self._sync_directory_list()
            self._update_timer()

    def _remove_selected(self) -> None:
        selected = [item.text() for item in self.directory_list.selectedItems()]
        if self._controller.remove_directories(selected):
            self._sync_directory_list()
            self._update_timer()

    def _create_baseline(self) -> None:
        if not self._controller.directories:
            QMessageBox.warning(self, "No folders", "Select at least one folder first.")
            return
        try:
            self._controller.capture_baseline(self._controller.directories)
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Failed to create baseline: {error}")
            return
        self._set_ack_state(None, False, True)
        self._append_log("Baseline captured for monitored folders.")
        self._update_status()
        self._update_timer()

    def _perform_scan(self, trigger: str) -> None:
        if self._is_scanning:
            return
        if not self._controller.has_baseline():
            QMessageBox.information(self, "Baseline missing", "Create a baseline first.")
            return
        self._is_scanning = True
        try:
            handle_scan(self, trigger)
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Scan failed: {error}")
        finally:
            self._is_scanning = False

    def _set_ack_state(self, signature: str | None, enabled: bool, reset_result: bool = False) -> None:
        self._pending_signature = signature if enabled else None
        if reset_result:
            self._last_reported_result = None
        self.ack_button.setEnabled(enabled)

    def _acknowledge_changes(self) -> None:
        if not self._pending_signature:
            return
        acknowledge(self._pending_signature)
        self._append_log(timestamped("Current findings acknowledged."))
        self._set_ack_state(None, False, True)
