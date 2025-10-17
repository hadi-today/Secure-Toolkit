from flask import Blueprint, jsonify, request

from .database import ListItem, ManagedList, db
from .web_auth import token_required


items_bp = Blueprint('items', __name__)


@items_bp.route('/<int:list_id>', methods=['POST'])
@token_required
def add_item_to_list(list_id):
    ManagedList.query.get_or_404(list_id)

    data = request.get_json()
    if not data or 'key' not in data:
        return jsonify({'error': 'Key is required'}), 400

    new_item = ListItem(
        list_id=list_id,
        key=data['key'],
        value=data.get('value'),
        is_enabled=data.get('is_enabled', True),
    )
    db.session.add(new_item)
    db.session.commit()

    return jsonify(new_item.to_dict()), 201


@items_bp.route('/<int:item_id>', methods=['PUT'])
@token_required
def update_item(item_id):
    item = ListItem.query.get_or_404(item_id)
    data = request.get_json()

    item.key = data.get('key', item.key)
    item.value = data.get('value', item.value)
    item.is_enabled = data.get('is_enabled', item.is_enabled)

    db.session.commit()
    return jsonify(item.to_dict())


@items_bp.route('/<int:item_id>', methods=['DELETE'])
@token_required
def delete_item(item_id):
    item = ListItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return '', 204
