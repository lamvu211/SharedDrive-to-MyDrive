import unittest
from unittest.mock import MagicMock, patch
import json

from drive_copier import DownloadFromDrive, execute_with_retry, HttpError

class DummyResponse:
    def __init__(self, status):
        self.status = status

class TestDriveCopier(unittest.TestCase):
    def setUp(self):
        self.copier = DownloadFromDrive(max_workers=2)

    def test_extract_folder_id_various_urls(self):
        valid_id = "1aBcDeFgHiJkLmNoPqRsTuVwXyZ12345"
        
        # Test Case 1: Standard URL
        url1 = f"https://drive.google.com/drive/folders/{valid_id}"
        self.assertEqual(self.copier.extract_folder_id_from_url(url1), valid_id)

        # Test Case 2: URL with query parameters
        url2 = f"https://drive.google.com/drive/folders/{valid_id}?usp=sharing&authuser=0"
        self.assertEqual(self.copier.extract_folder_id_from_url(url2), valid_id)

        # Test Case 3: URL with user index
        url3 = f"https://drive.google.com/drive/u/1/folders/{valid_id}"
        self.assertEqual(self.copier.extract_folder_id_from_url(url3), valid_id)

        # Test Case 4: URL with id query param
        url4 = f"https://drive.google.com/open?id={valid_id}"
        self.assertEqual(self.copier.extract_folder_id_from_url(url4), valid_id)

        # Test Case 5: Raw ID string
        self.assertEqual(self.copier.extract_folder_id_from_url(valid_id), valid_id)

        # Test Case 6: URL with surrounding quotes and whitespace
        url6 = f'  "{url1}"  '
        self.assertEqual(self.copier.extract_folder_id_from_url(url6), valid_id)

        # Test Case 7: Invalid or empty URL
        self.assertIsNone(self.copier.extract_folder_id_from_url(""))
        self.assertIsNone(self.copier.extract_folder_id_from_url(None))

    def test_get_existing_items_in_dest_pagination(self):
        mock_service = MagicMock()
        mock_files = mock_service.files.return_value

        # Mock 2 trang trả về từ Google Drive API
        page1 = {
            'files': [{'name': 'file1.pdf'}, {'name': 'file2.jpg'}],
            'nextPageToken': 'token_page_2'
        }
        page2 = {
            'files': [{'name': 'file3.docx'}],
            'nextPageToken': None
        }

        mock_req1 = MagicMock()
        mock_req1.execute.return_value = page1
        mock_req2 = MagicMock()
        mock_req2.execute.return_value = page2

        mock_files.list.side_effect = [mock_req1, mock_req2]

        items = self.copier.get_existing_items_in_dest(mock_service, "dest_folder_123")
        self.assertEqual(items, {'file1.pdf', 'file2.jpg', 'file3.docx'})
        self.assertEqual(mock_files.list.call_count, 2)

    def test_pagination_page_range_filtering(self):
        mock_service = MagicMock()
        mock_files = mock_service.files.return_value

        p1 = {'files': [{'name': 'item_p1'}], 'nextPageToken': 't2'}
        p2 = {'files': [{'name': 'item_p2'}], 'nextPageToken': 't3'}
        p3 = {'files': [{'name': 'item_p3'}], 'nextPageToken': None}

        req1, req2, req3 = MagicMock(), MagicMock(), MagicMock()
        req1.execute.return_value = p1
        req2.execute.return_value = p2
        req3.execute.return_value = p3

        # Trường hợp 1: from_page=2, to_page=0 (lấy từ trang 2 đến hết)
        mock_files.list.side_effect = [req1, req2, req3]
        res = self.copier.get_childs_from_folder(mock_service, "folder_1", from_page=2, to_page=0)
        names = [f['name'] for f in res]
        self.assertEqual(names, ['item_p2', 'item_p3'])

    def test_google_docs_none_size_handling(self):
        # Google Docs / Sheets trả về size = None trong API
        mock_service = MagicMock()
        mock_files = mock_service.files.return_value
        mock_copy_req = MagicMock()
        mock_copy_req.execute.return_value = {'id': 'copied_doc_id'}
        mock_files.copy.return_value = mock_copy_req

        source_doc = {
            'id': 'doc_123',
            'name': 'Báo cáo Google Docs.gdoc',
            'mimeType': 'application/vnd.google-apps.document',
            'size': None  # None size
        }

        # Đảm bảo không ném TypeError int(None)
        try:
            self.copier.copy_single_file_worker("dest_id", source_doc, drive_service=mock_service)
        except TypeError:
            self.fail("copy_single_file_worker crashed with TypeError on Google Doc with None size!")

        self.assertEqual(self.copier._total_files_copied, 1)
        self.assertEqual(self.copier._total_size_mb, 0.0)

    def test_graceful_stop_when_size_limit_exceeded(self):
        mock_service = MagicMock()
        mock_files = mock_service.files.return_value
        mock_copy_req = MagicMock()
        mock_copy_req.execute.return_value = {'id': 'copied_file_id'}
        mock_files.copy.return_value = mock_copy_req

        # Đặt giới hạn 1 GB (~1024 MB)
        self.copier._limit_size_gb = 1.0

        # File lớn 1.5 GB = 1536 MB
        large_file = {
            'id': 'large_file_1',
            'name': 'big_video.mp4',
            'mimeType': 'video/mp4',
            'size': str(1536 * 1024 * 1024)
        }

        self.copier.copy_single_file_worker("dest_id", large_file, drive_service=mock_service)
        self.assertTrue(self.copier._stop_event.is_set())

        # Thử copy file tiếp theo sau khi đã ngắt
        next_file = {
            'id': 'file_2',
            'name': 'doc.pdf',
            'mimeType': 'application/pdf',
            'size': '1000'
        }
        self.copier.copy_single_file_worker("dest_id", next_file, drive_service=mock_service)
        # Số file copy vẫn giữ nguyên 1
        self.assertEqual(self.copier._total_files_copied, 1)

    def test_retry_on_rate_limit(self):
        mock_req = MagicMock()
        resp_429 = DummyResponse(429)
        err_429 = HttpError(resp_429, b'{"error": {"message": "Rate Limit Exceeded"}}')

        # Lần 1 ném 429, lần 2 thành công
        mock_req.execute.side_effect = [err_429, {'status': 'ok'}]

        with patch('time.sleep', return_value=None):
            result = execute_with_retry(mock_req, max_retries=3)

        self.assertEqual(result, {'status': 'ok'})
        self.assertEqual(mock_req.execute.call_count, 2)

    def test_folder_creation_logic(self):
        mock_service = MagicMock()
        mock_files = mock_service.files.return_value

        # Giả lập folder chưa tồn tại -> gọi create
        mock_list_req = MagicMock()
        mock_list_req.execute.return_value = {'files': []}
        mock_files.list.return_value = mock_list_req

        mock_create_req = MagicMock()
        mock_create_req.execute.return_value = {'id': 'new_folder_id_999'}
        mock_files.create.return_value = mock_create_req

        folder_id = self.copier.get_or_create_folder(mock_service, "dest_parent_id", "New Subfolder")
        self.assertEqual(folder_id, 'new_folder_id_999')
        self.assertEqual(mock_files.create.call_count, 1)

if __name__ == '__main__':
    unittest.main()
