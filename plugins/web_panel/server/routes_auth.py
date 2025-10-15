# plugins/web_panel/server/routes_auth.py

from flask import Blueprint, request, jsonify, current_app

from .web_auth import encode_auth_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'error': 'Password is required'}), 400
    
    password = data['password']
    
    verifier = current_app.config.get('PASSWORD_VERIFIER')
    
    if not verifier:
        return jsonify({'error': 'Password verifier is not configured'}), 500

    if verifier(password):
        token = encode_auth_token()
        if not isinstance(token, str) or not token:
            current_app.logger.error('Failed to generate auth token for login request')
            return jsonify({'error': 'Unable to generate auth token'}), 500

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
    else:
        return jsonify({'error': 'Invalid credentials'}), 401