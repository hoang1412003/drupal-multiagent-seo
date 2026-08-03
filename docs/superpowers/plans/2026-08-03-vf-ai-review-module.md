# Module `vf_ai_review` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hiển thị kết quả đánh giá của hệ Multi-Agent ngay trong giao diện soạn bài Drupal — khối tổng quan ở cột phải và chú thích lỗi ngay dưới từng field.

**Architecture:** Python ghi thêm một field `field_ai_report_json` chứa báo cáo có cấu trúc (song song với chuỗi text đang có). Module Drupal `vf_ai_review` móc vào form soạn node qua `hook_form_node_form_alter()`, đọc field đó, và dựng hiển thị bằng lớp `AiReportRenderer` — lớp này **không phụ thuộc Drupal** nên test được bằng script PHP thuần. Module chỉ đọc, không bao giờ ghi.

**Tech Stack:** PHP 8.4 / Drupal 10.6.14 (admin theme Claro), Python 3.12. Không thêm dependency nào ở cả hai phía.

**Spec:** `docs/superpowers/specs/2026-08-03-vf-ai-review-module-design.md`

## Global Constraints

- Người thực hiện **chưa từng viết module Drupal**. Mỗi bước phải kèm lệnh kiểm tra cụ thể và nói rõ nhìn thấy gì thì biết là đúng.
- Chạy lệnh Drupal từ thư mục `drupal/`: `ddev drush ...`, `ddev exec php ...`. Chạy Python từ `multiagent/`: `.venv\Scripts\python.exe scripts\<file>.py`.
- Test là **script thuần** khớp style hiện có (in `[PASS]`/`[FAIL]`, thoát mã 1 khi hỏng). **KHÔNG** dùng pytest, **KHÔNG** cài PHPUnit.
- Comment/chuỗi tiếng Việt, khớp văn phong code hiện có (`graph.py`, `create_ai_fields.php`).
- Commit **KHÔNG** kèm trailer `Co-Authored-By: Claude`.
- **Module chỉ ĐỌC.** Không tính điểm, không gọi API, không sửa dữ liệu node.
- **Mọi chuỗi động phải escape** bằng `htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')`. Nội dung chứa trích dẫn từ bài viết và văn bản do LLM sinh → render thô là lỗ hổng XSS (`docs/prompt-injection.md` M4).
- **`final_score` phải phân biệt `null` với `0`.** Trong PHP `empty(0)` trả `TRUE` → bắt buộc dùng `=== NULL`.
- **Quy tắc ghép `content_hash` cố định, hai ngôn ngữ phải y hệt:** `sha256(title + "\n" + body + "\n" + summary + "\n" + meta_description)`.
- Chuỗi `field_ai_suggestions` **giữ nguyên không đổi một ký tự** — phần suy giảm mềm phải còn hiệu lực.
- Không đụng: 4 agent, Aggregator, cơ chế veto, `state.py`, `fetch_content()`.

---

## File Structure

**Phía Python:**
- Modify: `multiagent/src/drupal_client.py` — `write_back()` nhận thêm `report_json`, PATCH thêm 1 field.
- Modify: `multiagent/src/graph.py` — thêm `_content_hash()`, `_issue_to_json()`, `_build_report_json()`; `write_back_node` gọi write_back với report_json.
- Create: `multiagent/scripts/content_hash_fixture.json` — dữ liệu mẫu cho test hợp đồng 2 ngôn ngữ.
- Create: `multiagent/scripts/test_report_json.py` — test cấu trúc JSON + hash.

**Phía Drupal:**
- Modify: `drupal/scripts/create_ai_fields.php` — thêm field thứ 5.
- Create: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.info.yml` — khai báo module.
- Create: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.libraries.yml` — khai báo CSS.
- Create: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module` — hook, ánh xạ field, ẩn field AI.
- Create: `drupal/web/modules/custom/vf_ai_review/src/AiReportRenderer.php` — JSON → HTML đã escape. **PHP thuần, không import gì của Drupal.**
- Create: `drupal/web/modules/custom/vf_ai_review/css/vf_ai_review.css` — màu theo severity.
- Create: `drupal/scripts/test_ai_report_renderer.php` — test lớp render + hash.

**Ranh giới trách nhiệm:** `AiReportRenderer` biết *báo cáo trông thế nào*; `vf_ai_review.module` biết *form Drupal có những gì và gắn vào đâu*. Đổi giao diện thì sửa file đầu, đổi cách móc vào Drupal thì sửa file sau.

---

## GIAI ĐOẠN 1 — Phía Python (Task 1–4)

Làm trước để khi sang phía PHP đã có JSON thật trong DB làm việc trên đó, thay vì vừa học Drupal vừa đoán dữ liệu trông thế nào.

---

## Task 1: Thêm field thứ 5 vào Drupal

**Files:**
- Modify: `drupal/scripts/create_ai_fields.php`

**Interfaces:**
- Produces: field `field_ai_report_json` kiểu `string_long` trên content type `article`.

- [ ] **Step 1: Thêm field vào script**

Trong `drupal/scripts/create_ai_fields.php`, thêm ngay sau khối `field_ai_suggestions`:

```php
// (OUTPUT) Báo cáo có cấu trúc cho module vf_ai_review render.
// Dùng string_long KHÔNG phải text_long: text_long chạy qua bộ lọc văn bản
// của Drupal và sẽ bóp méo JSON (đổi ký tự, tự chèn <p>).
create_field('field_ai_report_json', 'string_long', 'article', 'AI Report (JSON)');
```

Và sửa dòng cuối cùng của file:

```php
echo "\nHoan tat tao 5 field.\n";
```

- [ ] **Step 2: Chạy script**

Run (từ `drupal/`): `ddev drush php:script scripts/create_ai_fields.php`
Expected: in `Da tao field storage: field_ai_report_json (string_long)` và `Da gan field vao bundle 'article'`. Bốn field cũ in `da ton tai, bo qua`.

- [ ] **Step 3: Xác nhận field đã có**

Run (từ `drupal/`): `ddev drush field:info node article --format=table`
Expected: bảng có dòng `field_ai_report_json` kiểu `string_long`.

- [ ] **Step 4: Commit**

```bash
git add drupal/scripts/create_ai_fields.php
git commit -m "feat: them field_ai_report_json cho module vf_ai_review"
```

---

## Task 2: Hàm băm nội dung + test hợp đồng 2 ngôn ngữ

**Files:**
- Modify: `multiagent/src/graph.py`
- Create: `multiagent/scripts/content_hash_fixture.json`
- Create test: `multiagent/scripts/test_report_json.py`

**Interfaces:**
- Produces: `graph._content_hash(fields: dict) -> str` — sha256 hex 64 ký tự.
- Produces: file fixture với khoá `fields` và `expected_sha256`, dùng chung cho test phía PHP ở Task 6.

- [ ] **Step 1: Tạo file fixture**

Tạo `multiagent/scripts/content_hash_fixture.json`. Giá trị `expected_sha256` đã tính sẵn và **đã kiểm chứng cả Python lẫn PHP đều ra đúng nó**:

```json
{
  "_note": "Du lieu mau cho test hop dong giua Python va PHP. Ca hai phai tinh ra cung expected_sha256. Ben nao troi lech thi test ben do do.",
  "fields": {
    "title": "Hướng dẫn sạc pin ô tô điện VinFast",
    "body": "<p>Nội dung bài viết mẫu.</p>",
    "summary": "Tóm tắt ngắn",
    "meta_description": "Mô tả cho SEO"
  },
  "expected_sha256": "eaa72cddd3e11b26dde58e74b13c9f8bee7011a9f6706fdcb7595aab72f82536"
}
```

- [ ] **Step 2: Viết test trước**

Tạo `multiagent/scripts/test_report_json.py`:

```python
"""Test dung bao cao JSON ghi vao field_ai_report_json.

Khong goi LLM, khong can Drupal. Chay:
    .venv\\Scripts\\python.exe scripts\\test_report_json.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import _content_hash

FIXTURE = os.path.join(os.path.dirname(__file__), "content_hash_fixture.json")


def test_hash_khop_fixture():
    """HOP DONG 2 NGON NGU: PHP doc CUNG file nay va phai ra CUNG gia tri.

    Test nay do la lop bao ve duy nhat chong troi lech quy tac ghep chuoi -
    neu lech, bang canh bao 'noi dung da thay doi' se hien sai mai mai ma
    khong co gi bao.
    """
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    assert _content_hash(fx["fields"]) == fx["expected_sha256"], _content_hash(fx["fields"])
    print("[PASS] hash khop fixture (hop dong voi phia PHP)")


def test_hash_tat_dinh():
    fields = {"title": "A", "body": "B", "summary": "C", "meta_description": "D"}
    assert len({_content_hash(fields) for _ in range(20)}) == 1
    print("[PASS] cung dau vao -> cung hash")


def test_doi_mot_ky_tu_thi_hash_doi():
    a = {"title": "A", "body": "B", "summary": "C", "meta_description": "D"}
    b = {"title": "A", "body": "B.", "summary": "C", "meta_description": "D"}
    assert _content_hash(a) != _content_hash(b)
    print("[PASS] doi 1 ky tu trong body -> hash doi")


def test_field_thieu_coi_nhu_rong():
    assert _content_hash({"title": "A"}) == _content_hash(
        {"title": "A", "body": "", "summary": "", "meta_description": ""}
    )
    print("[PASS] field thieu = chuoi rong, khong loi")


def test_field_none_coi_nhu_rong():
    """fetch_content tra chuoi rong, nhung phong thu voi None de chac chan."""
    assert _content_hash({"title": "A", "body": None}) == _content_hash({"title": "A"})
    print("[PASS] field None = chuoi rong, khong loi")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_hash_khop_fixture,
        test_hash_tat_dinh,
        test_doi_mot_ky_tu_thi_hash_doi,
        test_field_thieu_coi_nhu_rong,
        test_field_none_coi_nhu_rong,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 3: Chạy test để xác nhận FAIL**

Run (từ `multiagent/`): `.venv\Scripts\python.exe scripts\test_report_json.py`
Expected: FAIL với `ImportError: cannot import name '_content_hash' from 'graph'`.

- [ ] **Step 4: Viết hàm băm**

Trong `multiagent/src/graph.py`, khối import hiện tại bắt đầu bằng `from langgraph.graph import ...`. Thêm `import hashlib` thành **dòng đầu tiên của khối import**, ngay sau docstring của file:

```python
import hashlib

from langgraph.graph import END, START, StateGraph
```

Rồi thêm hàm này ngay trước `def write_back_node`:

```python
# Các field tham gia tính content_hash, ĐÚNG THỨ TỰ NÀY. Phía PHP
# (AiReportRenderer::contentHash) phải ghép y hệt, nếu lệch thì băng cảnh báo
# "nội dung đã thay đổi" hiện sai vĩnh viễn. Có test hợp đồng dùng chung file
# scripts/content_hash_fixture.json để bắt sai lệch này.
_HASH_FIELDS = ("title", "body", "summary", "meta_description")


def _content_hash(fields: dict) -> str:
    """Băm nội dung đã chấm, để sau này biết bài có bị sửa sau khi chấm không.

    Dùng hash chứ KHÔNG dùng mốc thời gian `changed` của node: chính lệnh
    PATCH của write_back() làm `changed` nhảy, nên so mốc đó sẽ luôn báo
    "nội dung đã đổi" ngay sau khi chấm (spec mục 4.3, có bằng chứng đo trên
    DB). Hash chỉ đổi khi nội dung thật sự đổi.
    """
    ghep = "\n".join(str(fields.get(k) or "") for k in _HASH_FIELDS)
    return hashlib.sha256(ghep.encode("utf-8")).hexdigest()
```

- [ ] **Step 5: Chạy test để xác nhận PASS**

Run (từ `multiagent/`): `.venv\Scripts\python.exe scripts\test_report_json.py`
Expected: 5 dòng `[PASS]`, thoát mã 0.

- [ ] **Step 6: Commit**

```bash
git add multiagent/src/graph.py multiagent/scripts/test_report_json.py multiagent/scripts/content_hash_fixture.json
git commit -m "feat: content_hash phat hien bai bi sua sau khi cham"
```

---

## Task 3: Dựng cấu trúc báo cáo JSON

**Files:**
- Modify: `multiagent/src/graph.py`
- Modify test: `multiagent/scripts/test_report_json.py`

**Interfaces:**
- Consumes: `_content_hash()` (Task 2), `AGENT_LABELS` và `ISSUE_LIST_KEYS` (đã có trong `graph.py`).
- Produces: `graph._build_report_json(state: ContentReviewState) -> dict` — trả đúng cấu trúc spec mục 4.2.

- [ ] **Step 1: Thêm test trước**

Thêm vào `multiagent/scripts/test_report_json.py`, ngay trước khối `if __name__`:

```python
from graph import _build_report_json

STATE_MAU = {
    "node_id": "n1",
    "fields": {"title": "Tiêu đề", "body": "<p>Nội dung</p>",
               "summary": "Tóm tắt", "meta_description": "Mô tả"},
    "report": {
        "node_id": "n1",
        "final_score": 76.5,
        "decision": "needs_revision",
        "missing_agents": [],
        "details": {
            "seo": {"score": 75, "issues": [
                {"field": "title", "type": "Độ dài tiêu đề",
                 "suggestion": "Rút xuống 50-60 ký tự"}]},
            "compliance": {"score": 85, "flags": [
                {"field": "body", "severity": "medium",
                 "rule": "Claim thiếu điều kiện đo",
                 "excerpt": "chạy được 420km"}]},
        },
    },
}


def test_cau_truc_co_ban():
    j = _build_report_json(STATE_MAU)
    assert j["version"] == 1
    assert j["decision"] == "needs_revision"
    assert j["final_score"] == 76.5
    assert len(j["content_hash"]) == 64
    assert j["scored_at"], "phai co moc thoi gian"
    print("[PASS] cau truc co ban day du")


def test_issue_gom_dung_field():
    j = _build_report_json(STATE_MAU)
    assert set(j["fields"]) == {"title", "body"}, j["fields"]
    assert len(j["fields"]["title"]) == 1
    assert len(j["fields"]["body"]) == 1
    print("[PASS] moi issue gom dung field cua no")


def test_severity_chi_tu_compliance():
    """3 agent kia KHONG dinh nghia muc nghiem trong -> null.

    Co y khong bia: rubrics.md muc 6.1 chu truong severity phai tra bang tat
    dinh theo ma tieu chi, tu che mot muc o tang hien thi la di nguoc huong do.
    """
    j = _build_report_json(STATE_MAU)
    assert j["fields"]["body"][0]["severity"] == "medium"
    assert j["fields"]["title"][0]["severity"] is None
    print("[PASS] severity chi lay tu Compliance")


def test_compliance_message_la_none():
    """Compliance khong co truong goi y sua. Dat message = rule se khien giao
    dien in cung mot cau hai lan."""
    j = _build_report_json(STATE_MAU)
    muc = j["fields"]["body"][0]
    assert muc["label"] == "Claim thiếu điều kiện đo"
    assert muc["message"] is None, muc
    assert muc["excerpt"] == "chạy được 420km"
    print("[PASS] Compliance: label co, message None, excerpt co")


def test_agent_thuong_khong_co_excerpt():
    j = _build_report_json(STATE_MAU)
    muc = j["fields"]["title"][0]
    assert muc["agent"] == "SEO"
    assert muc["label"] == "Độ dài tiêu đề"
    assert muc["message"] == "Rút xuống 50-60 ký tự"
    assert muc["excerpt"] is None
    print("[PASS] agent thuong: label + message, khong excerpt")


def test_compliance_loi_thi_score_none():
    state = {
        "node_id": "n1",
        "fields": {"title": "T"},
        "report": {"final_score": None, "decision": "needs_revision",
                   "missing_agents": ["compliance"],
                   "note": "Không thể xác minh Compliance",
                   "details": {"compliance": None}},
    }
    j = _build_report_json(state)
    assert j["final_score"] is None, "phai giu None, KHONG duoc thanh 0"
    assert j["note"], "phai co note giai thich"
    assert j["missing_agents"] == ["compliance"]
    print("[PASS] Compliance loi -> final_score None, co note")


def test_veto_reason_duoc_giu():
    state = {
        "node_id": "n1", "fields": {"title": "T"},
        "report": {"final_score": 90.0, "decision": "rejected",
                   "missing_agents": [],
                   "veto_reason": "Bị từ chối do vi phạm Compliance",
                   "details": {}},
    }
    j = _build_report_json(state)
    assert "Compliance" in j["veto_reason"]
    print("[PASS] veto_reason duoc giu nguyen")


def test_agent_loi_khong_lam_sap():
    state = {"node_id": "n1", "fields": {"title": "T"},
             "report": {"final_score": 70.0, "decision": "needs_revision",
                        "missing_agents": ["seo"],
                        "details": {"seo": None, "compliance": {"score": 80, "flags": []}}}}
    j = _build_report_json(state)
    assert j["fields"] == {}
    print("[PASS] agent tra None -> bo qua, khong sap")


def test_issue_khong_co_field_thi_bo_qua():
    """Issue khong gan field khong hien duoc duoi widget nao ca."""
    state = {"node_id": "n1", "fields": {"title": "T"},
             "report": {"final_score": 70.0, "decision": "needs_revision",
                        "missing_agents": [],
                        "details": {"seo": {"score": 70, "issues": [
                            {"type": "Loi chung", "suggestion": "x"}]}}}}
    j = _build_report_json(state)
    assert j["fields"] == {}, j["fields"]
    print("[PASS] issue khong co field -> bo qua")
```

Và thêm 9 tên hàm đó vào tuple trong khối `if __name__ == "__main__":`.

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run (từ `multiagent/`): `.venv\Scripts\python.exe scripts\test_report_json.py`
Expected: FAIL với `ImportError: cannot import name '_build_report_json'`.

- [ ] **Step 3: Viết hàm dựng JSON**

Trong `multiagent/src/graph.py`, thêm `from datetime import datetime, timezone` vào khối import. Rồi thêm ngay sau `_content_hash`:

```python
def _issue_to_json(agent_key: str, issue: dict) -> dict:
    """Một issue/flag của agent -> một mục trong báo cáo JSON.

    Compliance có hình dạng khác 3 agent kia: nó dùng {rule, excerpt,
    severity} và KHÔNG có trường gợi ý sửa, nên `message` để None. Đặt
    message = rule sẽ khiến giao diện in cùng một câu hai lần.
    """
    if agent_key == "compliance":
        return {
            "agent": AGENT_LABELS[agent_key],
            "label": issue.get("rule", ""),
            "message": None,
            "excerpt": issue.get("excerpt") or None,
            "severity": issue.get("severity"),
        }
    return {
        "agent": AGENT_LABELS.get(agent_key, agent_key),
        "label": issue.get("type", ""),
        "message": issue.get("suggestion") or None,
        "excerpt": None,
        # Chỉ Compliance định nghĩa mức nghiêm trọng. KHÔNG bịa cho 3 agent
        # kia - docs/rubrics.md mục 6.1 chủ trương severity phải tra bảng
        # tất định theo mã tiêu chí.
        "severity": None,
    }


def _build_report_json(state: ContentReviewState) -> dict:
    """Dựng báo cáo có cấu trúc cho module vf_ai_review render.

    Chạy song song với chuỗi text ghi vào field_ai_suggestions - chuỗi đó
    KHÔNG đổi, để khi module chưa bật thì vẫn đọc được (suy giảm mềm).
    """
    report = state.get("report") or {}
    theo_field: dict = {}

    for agent_key, result in (report.get("details") or {}).items():
        if not isinstance(result, dict):
            continue      # agent lỗi -> đã phản ánh ở missing_agents/note
        for key in ISSUE_LIST_KEYS:
            for issue in result.get(key, []):
                if not isinstance(issue, dict):
                    continue
                field = issue.get("field")
                if not field:
                    continue      # không gắn field thì không hiện dưới widget nào
                theo_field.setdefault(field, []).append(
                    _issue_to_json(agent_key, issue)
                )

    return {
        "version": 1,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": _content_hash(state.get("fields") or {}),
        "decision": report.get("decision"),
        "final_score": report.get("final_score"),
        "note": report.get("note"),
        "veto_reason": report.get("veto_reason"),
        "missing_agents": report.get("missing_agents", []),
        "fields": theo_field,
    }
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run (từ `multiagent/`): `.venv\Scripts\python.exe scripts\test_report_json.py`
Expected: 14 dòng `[PASS]`, thoát mã 0.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/graph.py multiagent/scripts/test_report_json.py
git commit -m "feat: dung bao cao JSON co cau truc cho module UI"
```

---

## Task 4: Ghi JSON vào Drupal

**Files:**
- Modify: `multiagent/src/drupal_client.py`
- Modify: `multiagent/src/graph.py` (hàm `write_back_node`)
- Modify test: `multiagent/scripts/test_report_json.py`

**Interfaces:**
- Consumes: `_build_report_json()` (Task 3).
- Produces: `drupal_client.write_back(node_id, status, score, suggestions, report_json=None)` — `report_json` là dict, hàm tự `json.dumps`. Mặc định `None` để lời gọi cũ không đổi hành vi.

- [ ] **Step 1: Thêm test trước**

Thêm vào `multiagent/scripts/test_report_json.py`, ngay trước khối `if __name__`:

```python
def test_write_back_gui_ca_hai_field():
    """write_back phai PATCH ca field_ai_suggestions lan field_ai_report_json."""
    import drupal_client

    da_gui = {}

    def patch_gia(method, url, **kwargs):
        da_gui.update(kwargs["json"]["data"]["attributes"])

        class R:
            pass
        return R()

    that = drupal_client._request_with_retry
    drupal_client._request_with_retry = patch_gia
    try:
        drupal_client.write_back(
            node_id="n1", status="publish", score=80.0,
            suggestions="text", report_json={"version": 1, "fields": {}},
        )
    finally:
        drupal_client._request_with_retry = that

    assert da_gui["field_ai_suggestions"] == "text"
    assert "field_ai_report_json" in da_gui, da_gui
    assert json.loads(da_gui["field_ai_report_json"])["version"] == 1
    print("[PASS] write_back gui ca 2 field")


def test_write_back_khong_co_report_json_van_chay():
    """Loi goi cu (khong truyen report_json) khong duoc doi hanh vi."""
    import drupal_client

    da_gui = {}

    def patch_gia(method, url, **kwargs):
        da_gui.update(kwargs["json"]["data"]["attributes"])

        class R:
            pass
        return R()

    that = drupal_client._request_with_retry
    drupal_client._request_with_retry = patch_gia
    try:
        drupal_client.write_back(node_id="n1", status="publish", score=80.0,
                                 suggestions="text")
    finally:
        drupal_client._request_with_retry = that

    assert "field_ai_report_json" not in da_gui, da_gui
    print("[PASS] khong truyen report_json -> khong gui field do")


def test_json_giu_dau_tieng_viet():
    """ensure_ascii=False de JSON trong DB doc duoc bang mat khi debug."""
    import drupal_client

    da_gui = {}

    def patch_gia(method, url, **kwargs):
        da_gui.update(kwargs["json"]["data"]["attributes"])

        class R:
            pass
        return R()

    that = drupal_client._request_with_retry
    drupal_client._request_with_retry = patch_gia
    try:
        drupal_client.write_back(node_id="n1", status="publish", score=80.0,
                                 suggestions="t", report_json={"x": "Tiêu đề"})
    finally:
        drupal_client._request_with_retry = that

    assert "Tiêu đề" in da_gui["field_ai_report_json"], da_gui["field_ai_report_json"]
    print("[PASS] JSON giu nguyen dau tieng Viet")
```

Và thêm 3 tên hàm đó vào tuple trong khối `if __name__`.

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run (từ `multiagent/`): `.venv\Scripts\python.exe scripts\test_report_json.py`
Expected: FAIL — `write_back() got an unexpected keyword argument 'report_json'`.

- [ ] **Step 3: Sửa `drupal_client.write_back()`**

Thêm `import json` vào đầu `multiagent/src/drupal_client.py` (trước `import logging`).

Đổi chữ ký và phần dựng payload:

```python
def write_back(
    node_id: str, status: str, score: Optional[float], suggestions: str,
    report_json: Optional[dict] = None,
) -> None:
```

Trong docstring, thêm đoạn:

```
    `report_json` là báo cáo có cấu trúc cho module vf_ai_review render
    (docs/superpowers/specs/2026-08-03-vf-ai-review-module-design.md).
    Mặc định None để lời gọi cũ không đổi hành vi.
```

Đổi phần `attributes`:

```python
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
```

- [ ] **Step 4: Sửa `graph.write_back_node`**

Trong `multiagent/src/graph.py`, đổi lời gọi `write_back(...)` ở cuối `write_back_node` thành:

```python
    write_back(
        node_id=state["node_id"],
        # final_score = None nghĩa là CHƯA chấm được (Compliance lỗi), khác hẳn
        # với 0 điểm. Giữ nguyên None để Drupal hiển thị field trống thay vì
        # "0 điểm" - xem spec mục 5.1 "Agent lỗi không bị cho điểm 0".
        status=state["decision"],
        score=state["final_score"],
        suggestions="\n".join(lines) or "Không có gợi ý sửa.",
        report_json=_build_report_json(state),
    )
```

- [ ] **Step 5: Chạy test để xác nhận PASS**

Run (từ `multiagent/`): `.venv\Scripts\python.exe scripts\test_report_json.py`
Expected: 17 dòng `[PASS]`, thoát mã 0.

- [ ] **Step 6: Chạy lại toàn bộ test Python — không được hỏng gì**

Run (từ `multiagent/`):

```bash
for t in scripts/test_*.py; do printf "%-30s" "$(basename $t .py)"; .venv/Scripts/python.exe $t > /dev/null 2>&1 && echo OK || echo FAIL; done
```

Expected: **19/19 OK** (18 bộ cũ + `test_report_json` mới). Đặc biệt `test_write_back_failure` phải còn OK — nó gọi `write_back()` không truyền `report_json`.

- [ ] **Step 7: Chấm lại một bài thật để có JSON trong DB**

Cần DDEV đang chạy. Run (từ `multiagent/`):

```bash
HF_HUB_OFFLINE=1 .venv/Scripts/python.exe scripts/smoke_test_graph.py d115f055-e97a-4757-af9e-6b4f53e1f408
```

Expected: pipeline chạy hết, in report JSON ra màn hình.

- [ ] **Step 8: Xác nhận JSON đã nằm trong DB**

Run (từ `drupal/`):

```bash
ddev mysql -e "SELECT LEFT(field_ai_report_json_value, 200) FROM node__field_ai_report_json WHERE entity_id = 1;"
```

Expected: in ra chuỗi JSON bắt đầu bằng `{"version": 1, "scored_at": ...`. **Nếu rỗng** thì kiểm lại Task 1 (field đã tạo chưa) và Step 4.

- [ ] **Step 9: Commit**

```bash
git add multiagent/src/drupal_client.py multiagent/src/graph.py multiagent/scripts/test_report_json.py
git commit -m "feat: write_back ghi them field_ai_report_json"
```

---

## GIAI ĐOẠN 2 — Phía Drupal (Task 5–11)

---

## Task 5: Scaffold module — chỉ để Drupal nhận diện

**Files:**
- Create: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.info.yml`

**Interfaces:**
- Produces: module `vf_ai_review` bật được bằng `ddev drush en vf_ai_review -y`.

Tách riêng task này có chủ đích: xác nhận Drupal nhận diện được module **trước khi** viết logic, để nếu sai cấu trúc thư mục thì phát hiện ngay thay vì lẫn với lỗi code.

- [ ] **Step 1: Tạo thư mục**

```bash
mkdir -p drupal/web/modules/custom/vf_ai_review/src drupal/web/modules/custom/vf_ai_review/css
```

- [ ] **Step 2: Tạo file khai báo**

Tạo `drupal/web/modules/custom/vf_ai_review/vf_ai_review.info.yml`:

```yaml
name: 'VF AI Review'
type: module
description: 'Hiển thị kết quả đánh giá của hệ Multi-Agent AI trong giao diện soạn bài.'
core_version_requirement: ^10 || ^11
package: 'VF O2O'
```

File `.info.yml` **là thứ khiến Drupal biết module tồn tại** — không có nó thì thư mục chỉ là mấy file PHP nằm im.

- [ ] **Step 3: Bật module**

Run (từ `drupal/`): `ddev drush en vf_ai_review -y`
Expected: in `[success] Successfully enabled: vf_ai_review`.

Nếu báo `Could not find module` → kiểm lại đường dẫn thư mục và tên file (`vf_ai_review.info.yml`, đúng dấu gạch dưới).

- [ ] **Step 4: Xác nhận module đang bật**

Run (từ `drupal/`): `ddev drush pm:list --status=enabled --filter=vf_ai_review`
Expected: bảng có dòng `vf_ai_review` trạng thái `Enabled`.

- [ ] **Step 5: Xác nhận form soạn bài chưa đổi gì**

Mở `http://drupal.ddev.site/node/1/edit`.
Expected: form hiện bình thường, **vẫn thấy 4 field AI dạng ô nhập liệu** ở cuối (chưa ẩn — đúng, vì chưa viết hook).

- [ ] **Step 6: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_review/vf_ai_review.info.yml
git commit -m "feat: scaffold module vf_ai_review"
```

---

## Task 6: `AiReportRenderer` — lớp dựng HTML, PHP thuần

**Files:**
- Create: `drupal/web/modules/custom/vf_ai_review/src/AiReportRenderer.php`
- Create test: `drupal/scripts/test_ai_report_renderer.php`

**Interfaces:**
- Consumes: `multiagent/scripts/content_hash_fixture.json` (Task 2).
- Produces:
  - `AiReportRenderer::contentHash(array $fields): string`
  - `AiReportRenderer::decode(?string $json): ?array`
  - `AiReportRenderer::overviewHtml(?array $report, bool $stale, bool $loiJson = FALSE): string`
  - `AiReportRenderer::fieldNotesHtml(?array $report, string $fieldKey): string`

Cả 4 phương thức **không dùng gì của Drupal** — vào là mảng/chuỗi, ra là chuỗi HTML đã escape. Nhờ đó test được bằng script PHP thuần.

- [ ] **Step 1: Viết test trước**

Tạo `drupal/scripts/test_ai_report_renderer.php`:

```php
<?php

/**
 * Test lop AiReportRenderer - PHP thuan, khong can Drupal bootstrap.
 *
 * Chay (tu drupal/): ddev exec php scripts/test_ai_report_renderer.php
 */

require_once __DIR__ . '/../web/modules/custom/vf_ai_review/src/AiReportRenderer.php';

use Drupal\vf_ai_review\AiReportRenderer;

$failed = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $failed;
  if ($dieu_kien) {
    echo "[PASS] $ten\n";
  }
  else {
    $failed = TRUE;
    echo "[FAIL] $ten" . ($chi_tiet ? " - $chi_tiet" : '') . "\n";
  }
}

$r = new AiReportRenderer();

$bao_cao = [
  'version' => 1,
  'scored_at' => '2026-08-03T09:45:17+00:00',
  'content_hash' => 'abc',
  'decision' => 'needs_revision',
  'final_score' => 76.5,
  'note' => NULL,
  'veto_reason' => NULL,
  'missing_agents' => [],
  'fields' => [
    'title' => [
      ['agent' => 'SEO', 'label' => 'Độ dài tiêu đề',
       'message' => 'Rút xuống 50-60 ký tự', 'excerpt' => NULL, 'severity' => NULL],
    ],
    'body' => [
      ['agent' => 'Compliance', 'label' => 'Claim thiếu điều kiện đo',
       'message' => NULL, 'excerpt' => 'chạy được 420km', 'severity' => 'medium'],
    ],
  ],
];

// --- HOP DONG 2 NGON NGU -----------------------------------------------
$fx = json_decode(file_get_contents(__DIR__ . '/../../multiagent/scripts/content_hash_fixture.json'), TRUE);
kiem(
  'hash khop fixture (hop dong voi phia Python)',
  AiReportRenderer::contentHash($fx['fields']) === $fx['expected_sha256'],
  AiReportRenderer::contentHash($fx['fields'])
);

kiem('field thieu = chuoi rong',
  AiReportRenderer::contentHash(['title' => 'A'])
  === AiReportRenderer::contentHash(['title' => 'A', 'body' => '', 'summary' => '', 'meta_description' => '']));

// --- decode -------------------------------------------------------------
kiem('decode JSON hop le', is_array($r->decode('{"version":1}')));
kiem('decode JSON hong -> NULL', $r->decode('{khong phai json') === NULL);
kiem('decode chuoi rong -> NULL', $r->decode('') === NULL);
kiem('decode NULL -> NULL', $r->decode(NULL) === NULL);

// --- overview -----------------------------------------------------------
$html = $r->overviewHtml($bao_cao, FALSE);
kiem('overview co de xuat', str_contains($html, 'Cần sửa'));
kiem('overview co diem', str_contains($html, '76.5'));
kiem('overview dem van de theo field', str_contains($html, 'Tiêu đề') && str_contains($html, 'Nội dung'));

$html_chua_cham = $r->overviewHtml(NULL, FALSE);
kiem('chua cham -> bao chua duoc danh gia', str_contains($html_chua_cham, 'Chưa được đánh giá'));

// Bon trang thai cua spec muc 6.1 phai PHAN BIET duoc. "Chua cham" (field
// trong) khac han "JSON hong" (co du lieu nhung doc khong duoc) - gop chung
// se khien loi du lieu bi hieu nham thanh binh thuong.
$html_hong = $r->overviewHtml(NULL, FALSE, TRUE);
kiem('JSON hong -> bao khong doc duoc', str_contains($html_hong, 'Không đọc được báo cáo'));
kiem('JSON hong KHAC chua cham', !str_contains($html_hong, 'Chưa được đánh giá'), $html_hong);

// --- CAP DOI CHUNG null vs 0 --------------------------------------------
$null_score = $bao_cao;
$null_score['final_score'] = NULL;
$h1 = $r->overviewHtml($null_score, FALSE);
kiem('final_score NULL -> "chua danh gia duoc"', str_contains($h1, 'chưa đánh giá được'));
kiem('final_score NULL -> KHONG in "0"', !str_contains($h1, '>0 /'), $h1);

$zero_score = $bao_cao;
$zero_score['final_score'] = 0;
$h2 = $r->overviewHtml($zero_score, FALSE);
kiem('final_score 0 -> in "0 / 100"', str_contains($h2, '0 / 100'), $h2);

// --- veto + stale -------------------------------------------------------
$veto = $bao_cao;
$veto['decision'] = 'rejected';
$veto['veto_reason'] = 'Bị từ chối do vi phạm Compliance';
kiem('veto_reason hien ra', str_contains($r->overviewHtml($veto, FALSE), 'vi phạm Compliance'));

kiem('stale -> hien bang canh bao', str_contains($r->overviewHtml($bao_cao, TRUE), 'đã thay đổi'));
kiem('khong stale -> khong hien canh bao', !str_contains($r->overviewHtml($bao_cao, FALSE), 'đã thay đổi'));

// --- fieldNotes ---------------------------------------------------------
$note_title = $r->fieldNotesHtml($bao_cao, 'title');
kiem('chu thich title co ten agent', str_contains($note_title, 'SEO'));
kiem('chu thich title co goi y', str_contains($note_title, 'Rút xuống 50-60'));

$note_body = $r->fieldNotesHtml($bao_cao, 'body');
kiem('chu thich body co excerpt', str_contains($note_body, 'chạy được 420km'));
kiem('chu thich body co class severity', str_contains($note_body, 'vf-ai-sev-medium'));

kiem('field khong co loi -> chuoi rong', $r->fieldNotesHtml($bao_cao, 'summary') === '');
kiem('bao cao NULL -> chuoi rong', $r->fieldNotesHtml(NULL, 'title') === '');

// --- XSS (QUAN TRONG NHAT) ----------------------------------------------
$xss = $bao_cao;
$xss['fields']['title'][0]['message'] = '<script>alert(1)</script>';
$xss['fields']['title'][0]['excerpt'] = '"><img src=x onerror=alert(1)>';
$h = $r->fieldNotesHtml($xss, 'title');
kiem('XSS: khong con the <script>', !str_contains($h, '<script>'), $h);
kiem('XSS: khong con the <img', !str_contains($h, '<img'), $h);
kiem('XSS: noi dung van hien duoi dang chu', str_contains($h, '&lt;script&gt;'), $h);

$xss2 = $bao_cao;
$xss2['veto_reason'] = '<script>alert(2)</script>';
kiem('XSS: veto_reason cung duoc escape',
  !str_contains($r->overviewHtml($xss2, FALSE), '<script>'));

// --- doc phong thu ------------------------------------------------------
kiem('thieu khoa fields -> khong loi',
  is_string($r->overviewHtml(['decision' => 'publish'], FALSE)));
kiem('fields co field la -> bo qua',
  $r->fieldNotesHtml(['fields' => ['khong_ton_tai' => [[]]]], 'title') === '');
kiem('version khac 1 -> co canh bao',
  str_contains($r->overviewHtml(['version' => 2, 'decision' => 'publish'], FALSE), 'phiên bản khác'));

exit($failed ? 1 : 0);
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run (từ `drupal/`): `ddev exec php scripts/test_ai_report_renderer.php`
Expected: lỗi PHP `Failed to open stream ... AiReportRenderer.php`.

- [ ] **Step 3: Viết lớp**

Tạo `drupal/web/modules/custom/vf_ai_review/src/AiReportRenderer.php`:

```php
<?php

namespace Drupal\vf_ai_review;

/**
 * Dựng HTML báo cáo AI từ dữ liệu trong field_ai_report_json.
 *
 * CỐ Ý KHÔNG phụ thuộc gì của Drupal: vào là mảng, ra là chuỗi HTML đã
 * escape. Nhờ vậy test được bằng script PHP thuần (drupal/scripts/
 * test_ai_report_renderer.php), giữ đúng phong cách 18 bộ test Python của
 * dự án thay vì phải cài PHPUnit.
 *
 * Escape bằng htmlspecialchars() thay vì Html::escape() của Drupal - hai
 * hàm tương đương (Html::escape bên trong chính là htmlspecialchars với
 * cùng cờ), nhưng cái sau kéo theo phụ thuộc Drupal.
 */
class AiReportRenderer {

  /**
   * Phiên bản định dạng JSON mà lớp này biết đọc.
   */
  public const VERSION = 1;

  /**
   * Field tham gia tính content_hash, ĐÚNG THỨ TỰ NÀY.
   *
   * Phải khớp _HASH_FIELDS trong multiagent/src/graph.py. Lệch là băng cảnh
   * báo "nội dung đã thay đổi" hiện sai vĩnh viễn - có test hợp đồng dùng
   * chung file multiagent/scripts/content_hash_fixture.json để bắt.
   */
  private const HASH_FIELDS = ['title', 'body', 'summary', 'meta_description'];

  private const DECISION_LABELS = [
    'publish' => '✅ Có thể xuất bản',
    'needs_revision' => '⚠ Cần sửa',
    'rejected' => '⛔ Bị từ chối',
  ];

  private const FIELD_LABELS = [
    'title' => 'Tiêu đề',
    'meta_description' => 'Meta description',
    'url_alias' => 'Đường dẫn',
    'summary' => 'Tóm tắt',
    'body' => 'Nội dung',
    'image_alt' => 'Alt text ảnh',
  ];

  /**
   * Băm nội dung để so xem bài có bị sửa sau khi chấm không.
   */
  public static function contentHash(array $fields): string {
    $phan = [];
    foreach (self::HASH_FIELDS as $khoa) {
      $phan[] = (string) ($fields[$khoa] ?? '');
    }
    return hash('sha256', implode("\n", $phan));
  }

  /**
   * Giải mã JSON. Hỏng hoặc rỗng -> NULL, KHÔNG ném exception.
   */
  public function decode(?string $json): ?array {
    if ($json === NULL || trim($json) === '') {
      return NULL;
    }
    $data = json_decode($json, TRUE);
    return is_array($data) ? $data : NULL;
  }

  /**
   * Escape mọi chuỗi động trước khi ghép vào HTML.
   *
   * BẮT BUỘC dùng cho mọi giá trị lấy từ báo cáo: chúng chứa trích dẫn
   * nguyên văn từ bài viết và văn bản do LLM sinh. Render thô là lỗ hổng
   * XSS - người viết chèn thẻ vào bài, LLM trích lại, thẻ chạy trong trang
   * admin của người duyệt (docs/prompt-injection.md mục 5, biện pháp M4).
   */
  private function esc($gia_tri): string {
    return htmlspecialchars((string) ($gia_tri ?? ''), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
  }

  /**
   * Khối tổng quan cho cột advanced.
   */
  public function overviewHtml(?array $report, bool $stale, bool $loiJson = FALSE): string {
    // Bốn trạng thái ở spec mục 6.1 phải phân biệt được. "Chưa chấm" (field
    // trống) khác hẳn "JSON hỏng" (có dữ liệu nhưng đọc không được) - gộp
    // chung sẽ khiến lỗi dữ liệu bị hiểu nhầm thành tình trạng bình thường.
    if ($loiJson) {
      return '<div class="vf-ai-review vf-ai-warn">'
        . 'Không đọc được báo cáo — xem trường AI Suggestions.'
        . '</div>';
    }
    if ($report === NULL) {
      return '<div class="vf-ai-review vf-ai-empty">'
        . 'Chưa được đánh giá. Chuyển bài sang trạng thái cần duyệt để hệ thống chấm.'
        . '</div>';
    }

    $out = '<div class="vf-ai-review">';

    if (($report['version'] ?? self::VERSION) !== self::VERSION) {
      $out .= '<div class="vf-ai-warn">Báo cáo sinh bởi phiên bản khác, hiển thị có thể thiếu.</div>';
    }

    if (!empty($report['veto_reason'])) {
      $out .= '<div class="vf-ai-veto"><strong>⛔ BỊ TỪ CHỐI</strong><br>'
        . $this->esc($report['veto_reason']) . '</div>';
    }

    if ($stale) {
      $out .= '<div class="vf-ai-stale">⏱ Nội dung đã thay đổi sau lần chấm. '
        . 'Kết quả bên dưới có thể không còn đúng.</div>';
    }

    if (!empty($report['note'])) {
      $out .= '<div class="vf-ai-warn">' . $this->esc($report['note']) . '</div>';
    }

    $quyet_dinh = $report['decision'] ?? NULL;
    $nhan = self::DECISION_LABELS[$quyet_dinh] ?? $this->esc($quyet_dinh);
    $out .= '<dl class="vf-ai-meta">';
    $out .= '<dt>Đề xuất</dt><dd>' . $nhan . '</dd>';

    // === NULL chứ KHÔNG dùng empty(): empty(0) trả TRUE nên điểm 0 sẽ bị
    // hiển thị nhầm thành "chưa đánh giá được".
    $diem = $report['final_score'] ?? NULL;
    $out .= '<dt>Điểm</dt><dd>'
      . ($diem === NULL ? '<em>chưa đánh giá được</em>' : $this->esc($diem) . ' / 100')
      . '</dd>';

    if (!empty($report['scored_at'])) {
      $out .= '<dt>Chấm lúc</dt><dd>' . $this->esc($this->dinhDangGio($report['scored_at'])) . '</dd>';
    }
    $out .= '</dl>';

    $fields = $report['fields'] ?? [];
    $tong = 0;
    foreach ($fields as $ds) {
      $tong += is_array($ds) ? count($ds) : 0;
    }
    if ($tong > 0) {
      $out .= '<p class="vf-ai-count">' . $tong . ' vấn đề trên ' . count($fields) . ' trường:</p><ul>';
      foreach ($fields as $khoa => $ds) {
        $ten = self::FIELD_LABELS[$khoa] ?? $this->esc($khoa);
        $out .= '<li>' . $ten . ' (' . count($ds) . ')</li>';
      }
      $out .= '</ul>';
    }
    else {
      $out .= '<p class="vf-ai-count">Không phát hiện vấn đề nào.</p>';
    }

    return $out . '</div>';
  }

  /**
   * Chú thích hiển thị ngay dưới widget của một field.
   *
   * Trả chuỗi rỗng nếu field đó không có vấn đề gì.
   */
  public function fieldNotesHtml(?array $report, string $fieldKey): string {
    $ds = $report['fields'][$fieldKey] ?? NULL;
    if (!is_array($ds) || $ds === []) {
      return '';
    }

    $out = '<div class="vf-ai-notes">';
    foreach ($ds as $muc) {
      if (!is_array($muc)) {
        continue;
      }
      $sev = $muc['severity'] ?? NULL;
      $lop = 'vf-ai-sev-' . ($sev !== NULL ? $this->esc($sev) : 'none');
      $bieu_tuong = ($sev === 'critical') ? '⛔' : '⚠';

      $out .= '<div class="vf-ai-note ' . $lop . '">';
      $out .= $bieu_tuong . ' <strong>' . $this->esc($muc['agent'] ?? '') . '</strong>';
      if (!empty($muc['label'])) {
        $out .= ' — ' . $this->esc($muc['label']);
      }
      if (!empty($muc['message'])) {
        $out .= '<div class="vf-ai-msg">' . $this->esc($muc['message']) . '</div>';
      }
      if (!empty($muc['excerpt'])) {
        $out .= '<blockquote>' . $this->esc($muc['excerpt']) . '</blockquote>';
      }
      $out .= '</div>';
    }
    return $out . '</div>';
  }

  /**
   * ISO 8601 -> "03/08/2026 09:45". Không parse được thì trả nguyên bản.
   */
  private function dinhDangGio(string $iso): string {
    $ts = strtotime($iso);
    return $ts === FALSE ? $iso : date('d/m/Y H:i', $ts);
  }

}
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run (từ `drupal/`): `ddev exec php scripts/test_ai_report_renderer.php`
Expected: **31 dòng `[PASS]`**, không dòng `[FAIL]`, thoát mã 0.

Kiểm bằng mắt hai dòng quan trọng nhất phải có:
```
[PASS] hash khop fixture (hop dong voi phia Python)
[PASS] XSS: khong con the <script>
```

- [ ] **Step 5: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_review/src/AiReportRenderer.php drupal/scripts/test_ai_report_renderer.php
git commit -m "feat: AiReportRenderer - dung HTML bao cao, escape chong XSS"
```

---

## Task 7: Hook — ẩn 4 field AI

**Files:**
- Create: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`

**Interfaces:**
- Consumes: `AiReportRenderer` (Task 6).
- Produces: hook `vf_ai_review_form_node_form_alter()`.

Task này chỉ làm phần ẩn field — phần hiển thị báo cáo ở Task 8-9. Chia vậy để nếu hook không chạy thì biết ngay là do móc sai, không lẫn với lỗi dựng HTML.

- [ ] **Step 1: Viết file module**

Tạo `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`:

```php
<?php

/**
 * @file
 * Hiển thị kết quả đánh giá Multi-Agent AI trong giao diện soạn bài.
 *
 * Module CHỈ ĐỌC: không tính điểm, không gọi API, không sửa dữ liệu node.
 * Hỏng thì cùng lắm không thấy báo cáo, không thể làm sai dữ liệu đánh giá.
 */

use Drupal\Core\Form\FormStateInterface;
use Drupal\vf_ai_review\AiReportRenderer;

/**
 * Bốn field do hệ Multi-Agent ghi vào, người soạn không được sửa.
 */
const VF_AI_REVIEW_FIELDS = [
  'field_ai_status',
  'field_ai_score',
  'field_ai_suggestions',
  'field_ai_report_json',
];

/**
 * Implements hook_form_BASE_FORM_ID_alter() for node_form.
 *
 * Tên hàm CHÍNH LÀ phần khai báo: Drupal thấy hàm tên
 * <ten_module>_form_node_form_alter thì tự gọi mỗi khi dựng form node.
 * Dấu & trước $form nghĩa là sửa trực tiếp vào mảng gốc.
 */
function vf_ai_review_form_node_form_alter(array &$form, FormStateInterface $form_state, string $form_id): void {
  $node = $form_state->getFormObject()->getEntity();
  if ($node->bundle() !== 'article') {
    return;
  }

  // Ẩn hẳn 4 field AI. Dùng #access = FALSE chứ KHÔNG dùng
  // '#attributes' => ['readonly' => 'readonly'] - cái đó chỉ là thuộc tính
  // HTML, chặn ở trình duyệt nhưng người dùng vẫn gửi giá trị lên server.
  foreach (VF_AI_REVIEW_FIELDS as $ten) {
    if (isset($form[$ten])) {
      $form[$ten]['#access'] = FALSE;
    }
  }
}
```

- [ ] **Step 2: Xoá cache Drupal**

Run (từ `drupal/`): `ddev drush cr`
Expected: in `[success] Cache rebuild complete.`

Drupal ghi nhớ danh sách hook lúc khởi động, nên **thêm hook mới bắt buộc phải xoá cache** mới có tác dụng. Đây là bước dễ quên nhất khi mới làm Drupal.

- [ ] **Step 3: Kiểm bằng mắt**

Mở `http://drupal.ddev.site/node/1/edit`.
Expected: **KHÔNG còn thấy** 4 ô nhập liệu "AI Status", "AI Score", "AI Suggestions", "AI Report (JSON)" ở cuối form. Các field khác (Tiêu đề, Nội dung, Meta description, Ảnh) vẫn bình thường.

Nếu vẫn thấy → chạy lại `ddev drush cr`; vẫn còn thì kiểm tên hàm có đúng `vf_ai_review_form_node_form_alter` không.

- [ ] **Step 4: Kiểm trang không phải article**

Mở `http://drupal.ddev.site/node/add/page` (nếu có content type Basic page).
Expected: form hiện bình thường, không lỗi. Hook đã thoát sớm vì `bundle() !== 'article'`.

- [ ] **Step 5: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_review/vf_ai_review.module
git commit -m "feat: hook an 4 field AI khoi form soan bai"
```

---

## Task 8: Khối tổng quan ở cột phải

**Files:**
- Modify: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`

**Interfaces:**
- Consumes: `AiReportRenderer::decode()`, `overviewHtml()`, `contentHash()` (Task 6).
- Produces: `$form['vf_ai_review']` — phần tử `details` trong nhóm `advanced`.

- [ ] **Step 1: Thêm hàm đọc giá trị field an toàn**

Thêm vào cuối `vf_ai_review.module`:

```php
/**
 * Đọc giá trị một field của node, trả chuỗi rỗng nếu không có.
 *
 * Đọc phòng thủ giống fetch_content() bên Python: field chưa cấu hình hoặc
 * để trống thì trả rỗng, không làm sập form soạn bài.
 */
function _vf_ai_review_gia_tri($node, string $ten_field, string $thuoc_tinh = 'value'): string {
  if (!$node->hasField($ten_field) || $node->get($ten_field)->isEmpty()) {
    return '';
  }
  return (string) ($node->get($ten_field)->{$thuoc_tinh} ?? '');
}
```

- [ ] **Step 2: Thêm phần dựng khối tổng quan vào hook**

Thêm vào cuối hàm `vf_ai_review_form_node_form_alter()`, sau vòng lặp ẩn field:

```php
  $renderer = new AiReportRenderer();
  $tho = _vf_ai_review_gia_tri($node, 'field_ai_report_json');
  $report = $renderer->decode($tho);
  // Có dữ liệu nhưng giải mã không được -> trạng thái "JSON hỏng", khác hẳn
  // "chưa chấm" (field trống). Phải phân biệt để lỗi dữ liệu không bị hiểu
  // nhầm thành tình trạng bình thường.
  $loi_json = ($tho !== '' && $report === NULL);

  // So hash để biết bài có bị sửa sau khi chấm không. Dùng hash chứ KHÔNG
  // dùng mốc `changed` của node: chính lệnh PATCH của write_back() làm mốc
  // đó nhảy, nên so nó sẽ luôn báo "đã thay đổi" ngay sau khi chấm.
  $stale = FALSE;
  if ($report !== NULL && !empty($report['content_hash'])) {
    $hien_tai = AiReportRenderer::contentHash([
      'title' => (string) $node->label(),
      'body' => _vf_ai_review_gia_tri($node, 'body'),
      'summary' => _vf_ai_review_gia_tri($node, 'body', 'summary'),
      'meta_description' => _vf_ai_review_gia_tri($node, 'field_meta_description'),
    ]);
    $stale = ($hien_tai !== $report['content_hash']);
  }

  $form['vf_ai_review'] = [
    '#type' => 'details',
    '#title' => 'Đánh giá AI',
    '#group' => 'advanced',
    '#open' => TRUE,
    '#weight' => -10,
    'noi_dung' => [
      // Chuỗi này đã được AiReportRenderer escape toàn bộ phần động.
      '#markup' => $renderer->overviewHtml($report, $stale, $loi_json),
    ],
  ];
```

- [ ] **Step 3: Xoá cache và kiểm bằng mắt**

Run (từ `drupal/`): `ddev drush cr`

Mở `http://drupal.ddev.site/node/1/edit`.
Expected: **cột phải** (chỗ có "Thông tin xuất bản", "Tác giả") xuất hiện thêm khối **"Đánh giá AI"**, gập/mở được, bên trong có:
```
Đề xuất   ✅ Có thể xuất bản
Điểm      81.75 / 100
Chấm lúc  03/08/2026 ...
N vấn đề trên M trường: ...
```

Nếu khối không xuất hiện → kiểm `ddev drush cr` đã chạy chưa. Nếu khối hiện nhưng nội dung là "Chưa được đánh giá" → node đó chưa có JSON, quay lại Task 4 Step 7 chấm lại bài.

- [ ] **Step 4: Kiểm bài bị từ chối**

Mở `http://drupal.ddev.site/node/5/edit`.
Expected: khối hiện `⛔ Bị từ chối`, điểm `61 / 100`.

- [ ] **Step 5: Kiểm bài chưa từng chấm**

Run (từ `drupal/`): `ddev drush php:eval "\$n = \Drupal\node\Entity\Node::create(['type'=>'article','title'=>'Bai chua cham']); \$n->save(); print \$n->id();"`

Mở `http://drupal.ddev.site/node/<id vừa in>/edit`.
Expected: khối hiện *"Chưa được đánh giá. Chuyển bài sang trạng thái cần duyệt…"*, không lỗi.

- [ ] **Step 6: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_review/vf_ai_review.module
git commit -m "feat: khoi tong quan danh gia AI o cot phai form soan bai"
```

---

## Task 9: Chú thích ngay dưới từng field

**Files:**
- Modify: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`

**Interfaces:**
- Consumes: `AiReportRenderer::fieldNotesHtml()` (Task 6).
- Produces: `#suffix` trên các widget tương ứng.

Đây là phần đáp ứng đúng chữ đề bài: *"báo cáo lỗi/rủi ro theo từng field ngay trong giao diện editor"*.

- [ ] **Step 1: Thêm bảng ánh xạ**

Thêm vào đầu `vf_ai_review.module`, ngay sau `const VF_AI_REVIEW_FIELDS`:

```php
/**
 * Ánh xạ khoá field trong báo cáo -> tên phần tử trên form soạn bài.
 *
 * Để MỘT CHỖ DUY NHẤT. Tên nào không tồn tại trên form thì bỏ qua field đó
 * chứ không đổ lỗi - sai một tên không được làm trắng trang form soạn bài
 * (docs/editor-ui-design.md mục 8).
 *
 * `body` và `summary` cùng trỏ về widget 'body' vì summary là teaser nằm
 * trong chính widget đó - chú thích của hai khoá này được ghép lại.
 */
const VF_AI_REVIEW_FIELD_MAP = [
  'title' => 'title',
  'body' => 'body',
  'summary' => 'body',
  'meta_description' => 'field_meta_description',
  'url_alias' => 'path',
  'image_alt' => 'field_image',
];
```

- [ ] **Step 2: Thêm phần gắn chú thích vào hook**

Thêm vào cuối hàm `vf_ai_review_form_node_form_alter()`, sau khối `$form['vf_ai_review'] = [...]`:

```php
  // Gom chú thích theo widget đích trước, vì body và summary cùng trỏ về
  // widget 'body' - nếu gắn thẳng thì cái sau đè mất cái trước.
  $theo_widget = [];
  foreach (VF_AI_REVIEW_FIELD_MAP as $khoa_bao_cao => $ten_form) {
    $html = $renderer->fieldNotesHtml($report, $khoa_bao_cao);
    if ($html !== '') {
      $theo_widget[$ten_form] = ($theo_widget[$ten_form] ?? '') . $html;
    }
  }

  foreach ($theo_widget as $ten_form => $html) {
    if (isset($form[$ten_form])) {
      $form[$ten_form]['#suffix'] = ($form[$ten_form]['#suffix'] ?? '') . $html;
    }
  }
```

- [ ] **Step 3: Xoá cache và kiểm bằng mắt**

Run (từ `drupal/`): `ddev drush cr`

Mở `http://drupal.ddev.site/node/1/edit`.
Expected: ngay **dưới ô Tiêu đề** có dòng chú thích kiểu:
```
⚠ SEO — Độ dài tiêu đề
   Tiêu đề hiện tại dài 62 ký tự, nên rút gọn xuống 50-60 ký tự
```
Và dưới **ô Nội dung** có chú thích của Compliance/Chất lượng/Brand Voice, kèm đoạn trích trong khung.

- [ ] **Step 4: Kiểm chú thích gắn đúng field**

Đối chiếu với dữ liệu thật. Run (từ `drupal/`):

```bash
ddev mysql -e "SELECT field_ai_report_json_value FROM node__field_ai_report_json WHERE entity_id=1\G"
```

Expected: các khoá trong `fields` của JSON khớp đúng với những chỗ có chú thích trên form. Ví dụ JSON có `"meta_description"` thì dưới ô Meta description phải có chú thích.

- [ ] **Step 5: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_review/vf_ai_review.module
git commit -m "feat: chu thich loi ngay duoi tung field tren form soan bai"
```

---

## Task 10: CSS

**Files:**
- Create: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.libraries.yml`
- Create: `drupal/web/modules/custom/vf_ai_review/css/vf_ai_review.css`
- Modify: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`

**Interfaces:**
- Produces: thư viện `vf_ai_review/report`, nạp vào form soạn bài.

- [ ] **Step 1: Khai báo thư viện**

Tạo `drupal/web/modules/custom/vf_ai_review/vf_ai_review.libraries.yml`:

```yaml
report:
  css:
    theme:
      css/vf_ai_review.css: {}
```

- [ ] **Step 2: Viết CSS**

Tạo `drupal/web/modules/custom/vf_ai_review/css/vf_ai_review.css`:

```css
/* Báo cáo đánh giá AI trong form soạn bài.
   Màu lấy theo bảng màu Claro (admin theme mặc định của Drupal 10) để không
   lệch khỏi giao diện quản trị. */

.vf-ai-review { font-size: 0.9em; line-height: 1.5; }
.vf-ai-review .vf-ai-meta { margin: 0 0 0.75em; }
.vf-ai-review .vf-ai-meta dt { font-weight: 600; margin-top: 0.4em; }
.vf-ai-review .vf-ai-meta dd { margin: 0 0 0.2em; }
.vf-ai-review ul { margin: 0.3em 0 0; padding-left: 1.2em; }
.vf-ai-empty { color: #545560; font-style: italic; }

.vf-ai-veto {
  background: #fcf4f2; border-left: 4px solid #e34f4f;
  padding: 0.6em 0.8em; margin-bottom: 0.75em;
}
.vf-ai-stale {
  background: #fdf8ed; border-left: 4px solid #e5a83b;
  padding: 0.6em 0.8em; margin-bottom: 0.75em;
}
.vf-ai-warn {
  background: #f3f4f9; border-left: 4px solid #4d4d4d;
  padding: 0.6em 0.8em; margin-bottom: 0.75em;
}

/* Chú thích dưới từng field */
.vf-ai-notes { margin: 0.4em 0 1em; }
.vf-ai-note {
  border-left: 3px solid #ccc; padding: 0.4em 0.7em;
  margin-bottom: 0.4em; background: #fafafa; font-size: 0.9em;
}
.vf-ai-note .vf-ai-msg { margin-top: 0.25em; color: #454545; }
.vf-ai-note blockquote {
  margin: 0.35em 0 0; padding: 0.3em 0.6em;
  border-left: 2px solid #ddd; color: #666; font-style: italic;
}

.vf-ai-sev-critical { border-left-color: #e34f4f; background: #fcf4f2; }
.vf-ai-sev-medium   { border-left-color: #e5a83b; background: #fdf8ed; }
.vf-ai-sev-low      { border-left-color: #73b355; background: #f3faef; }
.vf-ai-sev-none     { border-left-color: #8e929c; }
```

- [ ] **Step 3: Nạp thư viện trong hook**

Thêm vào cuối hàm `vf_ai_review_form_node_form_alter()`:

```php
  $form['#attached']['library'][] = 'vf_ai_review/report';
```

- [ ] **Step 4: Xoá cache và kiểm bằng mắt**

Run (từ `drupal/`): `ddev drush cr`

Mở `http://drupal.ddev.site/node/1/edit`.
Expected: khối "Đánh giá AI" và các chú thích giờ **có màu và viền trái** — chú thích Compliance viền cam (`medium`), chú thích SEO/Chất lượng viền xám (`none`).

Mở `http://drupal.ddev.site/node/5/edit`.
Expected: khối "BỊ TỪ CHỐI" nền hồng nhạt viền đỏ.

Nếu không thấy màu → kiểm `vf_ai_review.libraries.yml` đúng tên file chưa, và đã `ddev drush cr` chưa.

- [ ] **Step 5: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_review/vf_ai_review.libraries.yml drupal/web/modules/custom/vf_ai_review/css/vf_ai_review.css drupal/web/modules/custom/vf_ai_review/vf_ai_review.module
git commit -m "feat: CSS cho bao cao AI, mau theo severity"
```

---

## Task 11: Kiểm tổng thể và đồng bộ tài liệu

**Files:**
- Modify: `README.md`, `docs/editor-ui-design.md`, `docs/architecture.md`, `docs/prompt-injection.md`

- [ ] **Step 1: Chạy toàn bộ test hai phía**

Run (từ `multiagent/`):

```bash
for t in scripts/test_*.py; do printf "%-30s" "$(basename $t .py)"; .venv/Scripts/python.exe $t > /dev/null 2>&1 && echo OK || echo FAIL; done
```

Expected: **19/19 OK**.

Run (từ `drupal/`): `ddev exec php scripts/test_ai_report_renderer.php`
Expected: 27 `[PASS]`, thoát mã 0.

- [ ] **Step 2: Kiểm bằng mắt theo checklist đầy đủ**

```
1.  ddev drush cr
2.  node/1/edit  -> khoi "Danh gia AI" o cot phai, diem 81.75, gap/mo duoc
3.  node/1/edit  -> duoi o Tieu de co chu thich SEO
4.  node/1/edit  -> KHONG thay 4 field AI dang o nhap lieu
5.  node/5/edit  -> khoi do "BI TU CHOI"
6.  node/7/edit  -> diem 62.75, it chu thich hon vi bai ngan
7.  Sua tieu de node/1, luu, mo lai -> hien bang "Noi dung da thay doi"
8.  Cham lai node/1 bang smoke_test_graph -> bang canh bao BIEN MAT
9.  ddev drush pmu vf_ai_review -y ; ddev drush cr -> form ve nguyen trang,
    4 field AI hien lai dang o nhap lieu, van doc duoc AI Suggestions
10. ddev drush en vf_ai_review -y ; ddev drush cr -> bat lai binh thuong
```

**Bước 7-8 là cặp kiểm chứng cơ chế hash** — dễ sai nhất nên phải thử thật. Bước 7 phải hiện cảnh báo, bước 8 phải làm nó biến mất.

**Bước 9 kiểm suy giảm mềm:** tắt module thì vẫn đọc được `field_ai_suggestions`.

- [ ] **Step 3: `README.md`**

Trong mục "Trạng thái Sprint 2", đổi dòng UI:

```markdown
- [x] UI báo cáo trong editor — module `vf_ai_review`: khối tổng quan ở cột phải + chú thích lỗi ngay dưới từng field. Python ghi thêm `field_ai_report_json` (báo cáo có cấu trúc), module chỉ đọc và render. Escape chống XSS theo `docs/prompt-injection.md` M4
```

Trong sơ đồ cấu trúc project, thêm vào nhánh `drupal/`:

```
│   └── web/modules/custom/vf_ai_review/   # module hiển thị báo cáo AI trong editor
```

- [ ] **Step 4: `docs/editor-ui-design.md`**

Sửa dòng trạng thái ở đầu file:

```markdown
**Trạng thái:** **đã triển khai (2026-08-03)** — mức P1, xem `docs/superpowers/specs/2026-08-03-vf-ai-review-module-design.md`
```

Thêm vào **cuối mục 4.4** đoạn đính chính:

```markdown
**Đính chính (2026-08-03).** Cơ chế trên **hỏng**: chính lệnh PATCH của `write_back()` làm mốc `changed` nhảy, nên so mốc đó sẽ luôn báo "nội dung đã thay đổi" ngay sau khi chấm. Bằng chứng đo trên DB: `changed` của nid 2/3/4 đúng bằng thời điểm chạy smoke test chấm lại (09:45:17 / 09:45:24 / 09:45:32). Đã thay bằng **hash nội dung** — hash chỉ đổi khi nội dung thật sự đổi, vì PATCH không đụng `title`/`body`/`summary`/`meta_description`. Chi tiết: spec `2026-08-03-vf-ai-review-module-design.md` mục 4.3.
```

- [ ] **Step 5: `docs/architecture.md` mục 2.3**

Thêm một dòng vào bảng field:

```markdown
| field_ai_report_json | Văn bản (string_long) | (OUTPUT) Báo cáo có cấu trúc để module `vf_ai_review` render. Giữ song song `field_ai_suggestions` dạng text để khi chưa bật module vẫn đọc được |
```

- [ ] **Step 6: `docs/prompt-injection.md` mục 5**

Đổi tiêu đề biện pháp M4:

```markdown
### M4 - Escape khi render báo cáo trong Drupal ✅ **đã triển khai (2026-08-03)**
```

Và thêm vào cuối mục đó:

```markdown
Triển khai: `AiReportRenderer::esc()` escape mọi chuỗi động bằng `htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')`. Có test riêng trong `drupal/scripts/test_ai_report_renderer.php` — nhét `<script>alert(1)</script>` và `"><img src=x onerror=alert(1)>` vào `message`/`excerpt`, kiểm tra chuỗi render ra không còn thẻ nào chạy được.
```

- [ ] **Step 7: Commit**

```bash
git add README.md docs/editor-ui-design.md docs/architecture.md docs/prompt-injection.md
git commit -m "docs: dong bo module vf_ai_review da trien khai"
```

---

## Kiểm tra cuối cùng trước khi mở PR

- [ ] 19/19 bộ test Python OK
- [ ] 27 `[PASS]` phía PHP, không `[FAIL]`
- [ ] Checklist kiểm bằng mắt ở Task 11 Step 2 chạy hết, đặc biệt bước 7-8 (hash) và bước 9 (suy giảm mềm)
- [ ] `git status` sạch, không file lạ

**Nhắc:** thư mục `drupal/web/modules/custom/` là code của dự án, **phải commit**. Kiểm bằng `git status` xem nó có bị `.gitignore` của Drupal nuốt không — Drupal core có file `web/example.gitignore` nhưng dự án này dùng `.gitignore` ở gốc repo, nên thư mục custom được theo dõi bình thường. Nếu `git status` không thấy file mới, chạy `git check-ignore -v drupal/web/modules/custom/vf_ai_review/vf_ai_review.info.yml` để tìm luật nào chặn.
