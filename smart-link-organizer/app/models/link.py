from datetime import datetime
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)


class Link(db.Model):
    __tablename__ = 'links'

    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    # Origin provenance: tracks where the link was discovered (WhatsApp, Slack, Manual, etc.)
    source = db.Column(db.String(30), default='Manual', nullable=False)

    # User intent field: stores rationale for saving this link
    context = db.Column(db.Text, nullable=True)

    # Health monitoring fields
    health_status = db.Column(db.String(20), default='Unchecked', nullable=False)
    http_status_code = db.Column(db.Integer, nullable=True)
    last_checked_at = db.Column(db.DateTime, nullable=True)

    # Scraped HTML metadata fields
    metadata_title = db.Column(db.String(255), nullable=True)
    metadata_description = db.Column(db.Text, nullable=True)
    favicon_url = db.Column(db.String(500), nullable=True)

    # Inbox and organization flags
    is_inbox = db.Column(db.Boolean, default=False, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)

    # Duplicate detection fields: indexed for fast O(1) hash lookups
    normalized_url = db.Column(db.String(2048), index=True, nullable=True)
    normalized_hash = db.Column(db.String(64), index=True, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship('Category', backref='links')

    def to_dict(self):
        """
        Serialize the Link record to a JSON-compatible dictionary.
        Includes all provenance, health, metadata, and normalization fields.
        """
        return {
            "id": self.id,
            "title": self.title,
            "original_url": self.original_url,
            "description": self.description,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "source": self.source,
            "context": self.context,
            "health_status": self.health_status,
            "http_status_code": self.http_status_code,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "metadata_title": self.metadata_title,
            "metadata_description": self.metadata_description,
            "favicon_url": self.favicon_url,
            "is_inbox": self.is_inbox,
            "is_favorite": self.is_favorite,
            "normalized_url": self.normalized_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
