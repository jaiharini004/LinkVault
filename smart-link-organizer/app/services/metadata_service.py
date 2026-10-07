import logging
import urllib.parse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DOMAIN_CATEGORY_MAP = {
    "github.com": "Development",
    "gitlab.com": "Development",
    "bitbucket.org": "Development",
    "stackoverflow.com": "Development",
    "drive.google.com": "Documents",
    "docs.google.com": "Documents",
    "notion.so": "Documents",
    "dropbox.com": "Documents",
    "youtube.com": "Media",
    "youtu.be": "Media",
    "vimeo.com": "Media",
    "spotify.com": "Media",
    "meet.google.com": "Meetings",
    "zoom.us": "Meetings",
    "teams.microsoft.com": "Meetings",
    "figma.com": "Design",
    "dribbble.com": "Design",
    "behance.net": "Design",
}

def suggest_category_from_url(url: str) -> str:
    """
    Parses the domain using standard urllib.parse and maps platform domain
    patterns to standard categories. Supports exact domain matches as well
    as subdomain matching (e.g., api.github.com maps to Development).
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.netloc:
            parsed_url = urllib.parse.urlparse("http://" + url)

        domain = parsed_url.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # Direct match first for O(1) lookup on common domains
        if domain in DOMAIN_CATEGORY_MAP:
            return DOMAIN_CATEGORY_MAP[domain]

        # Subdomain matching: e.g., api.github.com -> github.com -> Development
        for mapped_domain, category in DOMAIN_CATEGORY_MAP.items():
            if domain.endswith("." + mapped_domain):
                return category

    except Exception as err:
        logger.warning("Failed to parse category from URL: %s", err)

    return "General"

def _get_ui_tokens(status_code: int = None, error: bool = False) -> dict:
    """
    Returns exact CSS class name hints and exact color codes matching the project's visual system.
    """
    base_tokens = {
        "font_family": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
        "card_border": "#CBD5E1"
    }
    
    if error or status_code is None:
        base_tokens.update({
            "badge_color": "#64748B",
            "badge_bg": "#F1F5F9",
            "status_label": "Unreachable",
            "status_class": "badge-unreachable"
        })
    elif 200 <= status_code < 300:
        base_tokens.update({
            "badge_color": "#15803D",
            "badge_bg": "#DCFCE7",
            "status_label": "Healthy",
            "status_class": "badge-healthy"
        })
    elif status_code in (401, 403):
        base_tokens.update({
            "badge_color": "#B45309",
            "badge_bg": "#FEF3C7",
            "status_label": "Restricted",
            "status_class": "badge-restricted"
        })
    else:
        base_tokens.update({
            "badge_color": "#B91C1C",
            "badge_bg": "#FEE2E2",
            "status_label": "Broken",
            "status_class": "badge-broken"
        })
        
    return base_tokens

def scrape_url_metadata(url: str) -> dict:
    """
    Uses requests and BeautifulSoup4 to extract Page Title, Description, and Favicon URL.
    Enforces a strict 2.5-second timeout on requests.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    result = {
        "url": url,
        "suggested_category": suggest_category_from_url(url),
        "title": "",
        "description": "",
        "favicon_url": "",
        "scrape_success": False,
        "ui_tokens": _get_ui_tokens(error=True)
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Fail-Safe Requirement: strict 2.5-second timeout
        response = requests.get(url, timeout=2.5, headers=headers)
        
        # Update tokens based on real HTTP status
        result["ui_tokens"] = _get_ui_tokens(status_code=response.status_code)
        
        # Only parse HTML if successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract Title (<title> or og:title)
            og_title = soup.find('meta', property='og:title')
            title_tag = soup.find('title')
            if og_title and og_title.get('content'):
                result['title'] = og_title['content'].strip()
            elif title_tag and title_tag.string:
                result['title'] = title_tag.string.strip()
                
            # Extract Description (<meta name="description"> or og:description)
            og_desc = soup.find('meta', property='og:description')
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if og_desc and og_desc.get('content'):
                result['description'] = og_desc['content'].strip()
            elif desc_tag and desc_tag.get('content'):
                result['description'] = desc_tag['content'].strip()
                
            # Extract Favicon (<link rel="icon"> or default)
            icon_link = soup.find('link', rel=lambda x: x and 'icon' in x.lower())
            parsed_url = urllib.parse.urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            if icon_link and icon_link.get('href'):
                href = icon_link['href']
                if href.startswith('http'):
                    result['favicon_url'] = href
                elif href.startswith('//'):
                    result['favicon_url'] = 'https:' + href
                else:
                    result['favicon_url'] = urllib.parse.urljoin(base_url, href)
            else:
                result['favicon_url'] = f"{base_url}/favicon.ico"

            result['scrape_success'] = True
                
    except (requests.exceptions.RequestException, Exception) as exc:
        # On network error, timeout, or HTTP failure, return empty strings rather than raising exceptions
        logger.info("Metadata scraping timed out or failed for %s: %s", url, exc)
        result["ui_tokens"] = _get_ui_tokens(error=True)
        result["scrape_success"] = False
    return result
