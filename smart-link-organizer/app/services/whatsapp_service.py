import re
import logging
from app.services.link_service import normalize_url
from app.services.metadata_service import suggest_category_from_url
from app.models.link import Link

logger = logging.getLogger(__name__)

TIMESTAMP_PATTERNS = [
    # Bracketed format: [18/04/26, 14:32:05] Sender: Message
    re.compile(r'^\[(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2})\]\s([^:]+):\s(.*)$'),
    # Standard format: 4/18/26, 2:32 PM - Sender: Message
    re.compile(r'^(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?)\s-\s([^:]+):\s(.*)$')
]

URL_REGEX = re.compile(r'https?://[^\s<>"]+')

def parse_whatsapp_chat(chat_text: str) -> dict:
    """
    Parses WhatsApp .txt export string, reassembles multi-line messages,
    extracts valid HTTP/HTTPS URLs, strips tracking parameters, extracts context,
    and returns staged entries with platform breakdown statistics.
    """
    raw_lines = chat_text.splitlines()
    parsed_messages = []
    current_message = None

    for line in raw_lines:
        line_str = line.strip()
        if not line_str:
            continue

        matched = False
        for pattern in TIMESTAMP_PATTERNS:
            match = pattern.match(line_str)
            if match:
                if current_message:
                    parsed_messages.append(current_message)
                
                timestamp_str, sender, body = match.groups()
                current_message = {
                    "timestamp": timestamp_str,
                    "sender": sender.strip(),
                    "body": body.strip()
                }
                matched = True
                break

        if not matched and current_message:
            # Append multi-line overflow text
            current_message["body"] += "\n" + line_str

    if current_message:
        parsed_messages.append(current_message)

    staged_links = []
    seen_hashes_in_batch = set()
    platform_stats = {"GitHub": 0, "Drive": 0, "YouTube": 0, "Meet": 0, "Other": 0}

    for msg in parsed_messages:
        urls_found = URL_REGEX.findall(msg["body"])
        if not urls_found:
            continue

        # Extract context by stripping URLs from message body
        clean_context = URL_REGEX.sub('', msg["body"]).strip()
        context_snippet = f"Shared by {msg['sender']}: {clean_context}" if clean_context else f"Shared by {msg['sender']}"

        for raw_url in urls_found:
            normalized_url_str, norm_hash = normalize_url(raw_url)
            
            # Check for duplicate within the current batch
            is_batch_duplicate = norm_hash in seen_hashes_in_batch
            seen_hashes_in_batch.add(norm_hash)

            # Check for existing duplicate in PostgreSQL database
            existing_db_entry = Link.query.filter_by(normalized_hash=norm_hash).first()
            is_db_duplicate = existing_db_entry is not None

            category = suggest_category_from_url(normalized_url_str)

            # Platform stats accumulation
            if "github.com" in normalized_url_str or "gitlab.com" in normalized_url_str:
                platform_stats["GitHub"] += 1
            elif "drive.google.com" in normalized_url_str or "docs.google.com" in normalized_url_str:
                platform_stats["Drive"] += 1
            elif "youtube.com" in normalized_url_str or "youtu.be" in normalized_url_str:
                platform_stats["YouTube"] += 1
            elif "meet.google.com" in normalized_url_str or "zoom.us" in normalized_url_str:
                platform_stats["Meet"] += 1
            else:
                platform_stats["Other"] += 1

            staged_links.append({
                "original_url": raw_url,
                "normalized_url": normalized_url_str,
                "normalized_hash": norm_hash,
                "suggested_title": f"Resource from {msg['sender']}",
                "suggested_category": category,
                "context": context_snippet[:500],  # Cap context length
                "source": "WhatsApp",
                "is_duplicate": is_db_duplicate or is_batch_duplicate,
                "existing_link_id": existing_db_entry.id if existing_db_entry else None
            })

    return {
        "total_extracted": len(staged_links),
        "platform_stats": platform_stats,
        "staged_links": staged_links
    }
