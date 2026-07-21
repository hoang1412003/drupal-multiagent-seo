import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("DRUPAL_BASE_URL", "http://localhost:8080")
AUTH = (os.environ.get("DRUPAL_USER", ""), os.environ.get("DRUPAL_PASSWORD", ""))

JSONAPI_HEADERS = {"Accept": "application/vnd.api+json"}
PATCH_HEADERS = {"Content-Type": "application/vnd.api+json"}


def fetch_content(node_id: str) -> dict:
    """Lấy 1 bài viết (article) từ Drupal qua JSON:API.

    Trả về {"title", "body", "raw_content"} - raw_content là toàn bộ
    JSON:API resource object gốc.
    """
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    response = requests.get(url, headers=JSONAPI_HEADERS, auth=AUTH)
    response.raise_for_status()
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
