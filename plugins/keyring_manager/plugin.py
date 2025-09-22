import os
import json
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QTextEdit, 
                             QPushButton, QMessageBox, QInputDialog, QFileDialog, QDialog, 
                             QFormLayout, QLineEdit, QTabWidget, QComboBox)
from PyQt6.QtCore import Qt

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

PLUGIN_DIR = os.path.dirname(__file__)
KEYRING_FILE = os.path.join(PLUGIN_DIR, "keyring.json")





class AddPublicKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Contact's Public Key")
        self.key_content = None

        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.file_path_label = QLabel("No file selected.")
        select_file_button = QPushButton("Select Key File...")
        
        select_file_button.clicked.connect(self._select_file)
        
        layout.addRow("Enter Contact's Name:", self.name_input)
        layout.addRow(select_file_button, self.file_path_label)
        
        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Public Key", "", "PEM Files (*.pem *.pub)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.key_content = f.read()
                self.file_path_label.setText(os.path.basename(file_path))
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Could not read file: {e}")
                self.key_content = None

    def get_data(self):
        if self.exec() == QDialog.DialogCode.Accepted and self.name_input.text() and self.key_content:
            return self.name_input.text(), self.key_content
        return None, None

class GeneratePairDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate New Key Pair")
        
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.key_size_combo = QComboBox()
        self.key_size_combo.addItems(["2048", "3072", "4096"])
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addRow("Enter a Name:", self.name_input)
        layout.addRow("Select Key Size (bits):", self.key_size_combo)
        layout.addRow("Passphrase (optional, for private key):", self.passphrase_input)
        
        buttons = QHBoxLayout()
        ok_button = QPushButton("Generate")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def get_data(self):
        if self.exec() == QDialog.DialogCode.Accepted and self.name_input.text():
            return (self.name_input.text(), 
                    int(self.key_size_combo.currentText()), 
                    self.passphrase_input.text())
        return None, None, None

class ImportPairDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Key Pair")
        self.private_key_content = None
        
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.file_path_label = QLabel("No private key file selected.")
        select_file_button = QPushButton("Select Private Key File...")
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)

        select_file_button.clicked.connect(self._select_file)
        
        layout.addRow("Enter a Name:", self.name_input)
        layout.addRow(select_file_button, self.file_path_label)
        layout.addRow("Passphrase (if key is encrypted):", self.passphrase_input)

        buttons = QHBoxLayout()
        ok_button = QPushButton("Import")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "PEM Files (*.pem)")
        if file_path:
            try:
                with open(file_path, 'rb') as f: 
                    self.private_key_content = f.read()
                self.file_path_label.setText(os.path.basename(file_path))
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Could not read file: {e}")
                self.private_key_content = None

    def get_data(self):
        if self.exec() == QDialog.DialogCode.Accepted and self.name_input.text() and self.private_key_content:
            return (self.name_input.text(), 
                    self.private_key_content, 
                    self.passphrase_input.text())
        return None, None, None

class KeyringManagerWidget(QWidget):
    def __init__(self, keyring_data, save_callback):
        super().__init__()
        self.setWindowTitle("Keyring Manager")
        self.keyring_data = keyring_data
        self.save_callback = save_callback
        self.setMinimumSize(700, 500)

        main_layout = QHBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        self.my_keys_list_widget = QListWidget()
        self.contacts_list_widget = QListWidget()
        self.tab_widget.addTab(self.my_keys_list_widget, "My Key Pairs")
        self.tab_widget.addTab(self.contacts_list_widget, "Contacts' Public Keys")
        self.my_keys_list_widget.currentItemChanged.connect(self._update_details_view)
        self.contacts_list_widget.currentItemChanged.connect(self._update_details_view)
        self.tab_widget.currentChanged.connect(self._tab_changed)

        right_panel = QVBoxLayout()
        self.details_name = QLabel("Name: -")
        self.details_type = QLabel("Type: -")
        self.key_view = QTextEdit()
        self.key_view.setReadOnly(True)
        self.key_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        right_panel.addWidget(self.details_name)
        right_panel.addWidget(self.details_type)
        right_panel.addWidget(QLabel("Public Key Content:"))
        right_panel.addWidget(self.key_view)
        
        button_layout = QVBoxLayout()
        my_keys_group = QHBoxLayout()
        gen_pair_btn = QPushButton("Generate My Pair...")
        import_pair_btn = QPushButton("Import My Pair...")
        my_keys_group.addWidget(gen_pair_btn)
        my_keys_group.addWidget(import_pair_btn)
        
        contacts_group = QHBoxLayout()
        add_contact_btn = QPushButton("Import Contact Key...")
        contacts_group.addWidget(add_contact_btn)
        
        manage_group = QHBoxLayout()
        export_btn = QPushButton("Export...")
        delete_btn = QPushButton("Delete Selected")
        manage_group.addWidget(export_btn)
        manage_group.addWidget(delete_btn)
        
        button_layout.addWidget(QLabel("My Keys Actions:"))
        button_layout.addLayout(my_keys_group)
        button_layout.addWidget(QLabel("Contacts Actions:"))
        button_layout.addLayout(contacts_group)
        button_layout.addStretch()
        button_layout.addWidget(QLabel("General Actions:"))
        button_layout.addLayout(manage_group)
        
        right_panel.addLayout(button_layout)
        main_layout.addWidget(self.tab_widget, 1)
        main_layout.addLayout(right_panel, 2)
        
        add_contact_btn.clicked.connect(self._add_contact_key)
        gen_pair_btn.clicked.connect(self._generate_new_pair)
        import_pair_btn.clicked.connect(self._import_my_pair)
        export_btn.clicked.connect(self._export_key)
        delete_btn.clicked.connect(self._delete_key)
        
        self._populate_key_lists()

    def _populate_key_lists(self):
        self.my_keys_list_widget.clear()
        for item in self.keyring_data['my_key_pairs']:
            self.my_keys_list_widget.addItem(item['name'])
        self.contacts_list_widget.clear()
        for item in self.keyring_data['contact_public_keys']:
            self.contacts_list_widget.addItem(item['name'])
    
    def _tab_changed(self):
        self.my_keys_list_widget.setCurrentItem(None)
        self.contacts_list_widget.setCurrentItem(None)
        self._update_details_view()

    def _update_details_view(self):
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index == 0:
            list_widget, data_list, key_type = self.my_keys_list_widget, self.keyring_data['my_key_pairs'], "Key Pair"
        else:
            list_widget, data_list, key_type = self.contacts_list_widget, self.keyring_data['contact_public_keys'], "Public Key"

        idx = list_widget.currentRow()
        if idx < 0:
            self.details_name.setText("Name: -")
            self.details_type.setText("Type: -")
            self.key_view.clear()
            return

        key_info = data_list[idx]
        self.details_name.setText(f"Name: {key_info['name']}")
        self.details_type.setText(f"Type: {key_type}")
        self.key_view.setText(key_info['public_key'])

    def _add_contact_key(self):
        dialog = AddPublicKeyDialog(self)
        name, content = dialog.get_data()
        if name and content:
            new_key = {"name": name, "public_key": content}
            self.keyring_data['contact_public_keys'].append(new_key)
            self.save_callback(self.keyring_data)
            self._populate_key_lists()
            QMessageBox.information(None, "Success", "Contact's public key added.")

    def _generate_new_pair(self):
        dialog = GeneratePairDialog(self)
        name, key_size, passphrase = dialog.get_data()
        if name:
            try:
                private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
                public_key = private_key.public_key()
                encryption = (serialization.BestAvailableEncryption(passphrase.encode()) if passphrase else serialization.NoEncryption())
                private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=encryption)
                public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
                
                new_pair = {"name": name, "public_key": public_pem.decode('utf-8'), "private_key": private_pem.decode('utf-8')}
                self.keyring_data['my_key_pairs'].append(new_pair)
                self.save_callback(self.keyring_data)
                self._populate_key_lists()
                QMessageBox.information(None, "Success", f"New {key_size}-bit key pair generated.")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to generate key: {e}")

    def _import_my_pair(self):
        dialog = ImportPairDialog(self)
        name, private_key_content, passphrase = dialog.get_data()
        if name:
            try:
                private_key = serialization.load_pem_private_key(private_key_content, password=passphrase.encode() if passphrase else None)
                public_key = private_key.public_key()
                public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
                
                new_pair = {"name": name, "public_key": public_pem.decode('utf-8'), "private_key": private_key_content.decode('utf-8')}
                self.keyring_data['my_key_pairs'].append(new_pair)
                self.save_callback(self.keyring_data)
                self._populate_key_lists()
                QMessageBox.information(None, "Success", "Key pair imported successfully.")
            except (ValueError, TypeError) as e:
                QMessageBox.critical(None, "Import Error", 
                                     "Failed to load private key. It might be corrupted, or the passphrase is wrong.\n\n"
                                     f"Error: {e}")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"An unexpected error occurred: {e}")

    def _export_key(self):
        current_tab_index = self.tab_widget.currentIndex()
        list_widget = self.my_keys_list_widget if current_tab_index == 0 else self.contacts_list_widget
        idx = list_widget.currentRow()
        if idx < 0:
            QMessageBox.warning(None, "Selection Error", "Please select a key to export.")
            return

        key_info = (self.keyring_data['my_key_pairs'][idx] if current_tab_index == 0 else self.keyring_data['contact_public_keys'][idx])

        if current_tab_index == 0:
            item, ok = QInputDialog.getItem(self, "Export Key", "Which key do you want to export?", ["Public Key", "Private Key"], 0, False)
            if not ok: return
            content = key_info['public_key'] if item == "Public Key" else key_info['private_key']
            default_name = f"{key_info['name'].replace(' ', '_')}_{item.split(' ')[0].lower()}.pem"
        else:
            content = key_info['public_key']
            default_name = f"{key_info['name'].replace(' ', '_')}_public.pub"

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Key As...", default_name, "PEM/PUB Files (*.pem *.pub)")
        if file_path:
            with open(file_path, 'w') as f:
                f.write(content)
            QMessageBox.information(self, "Success", f"Key exported successfully.")

    def _delete_key(self):
        current_tab_index = self.tab_widget.currentIndex()
        list_widget = self.my_keys_list_widget if current_tab_index == 0 else self.contacts_list_widget
        idx = list_widget.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a key to delete.")
            return

        data_list = (self.keyring_data['my_key_pairs'] if current_tab_index == 0 else self.keyring_data['contact_public_keys'])
        key_name = data_list[idx]['name']
        
        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete '{key_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            data_list.pop(idx)
            self.save_callback(self.keyring_data)
            self._populate_key_lists()
            self._update_details_view()