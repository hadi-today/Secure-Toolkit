from flask import Blueprint, current_app, jsonify

from .web_auth import token_required


core_bp = Blueprint('core', __name__)


@core_bp.route('/registered_plugins', methods=['GET'])
@token_required
def get_registered_plugins():
    """Return metadata for all registered web plugins."""

    plugins_info = current_app.config.get('DISCOVERED_PLUGINS_INFO', [])
    return jsonify(plugins_info)


@core_bp.route('/gadgets', methods=['GET'])
@token_required
def get_registered_gadgets():
    """Return the catalog of dashboard gadgets provided by plugins."""

    gadgets = current_app.config.get('GADGETS_CATALOG', [])
    return jsonify(gadgets)

