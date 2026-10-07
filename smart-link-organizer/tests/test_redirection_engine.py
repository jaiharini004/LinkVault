import unittest
from flask import Flask
from app.extensions import db
from app.models.link import Link
from app.models.short_url import ShortURL
from app.services.short_url_service import record_click_event
from app.routes.link_routes import link_bp

class TestRedirectionEngine(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        self.app.register_blueprint(link_bp)
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_redirection_success_and_click_increment(self):
        link = Link(original_url="https://example.com/target")
        db.session.add(link)
        db.session.commit()
        
        short_entry = ShortURL(link_id=link.id, short_code="test-code")
        db.session.add(short_entry)
        db.session.commit()

        # Call endpoint
        response = self.client.get('/r/test-code')
        
        # Test 302 Redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "https://example.com/target")
        
        # Test atomic increment
        updated_entry = ShortURL.query.get(short_entry.id)
        self.assertEqual(updated_entry.clicks_count, 1)

    def test_redirection_not_found(self):
        response = self.client.get('/r/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        data = response.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["ui_tokens"]["badge_bg"], "#FEE2E2")
        self.assertEqual(data["ui_tokens"]["badge_text"], "#B91C1C")

    def test_analytics_endpoint(self):
        link = Link(original_url="https://example.com/target")
        db.session.add(link)
        db.session.commit()
        
        short_entry = ShortURL(link_id=link.id, short_code="analytics-test", clicks_count=42)
        db.session.add(short_entry)
        db.session.commit()
        
        response = self.client.get(f'/api/links/{link.id}/analytics')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data["total_clicks"], 42)
        self.assertEqual(data["short_code"], "analytics-test")
        self.assertEqual(data["ui_tokens"]["metric_color"], "#2563EB")

    def test_concurrent_click_tracking(self):
        link = Link(original_url="https://example.com/target")
        db.session.add(link)
        db.session.commit()
        
        short_entry = ShortURL(link_id=link.id, short_code="concurrent-code")
        db.session.add(short_entry)
        db.session.commit()
        
        for _ in range(5):
            record_click_event(short_entry.id)
            
        updated = ShortURL.query.get(short_entry.id)
        self.assertEqual(updated.clicks_count, 5)

if __name__ == '__main__':
    unittest.main()
