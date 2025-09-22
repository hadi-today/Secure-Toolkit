import base64
import os
import struct
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, 
                             QMessageBox, QInputDialog, QComboBox, QDialog, QLabel, 
                             QLineEdit, QHBoxLayout, QGroupBox)
from PyQt6.QtGui import QGuiApplication

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding

HEADER_SYMMETRIC = "-----BEGIN SECURE-TEXT (SYMMETRIC)-----"
FOOTER_SYMMETRIC = "-----END SECURE-TEXT (SYMMETRIC)-----"
HEADER_HYBRID = "-----BEGIN SECURE-TEXT (HYBRID)-----"
FOOTER_HYBRID = "-----END SECURE-TEXT (HYBRID)-----"
SALT_SIZE = 16
AES_KEY_SIZE = 32
ITERATIONS = 480000

class SecureTextWidget(QWidget):
    def __init__(self, keyring_data, save_callback):
        super().__init__()
        self.setWindowTitle("Secure Text Tool")
        self.keyring_data = keyring_data
        self.unlocked_keys = {} 

        self.setMinimumSize(600, 700)
        main_layout = QVBoxLayout(self)

        settings_group = QGroupBox("Encryption Settings")
        settings_layout = QHBoxLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Password", "Key (Encrypt for Contact)"])
        self.method_combo.currentIndexChanged.connect(self._update_ui_state)
        self.key_combo = QComboBox()
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password...")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        settings_layout.addWidget(QLabel("Method:"))
        settings_layout.addWidget(self.method_combo); settings_layout.addWidget(self.key_combo); settings_layout.addWidget(self.password_edit)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        main_layout.addWidget(QLabel("Input (Plaintext / Ciphertext)"))
        self.input_text = QTextEdit()
        main_layout.addWidget(self.input_text)
        
        actions_layout = QHBoxLayout()
        self.encrypt_btn = QPushButton("▼ Encrypt ▼"); self.decrypt_btn = QPushButton("▲ Decrypt ▲")
        self.encrypt_btn.clicked.connect(self._encrypt); self.decrypt_btn.clicked.connect(self._decrypt)
        actions_layout.addWidget(self.encrypt_btn); actions_layout.addWidget(self.decrypt_btn)
        main_layout.addLayout(actions_layout)
        
        main_layout.addWidget(QLabel("Output (Ciphertext / Plaintext)"))
        self.output_text = QTextEdit(); self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)
        
        bottom_actions_layout = QHBoxLayout()
        self.paste_btn = QPushButton("Paste Input"); self.copy_btn = QPushButton("Copy Output"); self.clear_btn = QPushButton("Clear")
        self.paste_btn.clicked.connect(self._paste_input); self.copy_btn.clicked.connect(self._copy_output); self.clear_btn.clicked.connect(self._clear_all)
        bottom_actions_layout.addStretch()
        bottom_actions_layout.addWidget(self.paste_btn); bottom_actions_layout.addWidget(self.copy_btn); bottom_actions_layout.addWidget(self.clear_btn)
        main_layout.addLayout(bottom_actions_layout)

        self._update_ui_state()

    def _update_ui_state(self):
        is_key_method = "Key" in self.method_combo.currentText()
        self.key_combo.setVisible(is_key_method); self.password_edit.setVisible(not is_key_method)
        if is_key_method and self.key_combo.count() == 0:
            self.key_combo.addItem("--- Select Public Key to Encrypt For ---", None)
            if self.keyring_data:
                for k in self.keyring_data['my_key_pairs']: self.key_combo.addItem(f"(Me) {k['name']}", k)
                for k in self.keyring_data['contact_public_keys']: self.key_combo.addItem(f"(Contact) {k['name']}", k)
    
    def _get_private_key_with_prompt(self, key_pair):
        key_name = key_pair['name']
        if key_name in self.unlocked_keys:
            return self.unlocked_keys[key_name]

        if "ENCRYPTED" not in key_pair['private_key']:
            private_key = serialization.load_pem_private_key(key_pair['private_key'].encode(), None)
            self.unlocked_keys[key_name] = private_key
            return private_key

        passphrase, ok = QInputDialog.getText(self, "Passphrase Required", f"Enter passphrase for key '{key_name}':", QLineEdit.EchoMode.Password)
        if not ok: return None

        try:
            private_key = serialization.load_pem_private_key(key_pair['private_key'].encode(), passphrase.encode())
            self.unlocked_keys[key_name] = private_key
            return private_key
        except TypeError:
            QMessageBox.critical(self, "Error", "Incorrect passphrase.")
            return None
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load key: {e}")
            return None

    def _paste_input(self): self.input_text.setText(QGuiApplication.clipboard().text())
    def _copy_output(self): QGuiApplication.clipboard().setText(self.output_text.toPlainText()); QMessageBox.information(self, "Success", "Output copied.")
    def _clear_all(self): self.input_text.clear(); self.output_text.clear()

    def _encrypt(self):
        text = self.input_text.toPlainText().encode('utf-8');
        if not text: return
        self.output_text.clear()
        if "Password" in self.method_combo.currentText():
            password = self.password_edit.text()
            if not password: QMessageBox.warning(self, "Input Error", "Password cannot be empty."); return
            salt, iv = os.urandom(SALT_SIZE), os.urandom(16)
            kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
            aes_key = kdf.derive(password.encode())
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv)); padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
            padded = padder.update(text) + padder.finalize()
            ciphertext = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
            payload = base64.b64encode(salt + iv + ciphertext).decode('utf-8')
            self.output_text.setText(f"{HEADER_SYMMETRIC}\n{payload}\n{FOOTER_SYMMETRIC}")
        else:
            key_data = self.key_combo.currentData()
            if not key_data: QMessageBox.warning(self, "Input Error", "Please select a public key to encrypt for."); return
            public_key = serialization.load_pem_public_key(key_data['public_key'].encode())
            session_key, iv = os.urandom(AES_KEY_SIZE), os.urandom(16)
            encrypted_session_key = public_key.encrypt(session_key, asymmetric_padding.OAEP(mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
            cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv)); padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
            padded = padder.update(text) + padder.finalize()
            ciphertext = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
            len_bytes = struct.pack('>H', len(encrypted_session_key))
            payload = base64.b64encode(len_bytes + encrypted_session_key + iv + ciphertext).decode('utf-8')
            self.output_text.setText(f"{HEADER_HYBRID}\n{payload}\n{FOOTER_HYBRID}")

    def _decrypt(self):
        text = self.input_text.toPlainText().strip()
        if not text: return
        self.output_text.clear()
        try:
            if text.startswith(HEADER_SYMMETRIC):
                payload = base64.b64decode(text.replace(HEADER_SYMMETRIC,"").replace(FOOTER_SYMMETRIC,"").strip())
                salt, iv, ciphertext = payload[:SALT_SIZE], payload[SALT_SIZE:SALT_SIZE+16], payload[SALT_SIZE+16:]
                password = self.password_edit.text()
                if not password:
                    password, ok = QInputDialog.getText(self, "Password", "Enter decryption password:", QLineEdit.EchoMode.Password)
                    if not ok or not password: return
                kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
                aes_key = kdf.derive(password.encode())
                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
                unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
                padded = cipher.decryptor().update(ciphertext) + cipher.decryptor().finalize()
                original = unpadder.update(padded) + unpadder.finalize()
                self.output_text.setText(original.decode('utf-8'))
            elif text.startswith(HEADER_HYBRID):
                payload = base64.b64decode(text.replace(HEADER_HYBRID,"").replace(FOOTER_HYBRID,"").strip())
                key_len = struct.unpack('>H', payload[:2])[0]
                encrypted_session_key, iv, ciphertext = payload[2:2+key_len], payload[2+key_len:2+key_len+16], payload[2+key_len+16:]
                
                aes_key = None
                for key_pair in self.keyring_data.get('my_key_pairs', []):
                    private_key = None
                    key_name = key_pair['name']
                    if key_name in self.unlocked_keys:
                        private_key = self.unlocked_keys[key_name]
                    elif "ENCRYPTED" not in key_pair['private_key']:
                        private_key = serialization.load_pem_private_key(key_pair['private_key'].encode(), None)
                    
                    if private_key:
                        try:
                            aes_key = private_key.decrypt(encrypted_session_key, asymmetric_padding.OAEP(mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                            if aes_key: break 
                        except ValueError: continue

                if not aes_key:
                    for key_pair in self.keyring_data.get('my_key_pairs', []):
                        key_name = key_pair['name']
                        if key_name in self.unlocked_keys or "ENCRYPTED" not in key_pair['private_key']:
                            continue
                        
                        private_key = self._get_private_key_with_prompt(key_pair)
                        if private_key:
                            try:
                                aes_key = private_key.decrypt(encrypted_session_key, asymmetric_padding.OAEP(mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                                if aes_key: break 
                            except ValueError: continue
                
                if not aes_key:
                    QMessageBox.critical(self, "Decryption Failed", "No suitable private key found, or passphrase was incorrect.")
                    return
                
                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
                unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
                padded = cipher.decryptor().update(ciphertext) + cipher.decryptor().finalize()
                original = unpadder.update(padded) + unpadder.finalize()
                self.output_text.setText(original.decode('utf-8'))
            else:
                QMessageBox.warning(self, "Format Error", "Input text format is not recognized.")
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"An error occurred: {e}")