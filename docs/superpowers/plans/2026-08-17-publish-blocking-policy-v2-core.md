# Publish Blocking Policy v2 Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Trước mỗi bug/RED không như dự kiến, dùng `superpowers:systematic-debugging`; trước khi tuyên bố checkpoint xanh, dùng `superpowers:verification-before-completion`.

**Goal:** Xây đầy đủ runtime `cam-nang-vn-v2` và công cụ release bằng test offline, trong khi mọi job `cam-nang-vn-v1` tiếp tục dùng đúng prompt/hash/decision cũ.

**Architecture:** Một catalog version nhỏ cung cấp ID bất biến. `decision_policy.yaml` là artifact khai báo release; `decision_policy.py` load exact, validate và quyết định thuần. Agent chỉ branch ở prompt/semantics theo version, không nhân đôi graph. Coverage được chuẩn hóa bằng helper dùng danh sách check bắt buộc. Worker validate release trước fetch/LLM và graph xuất report version theo policy.

**Tech Stack:** Python 3.12, LangGraph, PyYAML, psycopg 3/PostgreSQL, test script assert thuần.

**Parent plan:** `docs/superpowers/plans/2026-08-17-publish-blocking-decision-policy.md`.

**Quy ước lệnh:** Mọi block PowerShell bắt đầu từ `D:\drupal-multiagent-seo\multiagent`, trừ khi block tự đổi thư mục.

## Global Constraints

- Plan này không chạy `eval_*` theo đường gọi model, không cần `ANTHROPIC_API_KEY`, không tạo evidence kết quả v2 trên gold/functional-clean.
- Mọi test agent dùng fake LLM/retriever. Runner phải xóa API key và đặt `VF_ALLOW_PAID_EVAL=0` như hiện tại.
- Không chỉnh `labels.csv`, không tạo nhãn v1.4 hộ người gán, không dùng output v1 để suy CP7 v2.
- Giữ `_LLM_PROMPT_V1` byte-for-byte bằng nội dung `_LLM_PROMPT` hiện hành. V2 dùng constant/schema mới; không sửa string v1 để “dọn code”.
- Agent `run()` có thể default v1 để giữ direct unit API, nhưng graph/worker/evaluation production luôn truyền exact version; graph thiếu version phải raise.
- V1 report JSON tiếp tục `version: 1`. Chỉ v2 report dùng `version: 2` và key mới.
- Không đổi công thức score hoặc trọng số. Decision-only checks nằm ở `decision_checks`, không ở `criteria`.
- Migration append-only là `0006`; không sửa 0001–0005.

## File responsibilities

| File | Trách nhiệm mới |
|---|---|
| `docs/goldset/annotation-guideline.md` | Normative guideline v1.4; A7/B11/B7/B9 |
| `docs/rubrics.md` | Rubric v2 + mapping đúng + decision-only contract |
| `docs/evidence/publish-policy-v2-protocol.md` | Protocol/gates đăng ký trước output |
| `multiagent/src/policy_versions.py` | Hai ID release, không side effect |
| `multiagent/config/decision_policy.yaml` | Mode, required checks, level mapping, assurance của v1/v2 |
| `multiagent/src/decision_policy.py` | Exact loader, per-policy hash, normalize/dedup/evaluate |
| `multiagent/src/assessment.py` | Hoàn thiện coverage result, phân biệt NA/unavailable |
| `multiagent/src/prompt_registry.py` | Hash prompt theo exact bundle; v1 hash bất biến |
| `multiagent/src/agents/*.py` | Chọn prompt/semantics theo version và trả decision checks/coverage v2 |
| `multiagent/src/graph.py` | Score như cũ; delegate decision; report v1/v2 |
| `multiagent/src/worker.py` | Validate policy sớm; truyền version/ngày; audit metadata |
| `multiagent/migrations/0006_review_profile_immutability.sql` | Chặn update identity/snapshot của release đã tạo |
| `multiagent/scripts/policy_release.py` | verify/stage/activate/rollback profile có audit |

---

### Task 1: Khóa guideline v1.4, rubric v2 và protocol trước code

**Files:**
- Modify: `docs/goldset/annotation-guideline.md`
- Modify: `docs/rubrics.md`
- Modify: `docs/evaluation-plan.md`
- Create: `docs/evidence/publish-policy-v2-protocol.md`
- Modify: `docs/technical-debt.md`
- Modify: `multiagent/scripts/test_evaluation_datasets.py`

**Interfaces:**
- Guideline v1.4 là nguồn nhãn mới; `docs/goldset/labels.csv` vẫn là manifest v1.3 lịch sử.
- Protocol đăng ký exact metrics/gates của parent plan Checkpoint D.

- [ ] **Step 1: Viết test RED cho contract v1.4 nhưng không giả nâng nhãn cũ**

Thêm test đọc guideline và `labels.csv`: guideline normative phải khai báo v1.4/A7/B11/B7/B9 mới, trong khi cả 33 dòng lịch sử vẫn v1.3. Trước khi sửa docs, test RED ở vế guideline; không sửa CSV để ép xanh:

```python
def test_labels_lich_su_khong_bi_bulk_upgrade_len_v14():
    guideline = GUIDELINE.read_text(encoding="utf-8")
    assert "v1.4" in guideline
    assert "A7" in guideline and "B11" in guideline
    assert ">75" in guideline and ">500" in guideline and "không có H2" in guideline
    rows = _read_csv(GOLD_LABELS)
    versions = {r["guideline_version"] for r in rows if r["sample_id"]}
    assert versions == {"v1.3"}, versions
```

Chạy test và xác nhận RED vì guideline hiện hành chưa có contract mới; không sửa CSV để ép xanh.

- [ ] **Step 2: Sửa guideline thành v1.4 normative**

Giữ changelog v1.3 và thêm changelog v1.4. Bảng mã phải thêm nguyên nghĩa:

```text
A7: body chứa đoạn văn xuôi bị ẩn khỏi người đọc nhưng còn trong input đánh
giá, sau khi loại CSS, mã tracking, URL và marker kỹ thuật theo CP9.

B11: bài đưa claim cụ thể về chính sách pin/bảo hành pin/thuê pin nhưng thiếu
ít nhất một yếu tố thiết yếu đang áp dụng: đối tượng/điều kiện, thời hạn, hoặc
phí nếu chính sách đó có phát sinh phí.
```

Sửa B7 thành URL trống/còn dấu/thiếu từ khóa/quá dài `>75` ký tự theo `scoring.yaml`. Sửa B9 thành bài `>500 tiếng` không có H2; bỏ chữ H2/H3 mơ hồ. Ghi rõ generic policy mention/link là không áp dụng B11.

Mục quy nhãn giữ short-circuit: bất kỳ A → `rejected`; không A nhưng bất kỳ B → `needs_revision`; không A/B → `publish`; C chỉ notes.

- [ ] **Step 3: Sửa rubric v2**

Thêm header release tuple và bảng action theo design spec mục 6. Xóa mapping mô tả sai SEO4→B3 và BV4→B5; BV3 không có quyền B5 khi nợ B13 còn mở. CP7 v2 dùng đúng 0/1/2/NA. Ghi `CQ9`, `SEO11`, `CP9`, `CP10` ở bảng decision-only và câu rõ: `score_from_criteria()` không nhận bốn check này.

- [ ] **Step 4: Đăng ký protocol v2**

`publish-policy-v2-protocol.md` phải ghi trước output:

```text
Primary safety metric: false-publish = 0/33.
Agreement gate: Cohen's Kappa >= 0.60.
Class recall gates: rejected >= 0.80; needs_revision >= 0.80.
Coverage gate: 0 unavailable checks và 0 policy drift trong valid paid run.
Functional-clean gate (separate): 10/10 publish.
Repeatability gate: >= 90% decisions trùng modal decision trên 10 x 5 lượt.
Annotation reliability: test-retest Kappa >= 0.80, cách lượt đầu >=72 giờ.
```

Nêu rõ đây là development/limited-pilot gate, không phải external validation; output functional-clean không nhập Kappa; result v1 không replay.

- [ ] **Step 5: Cập nhật evaluation/technical-debt theo trạng thái planned**

Không xóa kết quả v1. Thêm section E5 v2 là đánh giá policy, không threshold scan. Technical debt tiếp tục ghi “chưa triển khai/chưa đo” cho tới checkpoint tương ứng.

- [ ] **Step 6: GREEN và commit**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_evaluation_datasets.py
.\.venv\Scripts\python.exe scripts\test_eval_calibration_dataset.py
git -C .. diff --check
```

Expected: test lịch sử v1.3 xanh; không có file nhãn v1.4 mang kết quả giả.

```powershell
git -C .. add docs/goldset/annotation-guideline.md docs/rubrics.md docs/evaluation-plan.md docs/evidence/publish-policy-v2-protocol.md docs/technical-debt.md multiagent/scripts/test_evaluation_datasets.py
git commit -m "docs: freeze publish policy v2 evaluation contract"
```

---

### Task 2: Tạo catalog version, policy artifact và exact loader

**Files:**
- Create: `multiagent/src/policy_versions.py`
- Create: `multiagent/config/decision_policy.yaml`
- Create: `multiagent/src/decision_policy.py`
- Create: `multiagent/scripts/test_decision_policy.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- Produces: `V1 = "cam-nang-vn-v1"`, `V2 = "cam-nang-vn-v2"`.
- Produces: `load_exact(policy_version: str, path: Path | None = None) -> dict`.
- Produces: `policy_hash(release: dict) -> str` using canonical JSON of that release subtree.
- Raises: `UnsupportedPolicyVersion`, `PolicySchemaError`.

- [ ] **Step 1: RED cho exact match/no fallback/schema**

Test phải khóa:

```python
def test_loader_exact_khong_fallback():
    assert load_exact(V1)["decision_mode"] == "score_thresholds"
    assert load_exact(V2)["decision_mode"] == "blocking_policy"
    for value in ("", "cam-nang-vn", "cam-nang-vn-v3", "CAM-NANG-VN-V2"):
        with expect(UnsupportedPolicyVersion, value or "empty"):
            load_exact(value)

def test_hash_chi_bam_release_duoc_chon():
    v1_before = policy_hash(load_exact(V1))
    mutated = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    mutated["policies"][V2]["rubric_version"] = "changed-v2-only"
    with temporary_policy(mutated) as path:
        assert policy_hash(load_exact(V1, path)) == v1_before
```

Thêm test duplicate criterion ID, action lạ, assurance lạ, required check không có mapping và v2 `score_used_for_decision=true` đều bị từ chối.

- [ ] **Step 2: Viết catalog không side effect**

```python
V1 = "cam-nang-vn-v1"
V2 = "cam-nang-vn-v2"
SUPPORTED = frozenset({V1, V2})
```

Không có DEFAULT constant. Direct agent default sẽ import `V1` rõ ràng ở chính chữ ký, còn production state bắt buộc truyền.

- [ ] **Step 3: Viết policy artifact đầy đủ**

Root schema:

```yaml
schema_version: 1
policies:
  cam-nang-vn-v1:
    decision_mode: score_thresholds
    score_used_for_decision: true
    prompt_bundle: cam-nang-vn-v1
    rubric_version: v1
    guideline_version: v1.3
  cam-nang-vn-v2:
    decision_mode: blocking_policy
    score_used_for_decision: false
    prompt_bundle: cam-nang-vn-v2
    rubric_version: v2
    guideline_version: v1.4
    required_checks:
      content_quality: [CQ1, CQ2, CQ3, CQ4, CQ5, CQ6, CQ7, CQ8, CQ9]
      seo: [SEO1, SEO2, SEO3, SEO4, SEO5, SEO6, SEO7, SEO8, SEO9, SEO10, SEO11]
      brand: [BV1, BV2, BV3, BV4, BV5, BV6, BV7]
      compliance: [CP1, CP2, CP3, CP4, CP5, CP6, CP7, CP8, CP9, CP10]
```

Mỗi level entry tự chứa `action`, `defect_code`, `assurance`; level 2/NA không tạo finding. Mapping phải chép đủ bảng spec mục 6. Các case đặc biệt được biểu diễn chính xác:

```yaml
CP3:
  allowed_levels: ["0", "1", "2", "NA"]
  levels:
    "0":
      action: reject
      defect_code: A3
      assurance: verified_rag
      requires_verified: true
      fallback_action: manual_review
      fallback_assurance: llm_evidence
    "1": {action: advisory, defect_code: null, assurance: verified_rag}
CP9:
  allowed_levels: ["0", "2"]
  levels:
    "0": {action: reject, defect_code: A7, assurance: deterministic}
CP10:
  allowed_levels: ["1", "2", "NA"]
  levels:
    "1": {action: manual_review, defect_code: A6, assurance: llm_evidence}
CQ9:
  allowed_levels: ["0", "1", "2", "NA"]
  levels:
    "0": {action: manual_review, defect_code: A5, assurance: hybrid}
    "1": {action: advisory, defect_code: null, assurance: hybrid}
SEO11:
  allowed_levels: ["0", "2", "NA"]
  levels:
    "0": {action: revise, defect_code: B4, assurance: hybrid}
CP7:
  allowed_levels: ["0", "1", "2", "NA"]
  levels:
    "0": {action: revise, defect_code: B11, assurance: llm_evidence}
    "1": {action: revise, defect_code: B11, assurance: llm_evidence}
```

Loader phải xác minh chính xác 37 required IDs, không dùng wildcard/default action. Criterion advisory vẫn có entry cụ thể và `defect_code` C hoặc null, để audit giải thích vì sao không chặn.

- [ ] **Step 4: Loader + canonical hash**

Canonical form là `json.dumps(release, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`, SHA-256 hex đủ 64 ký tự. Không hash raw YAML/newline và không hash toàn bộ file.

Error message chỉ nêu policy/version/path/key, không dump artifact hay nội dung bài.

- [ ] **Step 5: GREEN, manifest test và commit**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: new test được runner discover đúng một lần; meta-test xanh.

```powershell
git -C .. add multiagent/src/policy_versions.py multiagent/config/decision_policy.yaml multiagent/src/decision_policy.py multiagent/scripts/test_decision_policy.py multiagent/scripts/test_groups.json
git commit -m "feat: add exact versioned decision policy loader"
```

---

### Task 3: Implement evaluator v1/v2 thuần và decision basis

**Files:**
- Modify: `multiagent/src/decision_policy.py`
- Modify: `multiagent/scripts/test_decision_policy.py`
- Modify: `multiagent/scripts/test_e5_khop_aggregator.py`

**Interfaces:**
- Produces: `decide(release, *, results, final_score, thresholds) -> dict`.
- Output: `decision`, `decision_basis`, optional legacy `veto_reason`, `note`.
- Produces: `normalize_findings(release, results) -> tuple[list[dict], list[dict]]` where second list is policy drift.

- [ ] **Step 1: Khóa v1 bằng acceptance vectors trước refactor**

Test ít nhất các vector:

```python
V1_CASES = (
    ({"cq": 90, "seo": 90, "brand": 90, "compliance": 90}, False, "publish"),
    ({"cq": 70, "seo": 70, "brand": 70, "compliance": 70}, False, "needs_revision"),
    ({"cq": 20, "seo": 20, "brand": 20, "compliance": 20}, False, "rejected"),
    ({"cq": 95, "seo": 95, "brand": 95, "compliance": 90}, True, "rejected"),
)
```

Thêm compliance None → `needs_revision`, `final_score=None`; missing non-compliance vẫn renormalize score và note đúng hành vi cũ. So `eval_calibration.quyet_dinh()` với evaluator v1 ở các ngưỡng hiện hành.

- [ ] **Step 2: RED cho thứ tự v2**

Test độc lập:

- CP1 mức 0 verified deterministic → rejected.
- CP2 mức 0 llm evidence → needs_revision/manual_review.
- CP5 mức 1 → needs_revision/revise.
- chỉ CQ3 mức 0 → publish/advisory.
- CP3 mức 0 verified false → manual_review; true → reject.
- CQ7+CP8 B10 → hai source findings nhưng một effective defect.
- missing check + no reject → needs_revision/incomplete.
- missing check + CP1 reject → rejected và vẫn report incomplete.
- criterion ID lạ/level lạ → manual_review + policy drift, không publish.
- final_score 100 với B11 vẫn needs_revision; final_score 10 nhưng không blocker vẫn publish.

- [ ] **Step 3: Normalizer không nhận diện bằng label tiếng Việt**

Đọc `criteria`, `decision_checks` theo `id`; đọc flag compatibility chỉ khi có `criterion_id`. CP9 flag không có ID ở v2 là policy drift, không được so `_CP9_RULE` string.

Finding shape:

```python
{
    "agent": "compliance",
    "criterion_id": "CP3",
    "level": 0,
    "action": "manual_review",
    "defect_code": "A3",
    "assurance": "llm_evidence",
    "field": "body",
    "excerpt": "VF 8 đi được 999 km sau một lần sạc",
    "reason": "Số liệu cần người kiểm chứng vì nguồn chưa đủ provenance",
    "provenance": {"verified": False, "source_url": "/vn_vi/thong-so-vf8"},
}
```

Sort ổn định theo priority `reject, revise, manual_review, advisory`, agent order, criterion ID, field, excerpt. Dedupe effective decision theo `(defect_code, action)` khi code không null; giữ `sources` của CQ7/CP8 trong audit.

- [ ] **Step 4: Coverage/fail-closed**

Required list từ release. Với result None, toàn bộ check của agent unavailable. Với result v2, evaluator đối chiếu `assessment.evaluated_ids` và `assessment.unavailable`; missing không được khai báo trở thành `policy_drift_missing_output`.

Decision basis chính xác:

```python
{
    "mode": "blocking_policy",
    "score_used_for_decision": False,
    "primary_reason": "reject",
    "coverage_complete": False,
    "unavailable_checks": [{"agent": "seo", "criterion_id": "SEO11", "reason_code": "llm_unavailable"}],
    "findings": [],
    "effective_findings": [],
    "policy_drift": [],
}
```

Nếu có reject, `primary_reason=reject`; nếu không reject và incomplete, `incomplete_assessment`; sau đó revise/manual_review; cuối cùng `no_blocker`.

- [ ] **Step 5: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
.\.venv\Scripts\python.exe scripts\test_e5_khop_aggregator.py
```

```powershell
git -C .. add multiagent/src/decision_policy.py multiagent/scripts/test_decision_policy.py multiagent/scripts/test_e5_khop_aggregator.py
git commit -m "feat: evaluate publish decisions from versioned blockers"
```

---

### Task 4: Sửa CP5/B15 và truyền provenance CP3

**Files:**
- Modify: `multiagent/src/compliance_analysis.py`
- Modify: `multiagent/src/retrieval.py`
- Modify: `multiagent/src/agents/fact_check.py`
- Modify: `multiagent/src/agents/compliance.py`
- Modify: `multiagent/scripts/test_compliance_rubric.py`
- Modify: `multiagent/scripts/test_retrieval.py`
- Modify: `multiagent/scripts/test_compliance_factcheck_merge.py`

**Interfaces:**
- `claim_tam_hoat_dong()` chỉ trả claim km có ngữ cảnh range, loại tỷ lệ/tốc độ.
- `retrieve()` bảo toàn `verified` từ meta.
- Fact-check v2 occurrence có provenance; v1 output shape giữ nguyên.

- [ ] **Step 1: RED literal B15**

Test một body chứa đồng thời:

```text
13,4 kWh/100km; 7,8 lít/100km; chi phí cho 1km; tốc độ 80km/h;
quãng đường di chuyển 80km; xe đi được 420 km sau một lần sạc đầy.
```

Expected `claim_tam_hoat_dong` chỉ trả `80km` ở cụm quãng đường và `420 km`; không trả `100km`, `1km`, `80km/h`.

- [ ] **Step 2: Implement context window**

Dùng match `_KM`, loại ngay nếu ký tự trước số là `/`, hậu tố là `/h`, hoặc cửa sổ khớp đơn vị tỷ lệ `kWh/100km|lít/100km|đồng/km|chi phí cho mỗi km`. Sau đó yêu cầu cửa sổ 120 ký tự có một trong:

```python
_NGU_CANH_TAM = re.compile(
    r"tầm hoạt động|quãng đường(?:\s+(?:di chuyển|đi được|tối đa))?|"
    r"đi được|sau (?:một|1) lần sạc(?: đầy)?",
    re.IGNORECASE,
)
```

Không dùng chỉ mỗi chữ “km” hoặc “quãng đường” ở field khác. Match output vẫn giữ `{field,text}` như cũ.

- [ ] **Step 3: RED/GREEN provenance**

Retrieval fake row meta `{"verified": True, "source_url": "/source"}` phải trả cả hai. Fact-check v2 mismatch trả occurrence:

```python
{"field": "body", "text": "999 km", "rule": _RULE,
 "provenance": {"verified": True, "source_url": "/source"}}
```

V1 gọi `danh_gia(fields, content_type=content_type, langcode=langcode, include_provenance=False)` và giữ exact occurrence cũ. V2 gọi cùng hàm với `include_provenance=True`. Khi fake/legacy retriever thiếu key, `verified=False`, tuyệt đối không default true.

- [ ] **Step 4: GREEN + regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_retrieval.py
.\.venv\Scripts\python.exe scripts\test_compliance_factcheck_merge.py
```

```powershell
git -C .. add multiagent/src/compliance_analysis.py multiagent/src/retrieval.py multiagent/src/agents/fact_check.py multiagent/src/agents/compliance.py multiagent/scripts/test_compliance_rubric.py multiagent/scripts/test_retrieval.py multiagent/scripts/test_compliance_factcheck_merge.py
git commit -m "fix: scope range claims and preserve fact provenance"
```

---

### Task 5: Thêm coverage helper và CQ9 decision-only

**Files:**
- Create: `multiagent/src/assessment.py`
- Modify: `multiagent/src/content_analysis.py`
- Modify: `multiagent/src/agents/content_quality.py`
- Modify: `multiagent/scripts/test_cq_rubric.py`
- Modify: `multiagent/scripts/test_decision_policy.py`

**Interfaces:**
- Produces: `finalize_assessment(result, *, required_ids, unavailable) -> dict`.
- Produces: `chia_section(body: str) -> list[{id,text,word_count}]` ổn định.
- Content Quality v2 trả CQ1–CQ8 trong `criteria`, CQ9 trong `decision_checks`.

- [ ] **Step 1: RED coverage semantics**

Test ba trường hợp:

- CQ8 level None do summary không áp dụng vẫn nằm `evaluated_ids`, coverage complete.
- LLM exception làm CQ1/CQ2/CQ6/CQ7/CQ8/CQ9 unavailable với reason code an toàn.
- LLM response thiếu CQ9 làm `missing_output`, không tự coi CQ9=NA.

Helper output:

```python
{
    "status": "partial",
    "evaluated_ids": ["CQ3", "CQ4", "CQ5"],
    "unavailable": [
        {"criterion_id": "CQ9", "reason_code": "llm_unavailable"}
    ],
}
```

Helper từ chối duplicate ID, unavailable ngoài required và cùng ID vừa evaluated vừa unavailable.

- [ ] **Step 2: Sectionizer tất định**

Mỗi H2 mở section mới; phần trước H2 là `S1`; nếu không có H2 thì mỗi paragraph có chữ là section. Bỏ script/style/markup, đếm bằng convention tiếng hiện có. ID theo thứ tự `S1..Sn`; không lưu toàn body vào assessment.

Test cùng HTML luôn sinh cùng ID/word_count, heading rỗng không tạo denominator, tổng word_count >0 cho body có chữ.

- [ ] **Step 3: Giữ prompt/schema v1 và thêm prompt/schema v2**

Đổi tên constant cũ thành `_LLM_PROMPT_V1` nhưng không đổi bytes. `_LLM_PROMPT_V2` giữ CQ1/2/6/7/8 và thêm object CQ9 yêu cầu:

- `promise`: lời hứa trung tâm của title;
- `rewrite_section_ids`: danh sách ID cần viết lại để đáp ứng promise;
- `evidence`: exact excerpt cho từng section ID;
- `reason`: giải thích ngắn.

Máy bỏ ID/evidence không hợp lệ. Tỷ lệ:

```python
rewrite_words = sum(s["word_count"] for s in valid_rewrite_sections)
ratio = rewrite_words / sum(s["word_count"] for s in sections)
level = 0 if ratio > 0.50 else (1 if ratio > 0 else 2)
```

Title/body rỗng hoặc không section → CQ9 unavailable `insufficient_input`; không trả clean.

- [ ] **Step 4: Không đổi score denominator**

Gọi `score_from_criteria(criteria)` trước/sau khi gắn `decision_checks`; test cùng CQ1–CQ8 levels cho score bằng nhau từng byte/float. CQ9 mức 0 chỉ xuất issue nếu UI compatibility cần, nhưng không được chèn vào `criteria`.

- [ ] **Step 5: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_cq_rubric.py
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
```

```powershell
git -C .. add multiagent/src/assessment.py multiagent/src/content_analysis.py multiagent/src/agents/content_quality.py multiagent/scripts/test_cq_rubric.py multiagent/scripts/test_decision_policy.py
git commit -m "feat: add coverage-aware title promise check"
```

---

### Task 6: Thêm SEO11 theo assessment date

**Files:**
- Modify: `multiagent/src/agents/seo.py`
- Modify: `multiagent/src/seo_analysis.py`
- Modify: `multiagent/scripts/test_seo_rubric.py`

**Interfaces:**
- SEO mở rộng chữ ký hiện hành bằng hai keyword-only argument: `policy_version: str = V1` và `assessment_as_of: str | None = None`.
- V2 trả SEO11 trong `decision_checks`, không trong `criteria`.

- [ ] **Step 1: RED cho ngày và ranh giới semantic**

Với `assessment_as_of="2026-08-17"`:

| Title | LLM class | Expected SEO11 |
|---|---|---|
| `Bảng giá VinFast 2024 mới nhất` | freshness_marker | 0/B4 |
| `Lịch sử ra mắt VinFast năm 2017` | historical | 2 |
| `Kinh nghiệm sạc xe điện` | không gọi SEO11 | NA/evaluated |
| `Bảng giá VinFast 2026` | freshness_marker | 2 |
| `VinFast 2024` | unclear | unavailable |

Thiếu/invalid `assessment_as_of` ở v2 phải raise contract error trước LLM, không dùng `datetime.now()` fallback.

- [ ] **Step 2: Candidate detector và prompt v2**

`seo_analysis.nam_trong_title()` trả unique year 4 chữ số trong dải 1900–assessment year + 1. Chỉ year `< assessment_year` cần LLM phân loại. Prompt v2 thêm exact enum `freshness_marker|historical|unclear` và evidence là title nguyên văn.

Không dùng regex “mọi năm cũ = B4”. `unclear` đi vào unavailable để policy fail-closed.

- [ ] **Step 3: Coverage + score invariant**

SEO1–SEO10 ở `criteria`; SEO11 ở `decision_checks`. LLM lỗi làm các SEO criteria LLM-owned và SEO11 candidate unavailable; deterministic criteria vẫn evaluated. Test score SEO1–SEO10 không đổi khi SEO11 thay level.

- [ ] **Step 4: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_seo_rubric.py
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
```

```powershell
git -C .. add multiagent/src/agents/seo.py multiagent/src/seo_analysis.py multiagent/scripts/test_seo_rubric.py multiagent/scripts/test_decision_policy.py
git commit -m "feat: detect stale freshness years without scoring them"
```

---

### Task 7: Version CP7, chính thức hóa CP9, thêm CP10 và Brand coverage

**Files:**
- Modify: `multiagent/src/agents/compliance.py`
- Modify: `multiagent/src/agents/brand_voice.py`
- Modify: `multiagent/scripts/test_compliance_rubric.py`
- Modify: `multiagent/scripts/test_brand_voice.py`
- Modify: `multiagent/scripts/test_functional_clean.py`

**Interfaces:**
- Compliance v2: CP1–CP8 scored criteria; CP9/CP10 decision checks.
- CP9 flag giữ UI shape và thêm `criterion_id="CP9"`.
- Brand v2 trả assessment BV1–BV7; v1 output giữ shape cũ.

- [ ] **Step 1: RED CP7 v2/C-006**

Fake LLM cases:

- chỉ câu “chính sách thay đổi theo sản phẩm/thời điểm, xem link hiện hành” → CP7 NA;
- claim cụ thể thiếu ≥2 yếu tố applicable → level 0;
- thiếu đúng 1 → level 1;
- đủ condition/duration/fee-if-applicable → level 2;
- bảo hành miễn phí đủ condition/duration không bị ép phải có fee.

Test v1 trên cùng generic mention vẫn giữ semantics/prompt cũ; không replay output v1 thành expected v2.

- [ ] **Step 2: CP10 candidate không tự reject**

Prompt/schema v2 thêm CP10 với allowed result `1|2|NA`, exact evidence và reason:

- NA: không có hướng dẫn thao tác kỹ thuật/an toàn;
- 1: có bước cụ thể có thể gây rủi ro điện, pin, cháy, xe hoặc bỏ cảnh báo thiết yếu;
- 2: có hướng dẫn nhưng không tìm thấy rủi ro cụ thể.

Mức 1 → decision check A6/manual_review. Nếu model trả ID/mức ngoài schema hoặc evidence không có thật → unavailable/policy drift, không chuyển thành level 2.

- [ ] **Step 3: CP9 luôn có check**

`_cp9_chi_dan_an()` trả cặp `(decision_check, flags)` hoặc hai helper rõ ràng. Clean → CP9 level 2, flags rỗng; suspicious → CP9 level 0 và flag critical có `criterion_id`. Không đưa CP9 vào score.

Test CSS/tracking/URL/marker bị loại như trước; văn xuôi ẩn tiếng Việt bị bắt; giới hạn English-no-punctuation vẫn được giữ trong docs/test, không tuyên bố detector hoàn hảo.

- [ ] **Step 4: Compliance coverage chi tiết**

Không còn nhánh “LLM hỏng và không hard violation → return None” ở v2 làm mất toàn bộ deterministic evidence. V2 trả result partial gồm CP1/CP5/CP6/CP9 evaluated và các LLM-owned unavailable; policy chặn publish. V1 giữ nhánh None hiện hành để bảo toàn behavior.

CP3 retrieval exception phải đánh unavailable; “không có claim” là evaluated NA; “có claim nhưng KB không có hit” là level 1 như v1, không phải infrastructure failure.

- [ ] **Step 5: Brand coverage**

BV1–BV5/BV7 deterministic luôn evaluated khi input có chữ. BV6:

- no applicable corpus hit → unavailable `retrieval_no_evidence`;
- LLM/retrieval exception → unavailable `llm_or_retrieval_unavailable`;
- valid level/NA → evaluated.

V1 không thêm assessment key. V2 thêm assessment nhưng score BV1–BV7 giữ nguyên.

- [ ] **Step 6: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_brand_voice.py
.\.venv\Scripts\python.exe scripts\test_functional_clean.py
```

`test_functional_clean.py` ở đây chỉ dùng fixture/fake, không chạy `eval_functional_clean.py` và không gọi model.

```powershell
git -C .. add multiagent/src/agents/compliance.py multiagent/src/agents/brand_voice.py multiagent/scripts/test_compliance_rubric.py multiagent/scripts/test_brand_voice.py multiagent/scripts/test_functional_clean.py
git commit -m "feat: version compliance checks and assessment coverage"
```

---

### Task 8: Hash exact prompt bundle và khóa v1

**Files:**
- Create: `multiagent/src/prompt_registry.py`
- Modify: `multiagent/src/agents/content_quality.py`
- Modify: `multiagent/src/agents/seo.py`
- Modify: `multiagent/src/agents/compliance.py`
- Modify: `multiagent/scripts/eval_calibration.py`
- Modify: `multiagent/scripts/eval_stability.py`
- Modify: `multiagent/scripts/eval_functional_clean.py`
- Modify: `multiagent/scripts/test_eval_calibration_dataset.py`
- Modify: `multiagent/scripts/test_decision_policy.py`

**Interfaces:**
- `prompt_bundle(policy_version) -> dict[str, str]` exact match.
- `prompt_version(policy_version) -> str` SHA-256 first 16 chars.
- `eval_calibration.prompt_version(policy_version=V1)` remains compatibility API.

- [ ] **Step 1: RED hash v1 và khác biệt v2**

```python
assert prompt_version(V1) == "020738e209017213"
assert len(prompt_version(V2)) == 16
assert prompt_version(V2) != prompt_version(V1)
with expect(UnsupportedPolicyVersion, "unknown"):
    prompt_version("unknown")
```

Bundle v1 dùng đúng sáu key lịch sử: `brand_voice_bv6`, `compliance`, `content_quality`, `seo`, `fact_check_compare`, `fact_check_extract`. Bundle v2 dùng cùng key names nhưng ba prompt agent v2; fact_check/BV6 có thể cùng string và vẫn được hash.

- [ ] **Step 2: Registry lazy import không circular**

`prompt_registry` import agent constants trong function, không ở module top nếu gây cycle. Agent chỉ import `policy_versions`, không import registry/decision evaluator.

- [ ] **Step 3: Evaluation scripts bắt explicit v2**

Giữ default v1 để đọc evidence lịch sử. Thêm `--policy-version` choices exact; v2 output path bắt buộc khác default v1. Resume metadata so cả `policy_version` và `prompt_version`; thiếu key từ file cũ chỉ được dùng khi requested V1 và đúng legacy hash.

Không chạy các script trong task này; chỉ unit test parser/hash/resume rejection bằng temp file.

- [ ] **Step 4: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'; print(e.prompt_version())"
.\.venv\Scripts\python.exe scripts\test_eval_calibration_dataset.py
.\.venv\Scripts\python.exe scripts\test_decision_policy.py
```

```powershell
git -C .. add multiagent/src/prompt_registry.py multiagent/src/agents/content_quality.py multiagent/src/agents/seo.py multiagent/src/agents/compliance.py multiagent/scripts/eval_calibration.py multiagent/scripts/eval_stability.py multiagent/scripts/eval_functional_clean.py multiagent/scripts/test_eval_calibration_dataset.py multiagent/scripts/test_decision_policy.py
git commit -m "feat: hash prompts by immutable policy bundle"
```

---

### Task 9: Tích hợp exact policy vào state/graph/report

**Files:**
- Modify: `multiagent/src/state.py`
- Modify: `multiagent/src/graph.py`
- Modify: `multiagent/scripts/test_graph_truyen_khoa.py`
- Modify: `multiagent/scripts/test_report_json.py`
- Modify: `multiagent/scripts/test_e5_khop_aggregator.py`
- Modify: `multiagent/scripts/smoke_test_graph.py`

**Interfaces:**
- State required: `policy_version`, `assessment_as_of`.
- Graph agents nhận exact version/date.
- Report v2 includes policy metadata/basis; v1 report contract remains.

- [ ] **Step 1: RED thiếu policy và propagation**

`aggregator_node` với state không có/blank policy phải raise `UnsupportedPolicyVersion`; không default V1. Spy bốn agent assert nhận V2; SEO nhận exact date. Direct smoke script phải thêm V1 rõ ràng.

- [ ] **Step 2: Tách score khỏi decision**

Graph dựng `results`, `missing`, tính `final_score` bằng đúng công thức v1 hiện hành. Sau đó:

```python
release = decision_policy.load_exact(state["policy_version"])
outcome = decision_policy.decide(
    release,
    results=results,
    final_score=final_score,
    thresholds=_config_cua(state)["decision"],
)
```

V1 compliance None vẫn làm final_score None. V2 có thể tính score từ agent còn lại nhưng basis ghi incomplete; score không đổi decision.

- [ ] **Step 3: Report versioning**

V1 `_build_report_json` output giữ `version:1` và không bắt client hiểu key mới. V2:

```python
{
    "version": 2,
    "policy_version": "cam-nang-vn-v2",
    "policy_hash": decision_policy.policy_hash(release),
    "decision_basis": outcome["decision_basis"],
    "decision": state["decision"],
    "final_score": state["final_score"],
}
```

Trong implementation, `policy_hash` lấy từ loader, không hard-code chuỗi minh họa. `scored_at`, content hash, fields/issues tiếp tục như cũ.

- [ ] **Step 4: Acceptance cases**

Fixture agent outputs khóa:

- high score + B11 → needs_revision;
- low score + chỉ advisory → publish;
- CP9 → rejected;
- SEO unavailable → needs_revision/incomplete;
- C-006 CP7 NA + tất cả check sạch → publish.

- [ ] **Step 5: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_graph_truyen_khoa.py
.\.venv\Scripts\python.exe scripts\test_report_json.py
.\.venv\Scripts\python.exe scripts\test_e5_khop_aggregator.py
```

```powershell
git -C .. add multiagent/src/state.py multiagent/src/graph.py multiagent/scripts/test_graph_truyen_khoa.py multiagent/scripts/test_report_json.py multiagent/scripts/test_e5_khop_aggregator.py multiagent/scripts/smoke_test_graph.py
git commit -m "feat: select graph decisions by exact policy version"
```

---

### Task 10: Worker validate trước LLM và audit đủ release tuple

**Files:**
- Modify: `multiagent/src/job_queue.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/audit.py`
- Modify: `multiagent/scripts/test_job_queue.py`
- Modify: `multiagent/scripts/test_worker.py`
- Modify: `multiagent/scripts/test_worker_graph_integration.py`
- Modify: `multiagent/scripts/test_audit.py`

**Interfaces:**
- `claim()` trả thêm `created_at`.
- New run validates policy/prompt before connector fetch/LLM.
- Reusable saved result vẫn write-back bằng payload/run ID cũ, không cần chạy engine mới.

- [ ] **Step 1: RED unsupported policy không gọi fetch/LLM**

Fake job `cam-nang-vn-unknown`, connector spy và invoke spy. Expected `q.fail_permanent(conn, job["id"], "unsupported_policy_version", safe_message)`; fetch/invoke/write đều 0. Error không retry ba lần.

Test riêng saved reusable result: dù worker hiện tại không còn artifact của policy cũ, nó vẫn được phép gửi lại exact saved payload/run ID vì không gọi LLM/quyết định lại.

- [ ] **Step 2: Claim created_at và assessment date**

Thêm `claimed.created_at` cuối RETURNING để không đổi index cũ giữa chừng; dict có `created_at`. Worker yêu cầu timezone-aware value và truyền `created_at.astimezone(timezone.utc).date().isoformat()`.

Fake/manual job thiếu created_at phải fail contract trong new-run path; không dùng clock hiện tại. Update tất cả fixture jobs.

- [ ] **Step 3: Placement của validation**

Thứ tự bắt buộc:

```text
find reusable result
construct connector if needed for reusable write-back
if reusable: resend and return
load exact policy + verify prompt bundle/hash
fetch exact revision
verify content hash
invoke graph with policy_version + assessment_as_of
audit
callback CAS
```

Như vậy version lạ dừng trước fetch/model, còn retry callback không bị chặn bởi artifact runtime mới.

- [ ] **Step 4: Audit/config metadata**

`config_meta`/payload v2 thêm scalar/hash, không toàn văn:

```python
{
    "policy_version": V2,
    "policy_hash": decision_policy.policy_hash(release),
    "prompt_version": prompt_registry.prompt_version(V2),
    "rubric_version": release["rubric_version"],
    "guideline_version": release["guideline_version"],
    "assessment_as_of": assessment_as_of,
}
```

Job/run columns đã có policy version; không tạo cột duplicate. Report basis nằm trong payload/agent results JSON hiện có.

- [ ] **Step 5: Regression connector invariant**

`test_worker_graph_integration.py` tiếp tục chứng minh 1 fetch, 0 graph PATCH, 1 callback; job V1 thêm created_at và output v1 không đổi ngoài timestamps/run ID được loại khi compare.

- [ ] **Step 6: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_job_queue.py
.\.venv\Scripts\python.exe scripts\test_worker.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
.\.venv\Scripts\python.exe scripts\test_audit.py
```

```powershell
git -C .. add multiagent/src/job_queue.py multiagent/src/worker.py multiagent/src/audit.py multiagent/scripts/test_job_queue.py multiagent/scripts/test_worker.py multiagent/scripts/test_worker_graph_integration.py multiagent/scripts/test_audit.py
git commit -m "feat: validate and audit policy releases before review"
```

---

### Task 11: Làm profile release bất biến và thêm CLI stage/cutover

**Files:**
- Create: `multiagent/migrations/0006_review_profile_immutability.sql`
- Create: `multiagent/scripts/policy_release.py`
- Create: `multiagent/scripts/test_policy_release.py`
- Modify: `multiagent/src/review_platform/auth/audit_log.py`
- Modify: `multiagent/scripts/test_migrations.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- CLI core: `verify`, `status`, `stage`, `activate`, `rollback`. Plan Evaluation bổ sung `manifest` và `approve` sau khi schema evidence đã có test.
- Audit actions: `policy_staged`, `policy_activated`, `policy_rolled_back`.
- Profile identity/snapshot immutable; `status` được phép đổi.

- [ ] **Step 1: RED migration immutability**

Sau apply 0006, UPDATE `policy_version`, `policy_snapshot`, `code`, `market_code`, `language_code` hoặc `content_type` của profile hiện có phải raise. UPDATE chỉ `status` active↔inactive phải được phép.

Migration tạo trigger function, không sửa table history và không đụng row v1.

- [ ] **Step 2: RED snapshot builder/verify**

Với `$manifestPath` là path exact do phase evaluation tạo, `policy_release.py verify --policy-version cam-nang-vn-v2 --manifest $manifestPath` phải:

- fail nếu worktree có diff trong score path;
- compute policy/prompt/scoring/rules/KB/guideline/rubric hashes;
- compare exact metadata trong evidence manifest;
- check model/embedding backend/model/dimension;
- không kết nối DB và không ghi file.

Test dùng temp git-independent hash inputs/injected functions, không shell ra secret/environment.

`status --site drupal-vn-primary` là read-only: in active profile/policy và count job theo policy/status; không in external content ID, URL hoặc payload.

- [ ] **Step 3: Stage inactive profile**

`stage` chỉ chạy trên committed clean tree và manifest `approved_for_activation=true`. Insert code `cam-nang-vn-v2`, status `inactive`, policy V2, full snapshot; assignment insert `active=false`. Nếu code/version đã tồn tại với exact snapshot thì idempotent; khác snapshot thì fail, không update.

Ghi `admin_audit_log` với system actor, target profile ID, metadata allowlist gồm `policy_version`, `policy_hash`, `manifest_hash`; mutation và audit cùng transaction.

- [ ] **Step 4: Activate/rollback transaction**

`activate` yêu cầu:

- site `intake_paused=true`;
- target profile inactive/staged, snapshot khớp manifest;
- zero old-policy jobs status `queued|running`;
- current assignment đúng một profile.

Trong một transaction lock site/profile/assignments, deactivate old assignment/profile, activate target profile/assignment, ghi audit. Không tự resume intake.

`rollback` đối xứng, cũng yêu cầu pause/drain; không xóa v2 profile/job/run và không sửa callback/API.

- [ ] **Step 5: Audit allowlist**

Mở rộng enum/allowlist chỉ với scalar không nhạy cảm:

```python
POLICY_STAGED = "policy_staged"
POLICY_ACTIVATED = "policy_activated"
POLICY_ROLLED_BACK = "policy_rolled_back"
```

Cho metadata `site_slug`, `old_policy_version`, `new_policy_version`, `policy_hash`, `manifest_hash`. Không cho path đầy đủ, token, URL, nested dict.

- [ ] **Step 6: GREEN và commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\test_policy_release.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Không chạy `stage/activate` trên database thật trong Plan Core.

```powershell
git -C .. add multiagent/migrations/0006_review_profile_immutability.sql multiagent/scripts/policy_release.py multiagent/scripts/test_policy_release.py multiagent/src/review_platform/auth/audit_log.py multiagent/scripts/test_migrations.py multiagent/scripts/test_groups.json
git commit -m "feat: stage and switch immutable review profiles"
```

---

### Task 12: Full regression, review độc lập và bàn giao sang đo lường

**Files:**
- Modify: `docs/technical-debt.md`
- Modify: `docs/evidence/publish-policy-v2-protocol.md` only if commands/file inventory need correction; không đổi metrics sau output
- Create: `docs/evidence/publish-policy-v2-core-verification.txt`

- [ ] **Step 1: Kiểm scope/secret/placeholder**

```powershell
Set-Location D:\drupal-multiagent-seo
git status --short
git diff --check
rg -n "TODO|FIXME|placeholder|cam-nang-vn-v2.*default|latest" multiagent/src multiagent/config/decision_policy.yaml docs/evidence/publish-policy-v2-protocol.md
```

Review từng hit theo ngữ cảnh; không chấp nhận fallback/placeholder thật. Kiểm `git diff -- multiagent/config/scoring.yaml` rỗng và migration 0001–0005 không đổi.

- [ ] **Step 2: V1 immutability gate**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'; print(e.prompt_version())"
.\.venv\Scripts\python.exe scripts\test_e5_khop_aggregator.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
```

- [ ] **Step 3: Full offline một lệnh**

```powershell
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: manifest count thực tế, `hong: 0`, `co [SKIP]: 0`. Lưu stdout đầy đủ vào evidence bằng cơ chế phù hợp của shell/CI khi thực thi; không tự viết “PASS” trước output.

- [ ] **Step 4: DDEV PHP regression**

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_result_callback.php
ddev exec php scripts/test_ai_roles.php
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev exec php scripts/test_ai_report_renderer.php
```

Nếu DDEV không chạy, đây là blocker checkpoint chứ không phải skip. Không cần visual browser vì không sửa UI; xác nhận diff UI rỗng.

- [ ] **Step 5: Review kỹ thuật**

Review bắt buộc tập trung:

- v1 byte/hash/output;
- unknown policy trước LLM;
- NA vs unavailable;
- CP3 provenance không default true;
- decision-only không lọt vào score;
- profile switch/audit atomic;
- paid scripts chưa chạy.

Sửa finding Critical/Important bằng TDD, chạy lại regression liên quan và full offline.

- [ ] **Step 6: Cập nhật trạng thái thật và commit evidence**

Technical debt ghi Core hoàn tất nhưng **v2 chưa được đo/chưa active**. Không ghi E1/E5/functional pass.

```powershell
git -C .. add docs/technical-debt.md docs/evidence/publish-policy-v2-core-verification.txt
git commit -m "docs: record publish policy v2 core verification"
```

Checkpoint cuối: chuyển sang plan evaluation/cutover; không tự chạy lượt trả phí kế tiếp.
