import os
import json
import base64
import sys
from PyQt6.QtWidgets import QMessageBox
from auth import (
    LoginWindow,
    SetupWindow,
    CONFIG_FILE,
    KEYRING_FILE,
    derive_keyring_key,
    load_and_decrypt_keyring,
    encrypt_and_save_keyring,
)
from main_window import MainWindow


class ApplicationController:
    def __init__(self):
        self.main_window = None
        self.auth_window = None
        self.keyring_data = None
        self.keyring_encryption_key = None

    def start(self):
        if os.path.exists(CONFIG_FILE):
            self._show_login_window()
        else:
            self.auth_window = SetupWindow()
            self.auth_window.setup_successful.connect(self._handle_successful_login)
            self.auth_window.show()

    def _handle_successful_login(self, password):
        try:
            with open(CONFIG_FILE, 'r') as file:
                config = json.load(file)
            if 'keyring_salt' not in config:
                QMessageBox.critical(None, 'Config Error', "Configuration file is outdated. Please delete 'config.json' and restart.")
                sys.exit(1)
            keyring_salt = base64.b64decode(config['keyring_salt'])
            self.keyring_encryption_key = derive_keyring_key(password, keyring_salt)
            keyring_needs_initialization = not os.path.exists(KEYRING_FILE)
            try:
                self.keyring_data = load_and_decrypt_keyring(self.keyring_encryption_key)
            except ValueError as error:
                self._handle_keyring_boot_error(str(error))
                return
            if keyring_needs_initialization:
                print('First run: Initializing secure keyring file.')
                self.save_keyring_data(self.keyring_data)
            if self.auth_window:
                self.auth_window.close()
            self.show_main_window()
        except Exception as error:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(None, 'Fatal Error', f"Could not load secure data: {error}\n\nThe application will now exit.")
            sys.exit(1)

    def _show_login_window(self):
        self.auth_window = LoginWindow()
        self.auth_window.login_successful.connect(self._handle_successful_login)
        self.auth_window.show()

    def _handle_keyring_boot_error(self, message):
        response = QMessageBox.question(
            None,
            'Keyring Error',
            f"{message}\n\nWould you like to reset the secure keyring? This will delete all stored keys.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response == QMessageBox.StandardButton.Yes:
            try:
                self.save_keyring_data({"my_key_pairs": [], "contact_public_keys": []})
            except Exception as error:
                QMessageBox.critical(None, 'Reset Failed', f'Could not reset keyring: {error}')
                self._show_login_window()
                return
            QMessageBox.information(
                None,
                'Keyring Reset',
                'The corrupted keyring has been replaced with a new, empty one. The application will now open with a clean key store.',
            )
            self.show_main_window()
        else:
            self._show_login_window()

    def save_keyring_data(self, new_data):
        self.keyring_data = new_data
        try:
            encrypt_and_save_keyring(self.keyring_encryption_key, self.keyring_data)
            print('Keyring securely saved to disk.')
        except Exception as error:
            QMessageBox.critical(None, 'Save Error', f'Could not save keyring data securely: {error}')

    def show_main_window(self):
        if self.main_window is None:
            self.main_window = MainWindow(self.keyring_data, self.save_keyring_data)
        self.main_window.show()
