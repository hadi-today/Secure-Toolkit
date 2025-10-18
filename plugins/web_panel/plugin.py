"""UI widget that manages the lifecycle of the built-in web panel server.

The original version of this plugin mixed comments in multiple languages and
offered only minimal documentation for how the controls map to the background
service.  The current pass clarifies every step in English so future
maintainers can understand the dialog construction, dependency expectations,
and service control workflow at a glance.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .service_controller import ServiceStartError, WebPanelServiceController
from .ui_builder import (
    create_control_group,
    create_log_group,
    create_settings_group,
    populate_ip_addresses,
)


class WebPanelWidget(QDialog):
    """Modal dialog presented by the web panel plugin.

    The widget is instantiated by the launcher with a reference to the main
    window which exposes the shared ``background_services`` container.  The
    dialog accepts the parent argument so it can behave as an independent
    window while still stacking above the launcher.
    """

    def __init__(self, keyring_data, save_callback, parent=None):
        # Store the parent reference (usually the main window) before any other
        # initialization so we can provide a fallback background service host
        # when the dialog is instantiated stand-alone in tests or previews.
        self._service_host = (
            parent
            if parent is not None and hasattr(parent, "background_services")
            else self._create_service_host()
        )

        super().__init__(parent)

        # Ensure the dialog behaves modally relative to the main window and is
        # cleaned up automatically when closed.
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Persist the injected dependencies even though the plugin currently
        # does not use them directly.  Keeping them available simplifies future
        # enhancements and mirrors the other plugins' constructor contracts.
        self._keyring_data = keyring_data
        self._save_callback = save_callback

        # Controller object responsible for starting and stopping the worker
        # process that serves the web panel content.
        self.service_controller = WebPanelServiceController(self._service_host)

        # Main input widgets that allow the operator to choose which interface
        # the Flask server should bind to, which port to expose, and to review
        # any status log lines streamed from the worker process.
        self.ip_combo = QComboBox()
        self.port_input = QLineEdit("8080")
        self.start_stop_button = QPushButton("Start Server")
        self.kill_port_button = QPushButton("Kill Port 8080")
        self.status_label = QLabel("Status: Stopped")
        self.log_output = QTextEdit()

        self.setWindowTitle("Web Panel Management")
        self._init_ui()
        self._sync_ui_with_service_state()

    @staticmethod
    def _create_service_host():
        """Return a minimal service host when the main window is absent."""

        class _ServiceHost:  # pragma: no cover - simple data container
            def __init__(self):
                self.background_services = {}

        return _ServiceHost()

    def _init_ui(self):
        """Build the dialog layout and wire up signal handlers."""

        layout = QVBoxLayout(self)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #111827;
            }
            QGroupBox {
                border: 1px solid #1f2937;
                border-radius: 10px;
                margin-top: 16px;
                color: #e5e7eb;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 6px;
                font-weight: 600;
            }
            QLabel {
                color: #e5e7eb;
            }
            QComboBox, QLineEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton[class="danger"] {
                background-color: #dc2626;
            }
            QPushButton[class="danger"]:hover {
                background-color: #b91c1c;
            }
            QTextEdit {
                border: 1px solid #1f2937;
                border-radius: 8px;
            }
            """
        )

        # Offer sensible network defaults while also enumerating local
        # interfaces so the user can expose the web panel on the LAN if needed.
        populate_ip_addresses(self.ip_combo)

        self.log_output.setReadOnly(True)
        self.status_label.setStyleSheet("color: red;")

        for button in (self.start_stop_button, self.kill_port_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(36)

        self.log_output.setStyleSheet(
            "QTextEdit { background-color: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 8px; }"
        )

        settings_group = create_settings_group(self.ip_combo, self.port_input)
        self.kill_port_button.setToolTip(
            "Forcefully stop any process that is currently bound to port 8080."
        )
        self.kill_port_button.setProperty("class", "danger")

        control_group = create_control_group(
            self.start_stop_button, self.kill_port_button, self.status_label
        )
        log_group = create_log_group(self.log_output)

        layout.addWidget(settings_group)
        layout.addWidget(control_group)
        layout.addWidget(log_group)

        # The only interactive control toggles the server lifecycle; clicking
        # the button will decide to start or stop based on current state.
        self.start_stop_button.clicked.connect(self.toggle_server)
        self.kill_port_button.clicked.connect(self.kill_port_8080)

    def _sync_ui_with_service_state(self):
        """Display the correct status depending on the running service."""

        if self.service_controller.is_running():
            host, port = self.service_controller.current_endpoint()
            self._update_ui_for_server_start(host, port)
        else:
            self._update_ui_for_server_stop()

    def toggle_server(self):
        """Start or stop the background service depending on current state."""

        if self.service_controller.is_running():
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        """Launch the Flask server process using the selected configuration."""

        host = self.ip_combo.currentText().split(" ")[0]
        port = self.port_input.text()

        try:
            host, port = self.service_controller.start(
                host,
                port,
                self.log_output.append,
            )
        except ServiceStartError as error:
            QMessageBox.critical(self, "Config Error", str(error))
            return

        self._update_ui_for_server_start(host, port)

    def _stop_server(self):
        """Terminate the background service if it is currently running."""

        if not self.service_controller.is_running():
            return

        self.log_output.append("Stopping server process...")
        self.service_controller.stop()
        self._update_ui_for_server_stop()

    def _update_ui_for_server_start(self, host, port):
        """Apply the running-state visuals once the service launches."""

        self.start_stop_button.setText("Stop Server")
        self.status_label.setText(f"Status: Running on {host}:{port}")
        self.status_label.setStyleSheet("color: green;")

        index = self.ip_combo.findText(host, Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.ip_combo.setCurrentIndex(index)

        self.port_input.setText(str(port))
        self.ip_combo.setEnabled(False)
        self.port_input.setEnabled(False)

    def _update_ui_for_server_stop(self):
        """Reset the UI controls after the service stops."""

        self.start_stop_button.setText("Start Server")
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("color: red;")
        self.ip_combo.setEnabled(True)
        self.port_input.setEnabled(True)

    def kill_port_8080(self):
        """Forcefully terminate any process bound to the default web port."""

        killed, errors = self.service_controller.force_kill_port("8080")

        if killed:
            killed_text = ", ".join(str(pid) for pid in killed)
            self.log_output.append(
                f"Terminated processes on port 8080: {killed_text}"
            )
        else:
            self.log_output.append("No active processes detected on port 8080.")

        for error in errors:
            self.log_output.append(f"Warning: {error}")

        self._sync_ui_with_service_state()

