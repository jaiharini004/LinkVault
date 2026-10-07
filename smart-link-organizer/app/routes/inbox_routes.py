from flask import Blueprint, request, jsonify
from app.services.inbox_service import bulk_add_to_inbox, batch_organize_inbox
from app.models.link import Link

inbox_bp = Blueprint('inbox_routes', __name__)

@inbox_bp.route('/api/inbox', methods=['GET'])
def get_inbox():
    """
    Fetch all staged links where is_inbox=True sorted by created_at DESC.
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    query = Link.query.filter_by(is_inbox=True).order_by(Link.created_at.desc())
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        "success": True,
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
        "results": [link.to_dict() for link in pagination.items]
    }), 200

@inbox_bp.route('/api/inbox', methods=['POST'])
def add_to_inbox():
    """
    Bulk store raw URLs directly into inbox staging.
    """
    data = request.get_json()
    if not data or 'urls' not in data or not isinstance(data['urls'], list):
        return jsonify({"success": False, "message": "Invalid payload, expected a JSON object with a 'urls' list"}), 400
        
    created = bulk_add_to_inbox(data['urls'])
    
    return jsonify({
        "success": True,
        "saved_count": len(created),
        "results": created
    }), 201

@inbox_bp.route('/api/inbox/organize', methods=['POST'])
def organize_inbox():
    """
    Batch updates inbox links and moves them out of the inbox.
    """
    data = request.get_json()
    if not data or 'items' not in data or not isinstance(data['items'], list):
        return jsonify({"success": False, "message": "Invalid payload, expected a JSON object with an 'items' list"}), 400
        
    updated_count = batch_organize_inbox(data['items'])
    
    return jsonify({
        "success": True,
        "organized_count": updated_count,
        "message": f"Successfully organized {updated_count} inbox items into vaults."
    }), 200
