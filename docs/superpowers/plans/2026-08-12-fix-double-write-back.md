# Fix Double Write-Back Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bảo đảm worker production chỉ PATCH kết quả AI về Drupal đúng một lần cho mỗi job thành công, trong khi các script chạy graph thủ công vẫn giữ hành vi write-back hiện có.

**Architecture:** `build_graph()` nhận cờ keyword-only `include_write_back`, mặc định `True` để không phá `run_all_samples.py` và `smoke_test_graph.py`. Worker gọi graph với `include_write_back=False`, sau đó tiếp tục là tầng duy nhất ghi audit, xử lý retry và PATCH. Test tích hợp offline giữ graph/worker thật, chỉ thay các biên ngoài (Drupal, agent, audit, queue) bằng fake/spy.

**Tech Stack:** Python 3.12, LangGraph, các test script `assert` hiện có; không gọi Anthropic, Drupal hay PostgreSQL thật.

## Global Constraints

- Không gọi API trả phí và không chạy E1/E5.
- Không thay đổi scoring, rubric, prompt, agent output hoặc content hash.
- Giữ `build_graph()` mặc định có write-back cho hai script thủ công hiện hữu.
- Worker production phải yêu cầu graph không write-back và tự sở hữu audit/retry/PATCH.
- Test phải được quan sát đỏ trên code hiện tại trước khi sửa production.
- Chỉ cập nhật tài liệu sau khi test tái hiện và fix đã xanh.

---

### Task 1: Tái hiện double write-back tại ranh giới graph–worker

**Files:**
- Create: `multiagent/scripts/test_worker_graph_integration.py`
- Read: `multiagent/src/worker.py`
- Read: `multiagent/src/graph.py`

**Interfaces:**
- Consumes: `worker.chay_mot_job(conn, job)` với dependency mặc định của graph/write-back.
- Produces: regression test quan sát số lần transport PATCH được gọi qua một spy dùng chung.

- [ ] **Step 1: Kiểm tra baseline liên quan**

Run:

```powershell
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_report_json.py
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_per_field_report.py
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_worker.py
```

Expected: hai test thuần offline PASS; `test_worker.py` PASS nếu PostgreSQL local sẵn sàng, nếu không phải báo `[SKIP]` rõ ràng chứ không coi là PASS.

- [ ] **Step 2: Viết test tích hợp tối thiểu**

Test phải dùng `worker.chay_mot_job()` thật và để worker tự gọi `build_graph()`. Chỉ thay `graph.fetch_content`, bốn `agent.run`, `graph.write_back` và `drupal_client.write_back` bằng fake/spy; thay `audit.da_cham`, `audit.ghi`, `q.complete`, `q.fail` để không cần PostgreSQL. Payload agent dùng literal đầy đủ tối thiểu:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import drupal_client
import graph
import job_queue as q
import text_utils
import worker


def _ket_qua(score):
    return {"score": score, "issues": [], "flags": [], "criteria": []}


def test_worker_voi_graph_mac_dinh_chi_patch_mot_lan():
    fields = {
        "title": "Huong dan sac xe dien",
        "body": "<p>Noi dung mau day du de chay graph.</p>",
        "summary": "Tom tat mau",
        "meta_description": "Mo ta mau",
        "url_alias": "/huong-dan-sac-xe-dien",
        "image_alt": "Xe dien dang sac",
    }
    job = {
        "id": 901,
        "node_id": "00000000-0000-0000-0000-000000000901",
        "content_hash": text_utils.content_hash(fields),
        "attempts": 1,
    }
    patch_calls = []

    def patch_spy(**payload):
        patch_calls.append(payload)
        return True

    replacements = [
        (graph, "fetch_content", lambda node_id: {
            "fields": fields, "raw_content": {"data": {}}}),
        (graph.content_quality, "run", lambda article: _ket_qua(80.0)),
        (graph.seo, "run", lambda article: _ket_qua(80.0)),
        (graph.brand_voice, "run",
         lambda article, **keys: _ket_qua(80.0)),
        (graph.compliance, "run",
         lambda article, **keys: _ket_qua(80.0)),
        (graph, "write_back", patch_spy),
        (drupal_client, "write_back", patch_spy),
        (audit, "da_cham", lambda conn, node_id, content_hash: None),
        (audit, "ghi", lambda conn, **data: 1),
        (q, "complete", lambda conn, job_id: None),
        (q, "fail", lambda *args: (_ for _ in ()).throw(
            AssertionError(f"job khong duoc fail: {args}"))),
    ]
    originals = [(obj, name, getattr(obj, name))
                 for obj, name, replacement in replacements]
    for obj, name, replacement in replacements:
        setattr(obj, name, replacement)
    try:
        result = worker.chay_mot_job(None, job)
    finally:
        for obj, name, original in reversed(originals):
            setattr(obj, name, original)

    assert result == q.DONE, result
    assert len(patch_calls) == 1, (
        f"moi job chi duoc PATCH mot lan, thuc te {len(patch_calls)}"
    )


if __name__ == "__main__":
    test_worker_voi_graph_mac_dinh_chi_patch_mot_lan()
    print("[PASS] worker + graph mac dinh chi PATCH mot lan")
```

File phải tự gọi test trong `if __name__ == "__main__"` theo convention của repository.

- [ ] **Step 3: Chạy test để xác nhận RED**

Run:

```powershell
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_worker_graph_integration.py
```

Expected: FAIL đúng tại assertion số PATCH, diagnostic cho biết thực tế là `2`. Nếu lỗi import/schema hoặc actual không phải `2`, quay lại điều tra thay vì sửa production.

---

### Task 2: Cho worker dùng graph không side effect

**Files:**
- Modify: `multiagent/src/graph.py:1-12,328-350`
- Modify: `multiagent/src/worker.py:85-88`
- Test: `multiagent/scripts/test_worker_graph_integration.py`

**Interfaces:**
- Consumes: `build_graph(*, include_write_back: bool = True)`.
- Produces: graph mặc định giữ pipeline thủ công có PATCH; worker gọi `build_graph(include_write_back=False)` và chỉ worker PATCH sau audit.

- [ ] **Step 1: Thêm lựa chọn topology tối thiểu**

Đổi chữ ký và cạnh cuối trong `graph.py`:

```python
def build_graph(*, include_write_back: bool = True):
    graph = StateGraph(ContentReviewState)
    # ... các node/edge phân tích giữ nguyên ...
    if include_write_back:
        graph.add_node("write_back", write_back_node)
        graph.add_edge("aggregator", "write_back")
        graph.add_edge("write_back", END)
    else:
        graph.add_edge("aggregator", END)
    return graph.compile()
```

Không tạo hai bản topology và không đổi mặc định của public API hiện có.

- [ ] **Step 2: Worker tắt write-back bên trong graph**

Đổi đúng lời gọi mặc định:

```python
invoke = build_graph(include_write_back=False).invoke
```

Thêm comment ngắn: worker phải audit trước rồi mới write-back; graph không được tạo PATCH sớm nằm ngoài retry của worker.

- [ ] **Step 3: Chạy test để xác nhận GREEN**

Run:

```powershell
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_worker_graph_integration.py
```

Expected: PASS và spy có đúng một payload PATCH.

- [ ] **Step 4: Chạy regression liên quan**

Run:

```powershell
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_report_json.py
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_per_field_report.py
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_missing_agent_report.py
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_moi_test_deu_chay.py
```

Expected: tất cả PASS; meta-test nhận test file mới và xác nhận hàm test được gọi.

---

### Task 3: Đồng bộ bằng chứng và tài liệu

**Files:**
- Modify: `docs/technical-debt.md:725-880`
- Modify: `docs/architecture.md:540-580`
- Modify: `multiagent/src/graph.py:1-12`

**Interfaces:**
- Consumes: test RED/GREEN và topology đã xác minh ở Task 1–2.
- Produces: tài liệu nêu đúng quyền sở hữu side effect và trạng thái N1.

- [ ] **Step 1: Đóng N1 bằng bằng chứng**

Trong `technical-debt.md`, đổi N1 thành `✅ ĐÃ XÁC NHẬN VÀ SỬA`, ghi actual trước sửa là hai PATCH, nguyên nhân lịch sử là graph cũ có write-back trước khi worker queue được thêm, tên regression test và hành vi sau sửa. Cập nhật mục 8.8/checklist production tương ứng; không xoá lịch sử chẩn đoán.

- [ ] **Step 2: Sửa mô tả kiến trúc**

Trong `architecture.md`, sửa bước worker thành: `build_graph(include_write_back=False).invoke()` → `audit.ghi()` → worker PATCH. Nêu các script thủ công vẫn dùng mặc định `build_graph()` để giữ hành vi cũ.

- [ ] **Step 3: Kiểm tra toàn bộ diff**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Expected: chỉ plan, test, `graph.py`, `worker.py`, `technical-debt.md`, `architecture.md` thay đổi; không có whitespace error.

- [ ] **Step 4: Chạy full offline suite có sẵn**

Run từ `multiagent/`:

```powershell
$python = 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe'
$failed = @()
Get-ChildItem scripts\test_*.py | Sort-Object Name | ForEach-Object {
    & $python $_.FullName
    if ($LASTEXITCODE -ne 0) { $failed += $_.Name }
}
if ($failed.Count) { throw "Test failures: $($failed -join ', ')" }
```

Expected: exit code 0. Đọc output để liệt kê riêng `[SKIP]` do PostgreSQL hoặc dependency ngoài; không gọi script E1/E3/E5/E6 vì chúng không mang tiền tố `test_`.

- [ ] **Step 5: Commit trên nhánh cô lập sau khi người dùng chọn phương án hoàn tất**

```powershell
git add docs/superpowers/plans/2026-08-12-fix-double-write-back.md multiagent/scripts/test_worker_graph_integration.py multiagent/src/graph.py multiagent/src/worker.py docs/technical-debt.md docs/architecture.md
git commit -m "fix: prevent duplicate Drupal write-back"
```
