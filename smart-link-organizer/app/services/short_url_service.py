import re
import random
from app.extensions import db
from app.models.short_url import ShortURL
from app.models.link import Link

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
RESERVED_KEYWORDS = {'api', 'admin', 'import', 'inbox', 'health', 'static', 'login', 'register'}

def encode_base62(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]
    
    base62 = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        num, rem = divmod(num, base)
        base62.append(BASE62_ALPHABET[rem])
    
    return ''.join(reversed(base62))

def decode_base62(short_str: str) -> int:
    base = len(BASE62_ALPHABET)
    num = 0
    for char in short_str:
        num = num * base + BASE62_ALPHABET.index(char)
    return num

def validate_custom_alias(alias: str) -> tuple[bool, str]:
    if not alias:
        return False, "Alias cannot be empty."
        
    if alias.lower() in RESERVED_KEYWORDS:
        return False, f"Custom alias '{alias}' is a reserved system keyword."
        
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', alias):
        return False, "Alias must be 3-20 characters long and contain only letters, numbers, hyphens, or underscores."
        
    existing = ShortURL.query.filter((ShortURL.short_code == alias) | (ShortURL.custom_alias == alias)).first()
    if existing:
        return False, f"Custom alias '{alias}' is already in use."
        
    return True, "Valid alias."

def create_short_url(link_id: int, custom_alias: str = None) -> ShortURL:
    existing_entry = ShortURL.query.filter_by(link_id=link_id).first()
    if existing_entry:
        return existing_entry
        
    short_url_entry = ShortURL(link_id=link_id)
    
    if custom_alias:
        is_valid, message = validate_custom_alias(custom_alias)
        if not is_valid:
            raise ValueError(message)
        short_url_entry.custom_alias = custom_alias
        short_url_entry.short_code = custom_alias
    else:
        while True:
            random_num = random.randint(10**7, 10**9)
            code = encode_base62(random_num)
            if not ShortURL.query.filter((ShortURL.short_code == code) | (ShortURL.custom_alias == code)).first():
                short_url_entry.short_code = code
                break

    db.session.add(short_url_entry)
    db.session.commit()
    
    return short_url_entry

def get_short_url_response_ui_tokens(success: bool) -> dict:
    if success:
        return {
            "font_family": "Cascadia Code, Consolas, monospace",
            "text_color": "#1E293B"
        }
    else:
        return {
            "border_color": "#B91C1C",
            "message_color": "#B91C1C"
        }

def record_click_event(short_url_id: int):
    """
    Atomically increments the click counter for a shortened link.
    """
    db.session.query(ShortURL).filter(ShortURL.id == short_url_id).update(
        {ShortURL.clicks_count: ShortURL.clicks_count + 1},
        synchronize_session=False
    )
    db.session.commit()
