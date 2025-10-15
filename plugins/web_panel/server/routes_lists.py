# plugins/web_panel/server/routes_lists.py

from flask import Blueprint, jsonify, request
from .database import db
from .database import ManagedList, ListItem
from .web_auth import token_required  

lists_bp = Blueprint('lists', __name__)

@lists_bp.route('/', methods=['POST'])
@token_required  
def create_list():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    new_list = ManagedList(name=data['name'], description=data.get('description'))
    db.session.add(new_list)
    db.session.commit()
    
    return jsonify(new_list.to_dict()), 201

@lists_bp.route('/', methods=['GET'])
@token_required  
def get_all_lists():
    lists = ManagedList.query.all()
    return jsonify([l.to_dict() for l in lists])

@lists_bp.route('/<int:list_id>', methods=['GET'])
@token_required 
def get_list_with_items(list_id):
    managed_list = ManagedList.query.get_or_404(list_id)
    items = ListItem.query.filter_by(list_id=list_id).all()
    
    list_data = managed_list.to_dict()
    list_data['items'] = [item.to_dict() for item in items]
    
    return jsonify(list_data)

@lists_bp.route('/<int:list_id>', methods=['DELETE'])
@token_required  
def delete_list(list_id):
    managed_list = ManagedList.query.get_or_404(list_id)
    db.session.delete(managed_list)
    db.session.commit()
    return '', 204