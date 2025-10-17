"""Secure text processing plugin with encryption and decryption helpers."""

from __future__ import annotations

import base64
import os
import struct
from dataclasses import dataclass
from typing import Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HEADER_SYMMETRIC = "-----BEGIN SECURE-TEXT (SYMMETRIC)-----"
FOOTER_SYMMETRIC = "-----END SECURE-TEXT (SYMMETRIC)-----"
HEADER_HYBRID = "-----BEGIN SECURE-TEXT (HYBRID)-----"
FOOTER_HYBRID = "-----END SECURE-TEXT (HYBRID)-----"
SALT_SIZE = 16
AES_KEY_SIZE = 32
IV_SIZE = 16
ITERATIONS = 480_000


@dataclass
class KeyMetadata:
    """Simple container used by the combo box to reference key data."""

    name: str
    public_key: Optional[str] = None
    private_key: Optional[str] = None
    is_self: bool = False


class SecureTextWidget(QDialog):
    """Modal dialog that encrypts and decrypts secure text payloads."""

    def __init__(self, keyring_data, save_callback, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Secure Text Tool")
        self.setModal(True)
        self.setMinimumSize(600, 700)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # The plugin does not save back to the keyring but we retain the
        # constructor contract shared by the other plugins.
        self._keyring_data = keyring_data or {}
        self._save_callback = save_callback

        # Cache decrypted private keys to avoid repeatedly prompting the user.
        self._unlocked_keys: Dict[str, object] = {}

        self._build_ui()
        self._populate_key_options()
        self._update_ui_state()

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Create the full dialog layout and wire up interactions."""

        main_layout = QVBoxLayout(self)

        settings_group = QGroupBox("Encryption Settings")
        settings_layout = QHBoxLayout(settings_group)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Password", "Key (Encrypt for Contact)"])
        self.method_combo.currentIndexChanged.connect(self._update_ui_state)

        self.key_combo = QComboBox()
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password…")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        settings_layout.addWidget(QLabel("Method:"))
        settings_layout.addWidget(self.method_combo)
        settings_layout.addWidget(self.key_combo)
        settings_layout.addWidget(self.password_edit)

        main_layout.addWidget(settings_group)

        main_layout.addWidget(QLabel("Input (Plaintext / Ciphertext)"))
        self.input_text = QTextEdit()
        main_layout.addWidget(self.input_text)

        actions_layout = QHBoxLayout()
        self.encrypt_btn = QPushButton("▼ Encrypt ▼")
        self.decrypt_btn = QPushButton("▲ Decrypt ▲")
        self.encrypt_btn.clicked.connect(self._encrypt)
        self.decrypt_btn.clicked.connect(self._decrypt)
        actions_layout.addWidget(self.encrypt_btn)
        actions_layout.addWidget(self.decrypt_btn)
        main_layout.addLayout(actions_layout)

        main_layout.addWidget(QLabel("Output (Ciphertext / Plaintext)"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)

        bottom_actions_layout = QHBoxLayout()
        self.paste_btn = QPushButton("Paste Input")
        self.copy_btn = QPushButton("Copy Output")
        self.clear_btn = QPushButton("Clear")
        self.paste_btn.clicked.connect(self._paste_input)
        self.copy_btn.clicked.connect(self._copy_output)
        self.clear_btn.clicked.connect(self._clear_all)
        bottom_actions_layout.addStretch()
        bottom_actions_layout.addWidget(self.paste_btn)
        bottom_actions_layout.addWidget(self.copy_btn)
        bottom_actions_layout.addWidget(self.clear_btn)
        main_layout.addLayout(bottom_actions_layout)

    def _populate_key_options(self) -> None:
        """Fill the combo box with available self and contact keys."""

        self.key_combo.clear()
        self.key_combo.addItem("--- Select Public Key to Encrypt For ---", None)

        for key_info in self._keyring_data.get("my_key_pairs", []):
            metadata = KeyMetadata(
                name=key_info["name"],
                public_key=key_info["public_key"],
                private_key=key_info.get("private_key"),
                is_self=True,
            )
            self.key_combo.addItem(f"(Me) {metadata.name}", metadata)

        for key_info in self._keyring_data.get("contact_public_keys", []):
            metadata = KeyMetadata(
                name=key_info["name"],
                public_key=key_info["public_key"],
                is_self=False,
            )
            self.key_combo.addItem(f"(Contact) {metadata.name}", metadata)

    # ------------------------------------------------------------------
    # General UI helpers
    # ------------------------------------------------------------------
    def _update_ui_state(self) -> None:
        """Show or hide widgets depending on the chosen encryption mode."""

        is_key_method = "Key" in self.method_combo.currentText()
        self.key_combo.setVisible(is_key_method)
        self.password_edit.setVisible(not is_key_method)

        if is_key_method and self.key_combo.count() == 0:
            self._populate_key_options()

    def _paste_input(self) -> None:
        """Load the clipboard contents into the input field."""

        self.input_text.setText(QGuiApplication.clipboard().text())

    def _copy_output(self) -> None:
        """Copy the output text to the clipboard and notify the user."""

        QGuiApplication.clipboard().setText(self.output_text.toPlainText())
        QMessageBox.information(self, "Success", "Output copied to clipboard.")

    def _clear_all(self) -> None:
        """Reset both input and output widgets."""

        self.input_text.clear()
        self.output_text.clear()

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------
    def _encrypt(self) -> None:
        """Encrypt the current input text using the selected method."""

        plaintext = self.input_text.toPlainText().encode("utf-8")
        if not plaintext:
            return

        self.output_text.clear()

        if "Password" in self.method_combo.currentText():
            self._encrypt_with_password(plaintext)
        else:
            self._encrypt_for_contact(plaintext)

    def _encrypt_with_password(self, plaintext: bytes) -> None:
        """Perform password-based encryption and render the payload."""

        password = self.password_edit.text()
        if not password:
            QMessageBox.warning(self, "Input Error", "Password cannot be empty.")
            return

        salt = os.urandom(SALT_SIZE)
        iv = os.urandom(IV_SIZE)

        kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
        aes_key = kdf.derive(password.encode())

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
        padded = padder.update(plaintext) + padder.finalize()

        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        payload = base64.b64encode(salt + iv + ciphertext).decode("utf-8")
        self.output_text.setText(f"{HEADER_SYMMETRIC}\n{payload}\n{FOOTER_SYMMETRIC}")

    def _encrypt_for_contact(self, plaintext: bytes) -> None:
        """Encrypt the input for the selected contact public key."""

        key_data: Optional[KeyMetadata] = self.key_combo.currentData()
        if not key_data or not key_data.public_key:
            QMessageBox.warning(
                self,
                "Input Error",
                "Please select a public key to encrypt for.",
            )
            return

        public_key = serialization.load_pem_public_key(key_data.public_key.encode())
        session_key = os.urandom(AES_KEY_SIZE)
        iv = os.urandom(IV_SIZE)

        encrypted_session_key = public_key.encrypt(
            session_key,
            asymmetric_padding.OAEP(
                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv))
        padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
        padded = padder.update(plaintext) + padder.finalize()

        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        len_bytes = struct.pack(">H", len(encrypted_session_key))
        payload = base64.b64encode(len_bytes + encrypted_session_key + iv + ciphertext)
        self.output_text.setText(f"{HEADER_HYBRID}\n{payload.decode('utf-8')}\n{FOOTER_HYBRID}")

    # ------------------------------------------------------------------
    # Decryption helpers
    # ------------------------------------------------------------------
    def _decrypt(self) -> None:
        """Decrypt the supplied ciphertext if it matches the known formats."""

        text = self.input_text.toPlainText().strip()
        if not text:
            return

        self.output_text.clear()

        try:
            if text.startswith(HEADER_SYMMETRIC):
                self._decrypt_symmetric(text)
            elif text.startswith(HEADER_HYBRID):
                self._decrypt_hybrid(text)
            else:
                QMessageBox.warning(
                    self,
                    "Format Error",
                    "Input text format is not recognized.",
                )
        except Exception as error:  # pragma: no cover - defensive guard
            QMessageBox.critical(
                self,
                "Processing Error",
                f"An error occurred: {error}",
            )

    def _decrypt_symmetric(self, payload_text: str) -> None:
        """Handle password-based decryption flows."""

        payload = self._decode_payload(payload_text, HEADER_SYMMETRIC, FOOTER_SYMMETRIC)
        salt = payload[:SALT_SIZE]
        iv = payload[SALT_SIZE : SALT_SIZE + IV_SIZE]
        ciphertext = payload[SALT_SIZE + IV_SIZE :]

        password = self.password_edit.text()
        if not password:
            password, ok = QInputDialog.getText(
                self,
                "Password",
                "Enter decryption password:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not password:
                return

        kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
        aes_key = kdf.derive(password.encode())

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
        original = unpadder.update(padded) + unpadder.finalize()
        self.output_text.setText(original.decode("utf-8"))

    def _decrypt_hybrid(self, payload_text: str) -> None:
        """Handle hybrid decryption that requires an RSA private key."""

        payload = self._decode_payload(payload_text, HEADER_HYBRID, FOOTER_HYBRID)
        key_len = struct.unpack(">H", payload[:2])[0]
        encrypted_session_key = payload[2 : 2 + key_len]
        iv = payload[2 + key_len : 2 + key_len + IV_SIZE]
        ciphertext = payload[2 + key_len + IV_SIZE :]

        aes_key = self._resolve_session_key(encrypted_session_key)
        if not aes_key:
            QMessageBox.critical(
                self,
                "Decryption Failed",
                "No suitable private key found, or passphrase was incorrect.",
            )
            return

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
        original = unpadder.update(padded) + unpadder.finalize()
        self.output_text.setText(original.decode("utf-8"))

    def _resolve_session_key(self, encrypted_session_key: bytes) -> Optional[bytes]:
        """Try each private key to decrypt the provided session key."""

        # Attempt with already-unlocked keys first to avoid repeated prompts.
        for key_pair in self._keyring_data.get("my_key_pairs", []):
            key_name = key_pair["name"]
            private_key = self._unlocked_keys.get(key_name)
            if private_key:
                try:
                    return private_key.decrypt(
                        encrypted_session_key,
                        asymmetric_padding.OAEP(
                            mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None,
                        ),
                    )
                except ValueError:
                    continue

        # Prompt for additional keys as needed.
        for key_pair in self._keyring_data.get("my_key_pairs", []):
            key_name = key_pair["name"]
            if key_name in self._unlocked_keys:
                continue

            private_key = self._load_private_key_with_prompt(key_pair)
            if not private_key:
                continue

            try:
                decrypted = private_key.decrypt(
                    encrypted_session_key,
                    asymmetric_padding.OAEP(
                        mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None,
                    ),
                )
                self._unlocked_keys[key_name] = private_key
                return decrypted
            except ValueError:
                continue

        return None

    def _load_private_key_with_prompt(self, key_pair) -> Optional[object]:
        """Load the private key, asking for the passphrase when required."""

        key_name = key_pair["name"]
        private_key_pem = key_pair.get("private_key")
        if not private_key_pem:
            return None

        if "ENCRYPTED" not in private_key_pem:
            private_key = serialization.load_pem_private_key(private_key_pem.encode(), None)
            self._unlocked_keys[key_name] = private_key
            return private_key

        passphrase, ok = QInputDialog.getText(
            self,
            "Passphrase Required",
            f"Enter passphrase for key '{key_name}':",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return None

        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                passphrase.encode(),
            )
            self._unlocked_keys[key_name] = private_key
            return private_key
        except TypeError:
            QMessageBox.critical(self, "Error", "Incorrect passphrase.")
        except Exception as error:  # pragma: no cover - defensive guard
            QMessageBox.critical(self, "Error", f"Failed to load key: {error}")
        return None

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_payload(text: str, header: str, footer: str) -> bytes:
        """Extract and decode the base64 body between the header and footer."""

        body = text.replace(header, "").replace(footer, "").strip()
        return base64.b64decode(body)