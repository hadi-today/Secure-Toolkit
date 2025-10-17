import os
import json
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALT_SIZE = 16
ITERATIONS = 390000
KEY_LENGTH = 32
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
        backend=default_backend(),
    )
    return kdf.derive(password.encode('utf-8'))


def save_config(password):
    salt = os.urandom(SALT_SIZE)
    password_hash = hash_password(password, salt)
    keyring_salt = os.urandom(KEYRING_SALT_SIZE)
    config_data = {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'password_hash': base64.b64encode(password_hash).decode('utf-8'),
        'keyring_salt': base64.b64encode(keyring_salt).decode('utf-8'),
    }
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config_data, file)


def derive_keyring_key(password, keyring_salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=keyring_salt,
        iterations=ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(password.encode('utf-8'))


def load_and_decrypt_keyring(keyring_key):
    try:
        with open(KEYRING_FILE, 'rb') as file:
            nonce = file.read(12)
            ciphertext = file.read()
        aesgcm = AESGCM(keyring_key)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_data.decode('utf-8'))
    except FileNotFoundError:
        return {"my_key_pairs": [], "contact_public_keys": []}
    except Exception as error:
        print(f"Keyring decryption failed: {error}")
        raise ValueError("Could not decrypt keyring. Master password may be incorrect.")


def encrypt_and_save_keyring(keyring_key, keyring_data):
    keyring_dir = os.path.dirname(KEYRING_FILE)
    if not os.path.exists(keyring_dir):
        os.makedirs(keyring_dir)
    nonce = os.urandom(12)
    aesgcm = AESGCM(keyring_key)
    json_bytes = json.dumps(keyring_data, indent=4).encode('utf-8')
    encrypted_data = aesgcm.encrypt(nonce, json_bytes, None)
    with open(KEYRING_FILE, 'wb') as file:
        file.write(nonce + encrypted_data)


def verify_password(password):
    try:
        with open(CONFIG_FILE, 'r') as file:
            config_data = json.load(file)
        salt = base64.b64decode(config_data['salt'])
        stored_hash = base64.b64decode(config_data['password_hash'])
        kdf = PBKDF2HMAC(
            algorithm=HASH_ALGORITHM,
            length=32,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend(),
        )
        kdf.verify(password.encode('utf-8'), stored_hash)
        return True
    except (FileNotFoundError, json.JSONDecodeError, InvalidKey, KeyError):
        return False