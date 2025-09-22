import os
import json
import base64
from PyQt6.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
                             QMessageBox, QApplication)
from PyQt6.QtCore import pyqtSignal
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SALT_SIZE = 16 
ITERATIONS = 390000 
HASH_ALGORITHM = hashes.SHA256()
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')
KEYRING_FILE = os.path.join(APP_DIR, 'keyring.json.enc') 
KEYRING_SALT_SIZE = 16


def hash_password(password, salt):

    kdf = PBKDF2HMAC(
        algorithm=HASH_ALGORITHM,
        length=32,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))

def save_config(password):
    salt = os.urandom(SALT_SIZE)
    password_hash = hash_password(password, salt)
    
    keyring_salt = os.urandom(KEYRING_SALT_SIZE)
    
    config_data = {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'password_hash': base64.b64encode(password_hash).decode('utf-8'),
        'keyring_salt': base64.b64encode(keyring_salt).decode('utf-8')
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)
         
def derive_keyring_key(password, keyring_salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32, # AES-256
        salt=keyring_salt,
        iterations=ITERATIONS, 
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))

def load_and_decrypt_keyring(keyring_key):
    try:
        with open(KEYRING_FILE, 'rb') as f:
            nonce = f.read(12) # Nonce برای AES-GCM
            ciphertext = f.read()
        
        aesgcm = AESGCM(keyring_key)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_data.decode('utf-8'))
    except FileNotFoundError:
        return {"my_key_pairs": [], "contact_public_keys": []}
    except Exception as e:
        print(f"Keyring decryption failed: {e}")
        raise ValueError("Could not decrypt keyring. Master password may be incorrect.")

def encrypt_and_save_keyring(keyring_key, keyring_data):
    keyring_dir = os.path.dirname(KEYRING_FILE)
    if not os.path.exists(keyring_dir):
            os.makedirs(keyring_dir)
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(keyring_key)
    
    json_bytes = json.dumps(keyring_data, indent=4).encode('utf-8')
    
    encrypted_data = aesgcm.encrypt(nonce, json_bytes, None)
    
    with open(KEYRING_FILE, 'wb') as f:
        f.write(nonce + encrypted_data)
def verify_password(password):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        
        salt = base64.b64decode(config_data['salt'])
        stored_hash = base64.b64decode(config_data['password_hash'])
        
        kdf = PBKDF2HMAC(
            algorithm=HASH_ALGORITHM,
            length=32,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend()
        )
        kdf.verify(password.encode('utf-8'), stored_hash)
        return True
    except (FileNotFoundError, json.JSONDecodeError, InvalidKey, KeyError):
        return False


class SetupWindow(QWidget):
    setup_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Setup Initial Password')
        self.setGeometry(400, 400, 300, 150)
        layout = QVBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter a new password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm the password")
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
        self.password_input.setPlaceholderText("Enter your password")
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