import hashlib
import math
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import or_, desc
from app.extensions import db
from app.models.link import Link


# Tracking and session parameters that carry no functional URL meaning.
# These are stripped before normalization to prevent false-negative duplicate checks.
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term',
    'utm_content', 'fbclid', 'gclid', 'msclkid', 'mc_cid',
    'mc_eid', 'si', 'ref'
}


def normalize_url(raw_url: str) -> tuple:
    """
    Cleans a raw URL by removing tracking query parameters, lowercasing
    the scheme and host, stripping default ports and trailing slashes,
    and sorting remaining query parameters alphabetically.

    Returns a tuple of (normalized_url_string, sha256_hash_string).
    The hash enables O(1) indexed duplicate detection against the database.
    """
    parsed = urlparse(raw_url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports to avoid treating http://x.com:80 and http://x.com as distinct URLs
    if netloc.endswith(':80') and scheme == 'http':
        netloc = netloc[:-3]
    elif netloc.endswith(':443') and scheme == 'https':
        netloc = netloc[:-4]

    # Remove trailing slash from path to treat /path/ and /path as identical
    path = parsed.path.rstrip('/')

    # Filter out known tracking parameters and sort the rest for canonical ordering
    query_dict = parse_qs(parsed.query, keep_blank_values=False)
    filtered_params = []
    for key in sorted(query_dict.keys()):
        if key.lower() not in TRACKING_PARAMS:
            for val in query_dict[key]:
                filtered_params.append((key, val))

    clean_query = urlencode(filtered_params)

    # Reconstruct the normalized URL, discarding fragment anchors (#section)
    normalized_url = urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        clean_query,
        ''
    ))

    normalized_hash = hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
    return normalized_url, normalized_hash

def get_health_ui_tokens(health_status: str) -> dict:
    base = {
        "font_family": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
        "card_border": "#CBD5E1"
    }
    status = (health_status or "").lower()
    
    if status == "healthy":
        base.update({"badge_text_color": "#15803D", "badge_bg_color": "#DCFCE7"})
    elif status == "broken":
        base.update({"badge_text_color": "#B91C1C", "badge_bg_color": "#FEE2E2"})
    elif status == "restricted":
        base.update({"badge_text_color": "#B45309", "badge_bg_color": "#FEF3C7"})
    else:
        base.update({"badge_text_color": "#64748B", "badge_bg_color": "#F1F5F9"})
        
    return base

def search_links(
    query_term: str = None,
    category_id: int = None,
    source: str = None,
    health_status: str = None,
    is_inbox: bool = None,
    is_favorite: bool = None,
    page: int = 1,
    per_page: int = 12
) -> dict:
    
    query = Link.query
    
    if query_term:
        search_filter = f"%{query_term}%"
        query = query.filter(
            or_(
                Link.title.ilike(search_filter),
                Link.original_url.ilike(search_filter),
                Link.description.ilike(search_filter),
                Link.context.ilike(search_filter),
                Link.metadata_title.ilike(search_filter)
            )
        )
        
    if category_id is not None:
        query = query.filter(Link.category_id == category_id)
        
    if source:
        query = query.filter(Link.source == source)
        
    if health_status:
        query = query.filter(Link.health_status == health_status)
        
    if is_inbox is not None:
        query = query.filter(Link.is_inbox == is_inbox)
        
    if is_favorite is not None:
        query = query.filter(Link.is_favorite == is_favorite)
        
    # Order by created_at DESC
    query = query.order_by(desc(Link.created_at))
    
    # Pagination
    total_results = query.count()
    total_pages = math.ceil(total_results / per_page) if per_page > 0 else 1
    
    if page < 1:
        page = 1
        
    offset = (page - 1) * per_page
    links = query.offset(offset).limit(per_page).all()
    
    results = []
    # Determine base url for short links
    try:
        from flask import request
        host_url = request.host_url if request else "http://localhost:5000/"
    except RuntimeError:
        # If outside of request context (like background tasks)
        host_url = "http://localhost:5000/"
    
    for link in links:
        short_code = link.short_url_entry.short_code if link.short_url_entry else None
        short_url = f"{host_url}r/{short_code}" if short_code else None
        
        results.append({
            "id": link.id,
            "title": link.title,
            "original_url": link.original_url,
            "category_id": link.category_id,
            "category_name": link.category.name if link.category else None,
            "source": link.source,
            "context": link.context,
            "health_status": link.health_status,
            "http_status_code": link.http_status_code,
            "is_inbox": link.is_inbox,
            "short_url": short_url,
            "ui_tokens": get_health_ui_tokens(link.health_status)
        })
        
    filters_applied = {}
    if query_term: filters_applied['q'] = query_term
    if category_id: filters_applied['category_id'] = category_id
    if source: filters_applied['source'] = source
    if health_status: filters_applied['health_status'] = health_status
    if is_inbox is not None: filters_applied['is_inbox'] = is_inbox
    if is_favorite is not None: filters_applied['is_favorite'] = is_favorite
    
    return {
        "status": "success",
        "total_results": total_results,
        "page": page,
        "total_pages": total_pages,
        "filters_applied": filters_applied,
        "results": results
    }
