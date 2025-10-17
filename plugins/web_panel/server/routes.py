from flask import Blueprint, jsonify


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return '<h1>Web Panel is Running!</h1>'


@main_bp.route('/api/status')
def status():
    return jsonify({'status': 'ok', 'message': 'Server is running.'})
