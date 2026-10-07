import unittest
from flask import Flask
from app.extensions import db
from app.models.link import Link, Category
from app.models.short_url import ShortURL
from app.services.link_service import search_links
from app.routes.link_routes import link_bp

class TestSearchEngine(unittest.TestCase):
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

    def test_search_partial_match(self):
        link1 = Link(original_url="https://example.com", title="Agentic AI Project", description="An AI tool", health_status="Healthy")
        link2 = Link(original_url="https://github.com/repo", title="Something else", context="project agentic reference", health_status="Broken")
        link3 = Link(original_url="https://google.com", title="Google", description="Search engine")
        
        db.session.add_all([link1, link2, link3])
        db.session.commit()
        
        with self.app.test_request_context('/'):
            results = search_links(query_term="agentic")
            self.assertEqual(results['total_results'], 2)
            ids = [r['id'] for r in results['results']]
            self.assertIn(link1.id, ids)
            self.assertIn(link2.id, ids)

    def test_multi_filter_precision(self):
        cat = Category(name="Dev")
        db.session.add(cat)
        db.session.commit()
        
        link1 = Link(original_url="https://example.com", title="Agentic Repo", source="WhatsApp", health_status="Healthy", category_id=cat.id)
        link2 = Link(original_url="https://test.com", title="Agentic Doc", source="Telegram", health_status="Healthy", category_id=cat.id)
        link3 = Link(original_url="https://broken.com", title="Agentic Repo 2", source="WhatsApp", health_status="Broken", category_id=cat.id)
        
        db.session.add_all([link1, link2, link3])
        db.session.commit()
        
        with self.app.test_request_context('/'):
            results = search_links(query_term="repo", source="WhatsApp", health_status="Healthy")
            self.assertEqual(results['total_results'], 1)
            self.assertEqual(results['results'][0]['id'], link1.id)
            
            # Check UI tokens
            tokens = results['results'][0]['ui_tokens']
            self.assertIn("'Segoe UI'", tokens['font_family'])
            self.assertEqual(tokens['badge_text_color'], "#15803D")
            self.assertEqual(tokens['badge_bg_color'], "#DCFCE7")

    def test_pagination_math(self):
        links = [Link(original_url=f"https://ex.com/{i}", title=f"Link {i}") for i in range(25)]
        db.session.add_all(links)
        db.session.commit()
        
        with self.app.test_request_context('/'):
            results = search_links(page=1, per_page=10)
            self.assertEqual(results['total_results'], 25)
            self.assertEqual(results['total_pages'], 3)
            self.assertEqual(len(results['results']), 10)
            
            results_p3 = search_links(page=3, per_page=10)
            self.assertEqual(len(results_p3['results']), 5)

    def test_search_api_endpoint(self):
        link1 = Link(original_url="https://example.com", title="Agentic AI", source="WhatsApp", health_status="Healthy")
        db.session.add(link1)
        db.session.commit()
        
        response = self.client.get('/api/links/search?q=agentic&source=WhatsApp&health=Healthy&page=1&limit=12')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data['status'], "success")
        self.assertEqual(data['total_results'], 1)
        self.assertEqual(data['results'][0]['title'], "Agentic AI")

if __name__ == '__main__':
    unittest.main()
