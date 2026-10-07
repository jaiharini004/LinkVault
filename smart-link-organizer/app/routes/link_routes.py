from flask import Blueprint, request, jsonify, redirect
from sqlalchemy import or_
from app.services.metadata_service import scrape_url_metadata
from app.services.short_url_service import create_short_url, get_short_url_response_ui_tokens, record_click_event
from app.services.link_service import search_links, normalize_url
from app.services.validation_service import is_ssrf_safe, sanitize_search_query
from app.models.link import Link, Category
from app.models.short_url import ShortURL

link_bp = Blueprint('link_routes', __name__)

@link_bp.route('/api/links/preview', methods=['POST'])
def preview_link():
    """
    Exposes an API endpoint for live frontend preview cards.
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"success": False, "message": "URL field is required"}), 400
        
    url = data['url']
    
    is_safe, error_payload = is_ssrf_safe(url)
    if not is_safe:
        return jsonify(error_payload), 400
        
    # Synchronously fetch metadata (with fail-safe 2.5s timeout)
    metadata = scrape_url_metadata(url)
    
    return jsonify(metadata), 200

@link_bp.route('/api/links/<int:link_id>/shorten', methods=['POST'])
def shorten_link(link_id):
    """
    Exposes the endpoint to generate or retrieve a short URL for any saved link.
    """
    data = request.get_json() or {}
    custom_alias = data.get('custom_alias')
    
    link = Link.query.get(link_id)
    if not link:
        return jsonify({
            "status": "error",
            "message": "Link not found.",
            "ui_tokens": get_short_url_response_ui_tokens(False)
        }), 404

    try:
        short_entry = create_short_url(link_id, custom_alias)
        return jsonify({
            "status": "success",
            "short_code": short_entry.short_code,
            "short_url": f"{request.host_url}r/{short_entry.short_code}",
            "original_url": link.original_url,
            "clicks_count": short_entry.clicks_count,
            "ui_tokens": get_short_url_response_ui_tokens(True)
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "ui_tokens": get_short_url_response_ui_tokens(False)
        }), 400

@link_bp.route('/r/<short_code>', methods=['GET'])
def redirect_short_url(short_code):
    """
    Looks up short codes or custom aliases, atomically increments click counters,
    and issues an HTTP 302 temporary redirect to the destination URL.
    """
    short_entry = ShortURL.query.filter(
        (ShortURL.short_code == short_code) | (ShortURL.custom_alias == short_code)
    ).first()

    if not short_entry or not short_entry.link:
        return jsonify({
            "status": "error",
            "message": "Short URL not found.",
            "ui_tokens": {
                "font_family": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
                "text_color": "#1E293B",
                "badge_bg": "#FEE2E2",
                "badge_text": "#B91C1C"
            }
        }), 404
        
    record_click_event(short_entry.id)
    return redirect(short_entry.link.original_url, code=302)

@link_bp.route('/api/links/<int:link_id>/analytics', methods=['GET'])
def get_link_analytics(link_id):
    """
    Expose a lightweight endpoint to retrieve click statistics.
    """
    short_entry = ShortURL.query.filter_by(link_id=link_id).first()
    
    if not short_entry:
        return jsonify({
            "status": "error",
            "message": "Analytics not found for this link.",
        }), 404
        
    return jsonify({
        "link_id": link_id,
        "short_code": short_entry.short_code,
        "short_url": f"{request.host_url}r/{short_entry.short_code}",
        "total_clicks": short_entry.clicks_count,
        "created_at": short_entry.created_at.isoformat() + "Z" if short_entry.created_at else None,
        "ui_tokens": {
            "font_family": "Segoe UI",
            "metric_color": "#2563EB"
        }
    }), 200

@link_bp.route('/api/links/check-duplicate', methods=['POST'])
def check_duplicate():
    """
    Accepts a raw URL and performs a normalized SHA-256 hash lookup against the
    indexed normalized_hash column to detect pre-existing duplicate records.

    Returns structured card data for the frontend duplicate resolution modal
    along with design system UI tokens for consistent visual rendering.

    Request body: { "url": "<raw_url_string>" }

    Response (duplicate found):
        200 OK — { "is_duplicate": true, "existing_link": { ... }, "ui_tokens": { ... } }

    Response (no duplicate):
        200 OK — { "is_duplicate": false, "normalized_url": "...", "normalized_hash": "..." }
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"success": False, "message": "URL field is required"}), 400

    raw_url = data.get('url', '').strip()
    if not raw_url:
        return jsonify({"success": False, "message": "URL must not be blank"}), 400

    try:
        normalized_url, normalized_hash = normalize_url(raw_url)
    except Exception:
        return jsonify({"success": False, "message": "Invalid or malformed URL"}), 400

    existing = Link.query.filter_by(normalized_hash=normalized_hash).first()

    ui_tokens = {
        "font_family": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif",
        "card_border": "#CBD5E1",
        "modal_header_color": "#1E3A8A",
        "warning_border": "#B91C1C",
        "warning_bg": "#FEE2E2",
        "warning_text": "#B91C1C"
    }

    if existing:
        return jsonify({
            "is_duplicate": True,
            "existing_link": {
                "id": existing.id,
                "title": existing.title,
                "original_url": existing.original_url,
                "source": existing.source,
                "health_status": existing.health_status,
                "created_at": existing.created_at.isoformat() + "Z" if existing.created_at else None
            },
            "ui_tokens": ui_tokens
        }), 200

    return jsonify({
        "is_duplicate": False,
        "normalized_url": normalized_url,
        "normalized_hash": normalized_hash
    }), 200


@link_bp.route("/api/links/search", methods=["GET"])
def search_links():
    """
    Executes dynamic multi-criteria search filtering by q, category, source, health, and inbox.
    """
    q_term = request.args.get("q", "").strip()
    category_name = request.args.get("category", "").strip()
    source = request.args.get("source", "").strip()
    health = request.args.get("health", "").strip()
    inbox_param = request.args.get("inbox", "").strip().lower()
    
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)

    query = Link.query

    if q_term:
        search_pattern = f"%{q_term}%"
        query = query.filter(
            or_(
                Link.title.ilike(search_pattern),
                Link.original_url.ilike(search_pattern),
                Link.metadata_description.ilike(search_pattern),
                Link.context.ilike(search_pattern)
            )
        )

    if category_name:
        category = Category.query.filter_by(name=category_name).first()
        if category:
            query = query.filter(Link.category_id == category.id)
        else:
            # If category doesn't exist, return empty results
            query = query.filter(Link.id == -1)

    if source:
        query = query.filter(Link.source == source)

    if health:
        query = query.filter(Link.health_status == health)

    if inbox_param in ["true", "1"]:
        query = query.filter(Link.is_inbox == True)
    elif inbox_param in ["false", "0"]:
        query = query.filter(Link.is_inbox == False)

    pagination = query.order_by(Link.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        "success": True,
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
        "results": [link.to_dict() for link in pagination.items],
        "ui_tokens": {
            "font_family": "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
            "primary_color": "#1E3A8A",
            "secondary_color": "#2563EB",
            "bg_main": "#F8FAFC",
            "card_bg": "#FFFFFF",
            "border_color": "#CBD5E1",
            "text_dark": "#1E293B",
            "text_body": "#334155",
            "text_muted": "#64748B"
        }
    }), 200
