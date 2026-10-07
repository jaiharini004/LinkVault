from flask import Blueprint, jsonify, current_app
from app.services.health_service import perform_single_health_check, run_bulk_health_check_job

health_bp = Blueprint('health_routes', __name__)

@health_bp.route('/api/links/<int:link_id>/health', methods=['POST'])
def check_single_link_health(link_id):
    """
    Synchronously rechecks a single link and returns updated health tokens.
    """
    # Pass the actual app object to the background worker/function
    app = current_app._get_current_object()
    result = perform_single_health_check(app, link_id)
    
    if not result:
        return jsonify({"success": False, "message": "Link not found"}), 404
        
    return jsonify({
        "success": True,
        "link_id": result["link_id"],
        "health_status": result["health_status"],
        "http_status_code": result["http_status_code"],
        "last_checked_at": result["last_checked_at"],
        "ui_tokens": result["ui_tokens"]
    }), 200

@health_bp.route('/api/links/health-check-all', methods=['POST'])
def check_all_links_health():
    """
    Triggers asynchronous background bulk check across all stored links via ThreadPoolExecutor.
    """
    app = current_app._get_current_object()
    queued_count = run_bulk_health_check_job(app)
    
    return jsonify({
        "success": True,
        "message": "Bulk health check job initiated in background.",
        "total_queued": queued_count
    }), 202
