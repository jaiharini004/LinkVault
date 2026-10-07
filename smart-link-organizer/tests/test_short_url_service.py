import unittest
from flask import Flask
from app.extensions import db
from app.models.link import Link
from app.models.short_url import ShortURL
from app.services.short_url_service import encode_base62, decode_base62, validate_custom_alias, create_short_url

class TestShortUrlService(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_base62_math(self):
        self.assertEqual(encode_base62(0), "0")
        self.assertEqual(encode_base62(61), "Z")
        self.assertEqual(encode_base62(62), "10")
        
        # Test bidirectional encoding and decoding
        test_nums = [0, 1, 61, 62, 100, 999999, 123456789]
        for num in test_nums:
            encoded = encode_base62(num)
            self.assertEqual(decode_base62(encoded), num)

    def test_validate_custom_alias(self):
        # Valid alias
        is_valid, msg = validate_custom_alias("my-portfolio")
        self.assertTrue(is_valid)
        
        # Invalid characters
        is_valid, msg = validate_custom_alias("invalid@alias!")
        self.assertFalse(is_valid)
        
        # Too short
        is_valid, msg = validate_custom_alias("ab")
        self.assertFalse(is_valid)
        
        # Reserved keyword
        is_valid, msg = validate_custom_alias("admin")
        self.assertFalse(is_valid)
        
    def test_create_short_url_random(self):
        link = Link(original_url="https://github.com/test")
        db.session.add(link)
        db.session.commit()
        
        short_entry = create_short_url(link.id)
        self.assertIsNotNone(short_entry.short_code)
        self.assertIsNone(short_entry.custom_alias)
        self.assertEqual(short_entry.link_id, link.id)
        
    def test_create_short_url_custom(self):
        link = Link(original_url="https://youtube.com")
        db.session.add(link)
        db.session.commit()
        
        short_entry = create_short_url(link.id, "my-video")
        self.assertEqual(short_entry.short_code, "my-video")
        self.assertEqual(short_entry.custom_alias, "my-video")
        
    def test_custom_alias_collision(self):
        link1 = Link(original_url="https://youtube.com/1")
        link2 = Link(original_url="https://youtube.com/2")
        db.session.add_all([link1, link2])
        db.session.commit()
        
        create_short_url(link1.id, "collision-test")
        
        # Try to use same alias
        with self.assertRaises(ValueError):
            create_short_url(link2.id, "collision-test")

    def test_cascading_deletion(self):
        link = Link(original_url="https://example.com")
        db.session.add(link)
        db.session.commit()
        
        create_short_url(link.id)
        
        # Delete parent link
        db.session.delete(link)
        db.session.commit()
        
        # Ensure short url is deleted via cascade/SQLAlchemy
        count = ShortURL.query.count()
        self.assertEqual(count, 0)

if __name__ == '__main__':
    unittest.main()
