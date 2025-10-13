from PyQt6.QtWidgets import (QDialog, QComboBox, QVBoxLayout, QPushButton, 
                             QFormLayout, QInputDialog, QMessageBox, QLineEdit) # <-- اصلاح شده

class SelectKeyDialog(QDialog):
    def __init__(self, key_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Encryption Key")
        self.selected_key = None
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.key_combo = QComboBox()
        self.key_combo.addItems(key_names)
        form_layout.addRow("Choose a key from 'My Key Pairs':", self.key_combo)
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        
        layout.addLayout(form_layout)
        layout.addWidget(ok_button)

    def get_selected_key(self):
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.key_combo.currentText()
        return None

def get_passphrase(parent):
    text, ok = QInputDialog.getText(parent, "Passphrase Required", 
                                    "Enter passphrase for the private key:", 
                                    QLineEdit.EchoMode.Password)
    if ok:
        return text
    return None

def confirm_action(title, message, parent=None):
    reply = QMessageBox.question(parent, title, message, 
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                 QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes