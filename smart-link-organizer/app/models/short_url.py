from datetime import datetime
from app.extensions import db

class ShortURL(db.Model):
    __tablename__ = 'short_urls'
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id', ondelete='CASCADE'), nullable=False, unique=True)
    short_code = db.Column(db.String(20), unique=True, index=True, nullable=False)
    custom_alias = db.Column(db.String(30), unique=True, index=True, nullable=True)
    clicks_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship back to original Link model
    link = db.relationship('Link', backref=db.backref('short_url_entry', uselist=False, cascade='all, delete-orphan'))
