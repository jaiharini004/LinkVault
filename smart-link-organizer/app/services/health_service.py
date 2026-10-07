import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
from app import db
from app.models.link import Link

logger = logging.getLogger(__name__)

EXECUTOR = ThreadPoolExecutor(max_workers=10)

HEALTH_TOKENS = {
    "Healthy": {
        "text_color": "#15803D",
        "bg_color": "#DCFCE7",
        "label": "Healthy"
    },
    "Broken": {
        "text_color": "#B91C1C",
        "bg_color": "#FEE2E2",
        "label": "Broken"
    },
    "Restricted": {
        "text_color": "#B45309",
        "bg_color": "#FEF3C7",
        "label": "Restricted"
    },
    "Timeout/Unreachable": {
        "text_color": "#64748B",
        "bg_color": "#F1F5F9",
        "label": "Timeout/Unreachable"
    }
}


def evaluate_http_status(url: str) -> tuple:
    """
    Executes lightweight HTTP check (HEAD with GET fallback) and returns
    tuple of (health_status_string, status_code_integer).
    """
    headers = {
        "User-Agent": "LinkVault-HealthChecker/1.0 (+https://linkvault.internal)"
    }
    
    try:
        response = requests.head(url, headers=headers, timeout=5.0, allow_redirects=True)
        code = response.status_code

        # Fallback to GET if HEAD method is not allowed
        if code == 405:
            response = requests.get(url, headers=headers, timeout=5.0, stream=True, allow_redirects=True)
            code = response.status_code

        if 200 <= code < 300:
            return "Healthy", code
        elif code == 403:
            return "Restricted", code
        elif code == 404 or code >= 500:
            return "Broken", code
        else:
            return "Broken", code

    except requests.exceptions.Timeout:
        logger.warning("Health check timed out for URL: %s", url)
        return "Timeout/Unreachable", None
    except requests.exceptions.RequestException as err:
        logger.warning("Health check failed for URL %s: %s", url, err)
        return "Timeout/Unreachable", None


def perform_single_health_check(app, link_id: int) -> dict:
    """
    Executes health check for a single link within Flask app context.
    """
    with app.app_context():
        link = Link.query.get(link_id)
        if not link:
            logger.error("Link ID %s not found for health check.", link_id)
            return {}

        status_str, status_code = evaluate_http_status(link.original_url)

        link.health_status = status_str
        link.http_status_code = status_code
        link.last_checked_at = datetime.utcnow()

        db.session.commit()
        
        # Need to re-read values to construct response
        link_id_val = link.id
        health_status_val = link.health_status
        http_status_code_val = link.http_status_code
        last_checked_at_val = link.last_checked_at.isoformat() + "Z" if link.last_checked_at else None

        ui_tokens = dict(HEALTH_TOKENS.get(status_str, HEALTH_TOKENS["Timeout/Unreachable"]))
        ui_tokens["font_family"] = "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif"

        return {
            "link_id": link_id_val,
            "health_status": health_status_val,
            "http_status_code": http_status_code_val,
            "last_checked_at": last_checked_at_val,
            "ui_tokens": ui_tokens
        }


def run_bulk_health_check_job(app):
    """
    Asynchronous background job executing health checks across all saved links.
    """
    with app.app_context():
        links = Link.query.all()
        link_ids = [link.id for link in links]

    logger.info("Starting bulk health check job for %s links.", len(link_ids))
    
    for link_id in link_ids:
        EXECUTOR.submit(perform_single_health_check, app, link_id)
    
    return len(link_ids)
