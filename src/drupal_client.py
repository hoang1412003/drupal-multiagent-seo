import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("DRUPAL_BASE_URL", "http://localhost:8080")
AUTH = (os.environ.get("DRUPAL_USER", ""), os.environ.get("DRUPAL_PASSWORD", ""))

JSONAPI_HEADERS = {"Accept": "application/vnd.api+json"}
PATCH_HEADERS = {"Content-Type": "application/vnd.api+json"}

MAX_ATTEMPTS = 3          # 1 lan goi ban dau + 2 lan retry
BACKOFF_BASE_SECONDS = 1  # backoff luy thua: 1s sau lan 1, 2s sau lan 2


def _request_with_retry(method, url, **kwargs) -> requests.Response:
    """Goi method(url, **kwargs) (VD requests.get/requests.patch), tu retry
    khi gap loi mang (mat ket noi/timeout) hoac loi server (5xx).

    KHONG retry loi 4xx (VD 401/403/404) - thu lai khong giai quyet duoc vi
    day la loi phia client (sai quyen/sai node_id), raise ngay lap tuc.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = method(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError:
            if response.status_code < 500 or attempt == MAX_ATTEMPTS:
                raise
        except (requests.ConnectionError, requests.Timeout):
            if attempt == MAX_ATTEMPTS:
                raise
        time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))


def fetch_content(node_id: str) -> dict:
    """Lấy 1 bài viết (article) từ Drupal qua JSON:API.

    Trả về {"title", "body", "raw_content"} - raw_content là toàn bộ
    JSON:API resource object gốc. Tự retry khi Drupal không phản hồi
    (docs/architecture.md mục 7); nếu hết retry vẫn lỗi, exception văng ra
    ngoài để dừng pipeline, không chạy tiếp các agent.
    """
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    response = _request_with_retry(requests.get, url, headers=JSONAPI_HEADERS, auth=AUTH)
    resource = response.json()["data"]
    attributes = resource["attributes"]
    return {
        "title": attributes["title"],
        "body": attributes["body"]["value"],
        "raw_content": resource,
    }


def write_back(node_id: str, status: str, score: float, suggestions: str) -> None:
    """Ghi ngược kết quả đánh giá AI vào bài viết (PATCH)."""
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    payload = {
        "data": {
            "type": "node--article",
            "id": node_id,
            "attributes": {
                "field_ai_status": status,
                "field_ai_score": score,
                "field_ai_suggestions": suggestions,
            },
        }
    }
    response = requests.patch(url, headers=PATCH_HEADERS, json=payload, auth=AUTH)
    response.raise_for_status()
