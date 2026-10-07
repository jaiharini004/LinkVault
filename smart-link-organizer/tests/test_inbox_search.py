import unittest
from app import create_app, db
from app.models.link import Link, Category
from app.services.inbox_service import bulk_add_to_inbox, batch_organize_inbox

class TestConfig:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class TestInboxAndSearch(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_bulk_add_to_inbox(self):
        urls = [
            "https://github.com/example?utm_source=test",
            "https://youtube.com/watch?v=123"
        ]
        
        created = bulk_add_to_inbox(urls)
        
        self.assertEqual(len(created), 2)
        
        links = Link.query.all()
        self.assertEqual(len(links), 2)
        
        # Test the first link
        self.assertEqual(links[0].original_url, "https://github.com/example?utm_source=test")
        self.assertEqual(links[0].normalized_url, "https://github.com/example")
        self.assertEqual(links[0].category.name, "Development")
        self.assertTrue(links[0].is_inbox)
        self.assertEqual(links[0].source, "Manual")
        
        # Test the second link
        self.assertEqual(links[1].normalized_url, "https://youtube.com/watch?v=123")
        self.assertEqual(links[1].category.name, "Media")
        self.assertTrue(links[1].is_inbox)

    def test_batch_organize_inbox(self):
        urls = ["https://example.com/1", "https://example.com/2"]
        bulk_add_to_inbox(urls)
        
        links = Link.query.all()
        self.assertTrue(all(link.is_inbox for link in links))
        
        items_to_organize = [
            {
                "link_id": links[0].id,
                "title": "Organized 1",
                "category": "Documents",
                "context": "Context 1"
            },
            {
                "link_id": links[1].id,
                "title": "Organized 2"
            }
        ]
        
        updated_count = batch_organize_inbox(items_to_organize)
        self.assertEqual(updated_count, 2)
        
        updated_links = Link.query.all()
        
        # Link 1 checks
        self.assertFalse(updated_links[0].is_inbox)
        self.assertEqual(updated_links[0].title, "Organized 1")
        self.assertEqual(updated_links[0].category.name, "Documents")
        self.assertEqual(updated_links[0].context, "Context 1")
        
        # Link 2 checks
        self.assertFalse(updated_links[1].is_inbox)
        self.assertEqual(updated_links[1].title, "Organized 2")
        # Category not updated, should remain General (default from normalize_url for example.com)
        self.assertEqual(updated_links[1].category.name, "General")

    def test_dynamic_search_api(self):
        # Create some test data
        dev_cat = Category(name="Development")
        db.session.add(dev_cat)
        db.session.commit()
        
        link1 = Link(title="Test Link 1", original_url="https://github.com/1", normalized_url="https://github.com/1", source="WhatsApp", is_inbox=False, category_id=dev_cat.id)
        link2 = Link(title="Another Link", original_url="https://example.com/2", normalized_url="https://example.com/2", source="Manual", is_inbox=True)
        link3 = Link(title="Test Link 3", original_url="https://github.com/3", normalized_url="https://github.com/3", source="Slack", health_status="Broken", is_inbox=False)
        db.session.add_all([link1, link2, link3])
        db.session.commit()

        client = self.app.test_client()

        # Test search by query string (q matches title)
        response = client.get('/api/links/search?q=Test')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total"], 2)
        
        # Test search by category
        response = client.get('/api/links/search?category=Development')
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["title"], "Test Link 1")

        # Test search by source
        response = client.get('/api/links/search?source=WhatsApp')
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        
        # Test search by inbox state
        response = client.get('/api/links/search?inbox=true')
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["title"], "Another Link")

        # Test search by health
        response = client.get('/api/links/search?health=Broken')
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        
        # Test pagination
        response = client.get('/api/links/search?limit=1')
        data = response.get_json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["results"]), 1)
        
        # Verify UI Tokens
        tokens = data["ui_tokens"]
        self.assertEqual(tokens["primary_color"], "#1E3A8A")
        self.assertEqual(tokens["secondary_color"], "#2563EB")
        self.assertEqual(tokens["border_color"], "#CBD5E1")
        self.assertEqual(tokens["text_body"], "#334155")

if __name__ == '__main__':
    unittest.main()
