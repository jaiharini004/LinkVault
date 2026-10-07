import unittest
from unittest.mock import patch, MagicMock
from app.services.metadata_service import suggest_category_from_url, scrape_url_metadata


class TestCategorySuggestion(unittest.TestCase):
    """Tests for platform domain category suggestion logic."""

    def test_development_category(self):
        self.assertEqual(suggest_category_from_url("https://github.com/example/repo"), "Development")
        self.assertEqual(suggest_category_from_url("http://gitlab.com/test"), "Development")
        self.assertEqual(suggest_category_from_url("https://bitbucket.org/team/project"), "Development")
        self.assertEqual(suggest_category_from_url("https://stackoverflow.com/questions/123"), "Development")

    def test_documents_category(self):
        self.assertEqual(suggest_category_from_url("https://drive.google.com/file/d/123/view"), "Documents")
        self.assertEqual(suggest_category_from_url("https://docs.google.com/document/d/abc"), "Documents")
        self.assertEqual(suggest_category_from_url("https://notion.so/page-id"), "Documents")
        self.assertEqual(suggest_category_from_url("https://dropbox.com/s/file"), "Documents")

    def test_media_category(self):
        self.assertEqual(suggest_category_from_url("https://youtube.com/watch?v=123"), "Media")
        self.assertEqual(suggest_category_from_url("https://youtu.be/dQw4w9WgXcQ"), "Media")
        self.assertEqual(suggest_category_from_url("https://vimeo.com/12345"), "Media")
        self.assertEqual(suggest_category_from_url("https://spotify.com/track/abc"), "Media")

    def test_meetings_category(self):
        self.assertEqual(suggest_category_from_url("https://meet.google.com/abc-defg-hij"), "Meetings")
        self.assertEqual(suggest_category_from_url("https://zoom.us/j/123456"), "Meetings")
        self.assertEqual(suggest_category_from_url("https://teams.microsoft.com/l/meetup"), "Meetings")

    def test_design_category(self):
        self.assertEqual(suggest_category_from_url("https://figma.com/file/123"), "Design")
        self.assertEqual(suggest_category_from_url("https://dribbble.com/shots/456"), "Design")
        self.assertEqual(suggest_category_from_url("https://behance.net/gallery/789"), "Design")

    def test_fallback_general_category(self):
        self.assertEqual(suggest_category_from_url("https://unknown-domain.com"), "General")
        self.assertEqual(suggest_category_from_url("https://example.org/page"), "General")

    def test_www_prefix_stripped(self):
        self.assertEqual(suggest_category_from_url("https://www.github.com/repo"), "Development")
        self.assertEqual(suggest_category_from_url("https://www.youtube.com/watch?v=1"), "Media")

    def test_subdomain_matching(self):
        """Subdomains of mapped domains should resolve to the parent category."""
        self.assertEqual(suggest_category_from_url("https://api.github.com/repos"), "Development")
        self.assertEqual(suggest_category_from_url("https://gist.github.com/user/id"), "Development")
        self.assertEqual(suggest_category_from_url("https://open.spotify.com/track/abc"), "Media")

    def test_malformed_url_returns_general(self):
        self.assertEqual(suggest_category_from_url(""), "General")
        self.assertEqual(suggest_category_from_url("not-a-url"), "General")


class TestMetadataScraper(unittest.TestCase):
    """Tests for fail-safe HTML metadata extraction."""

    @patch('app.services.metadata_service.requests.get')
    def test_successful_scrape(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
                <link rel="icon" href="/favicon.png">
            </head>
        </html>
        """
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://github.com/repo")

        self.assertEqual(result['suggested_category'], "Development")
        self.assertEqual(result['title'], "Test Page")
        self.assertEqual(result['description'], "Test description")
        self.assertEqual(result['favicon_url'], "https://github.com/favicon.png")
        self.assertTrue(result['scrape_success'])

    @patch('app.services.metadata_service.requests.get')
    def test_og_tags_take_precedence(self, mock_get):
        """OpenGraph meta tags should take precedence over standard HTML tags."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <title>Fallback Title</title>
                <meta property="og:title" content="OpenGraph Title">
                <meta name="description" content="Fallback Desc">
                <meta property="og:description" content="OpenGraph Desc">
            </head>
        </html>
        """
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com/page")

        self.assertEqual(result['title'], "OpenGraph Title")
        self.assertEqual(result['description'], "OpenGraph Desc")

    @patch('app.services.metadata_service.requests.get')
    def test_absolute_favicon_url_preserved(self, mock_get):
        """Absolute favicon hrefs should be used as-is without prefixing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><head>
            <title>Page</title>
            <link rel="icon" href="https://cdn.example.com/icons/fav.ico">
        </head></html>
        """
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com")
        self.assertEqual(result['favicon_url'], "https://cdn.example.com/icons/fav.ico")

    @patch('app.services.metadata_service.requests.get')
    def test_protocol_relative_favicon(self, mock_get):
        """Protocol-relative favicon hrefs (//...) should get https: prepended."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><head>
            <title>Page</title>
            <link rel="icon" href="//cdn.example.com/fav.ico">
        </head></html>
        """
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com")
        self.assertEqual(result['favicon_url'], "https://cdn.example.com/fav.ico")

    @patch('app.services.metadata_service.requests.get')
    def test_default_favicon_fallback(self, mock_get):
        """When no <link rel=icon> tag exists, fall back to /favicon.ico."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>No Icon</title></head></html>"
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com")
        self.assertEqual(result['favicon_url'], "https://example.com/favicon.ico")


class TestFailSafeBehavior(unittest.TestCase):
    """Tests for error resilience -- timeouts, DNS failures, HTTP errors."""

    @patch('app.services.metadata_service.requests.get')
    def test_timeout_returns_failsafe(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout("Request timed out after 2.5s")

        result = scrape_url_metadata("https://slow-site.com")

        self.assertEqual(result['title'], "")
        self.assertEqual(result['description'], "")
        self.assertFalse(result['scrape_success'])

    @patch('app.services.metadata_service.requests.get')
    def test_connection_error_returns_failsafe(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("Failed to resolve host")

        result = scrape_url_metadata("http://this-site-does-not-exist.local")

        self.assertEqual(result['title'], "")
        self.assertFalse(result['scrape_success'])

    @patch('app.services.metadata_service.requests.get')
    def test_ssl_error_returns_failsafe(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.SSLError("SSL certificate verify failed")

        result = scrape_url_metadata("https://bad-cert.example.com")

        self.assertFalse(result['scrape_success'])
        self.assertEqual(result['ui_tokens']['status_label'], "Unreachable")


class TestUITokenCompliance(unittest.TestCase):
    """Tests that response UI tokens match the global design system exactly."""

    @patch('app.services.metadata_service.requests.get')
    def test_healthy_tokens(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>OK</title></head></html>"
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com")
        tokens = result['ui_tokens']

        self.assertEqual(tokens['status_label'], "Healthy")
        self.assertEqual(tokens['badge_color'], "#15803D")
        self.assertEqual(tokens['badge_bg'], "#DCFCE7")
        self.assertEqual(tokens['card_border'], "#CBD5E1")
        self.assertIn("Segoe UI", tokens['font_family'])

    @patch('app.services.metadata_service.requests.get')
    def test_broken_tokens_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com/not-found")
        tokens = result['ui_tokens']

        self.assertEqual(tokens['status_label'], "Broken")
        self.assertEqual(tokens['badge_color'], "#B91C1C")
        self.assertEqual(tokens['badge_bg'], "#FEE2E2")

    @patch('app.services.metadata_service.requests.get')
    def test_restricted_tokens_403(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = scrape_url_metadata("https://example.com/forbidden")
        tokens = result['ui_tokens']

        self.assertEqual(tokens['status_label'], "Restricted")
        self.assertEqual(tokens['badge_color'], "#B45309")
        self.assertEqual(tokens['badge_bg'], "#FEF3C7")

    @patch('app.services.metadata_service.requests.get')
    def test_unreachable_tokens_timeout(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()

        result = scrape_url_metadata("https://timeout.example.com")
        tokens = result['ui_tokens']

        self.assertEqual(tokens['status_label'], "Unreachable")
        self.assertEqual(tokens['badge_color'], "#64748B")
        self.assertEqual(tokens['badge_bg'], "#F1F5F9")


if __name__ == '__main__':
    unittest.main()
