# Corrected Publish & Criterion Coverage Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mở rộng evaluator policy v2 để đo bộ chính 63 và coverage 11 bằng paid guard chung, preregister gate, lưu full decision basis và xuất kết luận Mức A/B/C trung thực.

**Architecture:** Metric/report là module thuần chạy $0 trên raw results. Paid run dùng duy nhất runtime/provenance/guard của `eval_policy_v2.py`, parameterized theo dataset `e1|gold|corrected|coverage`; corrected hợp nhất C+GC nhưng không sửa hai manifests, coverage join parent results từ corrected. Release manifest hash mọi dataset/protocol trước output.

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
- Modify: `multiagent/scripts/eval_policy_v2_metrics.py`
- Modify: `multiagent/scripts/test_eval_policy_v2_metrics.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- `confusion(expected: dict[str, str], predicted: dict[str, str]) -> dict`
- `class_metrics(expected, predicted, labels=LABELS) -> dict`
- `main_metrics(gold_rows, clean_rows, corrected_rows, gold_raw, corrected_raw) -> dict`
- `coverage_metrics(coverage_rows, coverage_raw, corrected_raw) -> dict`
- CLI `--report-corrected` và `--report-coverage` consume exact manifests/raw files và viết JSON/Markdown không import model.
- `eval_policy_v2_metrics.py --dataset {e1,gold} --raw PATH --output PATH`
  ghi report JSON atomic, vẫn là report-only và không import provider.
- `eval_corrected_coverage.py --summary --manifest PATH --output PATH` chỉ đọc
  evidence đã hash-match sau `approve`, tạo Markdown Mức A/B/C không gọi model.

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
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2_metrics.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: PASS, không usage/model call.

- [ ] **Step 5: Commit**

```powershell
git add -- multiagent/scripts/eval_corrected_coverage.py multiagent/scripts/test_eval_corrected_coverage.py multiagent/scripts/eval_policy_v2_metrics.py multiagent/scripts/test_eval_policy_v2_metrics.py multiagent/scripts/test_groups.json
git commit -m "eval: add corrected and criterion coverage metrics"
```

---

### Task 2: Hoàn tất shared evaluator cho bốn dataset đo

**Files:**
- Modify: `multiagent/scripts/eval_policy_v2.py`
- Modify: `multiagent/scripts/test_eval_policy_v2.py`
- Modify: `multiagent/scripts/eval_functional_clean.py`
- Modify: `multiagent/scripts/test_functional_clean.py`

**Interfaces:**
- `load_dataset(kind: str, repo_root: Path) -> list[EvaluationSample]`
- `run_samples(samples, output_path, runtime_contract) -> dict`
- CLI `--dataset e1|gold|corrected|coverage` cho `--preflight|--run`;
  không tạo runner trả phí thứ hai.
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

### Task 3: Hoàn tất guard rồi freeze một release chung trước output

**Files:**
- Modify: `docs/evidence/corrected-publish-coverage-v1-protocol.md`
- Modify: `docs/evidence/publish-policy-v2-manifest.json`
- Modify: `multiagent/scripts/policy_release.py`
- Modify: `multiagent/scripts/test_policy_release.py`
- Modify: `docs/evaluation-plan.md` mục v2

**Interfaces:** Task 1–2 phải commit xong trước task này. Release manifest hashes
Data HEAD, bốn dataset manifests/content sets, toàn bộ runner/metrics/policy,
protocol và gates. `freeze` chạy đúng một lần từ clean protected tree; commit
sau đó chỉ chứa manifest để không tạo self-hash loop. Không command nào có
`--force`.

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

Mức A = core offline-ready sau checkpoint `$0`, không suy chất lượng thật.
Mức B = bốn paid dataset measured và tất cả gate định lượng pass.
Mức C = conditional limited pilot sau smoke + authority riêng;
`independent_label_reliability` vẫn `not_demonstrated` trong cả ba mức.

- [ ] **Step 3: Update release guard**

Manifest lưu status riêng `e1`, `gold`, `corrected`, `coverage`, `smoke`; mỗi
entry có preflight/raw/report SHA, confirmation hash, calls/tokens/cost, gate
summary và `diagnostic_only`. Preflight release chính khóa
`diagnostic_only=false`; nếu upstream trượt, downstream token cũ không được
dùng. Diagnostic cần protocol amendment, release version và preflight/token
mới ghi `diagnostic_only=true`. `approve` không được biến Mức C thành pass và luôn giữ
`approved_for_limited_pilot=false` cho tới Task 10 có smoke + người có thẩm
quyền riêng. Trước freeze phải hoặc đăng ký exact non-empty smoke contract,
hoặc giữ registry smoke rỗng và ghi rõ Task 10 sẽ fail closed; không bổ sung
smoke target vào release này sau khi đã thấy bốn output.

- [ ] **Step 4: Commit toàn bộ protected extension trước freeze**

```powershell
git add -- docs/evidence/corrected-publish-coverage-v1-protocol.md docs/evidence/publish-policy-v2-manifest.json docs/evaluation-plan.md multiagent/scripts/policy_release.py multiagent/scripts/test_policy_release.py
git commit -m "eval: finalize policy v2 release inputs"
```

- [ ] **Step 5: Freeze, commit manifest-only, rồi verify**

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py freeze --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root ..
git -C .. add -- docs/evidence/publish-policy-v2-manifest.json
git -C .. commit -m "eval: freeze policy v2 release manifest"
.\.venv\Scripts\python.exe scripts\policy_release.py verify --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root ..
```

`release_source_commit` phải là parent protected-source commit của
manifest-only commit; `protocol_commit` là ancestor của nó. Bất kỳ dirty hoặc
drift nào ở score/data path đều dừng trước preflight. Không chạy paid trước
commit manifest-only này.

---

### Task 4: Full offline checkpoint và preflight $0 cho bốn dataset

**Files created:** Bốn preflight JSON dưới `docs/evidence/`. Chúng chỉ chứa
release/cost estimate/token, không chứa model result và không phải experiment
evidence.

**Interfaces:** Mỗi preflight khóa một exact tuple
`dataset + IDs/content hashes + release + date + raw output path`, trả
`usage_events=0`, max calls/tokens/cost và token riêng. Token không dùng chéo.

- [ ] **Step 1: Full offline suite và verify frozen release**

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
$env:VF_ALLOW_PAID_EVAL = '0'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
.\.venv\Scripts\python.exe scripts\policy_release.py verify --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root ..
```

Expected: summary 0 fail/0 skip và release verify pass. Không có summary thì
không được coi là checkpoint đạt.

- [ ] **Step 2: Tạo bốn preflight trên cùng assessment date**

Tạo raw target và preflight path timestamped riêng cho `e1`, `gold`,
`corrected`, `coverage`. Với từng dataset, chạy:

```powershell
$evaluationDate = [DateTime]::UtcNow.ToString('yyyy-MM-dd')
$rawPath = "..\docs\evidence\<dataset>-v2-<stamp>.json"
$preflightPath = "..\docs\evidence\<dataset>-v2-preflight-<stamp>.json"
$preflightLines = & .\.venv\Scripts\python.exe scripts\eval_policy_v2.py --preflight --dataset <dataset> --manifest ..\docs\evidence\publish-policy-v2-manifest.json --output $rawPath --assessment-as-of $evaluationDate
if ($LASTEXITCODE -ne 0) { throw "preflight failed: <dataset>" }
[IO.File]::WriteAllText(
  [IO.Path]::GetFullPath($preflightPath),
  (($preflightLines -join [Environment]::NewLine) + [Environment]::NewLine),
  [Text.UTF8Encoding]::new($false)
)
```

Expected counts: E1 10×5, gold 33×1, corrected 30×1, coverage 11×1;
mọi `usage_events=0`; bốn token khác nhau. Lưu raw target path từ chính
preflight, không tự đổi tên sau đó.

- [ ] **Step 3: Record và commit cả bốn preflight**

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py record-preflight --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root .. --dataset <dataset> --path $preflightPath
```

Lặp cho đúng bốn dataset rồi commit manifest + bốn JSON trong một commit.
Không preflight smoke ở đây. Bốn file vẫn là evidence `$0`, không được gọi là
kết quả đo và không tự cho phép paid run.

---

### Task 5: USER GATE — chạy E1 stability v2 trước

**Files created:** E1 raw 10×5, E1 metrics JSON và manifest update.

**Interfaces:** Consumes exact E1 preflight token. Không token nào khác mở
được run này.

- [ ] **Step 1: Trình đúng estimate và xin xác nhận chi phí riêng**

Đọc `paid_runs.e1.preflight.path`, hiển thị sample/repeat, max calls/tokens,
max cost, model, assessment date và raw target. Chỉ tiếp tục sau xác nhận rõ
cho đúng lượt E1; việc người dùng duyệt plan/preflight không phải duyệt chi phí.

- [ ] **Step 2: Run exact token, rồi tắt paid env ngay**

```powershell
$release = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$preflight = Get-Content -LiteralPath $release.paid_runs.e1.preflight.path -Raw | ConvertFrom-Json
try {
  $env:VF_ALLOW_PAID_EVAL = '1'
  .\.venv\Scripts\python.exe scripts\eval_policy_v2.py --run --dataset e1 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --output $preflight.output_path --assessment-as-of $preflight.assessment_as_of --confirmation-token $preflight.confirmation_token
  if ($LASTEXITCODE -ne 0) { throw "E1 paid run failed" }
} finally {
  $env:VF_ALLOW_PAID_EVAL = '0'
}
```

- [ ] **Step 3: Report-only, record và commit dù pass hay fail**

```powershell
$e1Report = $preflight.output_path -replace '\.json$', '-metrics.json'
.\.venv\Scripts\python.exe scripts\eval_policy_v2_metrics.py --dataset e1 --raw $preflight.output_path --output $e1Report
.\.venv\Scripts\python.exe scripts\policy_release.py record-result --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root .. --dataset e1 --raw $preflight.output_path --report $e1Report
```

Commit raw/report/manifest bất kể gate. Nếu decision consistency `<0.90`,
dừng: gold/corrected/coverage chỉ được dùng như diagnostic sau protocol
amendment commit và xác nhận mới; không optional stopping hoặc chạy lại để
tìm lượt đẹp.

---

### Task 6: USER GATE — chạy gold v2 sau khi E1 đạt

**Files created:** Gold raw 33×1, gold metrics JSON và manifest update.

**Interfaces:** Chỉ mở khi E1 evidence hash-match và gate pass; consumes exact
gold token, giữ provenance `AI-annotated-partially-exposed`.

- [ ] **Step 1: Verify E1 gate và xin xác nhận chi phí gold riêng**

Nếu E1 chưa measured/pass thì dừng. Đọc `paid_runs.gold.preflight.path`, trình
đúng max cost/calls/model/date/target và xin xác nhận riêng cho 33 mẫu.

- [ ] **Step 2: Run, report-only, record và commit**

```powershell
$release = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$preflight = Get-Content -LiteralPath $release.paid_runs.gold.preflight.path -Raw | ConvertFrom-Json
try {
  $env:VF_ALLOW_PAID_EVAL = '1'
  .\.venv\Scripts\python.exe scripts\eval_policy_v2.py --run --dataset gold --manifest ..\docs\evidence\publish-policy-v2-manifest.json --output $preflight.output_path --assessment-as-of $preflight.assessment_as_of --confirmation-token $preflight.confirmation_token
  if ($LASTEXITCODE -ne 0) { throw "gold paid run failed" }
} finally {
  $env:VF_ALLOW_PAID_EVAL = '0'
}
$goldReport = $preflight.output_path -replace '\.json$', '-metrics.json'
.\.venv\Scripts\python.exe scripts\eval_policy_v2_metrics.py --dataset gold --raw $preflight.output_path --output $goldReport
.\.venv\Scripts\python.exe scripts\policy_release.py record-result --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root .. --dataset gold --raw $preflight.output_path --report $goldReport
```

Commit evidence dù gate fail. Chỉ đi tiếp khi Kappa/recall/false-publish đều
đạt protocol; nếu không, downstream cần amendment trước và chỉ là diagnostic.
Không được đổi nhãn/sample/policy sau khi xem output trong cùng release.

---

### Task 7: USER GATE — chạy corrected-publish 30

**Files created:** Timestamped raw/report JSON and updated release manifest.

**Interfaces:** Consumes exact corrected preflight token; produces 30 immutable v2 results.

- [ ] **Step 1: Verify upstream gates**

E1 v2 và gold v2 phải có raw/report provenance hợp lệ. Nếu gold gate trượt, corrected run chỉ được chạy như diagnostic sau một protocol amendment commit; diagnostic không được dùng để approve cutover.

- [ ] **Step 2: USER GATE riêng**

Đọc `$cpPreflightPath` từ `paid_runs.corrected.preflight.path` trong release
manifest, trình người dùng đúng estimated max calls/cost; chỉ tiếp tục sau xác
nhận riêng cho corrected 30.

- [ ] **Step 3: Run exact token**

```powershell
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$cpPreflightPath = $releaseState.paid_runs.corrected.preflight.path
$cpPreflight = Get-Content -LiteralPath $cpPreflightPath -Raw | ConvertFrom-Json
$evaluationDate = $cpPreflight.assessment_as_of
$cpRawPath = $cpPreflight.output_path
try {
  $env:VF_ALLOW_PAID_EVAL = '1'
  .\.venv\Scripts\python.exe scripts\eval_policy_v2.py --run --dataset corrected --manifest ..\docs\evidence\publish-policy-v2-manifest.json --assessment-as-of $evaluationDate --output $cpRawPath --confirmation-token $cpPreflight.confirmation_token
  if ($LASTEXITCODE -ne 0) { throw "corrected paid run failed" }
} finally {
  $env:VF_ALLOW_PAID_EVAL = '0'
}
```

- [ ] **Step 4: Report with paid path disabled**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
$cpReportPath = $cpRawPath -replace '\.json$', '-metrics.json'
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$goldRawPath = $releaseState.paid_runs.gold.raw.path
.\.venv\Scripts\python.exe scripts\eval_corrected_coverage.py --report-corrected --gold-results $goldRawPath --corrected-results $cpRawPath --output $cpReportPath
```

Report must state `publish_count/30`, false block, pair recovery using exact gold raw, per-slice C/GC, usage/cost and limitations.

- [ ] **Step 5: Commit result even if failed**

Update và commit bằng guarded command; không sửa GC từ output này trong cùng version:

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py record-result --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root .. --dataset corrected --raw $cpRawPath --report $cpReportPath
git -C .. add -- docs/evidence/publish-policy-v2-manifest.json $cpRawPath $cpReportPath
git -C .. commit -m "eval: record corrected publish v2 result"
```

---

### Task 8: USER GATE — chạy criterion coverage 11

**Files created:** Timestamped coverage raw/report and updated manifest.

**Interfaces:** Consumes exact coverage token and corrected parent results; produces per-code pass/fail, never aggregate calibration.

- [ ] **Step 1: Verify upstream hoặc dừng release chính**

Nếu E1/gold/corrected upstream đã trượt, không dùng coverage token của release
chính. Muốn chạy diagnostic phải commit protocol amendment, freeze release
version mới và tạo token `diagnostic_only=true` trước khi xin user approval;
không đổi status sau khi xem output.

- [ ] **Step 2: USER GATE riêng**

Đọc `$cvPreflightPath` từ `paid_runs.coverage.preflight.path`, trình đúng
estimated calls/cost; confirmation corrected không đủ.

- [ ] **Step 3: Xác minh unknown-version guard bằng fake unit test**

`test_eval_policy_v2.py` phải chứng minh `cam-nang-v2` bị từ chối trước provider import; không thử chuỗi sai trong paid command thật và không chấp nhận prefix/fuzzy matching.

- [ ] **Step 4: Run exact command**

```powershell
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$cvPreflightPath = $releaseState.paid_runs.coverage.preflight.path
$cvPreflight = Get-Content -LiteralPath $cvPreflightPath -Raw | ConvertFrom-Json
$evaluationDate = $cvPreflight.assessment_as_of
$cvRawPath = $cvPreflight.output_path
try {
  $env:VF_ALLOW_PAID_EVAL = '1'
  .\.venv\Scripts\python.exe scripts\eval_policy_v2.py --run --dataset coverage --manifest ..\docs\evidence\publish-policy-v2-manifest.json --assessment-as-of $evaluationDate --output $cvRawPath --confirmation-token $cvPreflight.confirmation_token
  if ($LASTEXITCODE -ne 0) { throw "coverage paid run failed" }
} finally {
  $env:VF_ALLOW_PAID_EVAL = '0'
}
```

- [ ] **Step 5: Report $0**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
$cvReportPath = $cvRawPath -replace '\.json$', '-metrics.json'
$releaseState = Get-Content -LiteralPath '..\docs\evidence\publish-policy-v2-manifest.json' -Raw | ConvertFrom-Json
$cpRawPath = $releaseState.paid_runs.corrected.raw.path
.\.venv\Scripts\python.exe scripts\eval_corrected_coverage.py --report-coverage --corrected-results $cpRawPath --coverage-results $cvRawPath --output $cvReportPath
```

Expected report has 11 rows, target finding, decision, parent decision, non-target blockers, coverage/drift and evidence excerpt.

- [ ] **Step 6: Commit evidence**

Update guarded manifest and commit raw/report/manifest regardless 11/11 pass or fail:

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py record-result --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root .. --dataset coverage --raw $cvRawPath --report $cvReportPath
git -C .. add -- docs/evidence/publish-policy-v2-manifest.json $cvRawPath $cvReportPath
git -C .. commit -m "eval: record criterion coverage v2 result"
```

---

### Task 9: Tổng hợp Mức A/B/C trước mọi quyết định pilot

**Files:**
- Create: `docs/evidence/corrected-publish-coverage-v1-summary.md`
- Modify: `docs/evidence/publish-policy-v2-manifest.json`
- Modify: `docs/technical-debt.md` mục 8

**Interfaces:** Consumes exact E1/gold/corrected/coverage raw+reports; produces
Mức A/B technical status. Nó không phải smoke/cutover authority.

- [ ] **Step 1: Recompute approval từ evidence, không từ status chép tay**

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\policy_release.py approve --manifest ..\docs\evidence\publish-policy-v2-manifest.json --repo-root ..
```

`approve` phải hash-verify và recompute mọi gate. Nó chỉ ghi Mức B pass/fail;
không tự đặt `approved_for_limited_pilot=true` vì smoke/user authority là gate
riêng sau đó.

- [ ] **Step 2: Generate summary from files, not memory**

Summary includes confusion 63, Kappa gold 33, class metrics, corrected 30,
pairs 20, CV 11, cost per run, provenance tuple and known limitations:

```powershell
.\.venv\Scripts\python.exe scripts\eval_corrected_coverage.py --summary --manifest ..\docs\evidence\publish-policy-v2-manifest.json --output ..\docs\evidence\corrected-publish-coverage-v1-summary.md
```

- [ ] **Step 3: Kiểm ba mức kết luận**

```text
Mức A = core offline-ready iff checkpoint offline/provenance pass
Mức B = measured_complete + passed iff all four raw/report artifacts hash-match and every quantitative gate passes
Mức C = conditional limited pilot only after smoke + authority; independent_label_reliability remains not_demonstrated
```

Không cho người dùng flag `--force` để đổi Mức B/C.

- [ ] **Step 4: Update handoff carefully**

Read latest dirty/main `docs/technical-debt.md` section 8 before patch. Preserve v1 numbers and add versioned v2 section; do not overwrite current truth from another branch.

- [ ] **Step 5: Commit summary/handoff**

Stage only summary, manifest and reconciled handoff. Evidence âm vẫn commit.

---

### Task 10: CONDITIONAL USER GATE — smoke/limited pilot

**Files:** Smoke protocol/evidence chỉ được tạo nếu Mức B pass và đã có exact
smoke contract trong frozen release.

**Interfaces:** Đây là paid gate thứ năm, không phải một phần của `approve`.
Nó cần xác nhận chi phí/quyền cutover riêng và không dùng lại bốn token đo.

- [ ] **Step 1: Fail closed nếu chưa đủ điều kiện**

Nếu `approval.level_b != pass`, dừng và không smoke. Nếu
`datasets.smoke.ordered_ids` vẫn rỗng hoặc chưa có smoke runner/protocol đã
freeze, cũng dừng: tạo protocol amendment + release version mới trước, không
vá manifest hiện tại sau khi đã nhìn bốn output.

- [ ] **Step 2: USER GATE riêng cho smoke**

Chỉ khi smoke contract đã nằm trong cùng frozen release: tạo/record preflight
`smoke`, trình exact scope/cost/target/rollback và xin xác nhận riêng. Smoke
phải kiểm vận hành/CAS/revision trên target được phép; không được tự bật
production hay đổi `scoring.yaml.meta.calibrated`.

- [ ] **Step 3: Record kết quả trung thực**

Commit cả smoke pass lẫn fail. Chỉ người có thẩm quyền mới được đổi
`approved_for_limited_pilot`; kết quả kỹ thuật Mức B không thay thế quyền đó.
`independent_label_reliability` vẫn `not_demonstrated` trong cả hai trường hợp.

---

### Task 11: Final verification

**Files:** Read-only verification of all plan outputs.

**Interfaces:** Produces final evidence-backed handoff; no new behavior.

- [ ] **Step 1:** Set paid env off and run full offline suite; require 0 fail/0 skip summary.
- [ ] **Step 2:** Run dataset inventory/hash validator and `policy_release.py verify`.
- [ ] **Step 3:** `git diff --check`; inspect `git status --short`; ensure no output/preflight secret or API key is committed.
- [ ] **Step 4:** Confirm `scoring.yaml.meta.calibrated` remains false and no `publish_min` was fitted from C/GC/CV.
- [ ] **Step 5:** Confirm all raw results have `is_fixture=false`; platform P1–P5 fixture runs are not mixed in.
- [ ] **Step 6:** Confirm final wording distinguishes measured, passed, and independent evidence.
