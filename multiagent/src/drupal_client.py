import json
import logging
import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("DRUPAL_BASE_URL", "http://localhost:8080")
AUTH = (os.environ.get("DRUPAL_USER", ""), os.environ.get("DRUPAL_PASSWORD", ""))

JSONAPI_HEADERS = {"Accept": "application/vnd.api+json"}
PATCH_HEADERS = {"Content-Type": "application/vnd.api+json"}

MAX_ATTEMPTS = 3          # 1 lan goi ban dau + 2 lan retry
BACKOFF_BASE_SECONDS = 1  # backoff luy thua: 1s sau lan 1, 2s sau lan 2
REQUEST_TIMEOUT_SECONDS = (5, 30)  # (connect_timeout, read_timeout)


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


_IMG_TAG = re.compile(r"<img[^>]*>", re.IGNORECASE)
# (?<![\w-]) chứ KHÔNG phải \b: \b khớp ngay giữa dấu gạch và chữ, nên
# data-alt="x" bị đọc nhầm thành alt. Sai theo hướng nguy hiểm - ảnh THIẾU
# alt thật nhưng có data-alt sẽ bị coi là có alt, tức bỏ sót lỗi B6.
_ALT_ATTR = re.compile(
    r"""(?<![\w-])alt\s*=\s*("([^"]*)"|'([^']*)'|([^\s>"']+))""", re.IGNORECASE
)


def _alt_cua_the_img(the: str) -> str:
    """Lấy giá trị alt của một thẻ <img>. Không có hoặc rỗng -> chuỗi rỗng."""
    khop = _ALT_ATTR.search(the)
    if not khop:
        return ""
    return (khop.group(2) or khop.group(3) or khop.group(4) or "").strip()


def _extract_image_alt(resource: dict, body_html: str = "") -> str:
    """Liệt kê alt text của ẢNH ĐẠI DIỆN và MỌI ẢNH TRONG BODY.

    Trước đây hàm này chỉ đọc relationships.field_image, nên ảnh nhúng trong
    body lọt lưới hoàn toàn. Đó là lệch có hệ thống so với ground truth: mã
    lỗi B6 (docs/goldset/annotation-guideline.md v1.2) xét MỌI thẻ <img>
    trong body, còn hệ thống chỉ xét một ảnh đại diện - hai bên đo hai tập
    ảnh khác nhau nên Recall/F1 của tiêu chí SEO9 không so được
    (docs/evaluation-plan.md mục 4.5 điều kiện 4).

    Bóc bằng regex ở đây thay vì để LLM tự đếm trong HTML: đếm ảnh là việc
    máy làm chính xác và miễn phí, đúng chủ trương của docs/rubrics.md mục
    2.4 - chỉ giao cho LLM phần cần hiểu ngữ nghĩa (alt có mô tả đúng ảnh
    không), không giao phần đếm được.

    Định dạng trả về: mỗi ảnh một dòng, alt nằm sau dấu hai chấm. Dòng nào
    trống sau dấu hai chấm nghĩa là ảnh đó THIẾU alt. Bài không có ảnh nào ->
    chuỗi rỗng.
    """
    dong = []

    rel = (resource.get("relationships") or {}).get("field_image") or {}
    data = rel.get("data")
    if isinstance(data, dict):
        dong.append(f"Ảnh đại diện: {(data.get('meta') or {}).get('alt') or ''}")

    for i, the in enumerate(_IMG_TAG.findall(body_html or ""), start=1):
        dong.append(f"Ảnh {i} trong bài: {_alt_cua_the_img(the)}")

    return "\n".join(dong)


def fetch_content(node_id: str) -> dict:
    """Lấy 1 bài viết (article) từ Drupal qua JSON:API.

    Trả về {"fields", "raw_content"} - fields là dict 6 trường nội dung dùng
    cho đánh giá theo từng field (docs/architecture.md mục 3); raw_content là
    toàn bộ JSON:API resource object gốc. Đọc phòng thủ: trường nào chưa cấu
    hình/để trống trên Drupal -> chuỗi rỗng, không làm sập pipeline.

    Tự retry khi Drupal không phản hồi (docs/architecture.md mục 7); nếu hết
    retry vẫn lỗi, exception văng ra ngoài để dừng pipeline.
    """
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    response = _request_with_retry(
        requests.get, url, headers=JSONAPI_HEADERS, auth=AUTH, timeout=REQUEST_TIMEOUT_SECONDS
    )
    resource = response.json()["data"]
    attributes = resource["attributes"]
    body = attributes.get("body") or {}
    path = attributes.get("path") or {}
    fields = {
        "title": attributes.get("title") or "",
        "body": body.get("value") or "",
        "summary": body.get("summary") or "",
        "url_alias": path.get("alias") or "",
        # custom field text (xem hướng dẫn setup) - production thật dùng Metatag
        "meta_description": attributes.get("field_meta_description") or "",
        "image_alt": _extract_image_alt(resource, body.get("value") or ""),
    }
    return {"fields": fields, "raw_content": resource}


def write_back(
    node_id: str, status: str, score: Optional[float], suggestions: str,
    report_json: Optional[dict] = None,
) -> None:
    """Ghi ngược kết quả đánh giá AI vào bài viết (PATCH).

    `score = None` nghĩa là hệ thống CHƯA chấm được (VD Compliance Agent lỗi
    nên không có điểm tổng) - ghi null để Drupal để trống field, không quy
    thành 0 điểm (docs/architecture.md mục 6.4).

    `report_json` là báo cáo có cấu trúc cho module vf_ai_review render
    (docs/superpowers/specs/2026-08-03-vf-ai-review-module-design.md).
    Mặc định None để lời gọi cũ không đổi hành vi.

    Tự retry khi Drupal lỗi mạng/5xx (docs/architecture.md mục 7). Nếu hết
    retry vẫn lỗi, KHÔNG raise - chỉ ghi log cảnh báo, vì ở bước này bài
    viết đã được 4 agent chấm điểm xong (tốn API call thật); để lỗi ghi-ngược
    làm sập cả script sẽ lãng phí toàn bộ công việc đã làm.
    """
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    attributes = {
        "field_ai_status": status,
        "field_ai_score": score,
        "field_ai_suggestions": suggestions,
    }
    if report_json is not None:
        # ensure_ascii=False để JSON trong DB đọc được bằng mắt khi debug.
        attributes["field_ai_report_json"] = json.dumps(report_json, ensure_ascii=False)

    payload = {
        "data": {
            "type": "node--article",
            "id": node_id,
            "attributes": attributes,
        }
    }
    try:
        _request_with_retry(
            requests.patch,
            url,
            headers=PATCH_HEADERS,
            json=payload,
            auth=AUTH,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        logging.warning(
            "Write-back that bai cho node %s: %s",
            node_id, e,
        )
