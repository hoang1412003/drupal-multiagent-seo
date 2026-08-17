# Corrected Publish & Criterion Coverage Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mở rộng evaluator policy v2 để đo bộ chính 63 và coverage 11 bằng paid guard chung, preregister gate, lưu full decision basis và xuất kết luận Mức A/B/C trung thực.

**Architecture:** Metric/report là module thuần chạy $0 trên raw results. Paid run dùng duy nhất runtime/provenance/guard của `eval_policy_v2.py`, parameterized theo dataset `gold|corrected|coverage`; corrected hợp nhất C+GC nhưng không sửa hai manifests, coverage join parent results từ corrected. Release manifest hash mọi dataset/protocol trước output.

**Tech Stack:** Python 3.12, JSON/CSV, policy v2 evaluator, standard-library metrics, PowerShell, Git.

## Global Constraints

- Áp dụng toàn bộ Global Constraints của parent plan.
- Không bắt đầu plan này nếu Data integrity checkpoint chưa commit hoặc policy v2 core/evaluator chưa tồn tại.
- Nếu implementation plan policy v2 cũ chưa được integrate, integrate/reconcile nó trước; không tạo bản sao `eval_policy_v2.py` khác tên để né dependency.
- Report-only/preflight phải chạy với `VF_ALLOW_PAID_EVAL=0` và không có usage/model call.
- Raw result mỗi sample phải có decision, decision_basis/findings/coverage/drift, criteria cần audit, usage/cost/latency và exact release metadata.
- Corrected 30 và coverage 11 là hai paid runs riêng; token xác nhận không dùng chéo.
- Kappa chính chỉ trên 33 gold. Confusion/macro metrics 63 được phép báo nhưng phải ghi synthetic slices.

---

### Task 1: Xây pure metrics cho 63 + 11 bằng TDD

**Files:**
- Create: `multiagent/scripts/eval_corrected_coverage.py`
- Create: `multiagent/scripts/test_eval_corrected_coverage.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- `confusion(expected: dict[str, str], predicted: dict[str, str]) -> dict`
- `class_metrics(expected, predicted, labels=LABELS) -> dict`
- `main_metrics(gold_rows, clean_rows, corrected_rows, gold_raw, corrected_raw) -> dict`
- `coverage_metrics(coverage_rows, coverage_raw, corrected_raw) -> dict`
- CLI `--report-corrected` và `--report-coverage` consume exact manifests/raw files và viết JSON/Markdown không import model.

- [ ] **Step 1: Viết RED metric tests**

Fake vectors phải khóa mười một trường hợp độc lập:

- confusion luôn dùng thứ tự `publish,needs_revision,rejected`;
- macro-F1 tính đủ ba lớp trong bộ 63;
- denominator bằng 0 trả `NA/null`, không trả 1;
- false-publish chỉ có denominator 33 gold;
- corrected publish có denominator đúng 30;
- paired recovery yêu cầu G bị chặn **và** GC publish;
- CV chỉ pass khi có target finding và expected decision;
- parent của CV phải tiếp tục publish;
- blocking finding ngoài target làm isolation fail;
- thiếu/duplicate sample trong raw là fatal;
- release/meta mismatch giữa raw files là fatal.

Expected output keys:

```python
{
    "main_63": {"confusion": {}, "per_class": {}, "macro_f1": 0.0,
                "balanced_accuracy": 0.0},
    "gold_33": {"kappa": 0.0, "false_publish_count": 0,
                "false_publish_rate": 0.0},
    "corrected_30": {"publish_count": 0, "publish_rate": 0.0,
                     "false_block_count": 0},
    "paired_20": {"recovered_count": 0, "recovery_rate": 0.0},
    "coverage_11": {"passed": 0, "failed": 0, "by_code": {}},
}
```

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_corrected_coverage.py
```

Expected: FAIL vì module chưa tồn tại.

- [ ] **Step 3: Implement pure functions**

Không import `graph`, agents hoặc provider ở module scope. `balanced_accuracy` là trung bình recall của ba lớp có denominator >0 trong bộ 63; per-class denominator 0 lưu `null` + status `NA`, không ghi 1.0.

Paired formula literal:

```python
recovered = sum(
    gold_prediction[f"G-{i:03d}"] != "publish"
    and corrected_prediction[f"GC-{i:03d}"] == "publish"
    for i in range(1, 21)
)
```

Coverage pass cần đồng thời: target code trong effective findings, decision đúng expected, parent `publish`, không blocking code ngoài target và coverage/drift sạch.

- [ ] **Step 4: Chạy GREEN/meta-test**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_corrected_coverage.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: PASS, không usage/model call.

- [ ] **Step 5: Commit**

```powershell
git add -- multiagent/scripts/eval_corrected_coverage.py multiagent/scripts/test_eval_corrected_coverage.py multiagent/scripts/test_groups.json
git commit -m "eval: add corrected and criterion coverage metrics"
```

---

### Task 2: Parameterize paid evaluator cho ba dataset

**Files:**
- Modify: `multiagent/scripts/eval_policy_v2.py`
- Modify: `multiagent/scripts/test_eval_policy_v2.py`
- Modify: `multiagent/scripts/eval_functional_clean.py`
- Modify: `multiagent/scripts/test_functional_clean.py`

**Interfaces:**
- `load_dataset(kind: str, repo_root: Path) -> list[EvaluationSample]`
- `run_samples(samples, output_path, runtime_contract) -> dict`
- CLI `--dataset gold|corrected|coverage` cho `--preflight|--run`.
- `corrected` load 10 C + 20 GC; 10 C phải khớp cả `clean_labels.csv` lịch sử lẫn `functional-clean-ai-review-v1.4.csv`; `coverage` load 11 CV; `gold` dùng 33 dòng AI candidate v1.4 nhưng giữ provenance `partially exposed`.

- [ ] **Step 1: RED dataset routing tests**

Assert exact IDs/counts, physical dirs and no cross-contamination. `--dataset corrected` phải trả C-001..010 + GC-001..020; `coverage` exact 11 CV; `gold` exact G/P.

- [ ] **Step 2: RED paid guard tests**

Mỗi dataset preflight token phải hash ít nhất:

```text
dataset_kind + ordered sample IDs + manifests SHA + content SHA set
+ policy/prompt/rubric/guideline/model/scoring/KB/embedding/HEAD
+ assessment_as_of + output path
```

Token corrected không chạy coverage và ngược lại. Missing/mismatched content SHA phải fail trước import agent.

- [ ] **Step 3: Refactor một shared run path**

`eval_functional_clean.py` không tự import `cham_mot_bai` v1. Nó gọi `load_dataset("corrected")`/`run_samples()` của v2 runner hoặc trở thành compatibility wrapper CLI. Không copy vòng gọi bốn agent.

- [ ] **Step 4: Lock raw schema**

Mỗi file có `_meta.dataset_kind`, `dataset_manifest_hashes`, `content_hashes_sha256`, full release tuple và `is_fixture=false`. Mỗi sample có `decision`, `decision_basis`, `scores`, `final_score`, `criteria`, `usage`, `cost`, `latency`, `status`.

- [ ] **Step 5: GREEN**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2.py
.\.venv\Scripts\python.exe scripts\test_functional_clean.py
.\.venv\Scripts\python.exe scripts\test_eval_corrected_coverage.py
```

Expected: PASS; fake runner only, 0 provider calls.

- [ ] **Step 6: Commit runner extension**

```powershell
git add -- multiagent/scripts/eval_policy_v2.py multiagent/scripts/test_eval_policy_v2.py multiagent/scripts/eval_functional_clean.py multiagent/scripts/test_functional_clean.py
git commit -m "eval: route policy v2 corrected and coverage datasets"
```

---

### Task 3: Version release manifest và protocol trước output

**Files:**
- Create: `docs/evidence/corrected-publish-coverage-v1-protocol.md`
- Create/Modify: `docs/evidence/publish-policy-v2-manifest.json`
- Modify: `multiagent/scripts/policy_release.py`
- Modify: `multiagent/scripts/test_policy_release.py`
- Modify: `docs/evaluation-plan.md` mục v2

**Interfaces:** Release manifest hashes Data HEAD, four dataset manifests/content sets, protocol and gates. `policy_release.py record-preflight` khóa preflight path/hash/token hash; `record-result` khóa raw/report path/hash/metrics/cost; `approve` recompute mọi gate. Không command nào có `--force`.

- [ ] **Step 1: RED manifest tests**

Test phải từ chối missing/changed GC/CV manifest, content checksum drift, 29/30 corrected, 10/11 coverage, shared confirmation token, `independent_label_reliability=passed` khi không có evidence độc lập và protocol created after raw output.

- [ ] **Step 2: Write preregistered protocol**

Protocol khóa:

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
policy/prompt/content drift = 0
independent_label_reliability = not_demonstrated
```

Mức A = đủ evidence bất kể gate pass/fail. Mức B = tất cả gate định lượng pass. Mức C = `not_demonstrated` trong protocol này.

- [ ] **Step 3: Update release guard**

Manifest lưu status riêng `e1`, `gold`, `corrected`, `coverage`, `smoke`; mỗi entry có preflight/raw/report SHA, confirmation hash, calls/tokens/cost, gate summary và `diagnostic_only`. `record-preflight` suy `diagnostic_only=true` nếu upstream activation gate đã trượt; `approve` không được biến Mức C thành pass và chỉ set `approved_for_limited_pilot=true` khi Mức B pass.

- [ ] **Step 4: Commit protocol trước mọi paid output**

```powershell
git add -- docs/evidence/corrected-publish-coverage-v1-protocol.md docs/evidence/publish-policy-v2-manifest.json docs/evaluation-plan.md multiagent/scripts/policy_release.py multiagent/scripts/test_policy_release.py
git commit -m "eval: preregister corrected publish coverage protocol"
```

- [ ] **Step 5: Verify ancestry/clean score path**

Run `policy_release.py verify` and record exact full commit SHA; any dirty score/data path stops preflight.

---

### Task 4: Full offline checkpoint và preflight $0

**Files created:** Preflight JSON files under `docs/evidence/`; these contain no model result and are not reported as experiment evidence.

**Interfaces:** Each preflight outputs `confirmation_token`, `estimated_max_calls`, `estimated_cost_usd`, manifest/data/release hashes and `usage_events=0`.

- [ ] **Step 1: Full offline suite**

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
$env:VF_ALLOW_PAID_EVAL = '0'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: 0 fail/0 skip and summary printed. No summary means not verified.

- [ ] **Step 2: Corrected preflight**

```powershell
$cpStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$cpPreflightPath = "..\docs\evidence\corrected-publish-v2-preflight-$cpStamp.json"
$evaluationDate = [DateTime]::UtcNow.ToString('yyyy-MM-dd')
.\.venv\Scripts\python.exe scripts\eval_policy_v2.py --preflight --dataset corrected --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --assessment-as-of $evaluationDate --preflight-output $cpPreflightPath
```

Expected: 30 samples, usage 0, distinct confirmation token and explicit max cost.

- [ ] **Step 3: Coverage preflight**

```powershell
$cvStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$cvPreflightPath = "..\docs\evidence\criterion-coverage-v2-preflight-$cvStamp.json"
.\.venv\Scripts\python.exe scripts\eval_policy_v2.py --preflight --dataset coverage --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --assessment-as-of $evaluationDate --preflight-output $cvPreflightPath
```

Expected: 11 samples, usage 0, token khác corrected.

- [ ] **Step 4: Khóa và commit hai preflight**

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py record-preflight --manifest ..\docs\evidence\publish-policy-v2-manifest.json --dataset corrected --preflight $cpPreflightPath
.\.venv\Scripts\python.exe scripts\policy_release.py record-preflight --manifest ..\docs\evidence\publish-policy-v2-manifest.json --dataset coverage --preflight $cvPreflightPath
git -C .. add -- docs/evidence/publish-policy-v2-manifest.json "docs/evidence/corrected-publish-v2-preflight-$cpStamp.json" "docs/evidence/criterion-coverage-v2-preflight-$cvStamp.json"
git -C .. commit -m "eval: lock corrected and coverage preflights"
```

Hai file vẫn chỉ là preflight $0, không được gọi là kết quả thí nghiệm.

---

### Task 5: USER GATE — chạy corrected-publish 30

**Files created:** Timestamped raw/report JSON/Markdown and updated release manifest.

**Interfaces:** Consumes exact corrected preflight token; produces 30 immutable v2 results.

- [ ] **Step 1: Verify upstream gates**

E1 v2 và gold v2 phải có raw/report provenance hợp lệ. Nếu gold gate trượt, corrected run chỉ được chạy như diagnostic sau một protocol amendment commit; diagnostic không được dùng để approve cutover.

- [ ] **Step 2: USER GATE riêng**

Đọc `$cpPreflightPath` từ `paid_runs.corrected.preflight_path` trong release manifest, trình người dùng đúng estimated max calls/cost; chỉ tiếp tục sau xác nhận riêng cho corrected 30.

- [ ] **Step 3: Run exact token**

```powershell
$env:VF_ALLOW_PAID_EVAL = '1'
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$cpPreflightPath = $releaseState.paid_runs.corrected.preflight_path
$cpPreflight = Get-Content -LiteralPath $cpPreflightPath -Raw | ConvertFrom-Json
$evaluationDate = $cpPreflight.assessment_as_of
$cpRunStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$cpRawPath = "..\docs\evidence\corrected-publish-v2-$cpRunStamp.json"
.\.venv\Scripts\python.exe scripts\eval_policy_v2.py --run --dataset corrected --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --assessment-as-of $evaluationDate --output $cpRawPath --confirm-paid-run $cpPreflight.confirmation_token
```

- [ ] **Step 4: Report with paid path disabled**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
$cpReportPath = "..\docs\evidence\corrected-publish-v2-$cpRunStamp.md"
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$goldRawPath = $releaseState.paid_runs.gold.raw_path
.\.venv\Scripts\python.exe scripts\eval_corrected_coverage.py --report-corrected --gold-results $goldRawPath --corrected-results $cpRawPath --output $cpReportPath
```

Report must state `publish_count/30`, false block, pair recovery using exact gold raw, per-slice C/GC, usage/cost and limitations.

- [ ] **Step 5: Commit result even if failed**

Update và commit bằng guarded command; không sửa GC từ output này trong cùng version:

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py record-result --manifest ..\docs\evidence\publish-policy-v2-manifest.json --dataset corrected --raw $cpRawPath --report $cpReportPath
git -C .. add -- docs/evidence/publish-policy-v2-manifest.json "docs/evidence/corrected-publish-v2-$cpRunStamp.json" "docs/evidence/corrected-publish-v2-$cpRunStamp.md"
git -C .. commit -m "eval: record corrected publish v2 result"
```

---

### Task 6: USER GATE — chạy criterion coverage 11

**Files created:** Timestamped coverage raw/report and updated manifest.

**Interfaces:** Consumes exact coverage token and corrected parent results; produces per-code pass/fail, never aggregate calibration.

- [ ] **Step 1: Decide activation vs diagnostic status before run**

Nếu upstream Mức B gate đã trượt, protocol/manifest phải ghi coverage run là `diagnostic_only=true` trước khi user approves. Không đổi status sau khi xem output.

- [ ] **Step 2: USER GATE riêng**

Đọc `$cvPreflightPath` từ `paid_runs.coverage.preflight_path`, trình đúng estimated calls/cost; confirmation corrected không đủ.

- [ ] **Step 3: Xác minh unknown-version guard bằng fake unit test**

`test_eval_policy_v2.py` phải chứng minh `cam-nang-v2` bị từ chối trước provider import; không thử chuỗi sai trong paid command thật và không chấp nhận prefix/fuzzy matching.

- [ ] **Step 4: Run exact command**

```powershell
$env:VF_ALLOW_PAID_EVAL = '1'
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$cvPreflightPath = $releaseState.paid_runs.coverage.preflight_path
$cvPreflight = Get-Content -LiteralPath $cvPreflightPath -Raw | ConvertFrom-Json
$evaluationDate = $cvPreflight.assessment_as_of
$cvRunStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$cvRawPath = "..\docs\evidence\criterion-coverage-v2-$cvRunStamp.json"
.\.venv\Scripts\python.exe scripts\eval_policy_v2.py --run --dataset coverage --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --assessment-as-of $evaluationDate --output $cvRawPath --confirm-paid-run $cvPreflight.confirmation_token
```

- [ ] **Step 5: Report $0**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
$cvReportPath = "..\docs\evidence\criterion-coverage-v2-$cvRunStamp.md"
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$cpRawPath = $releaseState.paid_runs.corrected.raw_path
.\.venv\Scripts\python.exe scripts\eval_corrected_coverage.py --report-coverage --corrected-results $cpRawPath --coverage-results $cvRawPath --output $cvReportPath
```

Expected report has 11 rows, target finding, decision, parent decision, non-target blockers, coverage/drift and evidence excerpt.

- [ ] **Step 6: Commit evidence**

Update guarded manifest and commit raw/report/manifest regardless 11/11 pass or fail:

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py record-result --manifest ..\docs\evidence\publish-policy-v2-manifest.json --dataset coverage --raw $cvRawPath --report $cvReportPath
git -C .. add -- docs/evidence/publish-policy-v2-manifest.json "docs/evidence/criterion-coverage-v2-$cvRunStamp.json" "docs/evidence/criterion-coverage-v2-$cvRunStamp.md"
git -C .. commit -m "eval: record criterion coverage v2 result"
```

---

### Task 7: Tổng hợp Mức A/B/C và quyết định cutover

**Files:**
- Create: `docs/evidence/corrected-publish-coverage-v1-summary.md`
- Modify: `docs/evidence/publish-policy-v2-manifest.json`
- Modify: `docs/technical-debt.md` mục 8

**Interfaces:** Consumes exact E1/gold/corrected/coverage raw+reports; produces final status and activation gate.

- [ ] **Step 1: Generate summary from files, not memory**

Summary includes confusion 63, Kappa gold 33, class metrics, corrected 30, pairs 20, CV 11, cost per run, provenance tuple and known limitations.

- [ ] **Step 2: Compute status**

```text
Mức A = measured_complete iff all required raw/report/integrity artifacts exist and hash-match
Mức B = passed iff every preregistered quantitative gate passes
Mức C = not_demonstrated
```

Không cho người dùng flag `--force` để đổi Mức B/C.

- [ ] **Step 3: Run approval verifier**

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py approve --manifest ..\docs\evidence\publish-policy-v2-manifest.json --summary ..\docs\evidence\corrected-publish-coverage-v1-summary.md
```

Expected: approve limited pilot only if Mức B pass; otherwise non-zero exit with exact failed gates while keeping Mức A evidence.

- [ ] **Step 4: Update handoff carefully**

Read latest dirty/main `docs/technical-debt.md` section 8 before patch. Preserve v1 numbers and add versioned v2 section; do not overwrite current truth from another branch.

- [ ] **Step 5: Commit summary/handoff**

Stage only summary, manifest and reconciled handoff. Evidence âm vẫn commit.

---

### Task 8: Final verification

**Files:** Read-only verification of all plan outputs.

**Interfaces:** Produces final evidence-backed handoff; no new behavior.

- [ ] **Step 1:** Set paid env off and run full offline suite; require 0 fail/0 skip summary.
- [ ] **Step 2:** Run dataset inventory/hash validator and `policy_release.py verify`.
- [ ] **Step 3:** `git diff --check`; inspect `git status --short`; ensure no output/preflight secret or API key is committed.
- [ ] **Step 4:** Confirm `scoring.yaml.meta.calibrated` remains false and no `publish_min` was fitted from C/GC/CV.
- [ ] **Step 5:** Confirm all raw results have `is_fixture=false`; platform P1–P5 fixture runs are not mixed in.
- [ ] **Step 6:** Confirm final wording distinguishes measured, passed, and independent evidence.
