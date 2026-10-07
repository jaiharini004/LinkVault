import unittest
from unittest.mock import patch, MagicMock
from app.services.whatsapp_service import parse_whatsapp_chat

class TestWhatsAppService(unittest.TestCase):
    
    @patch('app.services.whatsapp_service.Link')
    def test_parse_whatsapp_chat_bracketed_format(self, mock_link):
        # Mocking the DB query to return None (no duplicate found)
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = None
        mock_link.query.filter_by.return_value = mock_filter_by

        chat_text = """[18/04/26, 14:32:05] Alice: Hey, check out this repo!
https://github.com/example/repo?utm_source=chat
[18/04/26, 14:35:10] Bob: Thanks! Also look at this doc.
https://docs.google.com/document/d/12345/edit
It is very useful."""

        result = parse_whatsapp_chat(chat_text)
        
        self.assertEqual(result["total_extracted"], 2)
        self.assertEqual(result["platform_stats"]["GitHub"], 1)
        self.assertEqual(result["platform_stats"]["Drive"], 1)
        
        staged = result["staged_links"]
        self.assertEqual(staged[0]["original_url"], "https://github.com/example/repo?utm_source=chat")
        self.assertEqual(staged[0]["normalized_url"], "https://github.com/example/repo")
        self.assertEqual(staged[0]["suggested_category"], "Development")
        self.assertEqual(staged[0]["context"], "Shared by Alice: Hey, check out this repo!")
        self.assertFalse(staged[0]["is_duplicate"])
        
        self.assertEqual(staged[1]["original_url"], "https://docs.google.com/document/d/12345/edit")
        self.assertEqual(staged[1]["normalized_url"], "https://docs.google.com/document/d/12345/edit")
        self.assertEqual(staged[1]["suggested_category"], "Documents")
        self.assertEqual(staged[1]["context"], "Shared by Bob: Thanks! Also look at this doc.\n\nIt is very useful.")
        self.assertFalse(staged[1]["is_duplicate"])

    @patch('app.services.whatsapp_service.Link')
    def test_parse_whatsapp_chat_standard_format(self, mock_link):
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = None
        mock_link.query.filter_by.return_value = mock_filter_by

        chat_text = """4/18/26, 2:32 PM - Charlie: Have you seen this video?
https://youtube.com/watch?v=dQw4w9WgXcQ
4/18/26, 2:35 PM - Dave: No, I was on a call here https://meet.google.com/abc-defg-hij"""

        result = parse_whatsapp_chat(chat_text)
        
        self.assertEqual(result["total_extracted"], 2)
        self.assertEqual(result["platform_stats"]["YouTube"], 1)
        self.assertEqual(result["platform_stats"]["Meet"], 1)
        
        staged = result["staged_links"]
        self.assertEqual(staged[0]["original_url"], "https://youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(staged[0]["normalized_url"], "https://youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(staged[0]["suggested_category"], "Media")
        self.assertEqual(staged[0]["context"], "Shared by Charlie: Have you seen this video?")
        
        self.assertEqual(staged[1]["original_url"], "https://meet.google.com/abc-defg-hij")
        self.assertEqual(staged[1]["normalized_url"], "https://meet.google.com/abc-defg-hij")
        self.assertEqual(staged[1]["suggested_category"], "Meetings")
        self.assertEqual(staged[1]["context"], "Shared by Dave: No, I was on a call here")

    @patch('app.services.whatsapp_service.Link')
    def test_batch_duplicate_detection(self, mock_link):
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = None
        mock_link.query.filter_by.return_value = mock_filter_by

        chat_text = """[18/04/26, 14:32:05] Alice: https://github.com/example/repo
[18/04/26, 14:35:10] Bob: Sending again just in case https://github.com/example/repo?utm_source=bob"""

        result = parse_whatsapp_chat(chat_text)
        
        self.assertEqual(result["total_extracted"], 2)
        staged = result["staged_links"]
        
        # First one shouldn't be duplicate
        self.assertFalse(staged[0]["is_duplicate"])
        # Second one should be duplicate within the batch
        self.assertTrue(staged[1]["is_duplicate"])

    @patch('app.services.whatsapp_service.Link')
    def test_db_duplicate_detection(self, mock_link):
        # Mocking the DB query to return an existing entry
        existing_link = MagicMock()
        existing_link.id = 99
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = existing_link
        mock_link.query.filter_by.return_value = mock_filter_by

        chat_text = """[18/04/26, 14:32:05] Alice: https://github.com/example/repo"""

        result = parse_whatsapp_chat(chat_text)
        
        self.assertEqual(result["total_extracted"], 1)
        staged = result["staged_links"]
        
        self.assertTrue(staged[0]["is_duplicate"])
        self.assertEqual(staged[0]["existing_link_id"], 99)

if __name__ == '__main__':
    unittest.main()
