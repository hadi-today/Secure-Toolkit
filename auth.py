from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import pyqtSignal
from auth_crypto import (
    CONFIG_FILE,
    KEYRING_FILE,
    ITERATIONS,
    KEY_LENGTH,
    derive_keyring_key,
    encrypt_and_save_keyring,
    load_and_decrypt_keyring,
    save_config,
    verify_password,
)


__all__ = [
    'CONFIG_FILE',
    'KEYRING_FILE',
    'ITERATIONS',
    'KEY_LENGTH',
    'derive_keyring_key',
    'encrypt_and_save_keyring',
    'load_and_decrypt_keyring',
    'save_config',
    'verify_password',
    'SetupWindow',
    'LoginWindow',
]


class SetupWindow(QWidget):
    setup_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Setup Initial Password')
        self.setGeometry(400, 400, 300, 150)
        layout = QVBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Enter a new password')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText('Confirm the password')
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.submit_button = QPushButton('Create Password')
        self.submit_button.clicked.connect(self.create_password)
        layout.addWidget(QLabel('Welcome! Please create a master password.'))
        layout.addWidget(self.password_input)
        layout.addWidget(self.confirm_input)
        layout.addWidget(self.submit_button)
        self.setLayout(layout)

    def create_password(self):
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        if not password or not confirm:
            QMessageBox.warning(self, 'Error', 'Both fields are required.')
            return
        if password != confirm:
            QMessageBox.warning(self, 'Error', 'Passwords do not match.')
            return
        save_config(password)
        QMessageBox.information(self, 'Success', 'Password has been set successfully.')
        self.setup_successful.emit(password)
        self.close()


class LoginWindow(QWidget):
    login_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Login')
        self.setGeometry(400, 400, 300, 120)
        layout = QVBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Enter your password')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.submit_button = QPushButton('Login')
        self.submit_button.clicked.connect(self.check_password)
        layout.addWidget(QLabel('Please enter your master password.'))
        layout.addWidget(self.password_input)
        layout.addWidget(self.submit_button)
        self.setLayout(layout)

    def check_password(self):
        password = self.password_input.text()
        if verify_password(password):
            self.login_successful.emit(password)
            self.close()
        else:
            QMessageBox.critical(self, 'Error', 'Invalid password.')
            self.password_input.clear()


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = SetupWindow()
    window.show()
    sys.exit(app.exec())
