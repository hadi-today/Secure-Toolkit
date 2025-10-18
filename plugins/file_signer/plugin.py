import os
import json
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QGroupBox,
    QComboBox,
    QTabWidget,
)
from PyQt6.QtCore import Qt

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, utils
from cryptography.exceptions import InvalidSignature

KEYRING_DIR = os.path.join(os.path.dirname(__file__), '..', 'keyring_manager')
KEYRING_FILE = os.path.join(KEYRING_DIR, "keyring.json")


class FileSignerWidget(QDialog):
    """Modal dialog that provides file signing and verification tools."""

    def __init__(self, keyring_data, save_callback, parent=None):
        # Accept the optional parent supplied by the plugin launcher while still
        # presenting the signer as its own dialog window.
        super().__init__(parent)

        self.setWindowTitle("Digital Signature Tool")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(500, 400)

        # Persist the injected dependencies for future enhancements that may
        # need to access the keyring or persist changes.
        self.keyring_data = keyring_data
        self.save_callback = save_callback

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        self.sign_tab = QWidget()
        self.verify_tab = QWidget()
        self.tab_widget.addTab(self.sign_tab, "Sign File")
        self.tab_widget.addTab(self.verify_tab, "Verify Signature")
        
        self._create_sign_tab()
        self._create_verify_tab()
        
        main_layout.addWidget(self.tab_widget)

    def _create_sign_tab(self):
        layout = QVBoxLayout(self.sign_tab)
        
        self.sign_file_path_edit = QLineEdit(); self.sign_file_path_edit.setReadOnly(True)
        select_file_btn = QPushButton("Select File to Sign...")
        select_file_btn.clicked.connect(self._select_sign_file)
        
        self.signing_key_combo = QComboBox()
        self.signing_key_combo.addItem("--- Select Your Private Key ---", -1)
        for i, key in enumerate(self.keyring_data['my_key_pairs']):
            self.signing_key_combo.addItem(key['name'], i)
            
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setPlaceholderText("Enter passphrase if required")
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)

        sign_button = QPushButton("Generate Signature")
        sign_button.clicked.connect(self._generate_signature)

        layout.addWidget(QLabel("1. Select the file you want to sign:"))
        layout.addWidget(self.sign_file_path_edit)
        layout.addWidget(select_file_btn)
        layout.addSpacing(20)
        layout.addWidget(QLabel("2. Choose your signing key:"))
        layout.addWidget(self.signing_key_combo)
        layout.addWidget(self.passphrase_edit)
        layout.addSpacing(20)
        layout.addWidget(sign_button)
        layout.addStretch()

    def _create_verify_tab(self):
        layout = QVBoxLayout(self.verify_tab)
        
        self.verify_file_path_edit = QLineEdit(); self.verify_file_path_edit.setReadOnly(True)
        select_orig_file_btn = QPushButton("Select Original File...")
        select_orig_file_btn.clicked.connect(self._select_verify_file)
        
        self.sig_file_path_edit = QLineEdit(); self.sig_file_path_edit.setReadOnly(True)
        select_sig_file_btn = QPushButton("Select Signature File (.sig)...")
        select_sig_file_btn.clicked.connect(self._select_sig_file)

        self.verifying_key_combo = QComboBox()
        self.verifying_key_combo.addItem("--- Select Signer's Public Key ---", -1)
        for i, key in enumerate(self.keyring_data['my_key_pairs']):
            self.verifying_key_combo.addItem(f"[My Pair] {key['name']}", {"type": "pair", "index": i})
        for i, key in enumerate(self.keyring_data['contact_public_keys']):
            self.verifying_key_combo.addItem(f"[Contact] {key['name']}", {"type": "public", "index": i})
            
        verify_button = QPushButton("Verify Signature")
        verify_button.clicked.connect(self._verify_signature)
        self.verify_result_label = QLabel("Result will be shown here.")
        self.verify_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QLabel("1. Select the original file:"))
        layout.addWidget(self.verify_file_path_edit)
        layout.addWidget(select_orig_file_btn)
        layout.addSpacing(10)
        layout.addWidget(QLabel("2. Select the signature file:"))
        layout.addWidget(self.sig_file_path_edit)
        layout.addWidget(select_sig_file_btn)
        layout.addSpacing(10)
        layout.addWidget(QLabel("3. Choose the public key of the person who signed the file:"))
        layout.addWidget(self.verifying_key_combo)
        layout.addSpacing(20)
        layout.addWidget(verify_button)
        layout.addWidget(self.verify_result_label)
        layout.addStretch()

    def _select_sign_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Sign")
        if path: self.sign_file_path_edit.setText(path)
            
    def _select_verify_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Original File")
        if path: self.verify_file_path_edit.setText(path)
            
    def _select_sig_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature File", "", "Signature Files (*.sig)")
        if path: self.sig_file_path_edit.setText(path)

    def _generate_signature(self):
        file_path = self.sign_file_path_edit.text()
        key_index = self.signing_key_combo.currentData()
        passphrase = self.passphrase_edit.text()

        if not file_path or key_index < 0:
            QMessageBox.warning(self, "Input Error", "Please select a file and a signing key.")
            return

        try:
            key_pair = self.keyring_data['my_key_pairs'][key_index]
            private_key = serialization.load_pem_private_key(
                key_pair['private_key'].encode(),
                password=passphrase.encode() if passphrase else None
            )

            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            signature = private_key.sign(
                file_data,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )

            sig_path = f"{file_path}.sig"
            with open(sig_path, 'wb') as f_sig:
                f_sig.write(signature)
            
            QMessageBox.information(self, "Success", f"Signature generated successfully!\nSaved as: {sig_path}")

        except TypeError:
            QMessageBox.critical(self, "Authentication Error", "Incorrect passphrase for the selected private key.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def _verify_signature(self):
        file_path = self.verify_file_path_edit.text()
        sig_path = self.sig_file_path_edit.text()
        key_info = self.verifying_key_combo.currentData()

        if not file_path or not sig_path or key_info == -1:
            QMessageBox.warning(self, "Input Error", "Please select all three items: original file, signature file, and public key.")
            return

        try:
            if key_info['type'] == 'pair':
                key_data = self.keyring_data['my_key_pairs'][key_info['index']]
            else: 
                key_data = self.keyring_data['contact_public_keys'][key_info['index']]
            
            public_key = serialization.load_pem_public_key(key_data['public_key'].encode())

            with open(file_path, 'rb') as f:
                file_data = f.read()
            with open(sig_path, 'rb') as f_sig:
                signature = f_sig.read()
            
            public_key.verify(
                signature,
                file_data,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            
            self.verify_result_label.setText("✅ SUCCESS: Signature is valid.")
            self.verify_result_label.setStyleSheet("color: green; font-weight: bold; border: 1px solid green; padding: 5px;")

        except InvalidSignature:
            self.verify_result_label.setText("❌ INVALID: Signature does not match!")
            self.verify_result_label.setStyleSheet("color: red; font-weight: bold; border: 1px solid red; padding: 5px;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during verification: {e}")