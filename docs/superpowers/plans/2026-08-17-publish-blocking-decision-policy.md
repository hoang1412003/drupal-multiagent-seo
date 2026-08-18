# Publish Blocking Decision Policy v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans tuần tự. Chủ dự án đã chọn chế độ 2, vì vậy không dispatch subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây policy candidate `cam-nang-vn-v2` quyết định theo taxonomy A1--A7/B1--B11, giữ policy v1 bất biến, đồng thời tạo evaluator/release guard offline đủ để Evaluation Plan mở rộng và freeze một release chung trước mọi paid output.

**Architecture:** Bốn agent tiếp tục phát hiện vấn đề; một module thuần chuẩn hóa finding, kiểm assessment coverage và quyết định A -> B -> incomplete -> publish. A5/A6 là policy checks nằm ngoài công thức điểm và chỉ bật ở v2; graph/worker route exact policy version, còn evaluator/guard dùng chung release tuple nhưng chưa chạy API trong plan này.

**Tech Stack:** Python 3.12, standard library, JSON/YAML, LangGraph hiện hành, standalone test scripts, SHA-256, PowerShell, Git.

**Spec:** `docs/superpowers/specs/2026-08-17-publish-blocking-decision-policy-design.md` tại commit `68e32be`.

## Global Constraints

- Giao tiếp, tài liệu nghiệp vụ và evidence bằng tiếng Việt Nam.
- Thực hiện tuần tự ở chế độ 2; không dispatch subagent.
- Không gọi model/API trả phí trong bất kỳ task nào của plan prerequisite này.
- Mọi test/preflight chạy với `VF_ALLOW_PAID_EVAL=0`; provider-call count phải bằng 0.
- Policy ID chỉ nhận exact `cam-nang-vn-v1` và `cam-nang-vn-v2`; không alias, prefix hoặc fuzzy match.
- `cam-nang-vn-v1` vẫn là mặc định; characterization tests phải khóa decision, score, veto và missing-agent behavior cũ.
- Không sửa `docs/goldset/raw/G-*.txt`, `docs/goldset/labels.csv`, evidence E1/E5/E6 v1 hoặc nội dung C/GC/CV đã khóa.
- Không sửa `multiagent/config/scoring.yaml`; `meta.calibrated` phải tiếp tục `false`.
- A có quyền `rejected`; B chỉ có quyền `needs_revision`; nhiều B không tự thành A.
- `final_score` chỉ là diagnostic ở v2, không tham gia decision.
- A5/A6 không đi vào `score_from_criteria()` và không tạo thêm lượt gọi LLM.
- A6 chỉ thành effective A6 khi có `reference_id` thuộc safety source chính thức đã khóa; thiếu reference chỉ được fail-safe `needs_revision`.
- B15 chỉ đổi hành vi v2; đường v1 vẫn giữ matcher legacy cho tới cutover.
- Unknown release/schema/hash drift là fatal; assessment unavailable là sample-level `needs_revision` nếu chưa có A.
- Mọi file sửa/tạo bằng `apply_patch`; mỗi task có RED đúng nguyên nhân, GREEN focused, meta-test và commit riêng.
- Full offline cuối plan dùng `cd multiagent && .venv\Scripts\python.exe scripts\run_test_group.py all-offline`; yêu cầu summary 0 fail/0 skip.
- Không cần Docker hoặc DDEV cho các task pure/evaluator này; không tuyên bố đã kiểm UI trình duyệt vì không sửa JS.

## File/Responsibility Map

| File | Trách nhiệm sau plan |
|---|---|
| `multiagent/src/decision_policy.py` | Registry canonical, normalize/dedupe, coverage và decision v2 thuần |
| `multiagent/src/compliance_analysis.py` | Matcher CP5 legacy và contextual-v2 tách rõ |
| `multiagent/src/agents/content_quality.py` | CQ1--CQ8 cũ + policy check A5 trong cùng call khi v2 |
| `multiagent/src/agents/compliance.py` | CP1--CP9 cũ + A6/CP7-v2/safety reference khi v2 |
| `multiagent/src/kb/safety_rules.json` | Allowlist nguồn an toàn chính thức, version/hash được |
| `multiagent/src/state.py` | `policy_version` và `assessment_as_of` đi xuyên graph |
| `multiagent/src/graph.py` | Validate/route exact v1/v2, giữ legacy aggregator, enrich report |
| `multiagent/src/worker.py` | Truyền policy của job và ngày assessment chụp một lần |
| `multiagent/scripts/eval_policy_v2.py` | Dataset/runtime/preflight/run path dùng chung, provider injectable |
| `multiagent/scripts/eval_policy_v2_metrics.py` | E1/gold metrics/report-only thuần |
| `multiagent/scripts/policy_release.py` | Verify/freeze/record/approve release manifest, không `--force` |
| `docs/evidence/publish-policy-v2-manifest.json` | Trạng thái/version/hash của một release chung |
| `docs/evidence/corrected-publish-coverage-v1-protocol.md` | Protocol đầy đủ đăng ký trước E1/gold/corrected/coverage/smoke |
| `multiagent/scripts/test_*.py` | Regression/contract tests, luôn thuộc đúng một test group |

---

### Task 1: Xây decision engine thuần và canonical registry

**Files:**
- Create: `multiagent/src/decision_policy.py`
- Create: `multiagent/scripts/test_decision_policy.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- Produces: `POLICY_V1 = "cam-nang-vn-v1"`, `POLICY_V2 = "cam-nang-vn-v2"`.
- Produces: `PolicyContractError(ValueError)`.
- Produces: `require_policy_version(value: str | None, *, allow_legacy_default: bool) -> str`.
- Produces: `evaluate(fields: dict, agent_results: dict, *, assessment_as_of: str, final_score: float | None = None) -> dict`.
- `agent_results` keys exact: `content_quality`, `seo`, `brand`, `compliance`; mỗi result dùng `criteria`, `policy_checks`, `flags`, `unavailable_checks`.
- `evaluate()` không mutate input và không import graph/agent/provider.

- [ ] **Step 1: Viết RED contract tests**

Tạo helpers và test literal cho 18 mã, advisory, incomplete và drift:

```python
from copy import deepcopy

import pytest

from decision_policy import PolicyContractError, evaluate, require_policy_version


def criterion(cid, level, field="body", text="evidence"):
    return {
        "id": cid,
        "level": level,
        "occurrences": ([{"field": field, "text": text}]
                        if level in {0, 1} else []),
        "suggestion": "sửa",
    }


def base_results():
    return {
        "content_quality": {
            "score": 100.0,
            "criteria": [criterion(cid, 2) for cid in ("CQ1", "CQ2", "CQ3", "CQ4", "CQ5", "CQ7")],
            "policy_checks": [{"id": "A5", "status": "absent"}],
            "unavailable_checks": [],
        },
        "seo": {
            "score": 100.0,
            "criteria": [criterion(cid, 2) for cid in ("SEO5", "SEO7", "SEO9", "SEO10")],
            "unavailable_checks": [],
        },
        "brand": {
            "score": 100.0,
            "criteria": [criterion(cid, 2) for cid in ("BV1", "BV2", "BV3", "BV4", "BV7")],
            "unavailable_checks": [],
        },
        "compliance": {
            "score": 100.0,
            "criteria": [criterion(cid, 2) for cid in ("CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CP7", "CP8")],
            "policy_checks": [{"id": "A6", "status": "not_applicable"}],
            "flags": [],
            "unavailable_checks": [],
        },
    }


def clean_fields():
    return {
        "title": "Hướng dẫn sử dụng xe điện VinFast an toàn mỗi ngày",
        "meta_description": (
            "Hướng dẫn thực hành giúp người dùng vận hành, sạc và bảo quản "
            "xe điện VinFast an toàn, rõ ràng và phù hợp cho nhu cầu hằng ngày."
        ),
        "url_alias": "huong-dan-su-dung-xe-dien-vinfast-an-toan-moi-ngay",
        "body": "<h2>Chuẩn bị</h2><p>Đọc hướng dẫn trước khi sử dụng.</p>",
    }


def add_policy_check(results, code, *, reference_id=None):
    target = "content_quality" if code == "A5" else "compliance"
    check = {
        "id": code,
        "status": "present",
        "field": "body",
        "evidence": "Đọc hướng dẫn trước khi sử dụng.",
        "reason": ("Body không trả lời title và cần viết lại trên 50%."
                   if code == "A5" else "Chỉ dẫn tạo nguy cơ kỹ thuật rõ ràng."),
    }
    if reference_id is not None:
        check["reference_id"] = reference_id
    results[target]["policy_checks"] = [check]


def replace_level(results, agent, cid, level, text="evidence"):
    results[agent]["criteria"] = [
        criterion(cid, level, text=text) if item["id"] == cid else item
        for item in results[agent]["criteria"]
    ]


def test_moi_ma_a_doc_lap_deu_rejected():
    criterion_by_code = {"A1": "CP1", "A2": "CP2", "A3": "CP3", "A4": "CP4"}
    for code, cid in criterion_by_code.items():
        results = base_results()
        replace_level(results, "compliance", cid, 0)
        assert evaluate(clean_fields(), results, assessment_as_of="2026-08-17")["decision"] == "rejected"

    results = base_results()
    add_policy_check(results, "A5")
    assert evaluate(clean_fields(), results, assessment_as_of="2026-08-17")["decision"] == "rejected"

    results = base_results()
    add_policy_check(results, "A6", reference_id="VF-SAFE-CHARGING-CABLE-001")
    assert evaluate(clean_fields(), results, assessment_as_of="2026-08-17")["decision"] == "rejected"

    results = base_results()
    results["compliance"]["flags"] = [{
        "criterion_id": "CP9", "defect_code": "A7", "field": "body",
        "evidence": "javascript:alert(1)",
    }]
    assert evaluate(clean_fields(), results, assessment_as_of="2026-08-17")["decision"] == "rejected"


def test_moi_ma_b_doc_lap_deu_needs_revision():
    criterion_by_code = {
        "B1": ("compliance", "CP5"),
        "B2": ("compliance", "CP6"),
        "B5": ("brand", "BV1"),
        "B6": ("seo", "SEO9"),
        "B7": ("seo", "SEO5"),
        "B8": ("content_quality", "CQ1"),
        "B9": ("content_quality", "CQ5"),
        "B10": ("content_quality", "CQ7"),
        "B11": ("compliance", "CP7"),
    }
    for code, (agent, cid) in criterion_by_code.items():
        results = base_results()
        replace_level(results, agent, cid, 0)
        actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
        assert actual["decision"] == "needs_revision", code

    bad_fields = {
        "B3": {**clean_fields(), "meta_description": "quá ngắn"},
        "B4": {**clean_fields(), "title": "TIÊU ĐỀ VIẾT HOA TOÀN BỘ"},
        "B9": {**clean_fields(), "body": " ".join(["từ"] * 501)},
    }
    for code, fields in bad_fields.items():
        actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
        assert actual["decision"] == "needs_revision", code


def test_nhieu_b_khong_tu_nang_thanh_rejected():
    results = base_results()
    replace_level(results, "compliance", "CP5", 0)
    replace_level(results, "compliance", "CP6", 0)
    replace_level(results, "content_quality", "CQ1", 0)
    replace_level(results, "content_quality", "CQ7", 0)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert {finding["defect_code"] for finding in actual["effective_findings"]} == {"B1", "B2", "B8", "B10"}


def test_cq3_cq4_seo7_seo10_level_0_van_publish():
    results = base_results()
    for cid in ("CQ3", "CQ4"):
        replace_level(results, "content_quality", cid, 0)
    for cid in ("SEO7", "SEO10"):
        replace_level(results, "seo", cid, 0)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "publish"
    assert len(actual["advisory_findings"]) == 4


def test_clean_complete_publish():
    actual = evaluate(clean_fields(), base_results(), assessment_as_of="2026-08-17", final_score=12.0)
    assert actual["decision"] == "publish"
    assert actual["final_score"] == 12.0


def test_unavailable_khong_co_a_thanh_needs_revision():
    results = base_results()
    replace_level(results, "seo", "SEO5", None)
    results["seo"]["unavailable_checks"] = ["SEO5"]
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert actual["incomplete_assessment"] is True


def test_a_cong_unavailable_van_rejected_va_incomplete():
    results = base_results()
    replace_level(results, "compliance", "CP1", 0)
    replace_level(results, "seo", "SEO5", None)
    results["seo"]["unavailable_checks"] = ["SEO5"]
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "rejected"
    assert actual["incomplete_assessment"] is True


def test_b10_dedupe_giu_hai_sources():
    results = base_results()
    replace_level(results, "content_quality", "CQ7", 0, text="cùng chứng cứ")
    replace_level(results, "compliance", "CP8", 0, text="cùng chứng cứ")
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    b10 = [finding for finding in actual["effective_findings"] if finding["defect_code"] == "B10"]
    assert len(b10) == 1
    assert b10[0]["sources"] == ["CQ7", "CP8"]


def test_output_order_canonical_va_khong_mutate_input():
    results = base_results()
    replace_level(results, "compliance", "CP7", 0)
    replace_level(results, "compliance", "CP1", 0)
    before = deepcopy(results)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert [item["defect_code"] for item in actual["effective_findings"]] == ["A1", "B11"]
    assert results == before


def test_unknown_policy_check_va_unknown_defect_code_fatal():
    results = base_results()
    results["content_quality"]["policy_checks"] = [{"id": "A99", "status": "present"}]
    with pytest.raises(PolicyContractError, match="A99"):
        evaluate(clean_fields(), results, assessment_as_of="2026-08-17")

    results = base_results()
    results["compliance"]["flags"] = [{
        "criterion_id": "CP9", "defect_code": "A99", "field": "body",
        "evidence": "văn xuôi ẩn",
    }]
    with pytest.raises(PolicyContractError, match="A99"):
        evaluate(clean_fields(), results, assessment_as_of="2026-08-17")


def test_policy_version_exact_khong_fuzzy():
    assert require_policy_version(None, allow_legacy_default=True) == "cam-nang-vn-v1"
    for value in ("v2", "cam-nang-vn-v2 ", "CAM-NANG-VN-V2", "cam-nang-vn-v3"):
        with pytest.raises(PolicyContractError):
            require_policy_version(value, allow_legacy_default=False)
```

Không dùng title/meta/body trống trong fixture clean vì chúng tự sinh B3/B4.
Fixture sạch tối thiểu phải có title 40--70 ký tự, meta 140--170 ký tự, `url_alias`
không dấu <=75 và body <=500 tiếng hoặc có H2.

- [ ] **Step 2: Chạy RED**

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
```

Expected: exit 1, `ModuleNotFoundError: No module named 'decision_policy'`.

- [ ] **Step 3: Implement registry và validator tối thiểu**

Registry phải literal, không suy mã từ chữ số trong tên criterion:

```python
POLICY_V1 = "cam-nang-vn-v1"
POLICY_V2 = "cam-nang-vn-v2"
DEFECT_ORDER = (
    "A1", "A2", "A3", "A4", "A5", "A6", "A7",
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11",
)

CRITERION_SOURCES = {
    "A1": (("compliance", "CP1", frozenset({0})),),
    "A2": (("compliance", "CP2", frozenset({0})),),
    "A3": (("compliance", "CP3", frozenset({0})),),
    "A4": (("compliance", "CP4", frozenset({0})),),
    "B1": (("compliance", "CP5", frozenset({0, 1})),),
    "B2": (("compliance", "CP6", frozenset({0, 1})),),
    "B5": tuple(("brand", cid, frozenset({0, 1}))
                for cid in ("BV1", "BV2", "BV3", "BV4", "BV7")),
    "B6": (("seo", "SEO9", frozenset({0, 1})),),
    "B7": (("seo", "SEO5", frozenset({0, 1})),),
    "B8": tuple(("content_quality", cid, frozenset({0, 1}))
                for cid in ("CQ1", "CQ2")),
    "B9": (("content_quality", "CQ5", frozenset({0, 1})),),
    "B10": (("content_quality", "CQ7", frozenset({0, 1})),
             ("compliance", "CP8", frozenset({0, 1}))),
    "B11": (("compliance", "CP7", frozenset({0, 1})),),
}
```

Field checks dùng `assessment_as_of` do caller truyền:

```python
B3 = not (140 <= len(meta_description) <= 170)
B4 = not (40 <= len(title) <= 70) or title_is_all_caps or stale_year
B9 = len(strip_html(body).split()) > 500 and not has_h2
```

A5/A6 chỉ đọc `policy_checks` exact ID; A6 `present` mà `reference_id` rỗng
phải chuyển check sang unavailable, không tạo A6. A7 chỉ đọc flag có đồng
thời `criterion_id == "CP9"` và `defect_code == "A7"`.

- [ ] **Step 4: Implement finding/coverage/dedupe/decision**

Finding deterministic dùng `evidence_kind=absence|measurement`; finding LLM
dùng `excerpt`. Dedupe key:

```python
(defect_code, field, " ".join(evidence.casefold().split()))
```

Coverage absent của mã multi-source chỉ complete khi mọi source không nằm
trong `unavailable_checks`. Quyết định đúng literal trong spec; trả đủ keys
`effective_findings`, `advisory_findings`, `decision_basis`, `coverage`,
`incomplete_assessment`, `missing_agents`, `drift`.

- [ ] **Step 5: Chạy GREEN và meta-test**

```powershell
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
.\.venv\Scripts\python.exe scripts\test_test_group_runner.py
```

Expected: toàn bộ pass, test mới thuộc đúng nhóm `pure`, provider calls 0.

- [ ] **Step 6: Commit**

```powershell
git add -- multiagent/src/decision_policy.py multiagent/scripts/test_decision_policy.py multiagent/scripts/test_groups.json
git commit -m "feat: add taxonomy publish decision engine"
```

---

### Task 2: Sửa B15 theo version mà không đổi CP5 legacy

**Files:**
- Modify: `multiagent/src/compliance_analysis.py:20-89`
- Modify: `multiagent/src/agents/compliance.py:216-240,608-674`
- Modify: `multiagent/scripts/test_compliance_rubric.py:175-208`

**Interfaces:**
- Modify: `claim_tam_hoat_dong(text_theo_field: dict, *, contextual: bool = False) -> list[dict]`.
- `contextual=False` giữ byte-for-byte matcher `_KM` legacy.
- `contextual=True` yêu cầu context tầm hoạt động và loại rate/consumption/cost.
- `compliance.run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi", danh_gia_llm=_danh_gia_llm, danh_gia_cp3=None, policy_version: str = POLICY_V1) -> dict | None` truyền contextual chỉ khi v2.

- [ ] **Step 1: Viết RED B15 literal tests**

```python
def test_cp5_v2_loai_ti_le_tieu_hao_va_chi_phi_nhung_giu_quang_duong():
    text = {"body": (
        "Xe tiêu thụ 13,4 kWh/100km, chi phí 1.000 đồng/km. "
        "Quãng đường di chuyển 80km sau một lần sạc."
    )}
    got = ca.claim_tam_hoat_dong(text, contextual=True)
    assert [x["text"] for x in got] == ["80km"]


def test_cp5_legacy_co_y_giu_hanh_vi_cu():
    text = {"body": "Xe tiêu thụ 13,4 kWh/100km."}
    assert ca.claim_tam_hoat_dong(text) == [
        {"field": "body", "text": "100km"}
    ]
```

Thêm ca positive cho `đi được 285 km`, `tầm hoạt động 420 km`, `sau một lần
sạc, xe đi được 300 km`; negative cho `7,8 lít/100km`, `chi phí trong 1km`,
`100 đồng/km`.

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
```

Expected: exit 1 vì `claim_tam_hoat_dong()` chưa nhận `contextual`.

- [ ] **Step 3: Implement contextual matcher**

Thêm cửa sổ 120 ký tự, regex context và regex loại trừ:

```python
_TAM_HOAT_DONG = re.compile(
    r"quãng đường|đi được|di chuyển được|tầm hoạt động|sau một lần sạc",
    re.IGNORECASE,
)
_TY_LE_KM = re.compile(
    r"(?:/\s*100\s*km|đồng\s*/\s*km|kwh\s*/\s*100\s*km|"
    r"lít\s*/\s*100\s*km)",
    re.IGNORECASE,
)
```

Chỉ nhánh contextual dùng filter; default gọi `_tim(_KM, text_theo_field)` như cũ.

- [ ] **Step 4: Route CP5 theo exact policy và khóa legacy score**

`_cp5_tam_hoat_dong(text_theo_field: dict, *, contextual: bool = False)` nhận cờ từ `run()`. Thêm test
cùng fields/fake LLM chứng minh v1 vẫn sinh CP5 legacy, v2 dùng contextual;
không đổi score v1 fixture hiện có.

- [ ] **Step 5: Chạy GREEN/regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_e5_khop_aggregator.py
```

Expected: pass, không LLM thật.

- [ ] **Step 6: Commit**

```powershell
git add -- multiagent/src/compliance_analysis.py multiagent/src/agents/compliance.py multiagent/scripts/test_compliance_rubric.py
git commit -m "fix: scope CP5 range claims in policy v2"
```

---

### Task 3: Thêm A5 policy check vào Content Quality trong cùng lượt gọi

**Files:**
- Modify: `multiagent/src/agents/content_quality.py:30-295`
- Modify: `multiagent/scripts/test_cq_rubric.py`
- Modify: `docs/rubrics.md`

**Interfaces:**
- Modify: `content_quality.run(fields: dict, *, danh_gia_llm=_danh_gia_llm, content_type: str = "cam_nang", langcode: str = "vi", policy_version: str = POLICY_V1) -> dict | None`.
- Produces result keys `policy_checks: list[dict]` và `unavailable_checks: list[str]`.
- V1 dùng prompt/schema CQ1--CQ8 cũ và trả `policy_checks=[]`.
- V2 dùng cùng một `call_agent()` với schema bổ sung exact check A5.
- A5 không xuất hiện trong `criteria` và không đổi `score_from_criteria()`.

- [ ] **Step 1: Viết RED tests cho schema/semantics/call count**

Test matrix phải chứa literal input và expected output sau:

| Case | Fake A5 response / lỗi | Assertion |
|---|---|---|
| body lạc hoàn toàn title và cần viết lại trên 50% | `present`, evidence là câu có thật trong body | A5 nằm trong `policy_checks`, không nằm trong `criteria` |
| chỉ một đoạn phụ lạc đề | `absent` | không sinh effective A5 |
| bài ngắn nhưng trả lời đúng title | `absent` | không sinh effective A5 |
| evidence không phải substring của field | `present` với evidence bịa | normalize thành `unavailable_checks=["A5"]` |
| callback ném `RuntimeError` | không có raw | `A5` unavailable và CQ deterministic vẫn được trả |
| exact v1 | response CQ1--CQ8 cũ | prompt không chứa `A5`, score/criteria bằng fixture trước thay đổi |

Call-count test phải dùng counter thật:

```python
def test_v2_a5_dung_chung_mot_call_cq(monkeypatch):
    calls = []

    def fake_call_agent(**kwargs):
        calls.append(kwargs)
        return {
            "loi": [],
            "criteria": [],
            "policy_checks": [{
                "id": "A5",
                "status": "absent",
                "field": "body",
                "evidence": "",
                "reason": "Body trả lời đúng chủ đề trong title.",
            }],
        }

    monkeypatch.setattr(content_quality, "call_agent", fake_call_agent)
    result = content_quality.run(FIELDS, policy_version="cam-nang-vn-v2")
    assert len(calls) == 1
    assert result["policy_checks"][0]["id"] == "A5"
    assert result["policy_checks"][0]["status"] == "absent"
```

Fake raw response v2:

```python
{
    "loi": [],
    "criteria": [],
    "policy_checks": [{
        "id": "A5",
        "status": "present",
        "field": "body",
        "evidence": "đoạn nguyên văn trong body",
        "reason": "Body không trả lời title và phải viết lại trên 50%.",
    }],
}
```

Monkeypatch `call_agent` bằng counter và assert đúng một lần cho toàn CQ.

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_cq_rubric.py
```

Expected: fail vì `run()` chưa nhận `policy_version`/chưa trả policy checks.

- [ ] **Step 3: Thêm prompt/schema variant v2**

Giữ `_LLM_PROMPT` v1 bất biến. Tạo `_A5_PROMPT` và builder:

```python
def llm_prompt(policy_version: str) -> str:
    require_policy_version(policy_version, allow_legacy_default=False)
    return (_LLM_PROMPT if policy_version == POLICY_V1
            else _LLM_PROMPT + "\n\n" + _A5_PROMPT)
```

Schema v2 bắt buộc đúng một A5 check; schema v1 giữ nguyên. `present` cần
evidence thật trong field; `absent` không cần occurrence; output thiếu/lỗi
thành unavailable.

- [ ] **Step 4: Giữ score và issues cũ**

Danh sách `criteria` vẫn đúng CQ1--CQ8. `policy_checks` và
`unavailable_checks` chỉ là keys cộng thêm; `_issues_from_criteria()` không
đọc A5. Cập nhật fake callbacks cũ nhận `**kwargs` nhưng không đổi expectation.

- [ ] **Step 5: Cập nhật rubric supplement v2**

Thêm mục versioned, không sửa ý nghĩa bảng v1:

```text
CQ-A5 là policy-only, present/absent/unavailable, không vào điểm;
present cần body không trả lời title + rewrite >50%; ánh xạ A5/rejected.
```

- [ ] **Step 6: Chạy GREEN/regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_cq_rubric.py
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
```

Expected: pass, provider calls 0.

- [ ] **Step 7: Commit**

```powershell
git add -- multiagent/src/agents/content_quality.py multiagent/scripts/test_cq_rubric.py docs/rubrics.md
git commit -m "feat: assess topic failure for policy v2"
```

---

### Task 4: Thêm safety source, A6, CP7-v2 và canonical A7

**Files:**
- Create: `multiagent/src/kb/safety_rules.json`
- Modify: `multiagent/src/agents/compliance.py:30-674`
- Modify: `multiagent/scripts/test_compliance_rubric.py`
- Modify: `multiagent/scripts/test_cp9_chi_dan_an.py`
- Modify: `multiagent/scripts/test_kb_specs.py`
- Modify: `docs/rubrics.md`

**Interfaces:**
- Produces: `load_safety_rules(path: str | None = None) -> dict` với schema/version validation.
- Modify: `compliance.run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi", danh_gia_llm=_danh_gia_llm, danh_gia_cp3=None, policy_version: str = POLICY_V1, safety_rules: dict | None = None) -> dict | None`.
- V2 trả `policy_checks` gồm exact A6 và `unavailable_checks`.
- CP7 v2: NA/0/1/2 theo guideline; level 0/1 được decision engine map B11.
- CP9 flag v2 có `criterion_id="CP9"`, `defect_code="A7"`; v1 severity/veto cũ không đổi.

- [ ] **Step 1: Tạo RED tests cho safety source**

Test từ chối duplicate `reference_id`, URL không HTTPS, thiếu `accessed_at`,
content/language sai kiểu và rule rỗng. Test exact hai reference chính thức:

```json
{
  "version": 1,
  "rules": [
    {
      "reference_id": "VF-SAFE-CHARGING-CABLE-001",
      "source_url": "https://vinfastauto.com/vn_vi/bo-sac-di-dong-tai-nha-co-an-toan-khong",
      "accessed_at": "2026-08-17",
      "content_type": "cam_nang",
      "langcode": "vi",
      "rule": "Không kéo căng, gập, thắt, kéo hoặc dẫm lên cáp sạc."
    },
    {
      "reference_id": "VF-SAFE-HIGH-VOLTAGE-001",
      "source_url": "https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien",
      "accessed_at": "2026-08-17",
      "content_type": "cam_nang",
      "langcode": "vi",
      "rule": "Người dùng không tự tháo, sửa hoặc thay bộ phận, cáp hay đầu nối điện áp cao."
    }
  ]
}
```

- [ ] **Step 2: Viết RED A6/CP7/A7 tests**

Test matrix phải khóa từng nhánh, không gộp thành một smoke test:

| Case | Input/fake response | Assertion |
|---|---|---|
| A6 hợp lệ | evidence là substring của body, `VF-SAFE-CHARGING-CABLE-001` | `status=present`, reference được giữ |
| A6 reference lạ | `reference_id=VF-UNKNOWN-001` | A6 bị chuyển thành unavailable, không rejected |
| hướng dẫn kỹ thuật đúng nguồn | fake response `absent` | assessment A6 complete, không finding |
| bài không có hướng dẫn kỹ thuật | fake response `not_applicable` | assessment A6 complete, không finding |
| callback hỏng | `RuntimeError` | A6 và CP2/CP4/CP7/CP8 chưa máy chốt đều unavailable |
| CP7 v2 | lần lượt NA, 0, 1, 2 | NA không finding; 0/1 map B11; 2 không finding |
| CP7 v1 | fixture prompt/raw cũ | prompt, score và severity không đổi |
| CP9 v2/v1 | cùng một URL nguy hiểm | v2 flag exact CP9/A7; v1 vẫn critical/veto cũ |
| CP9 exclusion | CSS ẩn layout, tracking pixel, URL và marker kỹ thuật | không sinh A7 |
| CP9 hidden prose | đoạn văn xuôi có ý nghĩa bị ẩn khỏi hiển thị | sinh exact CP9/A7 |

Call-count test dùng callback thật và kiểm schema gửi vào:

```python
def test_v2_compliance_chi_goi_llm_mot_lan():
    calls = []

    def fake_llm(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return {
            "criteria": {
                "CP2": {"id": "CP2", "level": 2, "occurrences": [], "suggestion": ""},
                "CP4": {"id": "CP4", "level": 2, "occurrences": [], "suggestion": ""},
                "CP7": {"id": "CP7", "level": None, "occurrences": [], "suggestion": ""},
                "CP8": {"id": "CP8", "level": 2, "occurrences": [], "suggestion": ""},
            },
            "policy_checks": [{
                "id": "A6", "status": "not_applicable", "field": "body",
                "evidence": "", "reason": "Không có hướng dẫn kỹ thuật.",
                "reference_id": "",
            }],
        }

    result = compliance.run(
        FIELDS,
        danh_gia_llm=fake_llm,
        policy_version="cam-nang-vn-v2",
        safety_rules=VALID_SAFETY_RULES,
    )
    assert len(calls) == 1
    assert result["policy_checks"][0]["status"] == "not_applicable"
```

Mọi fake callback cập nhật nhận `**kwargs`; test không gọi mạng/RAG thật.

- [ ] **Step 3: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_kb_specs.py
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_cp9_chi_dan_an.py
```

Expected: fail đúng vì safety loader/A6 output chưa tồn tại.

- [ ] **Step 4: Implement safety validation và prompt/schema v2**

V1 tiếp tục dùng `_LLM_PROMPT`/`_LLM_SCHEMA` cũ. V2 builder thêm safety
rules và policy check A6 vào chính call CP2/CP4/CP7/CP8. Schema A6:

```python
{
    "id": "A6",
    "status": "present|absent|not_applicable|unavailable",
    "field": "body",
    "evidence": "Không kéo căng hoặc dẫm lên cáp sạc.",
    "reason": "Nội dung hướng dẫn trái với quy tắc an toàn đã khóa.",
    "reference_id": "<enum safety allowlist>",
}
```

`present` thiếu exact evidence hoặc allowlisted reference -> unavailable.
Normalizer v2 trả nội bộ `{"criteria": {criterion_id: criterion},
"policy_checks": [A6]}`; adapter v1 vẫn chấp nhận mapping criterion cũ để
không phá characterization fixtures. Mọi callback v2 nhận `policy_version`
và `safety_rules` qua keyword; callback v1 hiện hữu được cập nhật nhận
`**kwargs` nhưng giữ nguyên expected output.

- [ ] **Step 5: Chuẩn hóa CP7-v2/A7 output và unavailable coverage**

CP7 v2 prompt dùng đúng contract guideline; không sửa CP7 v1 prompt. Khi
LLM hỏng nhưng hard CP1/CP3/A7 vẫn cho result, thêm các check LLM vào
`unavailable_checks` thay vì biến thành NA sạch. A7 thêm identifier canonical
chỉ ở output metadata, không đổi legacy severity.

- [ ] **Step 6: Cập nhật docs/rubric supplement**

Ghi A6 policy-only, A7 canonical, CP7-v2 -> B11 và safety source hash; không
gọi CP7 v1 là B11 trong evidence lịch sử.

- [ ] **Step 7: Chạy GREEN/regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_kb_specs.py
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_cp9_chi_dan_an.py
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
```

Expected: pass, 0 provider calls.

- [ ] **Step 8: Commit**

```powershell
git add -- multiagent/src/kb/safety_rules.json multiagent/src/agents/compliance.py multiagent/scripts/test_compliance_rubric.py multiagent/scripts/test_cp9_chi_dan_an.py multiagent/scripts/test_kb_specs.py docs/rubrics.md
git commit -m "feat: add safety and policy compliance checks"
```

---

### Task 5: Khóa assessment coverage và route graph/worker exact version

**Files:**
- Modify: `multiagent/src/agents/seo.py:273-330`
- Modify: `multiagent/src/state.py`
- Modify: `multiagent/src/graph.py:61-354`
- Modify: `multiagent/src/worker.py:306-430`
- Create: `multiagent/scripts/test_policy_routing.py`
- Modify: `multiagent/scripts/test_seo_rubric.py`
- Modify: `multiagent/scripts/test_aggregator_veto.py`
- Modify: `multiagent/scripts/test_worker_graph_integration.py`
- Modify: `multiagent/scripts/test_report_json.py`
- Modify: `multiagent/scripts/test_groups.json`
- Modify: `docs/architecture.md`

**Interfaces:**
- State imports `NotRequired` và thêm `policy_version: NotRequired[str]`, `assessment_as_of: NotRequired[str]` để không phá legacy callers đang thiếu hai key.
- `orchestrator_node()` validates version before fan-out/provider.
- Agent nodes pass exact version cho Content Quality/Compliance.
- `aggregate_score_v1(state) -> dict` is extracted characterization-equivalent legacy logic.
- `aggregator_node(state) -> dict` routes v1/v2; v2 calls `decision_policy.evaluate()`.
- Worker passes `job["policy_version"]` and one UTC date captured at run start.

- [ ] **Step 1: Viết RED routing/legacy/fail-before-provider tests**

Khóa routing bằng matrix độc lập:

| Case | State/job | Assertion |
|---|---|---|
| script legacy thiếu version | không có `policy_version` | normalize exact v1 |
| exact v1 | fixture aggregator hiện hữu | decision, score, veto reason và missing note giống snapshot trước refactor |
| v2 score 93 + CQ1 level 0 | assessment complete | `needs_revision`, basis B8 |
| v2 score 12 + không A/B | assessment complete | `publish`, score chỉ diagnostic |
| worker v2 | job có exact v2 | graph input có cùng version và một `assessment_as_of` ISO date |
| report v2 | output decision engine | có basis/findings/coverage/incomplete |
| report v1 | legacy state | các field cũ vẫn tồn tại và JSON consumer cũ đọc được |

Test fail-before-provider phải patch đủ bốn node và kiểm counter bằng 0:

```python
def test_unknown_version_fail_o_orchestrator_truoc_agent_call(monkeypatch):
    calls = []

    def forbidden_call(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(content_quality, "run", forbidden_call)
    monkeypatch.setattr(seo, "run", forbidden_call)
    monkeypatch.setattr(brand, "run", forbidden_call)
    monkeypatch.setattr(compliance, "run", forbidden_call)
    with pytest.raises(PolicyContractError):
        graph.orchestrator_node({"policy_version": "cam-nang-vn-v2-beta"})
    assert calls == []
```

Unknown-version test monkeypatch bốn `agent.run` tăng counter và assert counter
vẫn 0 sau `orchestrator_node()` ném `PolicyContractError`.

- [ ] **Step 2: Viết RED SEO unavailable coverage test**

```python
def test_seo_llm_hong_ghi_unavailable_mapped_checks():
    result = seo.run(FIELDS, danh_gia_llm=lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    assert {"SEO5", "SEO9"}.issubset(set(result["unavailable_checks"]))
```

Máy đã chốt SEO5/SEO9 thì không ghi unavailable cho chính check đó.

- [ ] **Step 3: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_policy_routing.py
.\.venv\Scripts\python.exe scripts\test_seo_rubric.py
```

Expected: fail vì route/coverage keys chưa tồn tại.

- [ ] **Step 4: Implement agent coverage và state routing**

SEO ghi `unavailable_checks` chỉ cho mã cần LLM mà chưa được máy chốt. Brand
B5 mappings đều deterministic; agent result `None` đã đủ làm toàn B5 sources
unavailable, không thêm trạng thái giả.

`orchestrator_node()` gọi:

```python
policy = require_policy_version(
    state.get("policy_version"), allow_legacy_default=True
)
return {"policy_version": policy}
```

- [ ] **Step 5: Extract legacy aggregator và thêm v2 route**

Di chuyển nguyên logic v1 vào `aggregate_score_v1()` trước khi thêm nhánh.
V2 tái dùng diagnostic score của v1 nhưng ghi đè decision/report basis bằng
`decision_policy.evaluate()`. Không dùng `publish_min`, `needs_revision_min`
hoặc compliance-score veto để quyết định v2.

- [ ] **Step 6: Pass policy/date từ worker và enrich report**

Worker dùng `datetime.now(timezone.utc).date().isoformat()` đúng một lần trước
`invoke()`. `_build_report_json()` cộng `policy_version`, `decision_basis`,
`effective_findings`, `coverage`, `incomplete_assessment`; field cũ giữ nguyên.

- [ ] **Step 7: Cập nhật architecture versioned**

Giữ mô tả v1 lịch sử, thêm flow v2 và ghi rõ chưa active/cutover. Không ghi
metric chưa chạy.

- [ ] **Step 8: Chạy GREEN/regression/meta-test**

```powershell
.\.venv\Scripts\python.exe scripts\test_policy_routing.py
.\.venv\Scripts\python.exe scripts\test_aggregator_veto.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
.\.venv\Scripts\python.exe scripts\test_report_json.py
.\.venv\Scripts\python.exe scripts\test_seo_rubric.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: pass, v1 characterization unchanged, 0 provider calls.

- [ ] **Step 9: Commit**

```powershell
git add -- multiagent/src/agents/seo.py multiagent/src/state.py multiagent/src/graph.py multiagent/src/worker.py multiagent/scripts/test_policy_routing.py multiagent/scripts/test_seo_rubric.py multiagent/scripts/test_aggregator_veto.py multiagent/scripts/test_worker_graph_integration.py multiagent/scripts/test_report_json.py multiagent/scripts/test_groups.json docs/architecture.md
git commit -m "feat: route versioned publish decision policy"
```

---

### Task 6: Xây evaluator v2 base và E1/gold metrics thuần

**Files:**
- Create: `multiagent/scripts/eval_policy_v2.py`
- Create: `multiagent/scripts/eval_policy_v2_metrics.py`
- Create: `multiagent/scripts/test_eval_policy_v2.py`
- Create: `multiagent/scripts/test_eval_policy_v2_metrics.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- Produces dataclass `EvaluationSample(sample_id, fields, expected_label, split, source_url, content_sha256)`.
- Produces: `load_dataset(kind: str, repo_root: Path) -> list[EvaluationSample]`, hỗ trợ `e1|gold` ở task này.
- Produces: `build_runtime_contract(repo_root: Path, dataset_kind: str, samples: list[EvaluationSample], assessment_as_of: str, output_path: Path) -> dict`.
- Produces: `run_policy_sample(sample, runtime_contract, *, agent_runner=None) -> dict`.
- Produces: `run_samples(samples, output_path, runtime_contract, *, repeats=1, agent_runner=None) -> dict`.
- Produces metrics: `stability_metrics(raw) -> dict`, `gold_metrics(raw) -> dict`.
- Raw là object `_meta` + flat `results`; E1 phân biệt bằng `repeat_index=1..5`.
- Report-only metrics module không import agent/provider.

- [ ] **Step 1: Viết RED dataset/runtime tests**

Dataset/runtime matrix:

| Case | Assertion exact |
|---|---|
| `load_dataset("e1")` | ordered IDs bằng `G-001` tới `G-010`; `run_samples(samples, output_path, runtime_contract, repeats=5)` có 50 result và mỗi ID đủ repeat 1--5 |
| `load_dataset("gold")` | ordered IDs bằng 33 dòng canonical của labels AI-v1.4, không lấy GC/CV |
| unknown dataset hoặc policy | ném contract error trước import agent/provider |
| raw schema | mỗi result đủ sample/repeat/decision/basis/coverage/final_score/usage/cost/latency/release tuple |
| resume | thiếu hoặc lệch bất kỳ release field nào đều fatal, không append |
| inventory | duplicate hoặc thiếu sample/repeat đều fatal |

Isolation test phải chứng minh label không rò vào runner:

```python
def test_expected_label_khong_duoc_truyen_vao_agent_runner(tmp_path):
    seen = []

    def fake_runner(**kwargs):
        seen.append(kwargs)
        return clean_agent_results()

    sample = EvaluationSample(
        sample_id="G-001",
        fields=VALID_FIELDS,
        expected_label="rejected",
        split="gold",
        source_url="https://example.invalid/G-001",
        content_sha256="0" * 64,
    )
    contract = fake_runtime_contract(dataset_kind="gold", output_path=tmp_path / "raw.json")
    raw = run_samples([sample], tmp_path / "raw.json", contract, agent_runner=fake_runner)
    assert len(raw["results"]) == 1
    assert set(seen[0]) == {"fields", "policy_version", "assessment_as_of"}
    assert "expected_label" not in repr(seen[0])
    assert raw["_meta"]["usage_events"] == 0
```

Fake runner nhận duy nhất `fields`, `policy_version`, `assessment_as_of`; test
assert không có `expected_label`, `defect_codes` hoặc manifest target trong
kwargs.

- [ ] **Step 2: Viết RED pure metric tests**

Metric tests dùng raw nhỏ nhưng đủ mẫu:

```python
def test_e1_decision_consistency_va_sigma():
    raw = e1_raw({
        "G-001": [("publish", 80.0)] * 5,
        "G-002": [("needs_revision", 70.0)] * 4 + [("publish", 74.0)],
    })
    metrics = stability_metrics(raw)
    assert metrics["decision_consistency"] == 0.9
    assert metrics["samples"]["G-001"]["mode_agreement"] == 1.0
    assert metrics["samples"]["G-002"]["mode_agreement"] == 0.8
    assert metrics["final_score_sigma"] is not None


def test_e1_thieu_mot_repeat_fatal():
    with pytest.raises(EvaluationContractError, match="repeat"):
        stability_metrics(e1_raw({"G-001": [("publish", 80.0)] * 4}))


def test_gold_confusion_kappa_recall_va_false_publish():
    raw = gold_raw([
        ("publish", "publish"),
        ("needs_revision", "needs_revision"),
        ("rejected", "rejected"),
        ("rejected", "publish"),
    ])
    metrics = gold_metrics(raw)
    assert metrics["label_order"] == ["publish", "needs_revision", "rejected"]
    assert metrics["confusion"] == [[1, 0, 0], [0, 1, 0], [1, 0, 1]]
    assert metrics["recall"]["rejected"] == 0.5
    assert metrics["false_publish_count"] == 1
    assert metrics["kappa"] is not None


def test_denominator_zero_tra_none_status_na():
    metrics = gold_metrics(gold_raw([("publish", "publish")]))
    assert metrics["recall"]["rejected"] is None
    assert metrics["gate_status"]["rejected_recall"] == "NA"


def test_report_only_khong_import_ai_core_agents():
    source = Path(eval_policy_v2_metrics.__file__).read_text(encoding="utf-8")
    assert "ai_core" not in source
    assert "src.agents" not in source
```

- [ ] **Step 3: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2.py
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2_metrics.py
```

Expected: exit 1 do hai module chưa tồn tại.

- [ ] **Step 4: Implement dataset loader và release tuple**

Gold đọc `docs/goldset/labels-ai-v1.4.csv`, exact 33 ID, provenance
`AI-annotated-partially-exposed`; E1 lấy G-001..G-010 nhưng không dùng label
trong prompt. Fields dùng `label_helper.parse_sample` và production
`_extract_image_alt`.

Runtime contract hash ít nhất:

```text
policy source + v1/v2 prompts + schemas + rubric/guideline + scoring
+ safety rules + fact/brand KB + embedding config + ordered content hashes
+ dataset manifests + Data HEAD + assessment_as_of + output path
```

Model phải lấy từ `ai_core.MODEL`; không đoán Codex runtime model.
`eval_policy_v2.py` không import `ai_core`, bốn agent hoặc provider ở module
scope: validate dataset/policy/release trước, rồi mới lazy-import `ai_core` để
đọc `MODEL`; chỉ authorized `--run` mới lazy-import/call các agent.

- [ ] **Step 5: Implement one shared fake-injectable run path**

Default `agent_runner` gọi bốn agent đúng một lần mỗi sample/repeat, tất cả
với policy v2, rồi `decision_policy.evaluate()`. Clear/snapshot
`ai_core.USAGE_LOG` theo repeat; cost dùng `review_platform.pricing` và
`config/model_pricing.yaml`. Ghi atomic/resumable sau mỗi repeat; output tồn
tại chỉ resume khi exact release tuple khớp.

- [ ] **Step 6: Implement metrics/report-only**

E1 lưu decision consistency, per-sample mode agreement, `final_score` sigma
và usage/cost. Gold lưu confusion, Kappa, recall rejected/needs_revision,
false publish 0/33 target và provenance limitation. Không scan threshold.

- [ ] **Step 7: Chạy GREEN/meta-test**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2.py
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2_metrics.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
.\.venv\Scripts\python.exe scripts\test_test_group_runner.py
```

Expected: pass, provider counter 0, tests thuộc `pure`.

- [ ] **Step 8: Commit**

```powershell
git add -- multiagent/scripts/eval_policy_v2.py multiagent/scripts/eval_policy_v2_metrics.py multiagent/scripts/test_eval_policy_v2.py multiagent/scripts/test_eval_policy_v2_metrics.py multiagent/scripts/test_groups.json
git commit -m "eval: add policy v2 core runner and metrics"
```

---

### Task 7: Xây release guard và protocol skeleton trước output

**Files:**
- Create: `multiagent/scripts/policy_release.py`
- Create: `multiagent/scripts/test_policy_release.py`
- Create: `docs/evidence/corrected-publish-coverage-v1-protocol.md`
- Create: `docs/evidence/publish-policy-v2-manifest.json`
- Modify: `multiagent/scripts/eval_policy_v2.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- Produces: `verify(manifest_path: Path, repo_root: Path) -> dict`.
- Produces: CLI commands `verify`, `freeze`, `record-preflight`, `record-result`, `approve`; không command nào có `--force`.
- `freeze` chỉ chạy trên clean protected paths, ghi `release_source_commit=HEAD`; manifest-only freeze commit sau đó không tạo self-hash loop.
- `eval_policy_v2.py --preflight|--run --dataset {e1,gold} --manifest PATH --output PATH --assessment-as-of YYYY-MM-DD [--confirmation-token TOKEN]` dùng guard chung.
- Plan này chỉ test/preflight giả; không gọi `--run` với provider thật.

- [ ] **Step 1: Viết RED negative guard tests**

Negative matrix phải mutate đúng một dimension mỗi case:

| Case | Mutation | Expected |
|---|---|---|
| manifest incomplete | lần lượt bỏ data HEAD, policy hash, protocol hash | `ReleaseContractError` nêu đúng field |
| artifact drift | đổi một byte ở prompt, safety, scoring hoặc dataset content | verify fail trước runner |
| dirty protected path | sửa một file policy/prompt/safety/scoring/dataset chưa commit | freeze fail và manifest giữ nguyên byte |
| protocol late | `protocol_commit` không là ancestor của `release_source_commit` | verify fail |
| token replay | dùng token E1 cho gold | token mismatch |
| unknown policy | `cam-nang-vn-v2-beta` | fail trước provider import |
| paid env off | token hoàn toàn đúng nhưng `VF_ALLOW_PAID_EVAL=0` | run bị chặn |
| bound-field drift | đổi lần lượt dataset, output, date hoặc release tuple | token mismatch |
| unsafe resume | output có release tuple khác | fatal, file giữ nguyên byte |
| fixture marker | fake runner và real-run builder | fake raw phải `is_fixture=true`; chỉ authorized provider path mới được ghi `false` |
| CLI force | parser nhận `--force` | parse error |
| approval wording | mọi metric kỹ thuật pass | `independent_label_reliability` vẫn `not_demonstrated` |

Test môi trường và tính bất biến của output phải có assertion trực tiếp:

```python
def test_paid_env_0_chan_run_du_token_dung(monkeypatch, tmp_path):
    manifest = frozen_manifest(tmp_path)
    token = confirmation_token(
        manifest=manifest,
        dataset_kind="e1",
        ordered_ids=[f"G-{index:03d}" for index in range(1, 11)],
        assessment_as_of="2026-08-17",
        output_path=tmp_path / "e1-raw.json",
    )
    monkeypatch.setenv("VF_ALLOW_PAID_EVAL", "0")
    with pytest.raises(ReleaseContractError, match="VF_ALLOW_PAID_EVAL"):
        authorize_paid_run(manifest, "e1", tmp_path / "e1-raw.json", "2026-08-17", token)
    assert not (tmp_path / "e1-raw.json").exists()


def test_cli_khong_co_force():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["freeze", "--manifest", "manifest.json", "--force"])
```

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_policy_release.py
```

Expected: exit 1 do `policy_release` chưa tồn tại.

- [ ] **Step 3: Viết protocol đầy đủ trước output**

Protocol khóa exact gates:

```text
E1 decision consistency >= 0.90
gold Kappa >= 0.60
gold rejected recall >= 0.80
gold needs_revision recall >= 0.80
gold false publish = 0/33
corrected publish = 30/30
paired recovery = 20/20
coverage target+decision+parent = 11/11
coverage failure = 0
drift = 0
independent_label_reliability = not_demonstrated
```

Ghi Mức A/B/C, synthetic limitation, no optional stopping và năm paid gates
riêng. Đây là protocol planned, chưa được gọi là evidence kết quả.

- [ ] **Step 4: Tạo manifest schema ban đầu**

Manifest có:

```json
{
  "schema_version": 1,
  "policy_version": "cam-nang-vn-v2",
  "data_head": "8635a45c9aee1369f6f7b17b0918a580db7390da",
  "release_source_commit": null,
  "independent_label_reliability": "not_demonstrated",
  "artifacts": {},
  "paid_runs": {
    "e1": {"status": "pending"},
    "gold": {"status": "pending"},
    "corrected": {"status": "pending"},
    "coverage": {"status": "pending"},
    "smoke": {"status": "pending"}
  },
  "approval": {"measured_complete": false, "level_b": "pending",
               "approved_for_limited_pilot": false}
}
```

Artifact hashes được tool tính, không chép tay.

- [ ] **Step 5: Implement guard/token/preflight $0**

Confirmation token SHA-256 của canonical JSON chứa exact dataset, ordered
IDs, manifest/content hashes, release tuple, assessment date và output path.
Preflight trả `usage_events=0`, `estimated_max_calls`, conservative token/cost
estimate, pricing version/source và token; không import provider client.

`record-*` xác minh hash trước khi mutate manifest. `approve` recompute gates
từ raw/report, không tin status do người sửa tay.

- [ ] **Step 6: Chạy GREEN và fake CLI preflights**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\test_policy_release.py
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2.py
```

Expected: pass, usage/provider calls 0. Chưa tạo preflight evidence thật vì
runner corrected/coverage và release freeze chưa hoàn tất.

- [ ] **Step 7: Commit**

```powershell
git add -- multiagent/scripts/policy_release.py multiagent/scripts/test_policy_release.py multiagent/scripts/eval_policy_v2.py multiagent/scripts/test_groups.json docs/evidence/corrected-publish-coverage-v1-protocol.md docs/evidence/publish-policy-v2-manifest.json
git commit -m "eval: preregister policy v2 release guard"
```

---

### Task 8: Reconcile Evaluation Plan để bỏ dependency vòng và chuẩn bị một release chung

**Files:**
- Modify: `docs/superpowers/plans/2026-08-17-corrected-publish-criterion-coverage-evaluation.md`
- Modify: `docs/superpowers/plans/2026-08-17-corrected-publish-criterion-coverage.md`
- Modify: `docs/evaluation-plan.md`
- Modify: `docs/technical-debt.md` mục 8

**Interfaces:**
- Consumes: policy core/evaluator/guard offline từ Tasks 1--7.
- Produces: thứ tự duy nhất: extend runner/metrics -> freeze release -> preflight bốn dataset -> USER GATE E1 -> gold -> corrected -> coverage -> aggregate -> conditional smoke.
- Không ghi metric/result chưa chạy; trạng thái vẫn `planned/offline-ready`.

- [ ] **Step 1: Viết checklist mâu thuẫn trước patch**

Ghi vào task report các dòng cũ cần sửa:

```text
- Evaluation plan giả định E1/gold raw đã có trước corrected extension.
- Raw meta yêu cầu exact release tuple nên không thể chạy paid trước khi extension/freeze xong.
- Task 4 hiện chỉ preflight corrected/coverage.
- Smoke gate có trong parent/spec nhưng chưa có task sau Mức B.
```

- [ ] **Step 2: Patch Evaluation Plan theo thứ tự mới**

Giữ Task metrics/runner/protocol hiện có nhưng:

1. coi policy core từ plan này là prerequisite offline đã tích hợp;
2. freeze manifest đúng một lần sau khi code corrected/coverage hoàn tất;
3. Task preflight tạo bốn token `e1|gold|corrected|coverage`;
4. thêm USER GATE E1 và gold trước corrected;
5. thêm USER GATE smoke sau khi `approve` chứng minh Mức B pass;
6. nếu upstream gate trượt, downstream chỉ chạy diagnostic sau protocol
   amendment commit và xác nhận riêng.

- [ ] **Step 3: Cập nhật parent/evaluation/handoff**

Parent trỏ đúng prerequisite plan này. `docs/evaluation-plan.md` ghi v2 là
planned, v1 vẫn historical truth. `technical-debt.md` chỉ ghi trạng thái
"focused tests pass; full offline pending" sau Tasks 1--7; chưa được dùng cụm
`offline-ready` trước checkpoint Task 9 và không thay các số v1.

- [ ] **Step 4: Verify docs consistency**

```powershell
rg -n "E1|gold|corrected|coverage|smoke|USER GATE|freeze" docs/superpowers/plans/2026-08-17-corrected-publish-criterion-coverage-evaluation.md
git diff --check
```

Đọc lại toàn bộ hai plan; không còn paid task nào trước freeze và mỗi token
chỉ thuộc một dataset.

- [ ] **Step 5: Commit**

```powershell
git add -- docs/superpowers/plans/2026-08-17-corrected-publish-criterion-coverage-evaluation.md docs/superpowers/plans/2026-08-17-corrected-publish-criterion-coverage.md docs/evaluation-plan.md docs/technical-debt.md
git commit -m "docs: sequence policy v2 release evaluation"
```

---

### Task 9: Offline verification checkpoint và bàn giao sang Evaluation Plan

**Files:**
- Create: `docs/evidence/publish-policy-v2-core-offline-verification.md`
- Modify: `docs/technical-debt.md` mục 8
- Read-only verify: toàn bộ protected data/score paths.

**Interfaces:**
- Produces: evidence $0 rằng core/runner/guard sẵn sàng để được mở rộng; không phải experiment result.
- Produces: exact Core HEAD; Evaluation Plan phải consume commit này.

- [ ] **Step 1: Chạy focused suite fresh**

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
$env:VF_ALLOW_PAID_EVAL = '0'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
.\.venv\Scripts\python.exe scripts\test_policy_routing.py
.\.venv\Scripts\python.exe scripts\test_cq_rubric.py
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2.py
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2_metrics.py
.\.venv\Scripts\python.exe scripts\test_policy_release.py
```

Expected: tất cả pass; không skip; provider calls/usage 0.

- [ ] **Step 2: Chạy full offline bằng lệnh canonical**

```powershell
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: summary 0 fail/0 skip; lấy tổng file từ output thật, không chép số
77 cũ.

- [ ] **Step 3: Verify immutable/protected paths**

```powershell
git diff --exit-code 8635a45 -- docs/goldset/raw docs/goldset/labels.csv docs/functional-tests/clean docs/functional-tests/gold-corrected docs/functional-tests/criterion-coverage multiagent/config/scoring.yaml
.\.venv\Scripts\python.exe scripts\functional_dataset_v2.py validate-inventory
git diff --check
git status --short
```

Expected: raw/labels/clean/GC/CV/scoring unchanged từ Data HEAD; inventory
20 corrected +11 coverage; worktree chỉ có verification evidence trước commit.

- [ ] **Step 4: Ghi evidence từ output, không từ memory**

File evidence ghi exact commands, exit codes, số test thực tế, Core HEAD parent,
policy/prompt/safety hashes, `VF_ALLOW_PAID_EVAL=0`, usage 0 và giới hạn:

```text
offline-ready != measured
preflight chưa phải result
policy v2 chưa active
independent label reliability = not_demonstrated
```

Chỉ sau khi evidence đã được dựng từ output fresh, cập nhật mục 8 từ
`full offline pending` sang `core offline-ready; chưa measured`, kèm exact
Core HEAD parent và link evidence.

- [ ] **Step 5: Commit verification evidence**

```powershell
git add -- docs/evidence/publish-policy-v2-core-offline-verification.md docs/technical-debt.md
git commit -m "test: verify policy v2 core offline"
```

- [ ] **Step 6: Final ancestry/status check**

```powershell
git log -1 --format=%H
git diff --check HEAD^ HEAD
git status --short
```

Expected: clean worktree. Ghi exact Core HEAD vào progress ledger; tiếp theo
thực thi Evaluation Plan đã reconcile, vẫn dừng tại từng USER GATE chi phí.

---

## Spec Traceability

| Spec | Nơi thực thi/kiểm chứng trong plan |
|---|---|
| §1 Vấn đề | Goal, Global Constraints; Task 1 thay quyền quyết định điểm bằng taxonomy |
| §2 Quyết định | Tasks 1, 5; exact A -> B -> incomplete -> publish và score diagnostic |
| §3 Phạm vi | Global Constraints; Tasks 8--9 không cutover và không chạy paid |
| §4 Ba lớp | Tasks 3--5 cho agent/engine/runtime; Task 6 cho evaluator |
| §5 Contract | Task 1 RED/GREEN contract tests |
| §6 Finding/coverage | Tasks 1 và 5, gồm unavailable/missing/drift/dedupe |
| §7 Registry | Task 1 literal A1--A7/B1--B11, gồm multi-source B5/B9/B10 |
| §8 A5/A6/A7/B11/B15 | Tasks 2--4 với test từng nhánh và call count |
| §9 Routing/tương thích | Task 5 exact v1/v2, worker date và characterization v1 |
| §10 Fail-safe/drift | Tasks 1, 5 và 7; sample incomplete khác release fatal |
| §11 Evaluator/raw | Task 6 shared runner, schema, resume và report-only |
| §12 Paid guard/manifest | Task 7 token-bound guard, clean freeze và năm gate tách biệt |
| §13 Gate/ý nghĩa | Task 7 protocol; Task 8 thứ tự gate; Task 9 chỉ offline evidence |
| §14 Test | RED/GREEN từng Task 1--7 và full offline Task 9 |
| §15 Trình tự/cutover | Tasks 1--9; Evaluation Plan tiếp quản paid runs sau prerequisite |
| §16 Tiêu chí hoàn tất | Task 9 xác minh protected paths, evidence, ancestry và trạng thái sạch |

---

## Plan Self-Review Checklist

- [x] Mọi yêu cầu spec §§1--16 có task tương ứng.
- [x] Không còn nhãn giữ chỗ hoặc bước mô tả mơ hồ.
- [x] Tên interface nhất quán: `policy_checks`, `unavailable_checks`,
  `assessment_as_of`, `effective_findings`, `decision_basis`, `coverage`.
- [x] V1 default và B15 legacy được test, không chỉ ghi trong prose.
- [x] A5/A6 không thêm call và không vào score được test trực tiếp.
- [x] Không paid command nào nằm trong prerequisite plan.
- [x] Evaluation Plan được reconcile trước freeze/paid run.
- [x] Mọi test file mới được đăng ký đúng một group.
- [x] Mỗi code task kết thúc bằng focused GREEN + commit có scope rõ.
