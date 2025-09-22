from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QGroupBox)


from auth import verify_password, save_config

class PasswordManagerWidget(QWidget):
    def __init__(self, keyring_data, save_callback):
        super().__init__()
        self.setWindowTitle("Change Master Password")
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)

        change_group = QGroupBox("Enter Password Details")
        form_layout = QVBoxLayout()

        self.current_pass_input = QLineEdit()
        self.current_pass_input.setPlaceholderText("Enter your current password")
        self.current_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.new_pass_input = QLineEdit()
        self.new_pass_input.setPlaceholderText("Enter a new password")
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setPlaceholderText("Confirm the new password")
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

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
            QMessageBox.critical(self, "Authentication Error", "The current password is incorrect.")
            self.current_pass_input.clear()
            self.new_pass_input.clear()
            self.confirm_pass_input.clear()
            return
            
        try:
            save_config(new_pass)
            QMessageBox.information(self, "Success", "Your master password has been changed successfully.")
            self.close() 
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")