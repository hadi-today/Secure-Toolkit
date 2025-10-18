"""UI widget that enables the user to change the master password."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QGroupBox,
)

from auth import verify_password, save_config


class PasswordManagerWidget(QDialog):
    """Modal dialog presented by the password manager plugin.

    The widget receives a reference to the keyring data as well as a callback
    that persists the keyring to disk.  The parent widget is optional so that
    the plugin can be instantiated directly by the main window while still
    presenting itself as an independent dialog window.
    """

    def __init__(self, keyring_data, save_callback, parent=None):
        # Accept the parent argument so Qt can manage the window stacking order
        # while still allowing the password manager to appear as its own dialog.
        super().__init__(parent)

        # Ensure the dialog behaves independently of the main window layout.
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Store the injected dependencies for potential future use.
        self._keyring_data = keyring_data
        self._save_callback = save_callback

        self.setWindowTitle("Change Master Password")
        self.setMinimumWidth(400)

        # Main container layout hosting all form elements.
        main_layout = QVBoxLayout(self)

        change_group = QGroupBox("Enter Password Details")
        form_layout = QVBoxLayout()

        # Input for the current master password.
        self.current_pass_input = QLineEdit()
        self.current_pass_input.setPlaceholderText("Enter your current password")
        self.current_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Input for the new master password.
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setPlaceholderText("Enter a new password")
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Confirmation input to avoid typing mistakes in the new password.
        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setPlaceholderText("Confirm the new password")
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Button that triggers the validation and update process.
        self.change_button = QPushButton("Change Password")
        self.change_button.clicked.connect(self._handle_password_change)
        self.change_button.setStyleSheet("font-size: 14px; padding: 10px;")

        form_layout.addWidget(QLabel("Current Password:"))
        form_layout.addWidget(self.current_pass_input)
        form_layout.addWidget(QLabel("New Password:"))
        form_layout.addWidget(self.new_pass_input)
        form_layout.addWidget(QLabel("Confirm New Password:"))
        form_layout.addWidget(self.confirm_pass_input)

        change_group.setLayout(form_layout)
        main_layout.addWidget(change_group)
        main_layout.addWidget(self.change_button)

    def _handle_password_change(self):
        """Validate the provided passwords and persist the updated value."""

        # Read the values entered by the user.
        current_pass = self.current_pass_input.text()
        new_pass = self.new_pass_input.text()
        confirm_pass = self.confirm_pass_input.text()

        if not current_pass or not new_pass or not confirm_pass:
            QMessageBox.warning(self, "Input Error", "All fields are required.")
            return

        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Input Error", "New passwords do not match.")
            return

        if not verify_password(current_pass):
            QMessageBox.critical(
                self,
                "Authentication Error",
                "The current password is incorrect.",
            )
            self.current_pass_input.clear()
            self.new_pass_input.clear()
            self.confirm_pass_input.clear()
            return

        try:
            # Persist the new master password using the shared application
            # configuration helpers.
            save_config(new_pass)
            QMessageBox.information(
                self,
                "Success",
                "Your master password has been changed successfully.",
            )
            self.close()
        except Exception as error:  # pragma: no cover - defensive programming.
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred: {error}",
            )
