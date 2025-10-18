import base64
import datetime
from functools import wraps

import jwt
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app, jsonify, request, g


ITERATIONS = 390000
KEY_LENGTH = 32
HASH_ALGORITHM = hashes.SHA256()


def verify_password_with_hash(
    password_attempt,
    stored_hash_b64,
    salt_b64,
    iterations=ITERATIONS,
    key_length=KEY_LENGTH,
):
    """Verify a password attempt against a stored hash and salt."""

    try:
        stored_hash = base64.b64decode(stored_hash_b64)
        salt = base64.b64decode(salt_b64)

        kdf = PBKDF2HMAC(
            algorithm=HASH_ALGORITHM,
            length=key_length,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        kdf.verify(password_attempt.encode('utf-8'), stored_hash)
        return True
    except InvalidKey:
        return False
    except Exception:
        return False


def _normalize_token_value(token_candidate):
    if token_candidate is None:
        return None

    if isinstance(token_candidate, bytes):
        try:
            token_candidate = token_candidate.decode('utf-8')
        except UnicodeDecodeError:
            return None

    if isinstance(token_candidate, str):
        cleaned = token_candidate.strip()
        if cleaned.startswith("b'") and cleaned.endswith("'") and len(cleaned) > 3:
            return cleaned[2:-1]
        if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
            return cleaned[1:-1]
        return cleaned

    return None


def encode_auth_token():
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            'iat': datetime.datetime.utcnow(),
            'sub': 'admin',
        }
        token = jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256',
        )
        return _normalize_token_value(token)
    except Exception as error:
        return error


def token_required(view_function):
    @wraps(view_function)
    def decorated(*args, **kwargs):
        token = None

        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = _normalize_token_value(parts[1])

        if not token:
            token = _normalize_token_value(request.args.get('token'))

        if not token:
            token = _normalize_token_value(request.cookies.get('authToken'))

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            jwt.decode(
                token,
                current_app.config.get('SECRET_KEY'),
                algorithms=['HS256'],
            )
            g.webpanel_token = token
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            sessions = current_app.config.get('KEYRING_SESSIONS')
            if sessions and token:
                sessions.pop(token, None)
            return jsonify({'message': 'Invalid Token!'}), 401

        return view_function(*args, **kwargs)

    return decorated
