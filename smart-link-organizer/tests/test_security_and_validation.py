import unittest
from app.services.validation_service import is_ssrf_safe, sanitize_html, validate_custom_alias_format, sanitize_search_query

class TestSecurityAndValidation(unittest.TestCase):
    def test_ssrf_protection_localhost(self):
        is_safe, err = is_ssrf_safe("http://localhost:5000/api")
        self.assertFalse(is_safe)
        self.assertEqual(err['error_code'], "SSRF_PROTECTION_TRIGGERED")
        self.assertEqual(err['ui_tokens']['bg_color'], "#FEE2E2")
        self.assertEqual(err['ui_tokens']['border_color'], "#B91C1C")
        
    def test_ssrf_protection_local_ip(self):
        is_safe, err = is_ssrf_safe("http://127.0.0.1/admin")
        self.assertFalse(is_safe)
        self.assertEqual(err['error_code'], "SSRF_PROTECTION_TRIGGERED")
        
    def test_ssrf_protection_private_ip(self):
        is_safe, err = is_ssrf_safe("http://192.168.1.1/")
        self.assertFalse(is_safe)
        self.assertEqual(err['error_code'], "SSRF_PROTECTION_TRIGGERED")
        
        is_safe, err = is_ssrf_safe("http://10.0.0.5/")
        self.assertFalse(is_safe)
        
    def test_ssrf_protection_valid(self):
        is_safe, err = is_ssrf_safe("https://github.com")
        self.assertTrue(is_safe)

    def test_xss_sanitization(self):
        xss_payload = "<script>alert('xss')</script>"
        sanitized = sanitize_html(xss_payload)
        self.assertEqual(sanitized, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")
        
    def test_alias_validation(self):
        # Invalid characters
        is_valid, err = validate_custom_alias_format("admin!")
        self.assertFalse(is_valid)
        self.assertEqual(err['error_code'], "INVALID_ALIAS_FORMAT")
        
        # Too short
        is_valid, err = validate_custom_alias_format("ab")
        self.assertFalse(is_valid)
        
        # Valid
        is_valid, err = validate_custom_alias_format("my-alias-123")
        self.assertTrue(is_valid)

    def test_search_query_sanitization(self):
        query = "agentic%_ai"
        sanitized = sanitize_search_query(query)
        self.assertEqual(sanitized, "agenticai")

if __name__ == '__main__':
    unittest.main()
