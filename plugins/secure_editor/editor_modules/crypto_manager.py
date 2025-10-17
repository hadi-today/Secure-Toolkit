import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config

def encrypt_content(plain_text_bytes, rsa_public_key_pem):
    """Encrypts content using Envelope Encryption."""
    # 1. Load the RSA public key
    public_key = serialization.load_pem_public_key(rsa_public_key_pem.encode('utf-8'))
    
    # 2. Generate a fresh, one-time AES key (CEK)
    cek = AESGCM.generate_key(bit_length=config.AES_KEY_SIZE * 8)
    
    # 3. Encrypt (wrap) the CEK with the RSA public key
    wrapped_cek = public_key.encrypt(
        cek,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )
    
    # 4. Encrypt the actual content with the CEK
    aesgcm = AESGCM(cek)
    nonce = os.urandom(config.AES_NONCE_SIZE)
    content_ciphertext = aesgcm.encrypt(nonce, plain_text_bytes, None)
    
    return {
        "content_ciphertext": nonce + content_ciphertext,
        "wrapped_cek": wrapped_cek
    }

def decrypt_content(encrypted_bundle, rsa_private_key_pem, passphrase):
    """Decrypts content from an encrypted bundle."""
    # 1. Load the RSA private key
    private_key = serialization.load_pem_private_key(
        rsa_private_key_pem.encode('utf-8'),
        password=passphrase.encode('utf-8') if passphrase else None
    )
    
    # 2. Decrypt (unwrap) the wrapped CEK to get the original AES key
    cek = private_key.decrypt(
        encrypted_bundle['wrapped_cek'],
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )

    # 3. Decrypt the content with the unwrapped CEK
    nonce = encrypted_bundle['content_ciphertext'][:config.AES_NONCE_SIZE]
    ciphertext = encrypted_bundle['content_ciphertext'][config.AES_NONCE_SIZE:]
    
    aesgcm = AESGCM(cek)
    plain_text_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    
    return plain_text_bytes