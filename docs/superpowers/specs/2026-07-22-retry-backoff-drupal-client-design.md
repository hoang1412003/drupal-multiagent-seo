# Thiết kế: Retry/Backoff cho Drupal Client (Sprint 2 — phần 2/5)

**Ngày:** 2026-07-22
**Phạm vi:** Đây là sub-project thứ 2 trong 5 phần của Sprint 2 (theo `docs/roadmap.md` và thứ tự đã chốt ở `docs/superpowers/specs/2026-07-22-compliance-agent-design.md`): Compliance Agent (đã xong, PR #12) → **Retry/backoff cho Drupal Client (tài liệu này)** → Gold set collection → UI báo cáo → Brand Voice Agent (RAG).

Việc này thay cho mục "Hoàn thiện Aggregator" ghi trong `docs/roadmap.md` — sau khi rà soát, logic tính điểm/veto của `aggregator_node` đã đúng và có test riêng (`scripts/test_aggregator_veto.py`, PR #12), không còn gap nào theo `docs/architecture.md` mục 6. Gap thật sự còn lại thuộc mục 7 (Error handling) là retry/backoff — chưa triển khai theo `docs/sprint1-report.md` mục 5.

## 1. Mục tiêu

Triển khai retry/backoff cho 2 lệnh gọi Drupal JSON:API trong `src/drupal_client.py` (`fetch_content()`, `write_back()`), theo đúng mục 7 `docs/architecture.md`:

| Tình huống | Cách xử lý theo architecture.md |
| --- | --- |
| Drupal API không phản hồi (Fetch Node) | Thử lại 2-3 lần với backoff; nếu vẫn lỗi thì dừng, không chạy tiếp các agent. |
| Ghi ngược vào Drupal thất bại (Write-back) | Thử lại; nếu vẫn lỗi, ghi log cảnh báo để người quản trị biết bài viết đã được chấm nhưng chưa cập nhật lên CMS. |

**Ngoài phạm vi:** retry cho lệnh gọi LLM (`ai_core.call_agent()`) — đã xác minh trực tiếp trong `.venv/Lib/site-packages/anthropic/_constants.py` (`DEFAULT_MAX_RETRIES = 2`) và `_base_client.py`: Anthropic SDK đã tự động retry (kết nối lỗi/timeout/429/5xx), viết thêm là code trùng lặp, không cần thiết. Xử lý "LLM trả JSON sai định dạng" (một tình huống khác trong bảng mục 7) cũng đã được giải quyết bởi `output_config: json_schema` (structured output) trong `ai_core.py` — LLM không thể trả JSON sai cấu trúc.

## 2. Helper dùng chung: `_request_with_retry()`

Thêm vào đầu `src/drupal_client.py`, sau các hằng số hiện có (`BASE_URL`, `AUTH`...):

```python
import logging
import time

MAX_ATTEMPTS = 3          # 1 lần gọi ban đầu + 2 lần retry
BACKOFF_BASE_SECONDS = 1  # backoff lũy thừa: 1s sau lần 1, 2s sau lần 2


def _request_with_retry(method, url, **kwargs) -> requests.Response:
    """Gọi method(url, **kwargs) (VD requests.get/requests.patch), tự retry
    khi gặp lỗi mạng (mất kết nối/timeout) hoặc lỗi server (5xx).

    KHÔNG retry lỗi 4xx (VD 401/403/404) - thử lại không giải quyết được vì
    đây là lỗi phía client (sai quyền/sai node_id), raise ngay lập tức.
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

- Dùng chung cho cả `fetch_content()` (GET) và `write_back()` (PATCH) - không viết 2 loop riêng.
- Không dùng thư viện ngoài (`tenacity`, `urllib3.util.retry.Retry`) - đã cân nhắc dùng `Retry` + `HTTPAdapter` của urllib3 (có sẵn qua `requests`, không cần cài thêm), nhưng bị loại vì: (1) mặc định urllib3 không retry method PATCH trừ khi tự khai báo `allowed_methods`, dễ cấu hình sai mà không nhận ra; (2) logic nằm trong thư viện ngoài, khó debug/trace hơn khi có sự cố so với 1 hàm Python thuần ngắn gọn.

## 3. Áp dụng vào `fetch_content()`

```python
def fetch_content(node_id: str) -> dict:
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    response = _request_with_retry(requests.get, url, headers=JSONAPI_HEADERS, auth=AUTH)
    resource = response.json()["data"]
    ...  # phần còn lại giữ nguyên
```

Nếu hết `MAX_ATTEMPTS` lần vẫn lỗi, exception văng ra ngoài như hiện tại (không thêm try/except mới ở đây) - lan lên `fetch_node()` trong `src/graph.py` (không bắt exception), làm dừng toàn bộ `graph.invoke()`, đúng yêu cầu "dừng, không chạy tiếp các agent".

## 4. Áp dụng vào `write_back()`

```python
def write_back(node_id: str, status: str, score: float, suggestions: str) -> None:
    url = f"{BASE_URL}/jsonapi/node/article/{node_id}"
    payload = {...}  # giữ nguyên
    try:
        _request_with_retry(requests.patch, url, headers=PATCH_HEADERS, json=payload, auth=AUTH)
    except requests.RequestException as e:
        logging.warning(
            "Write-back thất bại cho node %s sau %d lần thử: %s",
            node_id, MAX_ATTEMPTS, e,
        )
```

Khác với `fetch_content()`: nếu hết retry vẫn lỗi, **không raise** - chỉ log cảnh báo (`logging.warning`, dùng module `logging` chuẩn của Python, không thêm dependency) rồi hàm return bình thường. Lý do: ở bước Write-back, bài viết đã được 4 agent chấm điểm xong (tốn API call thật) - để lỗi ghi-ngược làm sập cả script sẽ lãng phí toàn bộ công việc đã làm, trong khi người quản trị chỉ cần biết để tự cập nhật thủ công sau.

`write_back_node` trong `src/graph.py` không cần thay đổi gì (đã gọi `write_back()` không có try/except, giờ `write_back()` tự xử lý nội bộ, không còn raise trong tình huống lỗi Drupal).

## 5. Kế hoạch kiểm thử

Giữ đúng phong cách hiện tại: không thêm pytest, viết script test thủ công.

**`scripts/test_retry.py`** - test thuần `_request_with_retry()`, không gọi Drupal/LLM thật, dùng hàm giả lập đếm số lần gọi:

1. Hàm giả fail 2 lần (lỗi kết nối) rồi thành công ở lần 3 → xác nhận trả về response thành công, gọi đúng 3 lần.
2. Hàm giả luôn trả lỗi 500 → xác nhận raise sau đúng `MAX_ATTEMPTS` lần gọi.
3. Hàm giả luôn trả lỗi 404 → xác nhận raise ngay ở lần gọi đầu tiên (không retry).

**Verify write_back không raise khi Drupal lỗi:** test riêng gọi `write_back()` với `BASE_URL` trỏ tới địa chỉ không tồn tại (VD `http://localhost:1`), xác nhận hàm return `None` bình thường (không raise), và có log warning in ra (kiểm tra bằng mắt qua console, không assert nội dung log).

**Verify không phá vỡ hành vi cũ:** chạy lại `scripts/run_all_samples.py` trên Drupal thật đang chạy bình thường, xác nhận cả 8 bài vẫn chạy và ghi-ngược thành công như trước (retry không kích hoạt khi không có lỗi).

## 6. Ngoài phạm vi

- Retry cho LLM call (`ai_core.call_agent()`) - đã có sẵn từ Anthropic SDK (mục 1).
- Retry cho `brand_node` - vẫn là stub, không gọi API nào.
- Gold set collection, UI báo cáo, Brand Voice Agent (RAG) - các sub-project riêng tiếp theo của Sprint 2.
- Circuit breaker / giới hạn tổng thời gian retry trên toàn bộ pipeline (VD nếu Drupal sập hẳn) - không có yêu cầu cụ thể nào từ `architecture.md` về việc này, không tự thêm.
