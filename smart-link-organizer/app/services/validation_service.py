import re
import html
import urllib.parse
import ipaddress
import socket

def get_error_ui_tokens() -> dict:
    return {
        "font_family": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
        "border_color": "#B91C1C",
        "text_color": "#B91C1C",
        "bg_color": "#FEE2E2"
    }

def format_validation_error(error_code: str, message: str, field: str) -> dict:
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "field": field,
        "ui_tokens": get_error_ui_tokens()
    }

def sanitize_html(text: str) -> str:
    if not text:
        return text
    return html.escape(str(text))

def validate_custom_alias_format(alias: str) -> tuple[bool, dict]:
    if not alias:
        return False, format_validation_error("INVALID_ALIAS", "Alias cannot be empty.", "custom_alias")
    
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', alias):
        return False, format_validation_error(
            "INVALID_ALIAS_FORMAT", 
            "Alias must be 3-20 characters long and contain only letters, numbers, hyphens, or underscores.", 
            "custom_alias"
        )
    return True, {}

def sanitize_search_query(query: str) -> str:
    if not query:
        return query
    # Strip illegal wildcards like % or _ often used in SQL
    sanitized = re.sub(r'[%_]', '', query)
    return sanitize_html(sanitized)

def is_ssrf_safe(url: str) -> tuple[bool, dict]:
    if not url:
        return False, format_validation_error("INVALID_URL", "URL cannot be empty.", "original_url")
        
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False, format_validation_error("INVALID_SCHEME", "Only HTTP and HTTPS are allowed.", "original_url")
            
        hostname = parsed.hostname
        if not hostname:
            return False, format_validation_error("INVALID_URL", "Could not parse hostname.", "original_url")
            
        # Hard block localhost
        if hostname.lower() in ['localhost', '0.0.0.0', '127.0.0.1']:
            return False, format_validation_error("SSRF_PROTECTION_TRIGGERED", "Access to local or private network IP addresses is restricted.", "original_url")
            
        # Check if it's an IP and if it's private
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_unspecified:
                return False, format_validation_error("SSRF_PROTECTION_TRIGGERED", "Access to local or private network IP addresses is restricted.", "original_url")
        except ValueError:
            # Domain string, try DNS resolution
            try:
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_unspecified:
                    return False, format_validation_error("SSRF_PROTECTION_TRIGGERED", "Access to local or private network IP addresses is restricted.", "original_url")
            except socket.gaierror:
                pass # Unresolvable, let normal request handle the 404/timeout
                
        return True, {}
    except Exception as e:
        return False, format_validation_error("URL_PARSE_ERROR", "Failed to parse URL safely.", "original_url")
