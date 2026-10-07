import unittest
from unittest.mock import patch, MagicMock
from app.services.health_service import evaluate_http_status

class TestHealthService(unittest.TestCase):
    
    @patch('app.services.health_service.requests.head')
    def test_evaluate_http_status_healthy_200(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        status, code = evaluate_http_status("https://example.com")
        self.assertEqual(status, "Healthy")
        self.assertEqual(code, 200)

    @patch('app.services.health_service.requests.head')
    def test_evaluate_http_status_restricted_403(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_head.return_value = mock_response

        status, code = evaluate_http_status("https://example.com/private")
        self.assertEqual(status, "Restricted")
        self.assertEqual(code, 403)

    @patch('app.services.health_service.requests.head')
    def test_evaluate_http_status_broken_404(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        status, code = evaluate_http_status("https://example.com/not-found")
        self.assertEqual(status, "Broken")
        self.assertEqual(code, 404)

    @patch('app.services.health_service.requests.head')
    def test_evaluate_http_status_broken_500(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response

        status, code = evaluate_http_status("https://example.com/error")
        self.assertEqual(status, "Broken")
        self.assertEqual(code, 500)

    @patch('app.services.health_service.requests.head')
    @patch('app.services.health_service.requests.get')
    def test_evaluate_http_status_fallback_get_on_405(self, mock_get, mock_head):
        # HEAD returns 405 Method Not Allowed
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        mock_head.return_value = mock_head_response
        
        # GET returns 200 OK
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response

        status, code = evaluate_http_status("https://example.com/api")
        self.assertEqual(status, "Healthy")
        self.assertEqual(code, 200)
        # Ensure GET was called
        mock_get.assert_called_once()

    @patch('app.services.health_service.requests.head')
    def test_evaluate_http_status_timeout(self, mock_head):
        import requests
        mock_head.side_effect = requests.exceptions.Timeout("Request timed out")

        status, code = evaluate_http_status("https://slow-site.com")
        self.assertEqual(status, "Timeout/Unreachable")
        self.assertIsNone(code)

    @patch('app.services.health_service.requests.head')
    def test_evaluate_http_status_connection_error(self, mock_head):
        import requests
        mock_head.side_effect = requests.exceptions.ConnectionError("DNS failure")

        status, code = evaluate_http_status("https://non-existent-domain.com")
        self.assertEqual(status, "Timeout/Unreachable")
        self.assertIsNone(code)

if __name__ == '__main__':
    unittest.main()
