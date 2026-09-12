import os
import time
import re
import random
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Tắt cảnh báo timeout vô hại của thư viện google_auth_httplib2
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    build = None
    class HttpError(Exception):
        def __init__(self, resp, content, uri=None):
            self.resp = resp
            self.content = content
            super().__init__(f"HTTP {getattr(resp, 'status', 'error')}: {content}")

_thread_local = threading.local()

def get_thread_safe_drive_service():
    if not hasattr(_thread_local, "service"):
        _thread_local.service = build('drive', 'v3', cache_discovery=False)
    return _thread_local.service

def execute_with_retry(request, max_retries=5):
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as err:
            status_code = err.resp.status if hasattr(err, 'resp') else None
            err_str = str(err)
            is_rate_limit = status_code in [403, 429, 500, 503] or 'rateLimitExceeded' in err_str or 'userRateLimitExceeded' in err_str
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"[Rate Limit / Busy] Thử lại lần {attempt + 1}/{max_retries} sau {sleep_time:0.1f}s...")
                time.sleep(sleep_time)
                continue
            raise err
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                continue
            raise e

class DownloadFromDrive:
    def __init__(self, max_workers=5):
        self._total_size_mb = 0.0
        self._total_files_copied = 0
        self._total_files_skipped = 0
        self._limit_size_gb = 700.0
        self._max_workers = max_workers
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.excluded_strings = []
        self._start_time = 0

    def extract_folder_id_from_url(self, url):
        if not url:
            return None
        url = url.strip().strip('"').strip("'")
        match = re.search(r'/folders/([-\w]{25,})', url)
        if match:
            return match.group(1)
        match = re.search(r'[?&]id=([-\w]{25,})', url)
        if match:
            return match.group(1)
        match = re.search(r'[-\w]{25,}', url)
        if match:
            return match.group(0)
        return None

    def get_existing_items_in_dest(self, drive_service, folder_id):
        # Lấy toàn bộ tên item trong folder đích bằng 1 lần quét bộ nhớ đệm O(1)
        existing_items = set()
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        while True:
            req = drive_service.files().list(
                q=query,
                fields='files(name), nextPageToken',
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=page_token
            )
            response = execute_with_retry(req)
            for item in response.get('files', []):
                if 'name' in item and item['name']:
                    existing_items.add(item['name'])
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        return existing_items

    def get_or_create_folder(self, drive_service, dest_folder_id, sub_folder_name):
        processed_name = sub_folder_name.replace('\\', '\\\\').replace("'", "\\'")
        req_check = drive_service.files().list(
            q=f"'{dest_folder_id}' in parents and name = '{processed_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields='files(id)',
            pageSize=1,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        )
        res = execute_with_retry(req_check)
        files = res.get('files', [])
        if files:
            return files[0]['id']

        sub_folder_inf = {
            'name': sub_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [dest_folder_id]
        }
        req_create = drive_service.files().create(
            body=sub_folder_inf,
            fields='id',
            supportsAllDrives=True
        )
        folder = execute_with_retry(req_create)
        return folder['id']

    def get_childs_from_folder(self, drive_service, folder_id, from_page, to_page):
        files = []
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        if self.excluded_strings and len(self.excluded_strings) > 0:
            not_contains_query = " and ".join([f"not name contains '{ext}'" for ext in self.excluded_strings])
            query += f" and ({not_contains_query})"

        pages = 0
        while True:
            try:
                pages += 1
                req = drive_service.files().list(
                    q=query,
                    orderBy='folder, name',
                    fields='files(id, name, mimeType, size), nextPageToken',
                    pageSize=1000,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                )
                response = execute_with_retry(req)
                is_in_page_range = (from_page == 0 or pages >= from_page) and (to_page == 0 or pages <= to_page)
                if is_in_page_range:
                    files.extend(response.get('files', []))

                page_token = response.get('nextPageToken', None)
                if page_token is None or (pages >= to_page > 0):
                    break
            except Exception as e:
                print(f"\nLỗi đọc danh sách trang {pages}: {e}")
                break

        return files

    def copy_single_file_worker(self, dest_folder_id, source_file, drive_service=None):
        if self._stop_event.is_set():
            return

        if drive_service is None:
            drive_service = get_thread_safe_drive_service()

        body_file_inf = {'parents': [dest_folder_id]}
        file_name = source_file.get('name', 'unknown')

        try:
            req_copy = drive_service.files().copy(
                body=body_file_inf,
                fileId=source_file['id'],
                supportsAllDrives=True
            )
            execute_with_retry(req_copy)

            # An toàn với Google Docs / Sheets (size trả về None)
            file_size_mb = int(source_file.get('size') or 0) / (1024 * 1024)

            with self._lock:
                self._total_size_mb += file_size_mb
                self._total_files_copied += 1
                elapsed = max(time.time() - self._start_time, 0.001)
                speed = self._total_size_mb / elapsed
                size_gb = self._total_size_mb / 1024

                print(f"\r[Đã copy: {self._total_files_copied} | Bỏ qua: {self._total_files_skipped} | {size_gb:0.2f} GB | {speed:0.2f} MB/s] {file_name[:35]}", end="", flush=True)

                if self._limit_size_gb > 0 and self._total_size_mb >= (self._limit_size_gb * 1024):
                    print(f"\n\n[DỪNG] Đã đạt giới hạn dung lượng {self._limit_size_gb} GB.")
                    self._stop_event.set()

        except Exception as e:
            print(f"\nLỗi khi copy file [{file_name}]: {e}")

    def copy_folder_recursive(self, drive_service, source_folder_id, dest_folder_id):
        if self._stop_event.is_set():
            return

        existing_dest_items = self.get_existing_items_in_dest(drive_service, dest_folder_id)
        items = self.get_childs_from_folder(drive_service, source_folder_id, 0, 0)
        if not items:
            return

        files_to_copy = []
        sub_folders = []

        for item in items:
            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                sub_folders.append(item)
            else:
                if item.get('name') in existing_dest_items:
                    with self._lock:
                        self._total_files_skipped += 1
                else:
                    files_to_copy.append(item)

        if files_to_copy:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = [executor.submit(self.copy_single_file_worker, dest_folder_id, f) for f in files_to_copy]
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

        for folder in sub_folders:
            if self._stop_event.is_set():
                break
            sub_dest_id = self.get_or_create_folder(drive_service, dest_folder_id, folder['name'])
            if sub_dest_id:
                self.copy_folder_recursive(drive_service, folder['id'], sub_dest_id)
