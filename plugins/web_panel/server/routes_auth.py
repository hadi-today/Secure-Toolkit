from flask import Blueprint, current_app, jsonify, request

import base64
import json

from auth_crypto import CONFIG_FILE, derive_keyring_key

from .web_auth import encode_auth_token


auth_bp = Blueprint('auth', __name__)

def _store_keyring_context(password):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        current_app.logger.error('Failed to read configuration for keyring access: %s', error)
        return

    keyring_salt_b64 = config.get('keyring_salt')
    if not keyring_salt_b64:
        current_app.logger.warning('Keyring salt missing from configuration file.')
        return

    try:
        keyring_salt = base64.b64decode(keyring_salt_b64)
        keyring_key = derive_keyring_key(password, keyring_salt)
    except Exception as error:  # pragma: no cover - logged for diagnostics
        current_app.logger.error('Failed to derive keyring encryption key: %s', error)
        return

    current_app.config['KEYRING_CONTEXT'] = {
        'key': keyring_key,
        'salt': keyring_salt,
    }


def _derive_keyring_context(password):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        current_app.logger.error('Failed to read configuration for keyring access: %s', error)
        return None

    keyring_salt_b64 = config.get('keyring_salt')
    if not keyring_salt_b64:
        current_app.logger.warning('Keyring salt missing from configuration file.')
        return None

    try:
        keyring_salt = base64.b64decode(keyring_salt_b64)
        keyring_key = derive_keyring_key(password, keyring_salt)
    except Exception as error:  # pragma: no cover - logged for diagnostics
        current_app.logger.error('Failed to derive keyring encryption key: %s', error)
        return None

    return {
        'key': keyring_key,
        'salt': keyring_salt,
    }


def _derive_keyring_context(password):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        current_app.logger.error('Failed to read configuration for keyring access: %s', error)
        return None

    keyring_salt_b64 = config.get('keyring_salt')
    if not keyring_salt_b64:
        current_app.logger.warning('Keyring salt missing from configuration file.')
        return None

    try:
        keyring_salt = base64.b64decode(keyring_salt_b64)
        keyring_key = derive_keyring_key(password, keyring_salt)
    except Exception as error:  # pragma: no cover - logged for diagnostics
        current_app.logger.error('Failed to derive keyring encryption key: %s', error)
        return None

    return {
        'key': keyring_key,
        'salt': keyring_salt,
    }


def _derive_keyring_context(password):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        current_app.logger.error('Failed to read configuration for keyring access: %s', error)
        return None

    keyring_salt_b64 = config.get('keyring_salt')
    if not keyring_salt_b64:
        current_app.logger.warning('Keyring salt missing from configuration file.')
        return None

    try:
        keyring_salt = base64.b64decode(keyring_salt_b64)
        keyring_key = derive_keyring_key(password, keyring_salt)
    except Exception as error:  # pragma: no cover - logged for diagnostics
        current_app.logger.error('Failed to derive keyring encryption key: %s', error)
        return None

    return {
        'key': keyring_key,
        'salt': keyring_salt,
    }


def _derive_keyring_context(password):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        current_app.logger.error('Failed to read configuration for keyring access: %s', error)
        return None

    keyring_salt_b64 = config.get('keyring_salt')
    if not keyring_salt_b64:
        current_app.logger.warning('Keyring salt missing from configuration file.')
        return None

    try:
        keyring_salt = base64.b64decode(keyring_salt_b64)
        keyring_key = derive_keyring_key(password, keyring_salt)
    except Exception as error:  # pragma: no cover - logged for diagnostics
        current_app.logger.error('Failed to derive keyring encryption key: %s', error)
        return None

    return {
        'key': keyring_key,
        'salt': keyring_salt,
    }


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'error': 'Password is required'}), 400

    verifier = current_app.config.get('PASSWORD_VERIFIER')

    if not verifier:
        return jsonify({'error': 'Password verifier is not configured'}), 500

    if verifier(data['password']):
        context = _derive_keyring_context(data['password'])
        if context is None:
            return jsonify({'error': 'Unable to unlock encrypted keyring.'}), 500
        token = encode_auth_token()
        if not isinstance(token, str) or not token:
            current_app.logger.error('Failed to generate auth token for login request')
            return jsonify({'error': 'Unable to generate auth token'}), 500

        keyring_sessions = current_app.config.setdefault('KEYRING_SESSIONS', {})
        keyring_sessions[token] = dict(context)
        if len(keyring_sessions) > 25:
            oldest_token = next(iter(keyring_sessions))
            if oldest_token != token:
                keyring_sessions.pop(oldest_token, None)
        current_app.config['KEYRING_CONTEXT'] = dict(context)
        current_app.config['KEYRING_ACTIVE_KEY'] = context.get('key')

        response = jsonify({'token': token})
        response.set_cookie(
            'authToken',
            token,
            max_age=24 * 3600,
            secure=False,
            httponly=False,
            samesite='Lax',
            path='/',
        )
        return response

    return jsonify({'error': 'Invalid credentials'}), 401
