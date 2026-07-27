# Retry/Backoff cho Drupal Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm retry/backoff cho 2 lệnh gọi Drupal JSON:API (`fetch_content()`, `write_back()`) trong `src/drupal_client.py`, theo đúng `docs/architecture.md` mục 7.

**Architecture:** Một helper dùng chung `_request_with_retry(method, url, **kwargs)` thử lại tối đa 3 lần (1 lần đầu + 2 retry) với backoff lũy thừa (1s, 2s) khi gặp lỗi mạng/timeout/5xx, không retry lỗi 4xx. `fetch_content()` để exception văng ra ngoài như hiện tại sau khi hết retry (dừng pipeline). `write_back()` bắt exception sau khi hết retry, ghi `logging.warning()` thay vì raise (không làm sập pipeline ở bước cuối).

**Tech Stack:** Python 3.12, `requests`, stdlib `time`/`logging` (không thêm dependency mới).

## Global Constraints

- Không thêm dependency mới — chỉ dùng stdlib `time`/`logging`, `requests` đã có sẵn trong `requirements.txt`.
- `MAX_ATTEMPTS = 3` (1 lần gọi ban đầu + 2 lần retry), `BACKOFF_BASE_SECONDS = 1`, backoff lũy thừa: `1s` sau lần 1, `2s` sau lần 2.
- Retry khi: `requests.ConnectionError`, `requests.Timeout`, hoặc HTTP 5xx. **Không** retry HTTP 4xx — raise ngay lập tức.
- `fetch_content()`: hết `MAX_ATTEMPTS` vẫn lỗi → exception raise ra ngoài (giữ nguyên hành vi hiện tại, không thêm try/except mới) → dừng pipeline, không chạy tiếp agent.
- `write_back()`: hết `MAX_ATTEMPTS` vẫn lỗi → bắt exception, gọi `logging.warning(...)`, hàm return `None` bình thường (không raise).
- Không thêm pytest/framework test mới — dùng script thủ công trong `scripts/`, in `[PASS]`/`[FAIL]` + `sys.exit`, theo đúng phong cách `scripts/test_aggregator_veto.py` và `scripts/test_compliance_rules.py`.
- Không sửa `src/graph.py` — toàn bộ thay đổi nằm trong `src/drupal_client.py` + file test mới trong `scripts/`.
- Retry cho LLM call (`ai_core.call_agent()`) và xử lý JSON sai định dạng **ngoài phạm vi** — đã được Anthropic SDK và structured output xử lý sẵn (xem spec mục 1).
- Spec đầy đủ: `docs/superpowers/specs/2026-07-22-retry-backoff-drupal-client-design.md`.

---

## Task 1: Helper `_request_with_retry()` + test thuần Python

**Files:**
- Modify: `src/drupal_client.py:1-12` (thêm import + hằng số + helper)
- Test: `scripts/test_retry.py` (mới)

**Interfaces:**
- Produces: `_request_with_retry(method: Callable, url: str, **kwargs) -> requests.Response` trong `src/drupal_client.py`. `method` là 1 hàm kiểu `requests.get`/`requests.patch` (nhận `url` + `**kwargs`, trả về object có `.status_code` và `.raise_for_status()`).
- Produces: `MAX_ATTEMPTS: int = 3` (hằng số module-level, dùng lại ở Task 3 để verify).

- [ ] **Step 1: Viết script test (sẽ fail vì `_request_with_retry` chưa tồn tại)**

Tạo `scripts/test_retry.py`:

```python
"""Test thu cong cho _request_with_retry() trong src/drupal_client.py -
dung ham gia lap (khong goi Drupal that) de kiem tra retry/backoff.

Cach chay:
    .venv\\Scripts\\python.exe scripts\\test_retry.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import requests

from drupal_client import MAX_ATTEMPTS, _request_with_retry


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


def _make_fail_then_succeed(num_failures):
    state = {"count": 0}

    def method(url, **kwargs):
        state["count"] += 1
        if state["count"] <= num_failures:
            raise requests.ConnectionError("gia lap loi ket noi")
        return _FakeResponse(200)

    return method, state


def _make_always_fail(status_code):
    state = {"count": 0}

    def method(url, **kwargs):
        state["count"] += 1
        return _FakeResponse(status_code)

    return method, state


if __name__ == "__main__":
    failed = False

    method, state = _make_fail_then_succeed(2)
    try:
        response = _request_with_retry(method, "http://fake")
        ok = response.status_code == 200 and state["count"] == 3
    except Exception as e:
        ok = False
        print(f"    loi khong mong doi: {e}")
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed = True
    print(f"[{status}] fail 2 lan roi thanh cong -> so lan goi={state['count']} (ky vong 3)")

    method, state = _make_always_fail(500)
    try:
        _request_with_retry(method, "http://fake")
        ok = False
    except requests.HTTPError:
        ok = state["count"] == MAX_ATTEMPTS
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed = True
    print(f"[{status}] luon fail 500 -> so lan goi={state['count']} (ky vong {MAX_ATTEMPTS})")

    method, state = _make_always_fail(404)
    try:
        _request_with_retry(method, "http://fake")
        ok = False
    except requests.HTTPError:
        ok = state["count"] == 1
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed = True
    print(f"[{status}] luon fail 404 -> so lan goi={state['count']} (ky vong 1, khong retry)")

    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Chạy script để xác nhận nó fail**

Run: `.venv\Scripts\python.exe scripts\test_retry.py`
Expected: `ImportError: cannot import name '_request_with_retry' from 'drupal_client'`

- [ ] **Step 3: Triển khai helper trong `src/drupal_client.py`**

Sửa phần đầu file từ:

```python
import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("DRUPAL_BASE_URL", "http://localhost:8080")
AUTH = (os.environ.get("DRUPAL_USER", ""), os.environ.get("DRUPAL_PASSWORD", ""))

JSONAPI_HEADERS = {"Accept": "application/vnd.api+json"}
PATCH_HEADERS = {"Content-Type": "application/vnd.api+json"}
```

thành:

```python
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
```

- [ ] **Step 4: Chạy lại script để xác nhận PASS**

Run: `.venv\Scripts\python.exe scripts\test_retry.py`
Expected: cả 3 dòng đều `[PASS]`, exit code 0. Script mất khoảng 6 giây (do backoff `time.sleep` thật ở 2 case đầu).

- [ ] **Step 5: Commit**

```bash
git add src/drupal_client.py scripts/test_retry.py
git commit -m "feat: add _request_with_retry helper for Drupal client"
```

---

## Task 2: Áp dụng retry vào `fetch_content()`

**Files:**
- Modify: `src/drupal_client.py:15-30` (hàm `fetch_content`)

**Interfaces:**
- Consumes: `_request_with_retry(method, url, **kwargs) -> requests.Response` (Task 1).

- [ ] **Step 1: Sửa `fetch_content()`**

Sửa:

```python
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
```

thành:

```python
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
```

- [ ] **Step 2: Xác nhận không phá vỡ hành vi cũ (nếu Drupal local đang chạy)**

Yêu cầu trước: `docker compose up -d` đang chạy, `.env` có `DRUPAL_USER`/`DRUPAL_PASSWORD` hợp lệ, và ít nhất 1 node article đã tồn tại (VD dùng lại node id từ `scripts/run_all_samples.py`).

Run:
```bash
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from drupal_client import fetch_content; print(fetch_content('3fea90a9-b0cc-422f-bee6-79c2b35aaf0f')['title'])"
```
Expected: in ra đúng title của bài viết, không có traceback.

Nếu chưa có Drupal local đang chạy sẵn lúc thực hiện task này, bỏ qua bước xác nhận thủ công này và note lại để verify ở Task 4 (khi có môi trường đầy đủ).

- [ ] **Step 3: Commit**

```bash
git add src/drupal_client.py
git commit -m "feat: retry fetch_content on Drupal network/5xx errors"
```

---

## Task 3: Áp dụng retry + log cảnh báo vào `write_back()`

**Files:**
- Modify: `src/drupal_client.py:33-48` (hàm `write_back`)
- Test: `scripts/test_write_back_failure.py` (mới)

**Interfaces:**
- Consumes: `_request_with_retry(method, url, **kwargs) -> requests.Response` (Task 1).
- Produces: `write_back(node_id, status, score, suggestions) -> None` — vẫn cùng chữ ký như hiện tại, nhưng giờ **không raise** khi Drupal lỗi sau khi hết retry (chỉ log warning).

- [ ] **Step 1: Viết test xác nhận `write_back()` không raise khi Drupal không kết nối được (sẽ fail vì hành vi hiện tại vẫn raise)**

Tạo `scripts/test_write_back_failure.py`:

```python
"""Test thu cong xac nhan write_back() KHONG raise khi Drupal khong the
ket noi (sau khi da het MAX_ATTEMPTS retry) - chi ghi log canh bao.

Cach chay:
    .venv\\Scripts\\python.exe scripts\\test_write_back_failure.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(level=logging.WARNING)

import drupal_client

# Dia chi khong co gi lang nghe -> connection refused ngay, khong can cho
# timeout that (nhanh hon nhieu so voi tro toi 1 IP khong ton tai).
drupal_client.BASE_URL = "http://127.0.0.1:1"

if __name__ == "__main__":
    try:
        result = drupal_client.write_back(
            node_id="fake-node-id",
            status="needs_revision",
            score=50,
            suggestions="test",
        )
        ok = result is None
    except Exception as e:
        ok = False
        print(f"    loi khong mong doi (le ra khong duoc raise): {e}")

    status = "PASS" if ok else "FAIL"
    print(f"[{status}] write_back() voi Drupal khong ket noi duoc -> khong raise, chi log canh bao")
    print("    (kiem tra bang mat: phia tren phai co dong 'WARNING:root:Write-back that bai...')")
    sys.exit(0 if ok else 1)
```

- [ ] **Step 2: Chạy script để xác nhận nó fail**

Run: `.venv\Scripts\python.exe scripts\test_write_back_failure.py`
Expected: `[FAIL]` (vì `write_back()` hiện tại vẫn raise `requests.ConnectionError` thay vì return `None`). Mất khoảng 3 giây (thời gian thử kết nối/timeout thật của `requests`).

- [ ] **Step 3: Sửa `write_back()`**

Sửa:

```python
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
```

thành:

```python
def write_back(node_id: str, status: str, score: float, suggestions: str) -> None:
    """Ghi ngược kết quả đánh giá AI vào bài viết (PATCH).

    Tự retry khi Drupal lỗi mạng/5xx (docs/architecture.md mục 7). Nếu hết
    retry vẫn lỗi, KHÔNG raise - chỉ ghi log cảnh báo, vì ở bước này bài
    viết đã được 4 agent chấm điểm xong (tốn API call thật); để lỗi ghi-ngược
    làm sập cả script sẽ lãng phí toàn bộ công việc đã làm.
    """
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
    try:
        _request_with_retry(requests.patch, url, headers=PATCH_HEADERS, json=payload, auth=AUTH)
    except requests.RequestException as e:
        logging.warning(
            "Write-back that bai cho node %s sau %d lan thu: %s",
            node_id, MAX_ATTEMPTS, e,
        )
```

- [ ] **Step 4: Chạy lại test để xác nhận PASS**

Run: `.venv\Scripts\python.exe scripts\test_write_back_failure.py`
Expected: dòng `WARNING:root:Write-back that bai cho node fake-node-id sau 3 lan thu: ...` in ra trước, sau đó `[PASS] write_back() voi Drupal khong ket noi duoc -> khong raise, chi log canh bao`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add src/drupal_client.py scripts/test_write_back_failure.py
git commit -m "feat: write_back logs warning instead of raising after retries exhausted"
```

---

## Task 4: Verify end-to-end trên Drupal thật (không phá vỡ hành vi cũ)

**Files:** không tạo/sửa file — chỉ chạy lại script đã có sẵn để xác nhận.

**Interfaces:** không có (task xác minh, không sinh interface mới).

- [ ] **Step 1: Xác nhận Drupal local đang chạy**

Yêu cầu trước: `docker compose up -d` đã chạy, `.env` có đủ `ANTHROPIC_API_KEY`, `DRUPAL_USER`, `DRUPAL_PASSWORD`, và 8 node mẫu từ Sprint 1 vẫn còn tồn tại trên Drupal (xem danh sách node id trong `scripts/run_all_samples.py`).

Run: `docker compose ps`
Expected: cả `vf_o2o_drupal` và `vf_o2o_drupal_db` đang ở trạng thái `Up`.

- [ ] **Step 2: Chạy lại toàn bộ 8 bài mẫu**

Run: `.venv\Scripts\python.exe scripts\run_all_samples.py`
Expected: cả 8 dòng in ra bình thường, không có traceback/exception. `final_score`/`decision` có thể khác với bảng cũ trong `docs/sprint1-report.md` (vì Compliance Agent giờ là thật, không phải do thay đổi ở task này) — không phải lỗi.

- [ ] **Step 3: Xác nhận field đã ghi ngược đúng trên Drupal**

Mở 1 trong 8 bài viết trên `http://localhost:8080/admin/content`, kiểm tra `field_ai_status`/`field_ai_score`/`field_ai_suggestions` đã được cập nhật (khớp với output của Step 2) — xác nhận retry helper không làm hỏng luồng ghi-ngược bình thường (retry chỉ kích hoạt khi có lỗi, không ảnh hưởng đường đi thành công).

- [ ] **Step 4: Không cần commit gì thêm ở task này**

Đây là bước xác minh thủ công (giống `docs/sprint1-report.md` mục 3) — không tạo file mới, không cần commit.

---

## Self-Review (đã thực hiện khi viết plan)

- **Spec coverage**: mục 2 (helper) → Task 1; mục 3 (fetch_content) → Task 2; mục 4 (write_back + logging) → Task 3; mục 5 (kế hoạch kiểm thử: test_retry.py / verify write_back / verify run_all_samples) → Task 1/3/4 tương ứng 1:1; mục 6 (ngoài phạm vi: LLM retry, brand_node, gold set, UI, Brand Voice) → không có task nào động tới các phần này.
- **Placeholder scan**: không còn TBD/TODO; mọi step đều có code đầy đủ.
- **Type consistency**: `_request_with_retry(method, url, **kwargs) -> requests.Response` (Task 1) được gọi đúng chữ ký ở Task 2 (`requests.get`) và Task 3 (`requests.patch`); `MAX_ATTEMPTS` (Task 1) được `scripts/test_retry.py` import đúng tên và được dùng lại trong docstring/log của Task 3.
