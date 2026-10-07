import logging
from app.extensions import db
from app.models.link import Link, Category
from app.services.link_service import normalize_url
from app.services.metadata_service import suggest_category_from_url

logger = logging.getLogger(__name__)

def bulk_add_to_inbox(raw_urls: list) -> list:
    """
    Ingests raw URLs into inbox staging area without requiring metadata fields.
    Sets is_inbox=True and attaches initial normalized URL and suggested category.
    """
    created_links = []
    
    for raw_url in raw_urls:
        url_str = raw_url.strip()
        if not url_str:
            continue

        normalized_url_str, norm_hash = normalize_url(url_str)
        suggested_cat = suggest_category_from_url(normalized_url_str)
        
        category = Category.query.filter_by(name=suggested_cat).first()
        if not category:
            category = Category(name=suggested_cat)
            db.session.add(category)
            db.session.flush()

        link = Link(
            title=normalized_url_str,  # Temporary fallback title
            original_url=url_str,
            normalized_url=normalized_url_str,
            normalized_hash=norm_hash,
            source="Manual",
            health_status="Unchecked",
            is_inbox=True,
            context="Quick inbox dump",
            category_id=category.id
        )
        db.session.add(link)
        created_links.append(link)

    db.session.commit()
    logger.info("Bulk created %s inbox links.", len(created_links))
    return [link.to_dict() for link in created_links]


def batch_organize_inbox(items: list) -> int:
    """
    Updates a batch of inbox links with categories, context, and moves them out of inbox.
    Sets is_inbox=False in a single atomic transaction.
    """
    updated_count = 0
    
    for item in items:
        link_id = item.get("link_id")
        link = Link.query.get(link_id)
        if not link:
            continue

        if "title" in item and item["title"]:
            link.title = item["title"]
        if "context" in item:
            link.context = item["context"]
        if "category" in item and item["category"]:
            category_name = item["category"]
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush()
            link.category_id = category.id

        link.is_inbox = False
        updated_count += 1

    db.session.commit()
    logger.info("Successfully organized %s inbox links.", updated_count)
    return updated_count
