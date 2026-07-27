# Compliance Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai Compliance Agent thật (thay stub) trong hệ thống LangGraph multi-agent kiểm duyệt nội dung, kết hợp rule-based blacklist (so khớp cứng) với đánh giá LLM (Claude).

**Architecture:** `src/agents/compliance.py` cung cấp `match_blacklist()` (thuần Python, đọc `compliance_rules.json`) và `run()` (gọi LLM qua `ai_core.call_agent()` rồi gộp flags của LLM + rule-based). `src/graph.py` thay `compliance_node` stub bằng lệnh gọi `compliance.run()` thật, và `aggregator_node`/`write_back_node` được cập nhật để giải thích rõ lý do khi Compliance phủ quyết (`veto_reason`).

**Tech Stack:** Python 3.12, LangGraph, Anthropic SDK (`claude-haiku-4-5-20251001` qua `ai_core.call_agent`), không dùng framework test mới — theo đúng phong cách script test thủ công đã có (`scripts/smoke_test_*.py`).

## Global Constraints

- Output của LLM luôn bằng tiếng Việt (thêm chỉ dẫn trong system prompt, nhất quán với `content_quality.py`/`seo.py`).
- Không thêm framework test mới (không pytest) — dùng script thủ công trong `scripts/`, in kết quả PASS/FAIL hoặc assert, theo đúng pattern hiện có.
- `compliance.run()` **không được sửa/ép `score`** do LLM trả về — chỉ gộp thêm `flags` từ rule-based. Đây là quyết định thiết kế cốt lõi (xem spec mục 4), không được thay đổi khi triển khai.
- Rule-based match luôn tạo flag `severity: "critical"` (không có mức khác ở bước này).
- `brand_node` trong `src/graph.py` giữ nguyên stub — ngoài phạm vi plan này.
- Theo pattern có sẵn của `src/agents/content_quality.py` và `src/agents/seo.py`: mỗi agent module có `SYSTEM_PROMPT`, `OUTPUT_SCHEMA`, và hàm `run(title, body) -> dict`.
- Spec đầy đủ: `docs/superpowers/specs/2026-07-22-compliance-agent-design.md`.

---

## Task 1: Rule-based blacklist matching

**Files:**
- Create: `src/agents/compliance_rules.json`
- Create: `src/agents/compliance.py`
- Test: `scripts/test_compliance_rules.py`

**Interfaces:**
- Produces: `match_blacklist(text: str) -> list[dict]` trong `src/agents/compliance.py`. Mỗi dict trong list có dạng `{"severity": str, "rule": str, "excerpt": str}`.

- [ ] **Step 1: Viết file blacklist**

Tạo `src/agents/compliance_rules.json`:

```json
{
  "phrases": [
    {"text": "tốt nhất", "severity": "critical", "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "số 1", "severity": "critical", "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "số một", "severity": "critical", "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "duy nhất", "severity": "critical", "rule": "Cường điệu tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "không đối thủ", "severity": "critical", "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "vô địch", "severity": "critical", "rule": "Cường điệu tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "chưa từng có", "severity": "critical", "rule": "Cường điệu tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "hiệu quả 100%", "severity": "critical", "rule": "Cam kết tuyệt đối không có căn cứ khoa học (Luật Quảng cáo)"},
    {"text": "an toàn tuyệt đối", "severity": "critical", "rule": "Cam kết tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "cam kết 100%", "severity": "critical", "rule": "Cam kết tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "giảm giá không giới hạn", "severity": "critical", "rule": "Thông tin khuyến mãi gây hiểu nhầm - thiếu điều kiện/thời hạn rõ ràng"},
    {"text": "cơ hội duy nhất trong đời", "severity": "critical", "rule": "Cường điệu tuyệt đối không có căn cứ (Luật Quảng cáo)"}
  ]
}
```

- [ ] **Step 2: Viết script test (sẽ fail vì `compliance.py` chưa tồn tại)**

Tạo `scripts/test_compliance_rules.py`:

```python
"""Test thủ công cho phần rule-based (blacklist) của Compliance Agent —
không gọi LLM, chỉ kiểm tra match_blacklist() có bắt đúng cụm từ cấm không.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_compliance_rules.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.compliance import match_blacklist

CASES = [
    ("VF3 tốt nhất thị trường Việt Nam", 1),
    ("VinFast VF3 là lựa chọn tuyệt vời cho gia đình bạn", 0),
    ("Đây là chiếc xe SỐ 1 hiện nay", 1),
    ("Chương trình giảm giá không giới hạn tới hết tháng", 1),
    ("VF3 tốt nhất và số 1 thị trường", 2),
]

if __name__ == "__main__":
    failed = False
    for text, expected_count in CASES:
        flags = match_blacklist(text)
        status = "PASS" if len(flags) == expected_count else "FAIL"
        if status == "FAIL":
            failed = True
        print(f"[{status}] '{text}' -> {len(flags)} flag(s) (ky vong {expected_count})")
        for f in flags:
            print(f"    {f}")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 3: Chạy script để xác nhận nó fail**

Run: `.venv\Scripts\python.exe scripts\test_compliance_rules.py`
Expected: `ModuleNotFoundError: No module named 'agents.compliance'` (vì `src/agents/compliance.py` chưa tồn tại).

- [ ] **Step 4: Triển khai `match_blacklist()`**

Tạo `src/agents/compliance.py` với nội dung sau (chỉ phần rule-based ở task này; phần LLM sẽ thêm ở Task 2):

```python
import json
import os

_RULES_PATH = os.path.join(os.path.dirname(__file__), "compliance_rules.json")

_rules_cache = None


def _load_rules() -> list[dict]:
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _rules_cache = json.load(f)["phrases"]
    return _rules_cache


def match_blacklist(text: str) -> list[dict]:
    """So khớp cứng (không phân biệt hoa/thường) với danh sách từ cấm.

    Mỗi cụm khớp tạo 1 flag severity "critical" (xem
    docs/superpowers/specs/2026-07-22-compliance-agent-design.md mục 4).
    """
    text_lower = text.lower()
    flags = []
    for rule in _load_rules():
        phrase = rule["text"].lower()
        idx = text_lower.find(phrase)
        if idx == -1:
            continue
        start = max(0, idx - 20)
        end = min(len(text), idx + len(phrase) + 20)
        flags.append(
            {
                "severity": rule["severity"],
                "rule": rule["rule"],
                "excerpt": text[start:end].strip(),
            }
        )
    return flags
```

- [ ] **Step 5: Chạy lại script để xác nhận PASS**

Run: `.venv\Scripts\python.exe scripts\test_compliance_rules.py`
Expected: cả 5 dòng đều `[PASS]`, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add src/agents/compliance_rules.json src/agents/compliance.py scripts/test_compliance_rules.py
git commit -m "feat: add rule-based blacklist matching for Compliance Agent"
```

---

## Task 2: LLM phần Compliance Agent + gộp kết quả (`run()`)

**Files:**
- Modify: `src/agents/compliance.py`
- Test: `scripts/smoke_test_compliance.py`

**Interfaces:**
- Consumes: `match_blacklist(text: str) -> list[dict]` (Task 1), `call_agent(system_prompt: str, title: str, body: str, output_schema: dict) -> dict` (đã có sẵn trong `src/ai_core.py`).
- Produces: `run(title: str, body: str) -> dict` trong `src/agents/compliance.py`, trả về `{"score": int, "flags": list[dict]}`.

- [ ] **Step 1: Viết smoke test script (sẽ fail vì `run()` chưa tồn tại)**

Tạo `scripts/smoke_test_compliance.py`:

```python
"""Smoke test thủ công cho src/agents/compliance.py — gọi Claude API thật
kết hợp với rule-based blacklist, xác nhận run() trả về đúng cấu trúc và
rule-based flag được gộp đúng vào danh sách flags.

Cách chạy (sau khi đã điền ANTHROPIC_API_KEY trong .env):
    .venv\\Scripts\\python.exe scripts\\smoke_test_compliance.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.compliance import run

title = "VF3 - Chiếc xe điện tốt nhất thế giới, giảm giá không giới hạn"
body = (
    "VinFast VF3 là chiếc xe điện tốt nhất thế giới hiện nay, với mức giá "
    "không đối thủ nào sánh được. Chương trình giảm giá không giới hạn, "
    "đây là cơ hội duy nhất trong đời để sở hữu xe điện."
)

if __name__ == "__main__":
    result = run(title, body)
    print(f"score={result['score']}")
    print(f"flags ({len(result['flags'])}):")
    for f in result["flags"]:
        print(f"  {f}")

    assert isinstance(result["score"], int), "score phai la int"
    assert isinstance(result["flags"], list), "flags phai la list"

    critical_flags = [f for f in result["flags"] if f["severity"] == "critical"]
    assert len(critical_flags) >= 1, (
        "Phai co it nhat 1 flag critical tu rule-based (van ban chua 'tot nhat')"
    )
    print("PASS: co flag critical tu rule-based nhu ky vong")
```

- [ ] **Step 2: Chạy script để xác nhận nó fail**

Run: `.venv\Scripts\python.exe scripts\smoke_test_compliance.py`
Expected: `ImportError: cannot import name 'run' from 'agents.compliance'`

- [ ] **Step 3: Thêm phần LLM + `run()` vào `src/agents/compliance.py`**

Thêm vào đầu file (sau các import hiện có) và cuối file:

```python
from ai_core import call_agent

SYSTEM_PROMPT = (
    "Bạn là chuyên gia kiểm duyệt tuân thủ pháp lý cho nội dung marketing. "
    "Chỉ đánh giá các yếu tố sau, KHÔNG đánh giá chính tả, văn phong hay SEO:\n"
    "1. Claim nhạy cảm/thổi phồng thiếu căn cứ (ví dụ: cam kết hiệu quả tuyệt "
    "đối, so sánh hơn hẳn đối thủ không có bằng chứng).\n"
    "2. Nội dung có nguy cơ vi phạm luật quảng cáo Việt Nam.\n"
    "3. Thông tin giá/khuyến mãi gây hiểu nhầm (ví dụ thời hạn không rõ ràng, "
    "điều kiện áp dụng bị giấu).\n"
    "Với mỗi vi phạm tìm thấy, tạo 1 flag với severity 'low' (nhẹ), 'medium' "
    "(đáng chú ý), hoặc 'critical' (nghiêm trọng, rủi ro pháp lý rõ ràng).\n"
    "Luôn trả lời bằng tiếng Việt trong tất cả các trường văn bản."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "critical"]},
                    "rule": {"type": "string"},
                    "excerpt": {"type": "string"},
                },
                "required": ["severity", "rule", "excerpt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["score", "flags"],
    "additionalProperties": False,
}


def run(title: str, body: str) -> dict:
    llm_result = call_agent(SYSTEM_PROMPT, title, body, OUTPUT_SCHEMA)
    rule_flags = match_blacklist(f"{title}\n{body}")
    return {
        "score": llm_result["score"],
        "flags": llm_result["flags"] + rule_flags,
    }
```

Lưu ý: **không** sửa `llm_result["score"]` — giữ nguyên như spec mục 4 đã chốt.

- [ ] **Step 4: Chạy lại script để xác nhận PASS**

Run: `.venv\Scripts\python.exe scripts\smoke_test_compliance.py`
Expected: in ra `score=<số>`, danh sách flags (ít nhất có flag rule-based cho "tốt nhất"/"không đối thủ"/"giảm giá không giới hạn"/"cơ hội duy nhất trong đời"), và dòng cuối `PASS: co flag critical tu rule-based nhu ky vong`. Không có `AssertionError`.

- [ ] **Step 5: Commit**

```bash
git add src/agents/compliance.py scripts/smoke_test_compliance.py
git commit -m "feat: add LLM evaluation to Compliance Agent, merge with rule-based flags"
```

---

## Task 3: Tích hợp vào `graph.py` (thay stub, thêm `veto_reason`)

**Files:**
- Modify: `src/graph.py`

**Interfaces:**
- Consumes: `compliance.run(title: str, body: str) -> dict` (Task 2).
- Produces: `report["veto_reason"]` (str, optional) — dùng bởi `write_back_node` trong cùng file.

- [ ] **Step 1: Cập nhật import**

Trong `src/graph.py`, sửa dòng:

```python
from agents import content_quality, seo
```

thành:

```python
from agents import compliance, content_quality, seo
```

- [ ] **Step 2: Thay `compliance_node` stub bằng gọi thật**

Sửa:

```python
def compliance_node(state: ContentReviewState) -> dict:
    result = _stub_agent_result("Compliance")
    result["flags"] = []
    return {"compliance_result": result}
```

thành:

```python
def compliance_node(state: ContentReviewState) -> dict:
    try:
        result = compliance.run(state["title"], state["body"])
    except Exception:
        result = None  # agent lỗi -> để Aggregator xử lý theo fail-safe (mục 6.4)
    return {"compliance_result": result}
```

- [ ] **Step 3: Thêm `veto_reason` vào `aggregator_node`**

Sửa toàn bộ hàm `aggregator_node` từ:

```python
def aggregator_node(state: ContentReviewState) -> dict:
    results = {
        "content_quality": state.get("content_quality_result"),
        "seo": state.get("seo_result"),
        "brand": state.get("brand_result"),
        "compliance": state.get("compliance_result"),
    }
    compliance = results["compliance"]
    missing = [name for name, r in results.items() if r is None]

    if compliance is None:
        # Compliance có quyền phủ quyết (docs/architecture.md mục 6.4) - không bao
        # giờ tự động publish khi không xác minh được rủi ro pháp lý.
        decision = "needs_revision"
        final_score = None
    else:
        has_critical_flag = any(
            f.get("severity") == "critical" for f in compliance.get("flags", [])
        )
        available = {k: v for k, v in results.items() if v is not None}
        total_weight = sum(WEIGHTS[k] for k in available)
        final_score = (
            sum(WEIGHTS[k] * v["score"] for k, v in available.items())
            / total_weight
        )
        if compliance["score"] < 50 or has_critical_flag:
            decision = "rejected"
        elif final_score >= 80:
            decision = "publish"
        elif final_score >= 50:
            decision = "needs_revision"
        else:
            decision = "rejected"

    report = {
        "node_id": state["node_id"],
        "final_score": final_score,
        "decision": decision,
        "missing_agents": missing,
        "details": results,
    }
    return {"final_score": final_score, "decision": decision, "report": report}
```

thành:

```python
def aggregator_node(state: ContentReviewState) -> dict:
    results = {
        "content_quality": state.get("content_quality_result"),
        "seo": state.get("seo_result"),
        "brand": state.get("brand_result"),
        "compliance": state.get("compliance_result"),
    }
    compliance_result = results["compliance"]
    missing = [name for name, r in results.items() if r is None]
    veto_reason = None

    if compliance_result is None:
        # Compliance có quyền phủ quyết (docs/architecture.md mục 6.4) - không bao
        # giờ tự động publish khi không xác minh được rủi ro pháp lý.
        decision = "needs_revision"
        final_score = None
    else:
        has_critical_flag = any(
            f.get("severity") == "critical" for f in compliance_result.get("flags", [])
        )
        available = {k: v for k, v in results.items() if v is not None}
        total_weight = sum(WEIGHTS[k] for k in available)
        final_score = (
            sum(WEIGHTS[k] * v["score"] for k, v in available.items())
            / total_weight
        )
        if compliance_result["score"] < 50 or has_critical_flag:
            decision = "rejected"
            if has_critical_flag and compliance_result["score"] >= 50:
                # Score không phản ánh vi phạm (xem spec mục 4) - ghi rõ lý do
                # thật để tránh gây hiểu nhầm khi điểm cao nhưng vẫn bị từ chối.
                veto_reason = (
                    "Bị từ chối do vi phạm Compliance (severity: critical), "
                    "độc lập với điểm tổng."
                )
        elif final_score >= 80:
            decision = "publish"
        elif final_score >= 50:
            decision = "needs_revision"
        else:
            decision = "rejected"

    report = {
        "node_id": state["node_id"],
        "final_score": final_score,
        "decision": decision,
        "missing_agents": missing,
        "details": results,
    }
    if veto_reason:
        report["veto_reason"] = veto_reason
    return {"final_score": final_score, "decision": decision, "report": report}
```

(Đổi tên biến cục bộ `compliance` → `compliance_result` để không trùng tên với module `compliance` vừa import ở Step 1 — chỉ trong phạm vi hàm này.)

- [ ] **Step 4: In `veto_reason` lên đầu suggestions trong `write_back_node`**

Sửa:

```python
def write_back_node(state: ContentReviewState) -> dict:
    suggestions_lines = []
    for name, result in (state.get("report") or {}).get("details", {}).items():
```

thành:

```python
def write_back_node(state: ContentReviewState) -> dict:
    report = state.get("report") or {}
    suggestions_lines = []
    if report.get("veto_reason"):
        suggestions_lines.append(f"[LÝ DO TỪ CHỐI] {report['veto_reason']}")
    for name, result in report.get("details", {}).items():
```

(Phần còn lại của hàm giữ nguyên không đổi.)

- [ ] **Step 5: Verify end-to-end trên bài mẫu Drupal thật đã có sẵn**

Yêu cầu trước: Docker Drupal đang chạy (`docker compose up -d`) và bài mẫu Sprint 1 "VF3 - Chiếc xe điện tốt nhất thế giới..." (node id `fdeeaec6-472a-449e-b007-1ee0e42dd51f`, xem `scripts/run_all_samples.py`) vẫn tồn tại trên Drupal.

Run: `.venv\Scripts\python.exe scripts\smoke_test_graph.py fdeeaec6-472a-449e-b007-1ee0e42dd51f`

Expected: JSON in ra có `"decision": "rejected"`, `report.details.compliance.flags` chứa ít nhất 1 flag với `"severity": "critical"` và `"rule"` nhắc tới "Luật Quảng cáo" (từ rule-based bắt cụm "tốt nhất"). Nếu `compliance.score >= 50`, JSON còn có thêm `"veto_reason"` giải thích lý do.

- [ ] **Step 6: Chạy lại toàn bộ 8 bài mẫu để xác nhận không có gì sập**

Run: `.venv\Scripts\python.exe scripts\run_all_samples.py`

Expected: cả 8 dòng đều in ra bình thường (không exception/traceback). Lưu ý: `final_score` của các bài sẽ đổi khác so với bảng trong `docs/sprint1-report.md` (vì trước đây compliance stub luôn = 100, giờ là điểm LLM thật) — đây là thay đổi dự kiến, không phải lỗi.

- [ ] **Step 7: Commit**

```bash
git add src/graph.py
git commit -m "feat: wire real Compliance Agent into graph, add veto_reason to report"
```

---

## Self-Review (đã thực hiện khi viết plan)

- **Spec coverage**: mục 2 (blacklist file) → Task 1; mục 3 (module compliance.py) → Task 1+2; mục 4 (không ép score) → ghi rõ trong Global Constraints + Task 2 Step 3 note; mục 5 (graph.py: compliance_node/aggregator_node/write_back_node) → Task 3; mục 6 (kiểm thử: rule-based / smoke test / verify Drupal thật) → Task 1/2/3 tương ứng 1:1; mục 7 (ngoài phạm vi) → không có task nào động tới brand_node, retry, pytest, gold set, UI.
- **Placeholder scan**: không còn TBD/TODO; mọi step đều có code đầy đủ.
- **Type consistency**: `match_blacklist(text: str) -> list[dict]` (Task 1) được `run()` gọi đúng chữ ký ở Task 2; `run(title, body) -> dict` (Task 2) được `compliance_node` gọi đúng ở Task 3; `report["veto_reason"]` (Task 3 Step 3) được `write_back_node` đọc đúng tên field ở Task 3 Step 4.
