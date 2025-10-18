"""File encryption dialog and helpers for the file encryptor plugin.

The original implementation bundled a significant amount of logic without any
descriptive comments.  This pass documents each helper class so that future
maintainers can reason about the workflow that drives the encryption and
decryption pipelines.
"""

import base64
import hashlib
import json
import os
import struct
import uuid

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC_NUMBER = b'\x8A\xDF\x04\xFA' 
VERSION = b'\x01'
TYPE_SYMMETRIC = b'\x01'
TYPE_HYBRID = b'\x02'
SALT_SIZE = 16
AES_KEY_SIZE = 32 
ITERATIONS = 480000
BUFFER_SIZE = 1024 * 1024 

KEYRING_DIR = os.path.join(os.path.dirname(__file__), '..', 'keyring_manager')
KEYRING_FILE = os.path.join(KEYRING_DIR, "keyring.json")



class SelectPrivateKeyDialog(QDialog):
    """Dialog that prompts the user to choose which private key to unlock."""

    def __init__(self, key_pairs, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select Private Key for Decryption")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "This file was encrypted with a key pair.\n"
                "Please select which of your private keys to use:"
            )
        )
        self.key_combo = QComboBox()
        for i, key_pair in enumerate(key_pairs):
            self.key_combo.addItem(key_pair['name'], i)
        layout.addWidget(self.key_combo)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

    def get_selected_key_index(self):
        """Return the index of the chosen private key or ``-1`` on cancel."""

        if self.exec() == QDialog.DialogCode.Accepted:
            return self.key_combo.currentData()
        return -1
class EncryptWorker(QThread):
    """Background task that encrypts a file and optionally emits chunks."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, in_path, out_path, method, key_data, original_filename, chunk_size_bytes=0):
        super().__init__()

        self.in_path = in_path
        self.out_path = out_path
        self.method = method
        self.key_data = key_data
        self.original_filename = original_filename
        self.chunk_size = chunk_size_bytes
        self.is_chunking = chunk_size_bytes > 0

    def run(self):
        """Encrypt ``self.in_path`` and notify the UI about the progress."""

        try:
            aes_key, key_header_part = None, b''
            if self.method == 'password':
                salt = os.urandom(SALT_SIZE)
                kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
                aes_key = kdf.derive(self.key_data.encode())
                key_header_part = TYPE_SYMMETRIC + salt
            else:
                public_key = serialization.load_pem_public_key(self.key_data['public_key'].encode())
                session_key = os.urandom(AES_KEY_SIZE)
                aes_key = session_key
                encrypted_session_key = public_key.encrypt(session_key, asymmetric_padding.OAEP(mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                key_header_part = TYPE_HYBRID + struct.pack('>H', len(encrypted_session_key)) + encrypted_session_key
            
            iv_for_filename = os.urandom(16)
            fn_cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_for_filename))
            fn_encryptor = fn_cipher.encryptor()
            fn_padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
            padded_fn = fn_padder.update(self.original_filename.encode('utf-8')) + fn_padder.finalize()
            encrypted_fn = fn_encryptor.update(padded_fn) + fn_encryptor.finalize()
            
            iv_for_content = os.urandom(16)
            header = (MAGIC_NUMBER + VERSION + key_header_part + 
                      struct.pack('>H', len(encrypted_fn)) + encrypted_fn + 
                      iv_for_filename + iv_for_content)

            content_cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_for_content))
            encryptor = content_cipher.encryptor()
            padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
            
            total_size = os.path.getsize(self.in_path)
            
            if not self.is_chunking:
                with open(self.in_path, 'rb') as f_in, open(self.out_path, 'wb') as f_out:
                    f_out.write(header)
                    bytes_processed = 0
                    while chunk := f_in.read(BUFFER_SIZE):
                        padded_chunk = padder.update(chunk)
                        encrypted_chunk = encryptor.update(padded_chunk)
                        f_out.write(encrypted_chunk)
                        bytes_processed += len(chunk)
                        self.progress.emit(int(bytes_processed * 100 / total_size))
                    final_padded = padder.finalize()
                    final_encrypted = encryptor.update(final_padded) + encryptor.finalize()
                    f_out.write(final_encrypted)
                self.finished.emit(f"File encrypted successfully to:\n{self.out_path}")
            else:
                manifest = {
                    "original_filename": self.original_filename,
                    "total_size": total_size,
                    "chunk_size": self.chunk_size,
                    "chunk_hashes": [],
                    "encryption_header": base64.b64encode(header).decode('utf-8')
                }
                
                part_num = 1
                current_chunk_size = 0
                f_out = None
                hasher = hashlib.sha256()
                
                with open(self.in_path, 'rb') as f_in:
                    bytes_processed = 0
                    while chunk := f_in.read(BUFFER_SIZE):
                        if f_out is None:
                            part_path = os.path.join(self.out_path, f"{self.original_filename}.enc.part{part_num:03d}")
                            f_out = open(part_path, 'wb')
                            hasher = hashlib.sha256()

                        padded_chunk = padder.update(chunk)
                        encrypted_chunk = encryptor.update(padded_chunk)
                        
                        f_out.write(encrypted_chunk)
                        hasher.update(encrypted_chunk)
                        current_chunk_size += len(encrypted_chunk)
                        
                        if current_chunk_size >= self.chunk_size:
                            f_out.close()
                            manifest['chunk_hashes'].append(hasher.hexdigest())
                            part_num += 1
                            current_chunk_size = 0
                            f_out = None

                        bytes_processed += len(chunk)
                        self.progress.emit(int(bytes_processed * 100 / total_size))

                    final_padded = padder.finalize()
                    final_encrypted = encryptor.update(final_padded) + encryptor.finalize()
                    
                    if f_out is None:
                        part_path = os.path.join(self.out_path, f"{self.original_filename}.enc.part{part_num:03d}")
                        f_out = open(part_path, 'wb')
                        hasher = hashlib.sha256()
                        
                    f_out.write(final_encrypted)
                    hasher.update(final_encrypted)
                    f_out.close()
                    manifest['chunk_hashes'].append(hasher.hexdigest())
                
                manifest_path = os.path.join(self.out_path, "manifest.json")
                with open(manifest_path, 'w') as f_manifest:
                    json.dump(manifest, f_manifest, indent=4)
                
                self.finished.emit(f"File encrypted and split into {part_num} parts in:\n{self.out_path}")
        except Exception as error:  # pragma: no cover - surfaced to UI
            import traceback

            traceback.print_exc()
            self.error.emit(f"An error occurred during encryption: {error}")
class DecryptWorker(QThread):
    """Background task that reverses the encryption process."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, in_path, out_path, aes_key):
        super().__init__()

        self.in_path = in_path
        self.out_path = out_path
        self.aes_key = aes_key
        self.is_chunking = self.in_path.lower().endswith('manifest.json')

    def run(self):
        """Decrypt ``self.in_path`` into ``self.out_path`` while reporting progress."""

        try:
            if not self.is_chunking:
                with open(self.in_path, 'rb') as f_in:
                    f_in.seek(len(MAGIC_NUMBER) + 1) 
                    enc_type = f_in.read(1)
                    
                    if enc_type == TYPE_SYMMETRIC:
                        f_in.seek(SALT_SIZE, 1)
                    elif enc_type == TYPE_HYBRID:
                        key_len = struct.unpack('>H', f_in.read(2))[0]
                        f_in.seek(key_len, 1)
                    else:
                        self.error.emit("Unknown encryption type."); return
                    
                    fn_len = struct.unpack('>H', f_in.read(2))[0]
                    f_in.seek(fn_len, 1) 
                    f_in.seek(16, 1)    
                    
                    iv_for_content = f_in.read(16)
                    header_size = f_in.tell()

                    cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv_for_content))
                    decryptor = cipher.decryptor()
                    unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
                    total_size = os.path.getsize(self.in_path)
                    
                    with open(self.out_path, 'wb') as f_out:
                        bytes_processed = header_size
                        while chunk := f_in.read(BUFFER_SIZE):
                            decrypted = decryptor.update(chunk)
                            unpadded = unpadder.update(decrypted)
                            f_out.write(unpadded)
                            bytes_processed += len(chunk)
                            self.progress.emit(int(bytes_processed * 100 / total_size))
                        
                        final_dec = decryptor.finalize()
                        final_unpadded = unpadder.update(final_dec) + unpadder.finalize()
                        f_out.write(final_unpadded)
                        
                    self.finished.emit(f"File decrypted successfully to:\n{self.out_path}")
            else:
                with open(self.in_path, 'r') as f:
                    manifest = json.load(f)
                manifest_dir = os.path.dirname(self.in_path)
                
                self.progress.emit(5)
                for i, expected_hash in enumerate(manifest['chunk_hashes']):
                    part_filename = f"{manifest['original_filename']}.enc.part{i+1:03d}"
                    part_path = os.path.join(manifest_dir, part_filename)
                    if not os.path.exists(part_path):
                        self.error.emit(f"Chunk file not found: {part_filename}"); return
                    
                    hasher = hashlib.sha256()
                    with open(part_path, 'rb') as f_part:
                        while chunk := f_part.read(BUFFER_SIZE):
                            hasher.update(chunk)
                    if hasher.hexdigest() != expected_hash:
                        self.error.emit(f"Integrity check failed for: {part_filename}"); return
                
                header = base64.b64decode(manifest['encryption_header'])
                iv_for_content = header[-16:]
                
                cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv_for_content))
                decryptor = cipher.decryptor()
                unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
                
                total_size = manifest['total_size']
                bytes_processed = 0
                
                with open(self.out_path, 'wb') as f_out:
                    for i in range(len(manifest['chunk_hashes'])):
                        part_filename = f"{manifest['original_filename']}.enc.part{i+1:03d}"
                        part_path = os.path.join(manifest_dir, part_filename)
                        with open(part_path, 'rb') as f_part:
                            while chunk := f_part.read(BUFFER_SIZE):
                                decrypted = decryptor.update(chunk)
                                unpadded = unpadder.update(decrypted)
                                f_out.write(unpadded)
                                bytes_processed += len(chunk)
                                self.progress.emit(int(bytes_processed * 100 / total_size)) if total_size > 0 else 0
                                
                    final_dec = decryptor.finalize()
                    final_unpadded = unpadder.update(final_dec) + unpadder.finalize()
                    f_out.write(final_unpadded)
                    
                self.finished.emit(f"File successfully reassembled and decrypted to:\n{self.out_path}")
        except Exception as error:  # pragma: no cover - surfaced to UI
            import traceback

            traceback.print_exc()
            self.error.emit(f"An error occurred during decryption: {error}")
class FileEncryptorWidget(QDialog):
    """Modal dialog presented by the file encryptor plugin.

    The widget receives the decrypted keyring content alongside a callback
    that persists updates, mirroring the signature expected by the plugin
    loader.  Accepting an optional parent keeps Qt's window stacking behavior
    while allowing the encryptor to appear as an independent dialog instead of
    embedding itself inside the main application tab view.
    """

    def __init__(self, keyring_data, save_callback, parent=None):
        super().__init__(parent)

        # Present the widget as its own window while keeping the Qt parent for stacking.
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("File Encryptor / Decryptor")

        # Persist the dependencies so the plugin matches the signature used by
        # the launcher and can access the decrypted keyring entries.
        self.keyring_data = keyring_data
        self.save_callback = save_callback
        self.worker = None

        main_layout = QVBoxLayout(self)
        input_group = QGroupBox("1. Select Input File")
        input_layout = QGridLayout()
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setReadOnly(True)
        select_file_btn = QPushButton("Select File...")
        select_file_btn.clicked.connect(self._select_input_file)
        input_layout.addWidget(self.input_path_edit, 0, 0)
        input_layout.addWidget(select_file_btn, 0, 1)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        self.method_group = QGroupBox("2. Encryption Method")
        method_layout = QVBoxLayout()
        self.key_combo = QComboBox()
        self.key_combo.addItem("--- Select a Key ---", None)
        for key in self.keyring_data['my_key_pairs']:
            self.key_combo.addItem(f"[My Pair] {key['name']}", {'type': 'pair', 'data': key})
        for key in self.keyring_data['contact_public_keys']:
            self.key_combo.addItem(f"[Contact] {key['name']}", {'type': 'public', 'data': key})
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Or enter a password here")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_combo.currentIndexChanged.connect(self._update_ui_state)
        self.password_edit.textChanged.connect(self._update_ui_state)
        method_layout.addWidget(QLabel("Encrypt for a contact/yourself (select from keyring):"))
        method_layout.addWidget(self.key_combo)
        method_layout.addWidget(QLabel("OR"))
        method_layout.addWidget(QLabel("Encrypt with a password (for personal use):"))
        method_layout.addWidget(self.password_edit)
        self.method_group.setLayout(method_layout)
        main_layout.addWidget(self.method_group)
        output_group = QGroupBox("3. Output Settings")
        output_layout = QGridLayout()
        self.split_checkbox = QCheckBox("Split output file into chunks")
        self.chunk_size_label = QLabel("Chunk Size:")
        self.chunk_size_edit = QLineEdit("100") 
        self.chunk_unit_combo = QComboBox()
        self.chunk_unit_combo.addItems(["MB", "GB"])

        output_layout.addWidget(self.split_checkbox, 0, 0, 1, 4) 
        output_layout.addWidget(self.chunk_size_label, 1, 0)
        output_layout.addWidget(self.chunk_size_edit, 1, 1)
        output_layout.addWidget(self.chunk_unit_combo, 1, 2)
        output_layout.setColumnStretch(3, 1) 
        
        self.split_checkbox.toggled.connect(self._update_ui_state)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        action_group = QGroupBox("4. Actions")
        action_layout = QVBoxLayout()
        self.encrypt_btn = QPushButton("Encrypt")
        self.decrypt_btn = QPushButton("Decrypt")
        self.progress_bar = QProgressBar()
        self.encrypt_btn.clicked.connect(self._start_encryption)
        self.decrypt_btn.clicked.connect(self._start_decryption)
        action_layout.addWidget(self.encrypt_btn)
        action_layout.addWidget(self.decrypt_btn)
        action_layout.addWidget(self.progress_bar)
        action_group.setLayout(action_layout)
        main_layout.addWidget(action_group)
        
        self._update_ui_state()

    def _update_ui_state(self):
        """Enable or disable controls based on current selections."""

        self.key_combo.blockSignals(True)
        self.password_edit.blockSignals(True)
        self.split_checkbox.blockSignals(True)

        try:
            has_input_file = bool(self.input_path_edit.text())
            is_encrypted_file = has_input_file and (self.input_path_edit.text().lower().endswith('.enc') or self.input_path_edit.text().lower().endswith('manifest.json'))
            
            self.decrypt_btn.setEnabled(is_encrypted_file)
            self.method_group.setEnabled(not is_encrypted_file)
            self.split_checkbox.setEnabled(not is_encrypted_file)

            split_widgets_enabled = (not is_encrypted_file) and self.split_checkbox.isChecked()
            self.chunk_size_label.setEnabled(split_widgets_enabled)
            self.chunk_size_edit.setEnabled(split_widgets_enabled)
            self.chunk_unit_combo.setEnabled(split_widgets_enabled)

            has_method = self.key_combo.currentIndex() > 0 or bool(self.password_edit.text())
            self.encrypt_btn.setEnabled(has_input_file and has_method and not is_encrypted_file)
            
            if not self.method_group.isEnabled():
                return

           
            if self.password_edit.text():
                if self.key_combo.isEnabled():
                    self.key_combo.setCurrentIndex(0)
                self.key_combo.setEnabled(False)
            else:
                self.key_combo.setEnabled(True)

            if self.key_combo.currentIndex() > 0:
                if self.password_edit.isEnabled():
                    self.password_edit.clear()
                self.password_edit.setEnabled(False)
            else:
                self.password_edit.setEnabled(True)
                
        finally:
          
            self.key_combo.blockSignals(False)
            self.password_edit.blockSignals(False)
            self.split_checkbox.blockSignals(False)
            
    def _select_input_file(self):
        """Prompt the user to choose a file to encrypt or decrypt."""

        filter_text = "Encrypted Packages (*.enc manifest.json);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Encrypt or Decrypt", "", filter_text)
        if path:
            self.input_path_edit.setText(path)
            self._update_ui_state()

    def _start_encryption(self):
        """Validate options and hand off work to :class:`EncryptWorker`."""

        in_path = self.input_path_edit.text()
        if not in_path:
            return
            
        original_filename = os.path.basename(in_path)
        method = 'password' if self.password_edit.text() else 'key'
        key_data = self.password_edit.text() if method == 'password' else self.key_combo.currentData()['data']
        
        out_path = ""  # Output path can be either a file or a directory.
        chunk_size_bytes = 0

        # Determine if the user requested chunked output.
        if self.split_checkbox.isChecked():
            # Ask the user for a directory when chunking is enabled.
            try:
                size_str = self.chunk_size_edit.text()
                if not size_str.isdigit() or int(size_str) <= 0:
                    self._show_error("Chunk size must be a positive number.")
                    return
                size = int(size_str)
                unit = self.chunk_unit_combo.currentText()
                multiplier = 1024 * 1024 if unit == "MB" else 1024 * 1024 * 1024
                chunk_size_bytes = size * multiplier
            except ValueError:
                self._show_error("Invalid chunk size. Please enter a valid number.")
                return

            # Directory selection dialog when chunking output.
            out_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not out_path:  # Abort when the user cancels the directory selection.
                return
        else:
            # Otherwise request a filename for the encrypted output.
            random_name = f"{uuid.uuid4()}.enc"
            out_path, _ = QFileDialog.getSaveFileName(self, "Save Encrypted File As...", random_name, "Encrypted Files (*.enc)")
            if not out_path:  # Abort when the user cancels the file selection.
                return

        # Disable actions and start the worker thread.
        self.encrypt_btn.setEnabled(False)
        self.decrypt_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # Pass all parameters to the encryption worker.
        self.worker = EncryptWorker(
            in_path,
            out_path,
            method,
            key_data,
            original_filename,
            chunk_size_bytes,
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._show_error)
        self.worker.start()

    def _start_decryption(self):
        """Inspect the selected file and launch :class:`DecryptWorker`."""

        in_path = self.input_path_edit.text()
        if not in_path:
            return

        try:
            aes_key = None
            original_filename = ""

            if in_path.lower().endswith('manifest.json'):
                with open(in_path, 'r', encoding='utf-8') as manifest_file:
                    manifest = json.load(manifest_file)

                header = base64.b64decode(manifest['encryption_header'])
                original_filename_from_manifest = manifest['original_filename']
                header_view = memoryview(header)

                offset = len(MAGIC_NUMBER) + 1
                enc_type = header_view[offset : offset + 1].tobytes()
                offset += 1

                if enc_type == TYPE_SYMMETRIC:
                    password, ok = QInputDialog.getText(
                        self,
                        "Password",
                        "Enter file password:",
                        QLineEdit.EchoMode.Password,
                    )
                    if not ok or not password:
                        self._show_error("Decryption cancelled.")
                        return

                    salt = header_view[offset : offset + SALT_SIZE].tobytes()
                    offset += SALT_SIZE

                    kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
                    aes_key = kdf.derive(password.encode())
                elif enc_type == TYPE_HYBRID:
                    key_len = struct.unpack('>H', header_view[offset : offset + 2])[0]
                    offset += 2
                    encrypted_session_key = header_view[offset : offset + key_len].tobytes()
                    offset += key_len

                    if not self.keyring_data['my_key_pairs']:
                        self._show_error("No private keys in keyring.")
                        return

                    dialog = SelectPrivateKeyDialog(self.keyring_data['my_key_pairs'], self)
                    idx = dialog.get_selected_key_index()
                    if idx < 0:
                        self._show_error("Decryption cancelled.")
                        return

                    key_pair = self.keyring_data['my_key_pairs'][idx]
                    key_pem = key_pair['private_key'].encode()
                    key_name = key_pair['name']

                    try:
                        private_key = serialization.load_pem_private_key(key_pem, None)
                    except TypeError:
                        passphrase, ok = QInputDialog.getText(
                            self,
                            "Passphrase",
                            f"Enter passphrase for '{key_name}':",
                            QLineEdit.EchoMode.Password,
                        )
                        if not ok:
                            self._show_error("Decryption cancelled.")
                            return
                        try:
                            private_key = serialization.load_pem_private_key(
                                key_pem, passphrase.encode()
                            )
                        except TypeError:
                            self._show_error("Incorrect passphrase.")
                            return

                    try:
                        aes_key = private_key.decrypt(
                            encrypted_session_key,
                            asymmetric_padding.OAEP(
                                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                                algorithm=hashes.SHA256(),
                                label=None,
                            ),
                        )
                    except ValueError:
                        self._show_error("Selected key is not correct for this file.")
                        return
                else:
                    self._show_error("Unknown type in header.")
                    return

                fn_len = struct.unpack('>H', header_view[offset : offset + 2])[0]
                offset += 2
                encrypted_fn = header_view[offset : offset + fn_len].tobytes()
                offset += fn_len
                iv_for_fn = header_view[offset : offset + 16].tobytes()
                offset += 16

                fn_cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_for_fn))
                fn_decryptor = fn_cipher.decryptor()
                fn_unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
                padded = fn_decryptor.update(encrypted_fn) + fn_decryptor.finalize()
                original_fn_bytes = fn_unpadder.update(padded) + fn_unpadder.finalize()
                original_filename = original_fn_bytes.decode('utf-8')

                if original_filename != original_filename_from_manifest:
                    self._show_error("Manifest file might be corrupt. Filename mismatch.")
                    return

            elif in_path.lower().endswith('.enc'):
                with open(in_path, 'rb') as encrypted_file:
                    magic = encrypted_file.read(len(MAGIC_NUMBER))
                    version = encrypted_file.read(1)
                    if magic != MAGIC_NUMBER or version > VERSION:
                        self._show_error("Invalid/unsupported file.")
                        return

                    enc_type = encrypted_file.read(1)
                    if enc_type == TYPE_SYMMETRIC:
                        password, ok = QInputDialog.getText(
                            self,
                            "Password",
                            "Enter file password:",
                            QLineEdit.EchoMode.Password,
                        )
                        if not ok or not password:
                            self._show_error("Decryption cancelled.")
                            return
                        salt = encrypted_file.read(SALT_SIZE)
                        kdf = PBKDF2HMAC(hashes.SHA256(), AES_KEY_SIZE, salt, ITERATIONS)
                        aes_key = kdf.derive(password.encode())
                    elif enc_type == TYPE_HYBRID:
                        key_len = struct.unpack('>H', encrypted_file.read(2))[0]
                        encrypted_session_key = encrypted_file.read(key_len)

                        if not self.keyring_data['my_key_pairs']:
                            self._show_error("No private keys in keyring.")
                            return

                        dialog = SelectPrivateKeyDialog(self.keyring_data['my_key_pairs'], self)
                        idx = dialog.get_selected_key_index()
                        if idx < 0:
                            self._show_error("Decryption cancelled.")
                            return

                        key_pair = self.keyring_data['my_key_pairs'][idx]
                        key_pem = key_pair['private_key'].encode()
                        key_name = key_pair['name']

                        try:
                            private_key = serialization.load_pem_private_key(key_pem, None)
                        except TypeError:
                            passphrase, ok = QInputDialog.getText(
                                self,
                                "Passphrase",
                                f"Enter passphrase for '{key_name}':",
                                QLineEdit.EchoMode.Password,
                            )
                            if not ok:
                                self._show_error("Decryption cancelled.")
                                return
                            try:
                                private_key = serialization.load_pem_private_key(
                                    key_pem, passphrase.encode()
                                )
                            except TypeError:
                                self._show_error("Incorrect passphrase.")
                                return

                        try:
                            aes_key = private_key.decrypt(
                                encrypted_session_key,
                                asymmetric_padding.OAEP(
                                    mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                                    algorithm=hashes.SHA256(),
                                    label=None,
                                ),
                            )
                        except ValueError:
                            self._show_error("Selected key is not correct for this file.")
                            return
                    else:
                        self._show_error("Unknown type.")
                        return

                    fn_len = struct.unpack('>H', encrypted_file.read(2))[0]
                    encrypted_fn = encrypted_file.read(fn_len)
                    iv_for_fn = encrypted_file.read(16)
                    fn_cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_for_fn))
                    fn_decryptor = fn_cipher.decryptor()
                    fn_unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
                    padded = fn_decryptor.update(encrypted_fn) + fn_decryptor.finalize()
                    original_fn_bytes = fn_unpadder.update(padded) + fn_unpadder.finalize()
                    original_filename = original_fn_bytes.decode('utf-8')
            else:
                self._show_error("Please select a valid '.enc' file or a 'manifest.json' to decrypt.")
                return

            out_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Decrypted File As...",
                original_filename,
            )
            if not out_path:
                return

            self.encrypt_btn.setEnabled(False)
            self.decrypt_btn.setEnabled(False)
            self.progress_bar.setValue(0)

            self.worker = DecryptWorker(in_path, out_path, aes_key)
            self.worker.progress.connect(self.progress_bar.setValue)
            self.worker.finished.connect(self._on_finished)
            self.worker.error.connect(self._show_error)
            self.worker.start()

        except Exception as error:  # pragma: no cover - surfaced to UI
            import traceback

            traceback.print_exc()
            self._show_error(f"Failed to process file: {error}")

    def _on_finished(self, message):
        """Re-enable actions when a worker signals completion."""

        QMessageBox.information(self, "Success", message)
        self.worker = None
        self.progress_bar.setValue(100)
        self._update_ui_state()

    def _show_error(self, message):
        """Display an error message and reset the worker state."""

        QMessageBox.critical(self, "Error", message)
        self.worker = None
        self.progress_bar.setValue(0)
        self._update_ui_state()
