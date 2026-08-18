# Publish Blocking Policy v2 Evaluation and Cutover Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Mọi bước có chữ **USER GATE** phải dừng và chờ đúng xác nhận; không dùng một xác nhận chi phí cho nhiều lượt chạy.

**Goal:** Tạo ground truth v1.4 độc lập, đo đúng policy v2 đã khóa, và chỉ chuyển active profile từ v1 sang v2 khi toàn bộ gate đăng ký trước đạt.

**Architecture:** Công cụ session tạo bản gán nhãn mù không rò nhãn/codes cũ, khóa hash trước khi compare. Evaluation v2 tách phase gọi model khỏi phase báo cáo $0, lưu full decision basis và release provenance. Evidence manifest là cầu nối duy nhất sang CLI release: profile stage/activate bị từ chối nếu manifest/hash/gates không khớp.

**Tech Stack:** Python 3.12, CSV/JSON, Cohen's Kappa/confusion metrics thuần Python hiện hành, agent/graph v2 từ Core Plan, PostgreSQL/profile assignment, Drupal/DDEV callback CAS.

**Parent plan:** `docs/superpowers/plans/2026-08-17-publish-blocking-decision-policy.md`.

**Prerequisite:** Core Plan đã hoàn tất checkpoint, full offline 0 hỏng/0 skip, v1 prompt hash `020738e209017213`, v2 chưa active.

## Global Constraints

- Người gán nhãn là người quyết định nhãn. AI được chuẩn bị file/session/check định dạng nhưng không tự điền 33 nhãn rồi gọi đó là human gold.
- Người gán không mở nhãn/codes/notes v1.3 hoặc output AI v1/v2 trong lúc gán v1.4 và test–retest.
- `injected_codes` của perturbation bị ẩn khỏi session gán; chỉ merge lại sau khi file nhãn đã khóa hash.
- Không ghi đè `docs/goldset/labels.csv`; v1.4 ở file mới và evaluator bắt exact guideline version.
- Test–retest bắt đầu ít nhất 72 giờ sau timestamp khóa lượt đầu, chọn 4/33 bằng seed đã đăng ký, mù với nhãn lượt đầu.
- Preflight, report-only, Kappa và confusion matrix là $0. Chỉ phase thực sự gọi agent/model cần xác nhận chi phí.
- Có bốn **USER GATE chi phí riêng**: E1 v2, gold policy v2, functional-clean v2 và một smoke job v2 sau cutover. Không gộp.
- Nếu E1 không đạt repeatability gate thì không chạy gold v2. Nếu gold không đạt thì không chạy functional/cutover để “tìm con số đẹp”.
- Nếu code/prompt/policy/KB/embedding thay đổi sau một paid run, run đó không được resume cho release mới.
- Không xem output rồi sửa cùng `cam-nang-vn-v2`. Nếu phải sửa behavior, giữ v2 bất biến, tạo release kế tiếp và lặp protocol.
- Functional-clean được báo cáo riêng; không thêm 10 bài vào labels/Kappa 33.
- Activation là external state mutation: ngoài các gate tự động còn cần chủ dự án đồng ý rõ stage/cutover.

## Evidence names

Tên file thực tế dùng timestamp UTC dạng `YYYYMMDDTHHMMSSZ`, không dùng chữ `latest`:

```text
docs/evidence/label-v1.4-session-YYYYMMDDTHHMMSSZ.csv
docs/evidence/label-v1.4-session-YYYYMMDDTHHMMSSZ.lock.json
docs/evidence/test-retest-v1.4-YYYYMMDDTHHMMSSZ.csv
docs/evidence/test-retest-v1.4-YYYYMMDDTHHMMSSZ.lock.json
docs/evidence/test-retest-v1.4-YYYYMMDDTHHMMSSZ.md
docs/evidence/e1-policy-v2-YYYYMMDDTHHMMSSZ.json
docs/evidence/e1-policy-v2-YYYYMMDDTHHMMSSZ.md
docs/evidence/e5-policy-v2-YYYYMMDDTHHMMSSZ.json
docs/evidence/e5-policy-v2-YYYYMMDDTHHMMSSZ.md
docs/evidence/functional-clean-policy-v2-YYYYMMDDTHHMMSSZ.json
docs/evidence/functional-clean-policy-v2-YYYYMMDDTHHMMSSZ.md
docs/evidence/publish-policy-v2-manifest.json
```

---

### Task 1: Tạo công cụ session gán nhãn mù v1.4

**Files:**
- Create: `multiagent/scripts/label_session_v14.py`
- Create: `multiagent/scripts/test_label_session_v14.py`
- Modify: `multiagent/scripts/test_groups.json`
- Create during execution: `docs/evidence/label-v1.4-session-YYYYMMDDTHHMMSSZ.csv`, thay chuỗi thời gian bằng UTC thực do tool sinh.
- Create after human completion: matching `.lock.json`
- Create after lock: `docs/goldset/labels-v1.4.csv`

**Interfaces:**
- `prepare` nhận seed `20260817` và output path exact.
- `lock` nhận session path exact và annotator ID.
- `merge` nhận session/lock path exact và chỉ cho output `docs/goldset/labels-v1.4.csv` hoặc một temp path trong test.

- [ ] **Step 1: RED cho no-leak session**

Temp input có nhãn/codes/notes bí mật. Output prepare chỉ được có:

```text
order,sample_id,source_url,split,label,defect_codes,notes,annotator,date,guideline_version
```

Các cột judgment đều blank, riêng `guideline_version=v1.4`. Assert serialized output không chứa bất kỳ old label, old defect code, old note hay `injected_codes` nào. Seed giống nhau sinh cùng thứ tự; seed khác đổi thứ tự.

- [ ] **Step 2: Implement prepare với allowlist**

Đọc `labels.csv` chỉ để lấy allowlist `sample_id, source_url, split`; không copy row dict nguyên khối. Chỉ nhận 33 split `gold-real|gold-pert`, 20 G + 13 P, unique. Random dùng `random.Random(seed).shuffle()` trên list đã sort.

Metadata session nằm ở companion JSON hoặc comment-safe file riêng, gồm source SHA-256, guideline SHA-256, seed, generated_at UTC, code HEAD. Không chứa old label hash theo từng row.

- [ ] **Step 3: Lock validation**

`lock` từ chối nếu:

- thiếu/duplicate 33 sample;
- label ngoài `rejected|needs_revision|publish`;
- guideline khác v1.4;
- annotator/date trống;
- quy nhãn mâu thuẫn với defect codes: có A nhưng không rejected; không A/có B nhưng không needs_revision; không A/B nhưng không publish.

Defect code parser chấp nhận A1–A7, B1–B11, C1–C5; không bắt người gán liệt kê đủ mã do guideline short-circuit. Lock JSON gồm session SHA-256, source/guideline hash, locked_at UTC, row count, class distribution; không ghi đè CSV.

- [ ] **Step 4: Merge sau lock**

`merge` verify session hash trước. Sau đó mới đọc `labels.csv` để copy các cột không phải judgment cần cho evaluator, gồm `injected_codes`; giữ nhãn/codes/notes/annotator/date/guideline từ session v1.4. Output final sort theo sample_id và từ chối nếu path là `labels.csv`.

- [ ] **Step 5: GREEN/meta-test và commit công cụ trước khi dùng**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_label_session_v14.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
git -C .. diff --check
```

```powershell
git -C .. add multiagent/scripts/label_session_v14.py multiagent/scripts/test_label_session_v14.py multiagent/scripts/test_groups.json
git commit -m "test: prepare blind v1.4 annotation sessions"
```

- [ ] **Step 6: Generate session $0**

Chọn timestamp thực tế một lần và dùng nhất quán:

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\label_session_v14.py prepare --seed 20260817 --output ..\docs\evidence\label-v1.4-session-20260817T000000Z.csv
```

Tên `20260817T000000Z` trong block chỉ minh họa format; khi thực thi phải dùng timestamp UTC do lệnh prepare in ra, không bịa timestamp. Ghi command/seed vào evidence.

- [ ] **Step 7: USER GATE — người dùng gán đủ 33 bài**

Dừng automation. Chỉ hướng dẫn người dùng mở bài/session/guideline v1.4. Không mở hoặc tóm tắt labels v1.3/AI output trong cùng phiên. Sau khi người dùng báo xong, chạy `lock`, rồi `merge` với đúng path mà prepare đã tạo.

- [ ] **Step 8: Commit nhãn đã khóa**

Chạy test dataset mới assert 33 rows, exact v1.4, hash lock đúng; review distribution chỉ sau khi khóa.

```powershell
git -C .. add docs/evidence/label-v1.4-session-*.csv docs/evidence/label-v1.4-session-*.lock.json docs/goldset/labels-v1.4.csv
git commit -m "data: lock blind v1.4 gold labels"
```

Không dùng wildcard trong thao tác thực thi nếu nó khớp nhiều session; resolve và add exact three paths.

---

### Task 2: Test–retest v1.4 sau ít nhất 72 giờ

**Files:**
- Modify: `multiagent/scripts/label_session_v14.py`
- Modify: `multiagent/scripts/test_label_session_v14.py`
- Create during execution: test–retest CSV/lock/report.

**Interfaces:**
- `prepare-retest` nhận labels/lock exact, seed `20260820`, size `4` và output path.
- `lock-retest` nhận session path exact.
- `compare-retest` nhận exact labels/locks/retest/report paths.

- [ ] **Step 1: RED time gate/no-leak/selection**

Fake `locked_at` mới 71h59m phải bị từ chối; đúng 72h được phép. Output 4 rows chỉ có order/sample ID và blank judgment, không old label/code/note. Cùng seed chọn cùng four unique IDs.

Selection đăng ký dùng simple random sample trên 33 IDs đã sort, seed `20260820`, không reroll vì class distribution xấu. Evidence ghi giới hạn n=4.

- [ ] **Step 2: Lock retest trước compare**

`compare-retest` tuyệt đối từ chối mở/so labels nếu retest chưa có lock hash hợp lệ. Đây là chốt chống việc xem nhãn cũ rồi sửa lượt hai.

- [ ] **Step 3: Kappa/report $0**

Sau lock, compute confusion 3×3, observed agreement, expected agreement, Cohen's Kappa. Nếu mẫu chỉ có một lớp làm denominator 0, report `undefined` và fail gate; không ghi 1.0 giả.

Report bắt buộc nêu:

```text
Gold set do một người gán nhãn; không đo được inter-annotator agreement.
Kappa test–retest của cùng người là proxy lạc quan so với trần người–người.
```

- [ ] **Step 4: GREEN và commit tool change**

```powershell
.\.venv\Scripts\python.exe scripts\test_label_session_v14.py
git -C .. add multiagent/scripts/label_session_v14.py multiagent/scripts/test_label_session_v14.py
git commit -m "test: enforce blind delayed label retest"
```

- [ ] **Step 5: Chờ thật ≥72 giờ và USER GATE gán 4 bài**

Không dùng sleep/blocking process. Kết thúc turn/session và quay lại khi timestamp đủ. Người dùng gán 4 bài mù, sau đó lock rồi compare.

- [ ] **Step 6: Gate**

Nếu Kappa <0.80 hoặc undefined: dừng; guideline cần sửa/version mới và gán lại toàn bộ. Không chạy E1/gold AI.

Nếu đạt:

```powershell
git -C .. add docs/evidence/test-retest-v1.4-*.csv docs/evidence/test-retest-v1.4-*.lock.json docs/evidence/test-retest-v1.4-*.md
git commit -m "data: record v1.4 label test-retest"
```

Resolve exact paths thay wildcard khi thực thi.

---

### Task 3: Xây evaluator policy v2 và paid-run guard bằng test fake

**Files:**
- Create: `multiagent/scripts/eval_policy_v2.py`
- Create: `multiagent/scripts/test_eval_policy_v2.py`
- Modify: `multiagent/scripts/eval_stability.py`
- Modify: `multiagent/scripts/eval_functional_clean.py`
- Modify: `multiagent/scripts/test_eval_calibration_dataset.py`
- Modify: `multiagent/scripts/test_functional_clean.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- `eval_policy_v2.py --preflight` với manifest/labels exact là $0.
- `eval_policy_v2.py --run` chỉ gọi model khi có confirmation token exact từ preflight.
- `eval_policy_v2.py --report` với raw result exact là $0.
- All scripts require exact `--policy-version cam-nang-vn-v2`, `--assessment-as-of YYYY-MM-DD`, explicit output.

- [ ] **Step 1: RED paid guard**

Phase run phải từ chối trước import/call agent khi thiếu một trong:

- `VF_ALLOW_PAID_EVAL=1`;
- exact confirmation token generated by preflight from manifest hash;
- V2 policy/version;
- output path mới không tồn tại hoặc resumable file có exact metadata.

`--report` phải chạy với `VF_ALLOW_PAID_EVAL=0` và fake/no API key.

- [ ] **Step 2: Full provenance/resume contract**

Raw `_meta` bắt buộc:

```json
{
  "policy_version": "cam-nang-vn-v2",
  "policy_hash": "sha256-hex",
  "prompt_version": "16-char-hash",
  "rubric_version": "v2",
  "guideline_version": "v1.4",
  "model": "exact-model-id",
  "scoring_sha256": "sha256-hex",
  "kb_hashes": {},
  "embedding_backend": "BGEM3Embedder-local",
  "embedding_model": "BAAI/bge-m3",
  "embedding_dimension": 1024,
  "assessment_as_of": "YYYY-MM-DD",
  "git_head": "full-commit-sha",
  "score_path_snapshot": "full-commit-sha",
  "labels_sha256": "sha256-hex",
  "protocol_sha256": "sha256-hex",
  "is_fixture": false
}
```

Trong code, mọi hash/ID lấy từ runtime/manifest; các chuỗi kiểu `sha256-hex`/`YYYY-MM-DD` trên chỉ mô tả schema, không được ghi literal vào evidence. Resume compare toàn bộ tuple, không chỉ prompt hash.

- [ ] **Step 3: Per-sample output**

Mỗi sample lưu:

- scores bốn agent và final score;
- decision;
- full `decision_basis` gồm findings/effective findings/manual review/coverage/drift;
- criteria + decision checks tối thiểu cần audit;
- usage/cost/latency;
- error status nếu incomplete.

Không lưu lại full title/body trong result. `sample_id` nối về raw file đã version trong repo.

- [ ] **Step 4: Report metrics thuần $0**

Từ exact v1.4 labels:

- 3×3 confusion matrix;
- Kappa, accuracy;
- precision/recall/F1 từng lớp với denominator 0 ghi `NA`;
- false-publish count/rate: human != publish nhưng AI publish;
- manual_review finding count theo criterion;
- coverage failure và policy drift count;
- perturbation detection theo `injected_codes` sau lock.

Vì defect codes ở bài thật có thể short-circuit/không đầy đủ, không tính false-positive code trên absence của human code. Chỉ báo recall injected code và agreement trên code human đã ghi; nêu denominator từng code.

- [ ] **Step 5: E1 v2 metrics**

Mở rộng `eval_stability.py` để V2 lưu decision/basis/coverage mỗi lượt. `--report` compute:

```python
modal_count = max(Counter(decisions_for_sample).values())
decision_consistency = sum(modal_count_per_sample) / 50
```

Với tie 2–2–1, modal_count vẫn 2 và report tie; không chọn nhãn theo severity để làm đẹp. Báo σ final score cho so sánh nhưng gate là consistency ≥0.90 và coverage/drift 0.

- [ ] **Step 6: Functional-clean parameterized v2**

Không import `cham_mot_bai` v1 ngầm. Dùng cùng runner/provenance V2. Report `publish_rate`, `false_block_articles`, `false_positive_issues`, CP7 distribution; tách file/meta.

- [ ] **Step 7: GREEN/meta-test/full offline**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:VF_ALLOW_PAID_EVAL = '0'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\test_eval_policy_v2.py
.\.venv\Scripts\python.exe scripts\test_eval_calibration_dataset.py
.\.venv\Scripts\python.exe scripts\test_functional_clean.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: 0 fail/0 skip, không usage event/model call.

- [ ] **Step 8: Commit evaluator trước output**

```powershell
git -C .. add multiagent/scripts/eval_policy_v2.py multiagent/scripts/test_eval_policy_v2.py multiagent/scripts/eval_stability.py multiagent/scripts/eval_functional_clean.py multiagent/scripts/test_eval_calibration_dataset.py multiagent/scripts/test_functional_clean.py multiagent/scripts/test_groups.json
git commit -m "feat: evaluate blocking policy v2 without threshold fitting"
```

---

### Task 4: Khóa release manifest/preflight $0

**Files:**
- Create/Modify via reviewed command: `docs/evidence/publish-policy-v2-manifest.json`
- Modify: `multiagent/scripts/policy_release.py`
- Modify: `multiagent/scripts/test_policy_release.py`

**Interfaces:**
- `policy_release.py manifest` nhận exact policy version, labels/lock, retest report, protocol và output path qua các option có tên tương ứng.
- Manifest initial `approved_for_activation=false`.

- [ ] **Step 1: RED clean-tree/hash/backend guards**

Manifest command từ chối dirty score-path, labels lock mismatch, retest Kappa dưới gate, policy/prompt mismatch, remote embedder env không được khai báo.

- [ ] **Step 2: Chọn backend rõ ràng**

Cho phép evaluation v2 này dùng local BGE-M3 giống profile v1:

```powershell
Remove-Item Env:EMBEDDING_SPACE_URL -ErrorAction SilentlyContinue
Remove-Item Env:EMBEDDING_API_TOKEN -ErrorAction SilentlyContinue
$env:HF_HUB_OFFLINE = '1'
```

Preflight phải instantiate/check dimension 1024 và chạy retrieval fixture $0. Nếu model local chưa cache, dừng và xin quyết định riêng; không tự tải mạng. Manifest ghi backend `BGEM3Embedder-local`, model `BAAI/bge-m3`, dimension 1024.

- [ ] **Step 3: Tạo manifest từ committed tree**

Manifest chứa exact full Git SHA và score-path snapshot chính commit đó, hashes mọi artifact, label/retest/protocol, expected sample IDs/counts, gates và `paid_runs` ban đầu trống. Không dùng current date làm semantic input ngoài field `created_at`.

Trong cùng TDD task, thêm command `approve`: nó đọc lại raw evidence, recompute các gate protocol, từ chối khi thiếu/fail/hash mismatch và chỉ khi tất cả pass mới ghi `approved_for_activation=true`, actor, time và summary hash. Không có `--force`; unit test dùng evidence fake pass/fail, không cần model/DB.

- [ ] **Step 4: Preflight evaluation $0**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:VF_ALLOW_PAID_EVAL = '0'
$e1Preflight = Join-Path $env:TEMP 'vf-e1-policy-v2-preflight.json'
$goldPreflight = Join-Path $env:TEMP 'vf-gold-policy-v2-preflight.json'
$cleanPreflight = Join-Path $env:TEMP 'vf-clean-policy-v2-preflight.json'
.\.venv\Scripts\python.exe scripts\eval_stability.py --preflight --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --preflight-output $e1Preflight
.\.venv\Scripts\python.exe scripts\eval_policy_v2.py --preflight --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --labels ..\docs\goldset\labels-v1.4.csv --preflight-output $goldPreflight
.\.venv\Scripts\python.exe scripts\eval_functional_clean.py --preflight --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json --preflight-output $cleanPreflight
```

Preflight in estimated max calls/cost/token dựa trên protocol, confirmation token riêng cho từng run, và 0 usage events.

- [ ] **Step 5: Commit manifest trước paid output**

```powershell
git -C .. add docs/evidence/publish-policy-v2-manifest.json multiagent/scripts/policy_release.py multiagent/scripts/test_policy_release.py
git commit -m "eval: preregister publish policy v2 release manifest"
```

Commit này phải là ancestor của mọi raw result v2.

---

### Task 5: Chạy E1 v2 sau xác nhận chi phí riêng

**Files created:** E1 raw JSON và report Markdown với timestamp thật.

- [ ] **Step 1: USER GATE — xác nhận E1 v2**

Trình người dùng: 10 bài × 5 lượt, model exact, estimated max cost từ preflight, output path, confirmation token. Chỉ tiếp tục nếu người dùng đồng ý đúng E1 này.

- [ ] **Step 2: Run với token exact**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
$env:VF_ALLOW_PAID_EVAL = '1'
$manifestPath = '..\docs\evidence\publish-policy-v2-manifest.json'
$preflightPath = Join-Path $env:TEMP 'vf-e1-policy-v2-preflight.json'
$preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
$assessmentDate = $preflight.assessment_as_of
$outputPath = $preflight.output_path
$confirmationToken = $preflight.confirmation_token
.\.venv\Scripts\python.exe scripts\eval_stability.py --run --policy-version cam-nang-vn-v2 --manifest $manifestPath --assessment-as-of $assessmentDate --output $outputPath --confirm-paid-run $confirmationToken
```

Ba biến cuối được đọc nguyên từ artifact preflight $0; script vẫn validate format/token/manifest hash khi chạy. Không tự retry toàn bộ khi một call lỗi. Script lưu resumable exact metadata sau từng sample/lượt.

- [ ] **Step 3: Report $0 và gate**

Đặt lại `VF_ALLOW_PAID_EVAL=0`, chạy `--report`. Nếu consistency <0.90, coverage failure >0 hoặc drift >0: dừng trước gold run, chẩn đoán. Không thay prompt v2 rồi resume file.

- [ ] **Step 4: Commit evidence thật**

Update manifest append E1 result SHA/cost/calls/status, vẫn `approved_for_activation=false`; commit exact files.

---

### Task 6: Chạy gold policy v2 sau xác nhận chi phí riêng thứ hai

**Files created:** E5/policy raw JSON và report Markdown.

- [ ] **Step 1: USER GATE — xác nhận gold v2**

Nêu rõ đây là 33 bài × một lượt, không quét threshold; estimated cost/token, model, output, token. Xác nhận E1 không được tái sử dụng.

- [ ] **Step 2: Run exact**

Chạy `eval_policy_v2.py --run` với manifest/date/output/token exact. Script từ chối nếu E1 gate trong manifest chưa pass.

- [ ] **Step 3: Report $0**

Chạy `--report` với paid env tắt. Report đủ metrics protocol, class distribution, manual review, coverage, per-code denominators và giới hạn development corpus.

- [ ] **Step 4: Gate không post-hoc**

Pass chỉ khi đồng thời:

```text
Kappa >= 0.60
recall rejected >= 0.80
recall needs_revision >= 0.80
false_publish == 0/33
coverage_failure == 0
policy_drift == 0
```

Nếu fail, giữ/commit negative result trung thực, manifest status failed, không chạy cutover. Không hạ gate hoặc đổi labels sau khi xem output.

- [ ] **Step 5: Commit evidence**

Update manifest với raw/report SHA, cost/calls/metrics; commit exact files. Evidence âm cũng phải giữ.

---

### Task 7: Rà functional-clean theo v1.4 và chạy sau xác nhận riêng thứ ba

**Files:**
- Modify: `docs/functional-tests/clean_labels.csv` only for reviewed v1.4 provenance, không đổi expected theo AI.
- Create: functional-clean v2 raw/report.

- [ ] **Step 1: Human review $0 trước AI output**

Người gán rà 10 corrected articles theo guideline v1.4 và xác nhận không A/B; ghi annotator/date/guideline v1.4. Không mở v2 output trước khi khóa file. Nếu có A/B thật, sửa expected dựa trên bài/guideline và ghi reason trước run; không sửa bài chỉ để đạt.

- [ ] **Step 2: Commit clean manifest trước run**

Hash file cập nhật vào evidence manifest; commit. Preflight lại và nhận token/cost mới.

- [ ] **Step 3: USER GATE — xác nhận functional-clean v2**

Đây là 10 bài × một lượt riêng. Chỉ chạy sau xác nhận đúng token/lượt.

- [ ] **Step 4: Run/report $0/gate**

Run exact V2, rồi report với paid env tắt. Gate `publish=10/10`, coverage/drift 0. C-006 phải có CP7 NA; nếu không, report failure, không sửa output.

- [ ] **Step 5: Commit evidence**

Update manifest raw/report hash, metrics/cost. Không gộp với Kappa 33.

---

### Task 8: Finalize manifest và quyết định có đủ điều kiện limited pilot

**Files:**
- Modify: `docs/evidence/publish-policy-v2-manifest.json`
- Create: `docs/evidence/publish-policy-v2-evaluation-summary.md`
- Modify: `docs/technical-debt.md`
- Modify: `docs/evaluation-plan.md`

- [ ] **Step 1: Verify all hashes/gates $0**

`policy_release.py verify` đọc mọi evidence exact, recompute metrics từ raw thay vì tin report text, check commit ancestry và current artifact hashes. Nó không được tự set approval.

- [ ] **Step 2: Viết summary outcome-first**

Summary nêu pass/fail từng preregistered gate, cost thật, limitation một annotator, development-corpus, functional n=10, manual_review count, known A1/BV3/CP9 limits. Không gọi preflight là kết quả.

- [ ] **Step 3: USER GATE — chấp thuận limited pilot/cutover**

Nếu tất cả automatic gates pass, trình summary cho chủ dự án. Chỉ sau câu đồng ý rõ mới chạy:

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py approve --manifest ..\docs\evidence\publish-policy-v2-manifest.json --summary ..\docs\evidence\publish-policy-v2-evaluation-summary.md
```

`approve` verify lại, set `approved_for_activation=true`, `approved_at`, summary SHA và actor; không chấp nhận `--force`. Nếu gate fail, command phải từ chối dù user muốn ép; khi đó cần release/protocol mới, không sửa manifest.

- [ ] **Step 4: Commit final manifest/summary trước database mutation**

Commit exact files; clean tree là gate của stage.

---

### Task 9: Stage và activate profile v2 có audit

**External mutation:** PostgreSQL profile/assignment và Drupal intake; cần user approval ở Task 8.

- [ ] **Step 1: Verify/stage**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\policy_release.py verify --policy-version cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json
.\.venv\Scripts\python.exe scripts\policy_release.py stage --policy-version cam-nang-vn-v2 --profile-code cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json
```

Check DB: v1 active/assigned, v2 inactive/unassigned active=false; audit `policy_staged` success. Không đổi intake/job.

- [ ] **Step 2: Pause intake và capability test**

Dùng `/admin/connection` với operator/admin để pause (có audit), rồi chạy capability test đủ pending feed/result/exact-revision. Không dùng generic GET làm bằng chứng.

- [ ] **Step 3: Drain old jobs/status**

`policy_release.py status --site drupal-vn-primary` phải in counts theo policy/status, không nội dung. Chờ queued/running v1 về 0; failed/dead-letter phải được xử lý/ghi quyết định, không xóa.

- [ ] **Step 4: Transaction activate**

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py activate --site drupal-vn-primary --profile-code cam-nang-vn-v2 --manifest ..\docs\evidence\publish-policy-v2-manifest.json
```

Sau command, v2 là exact one active assignment; v1 inactive nhưng row/snapshot còn nguyên; site vẫn paused; audit success cùng transaction.

- [ ] **Step 5: Verify job snapshot $0 trước paid smoke**

Tạo một fixture/intake contract test không gọi model hoặc dùng test schema để xác nhận job mới snapshot V2/dedup scope. Fixture không phải kết quả chấm.

- [ ] **Step 6: USER GATE chi phí thứ tư — một smoke job thật v2**

Nêu rõ node/revision, 1 bài × một lượt, estimated cost, và rằng moderation state không đổi. Sau xác nhận, submit đúng một bài test/staging, worker chạy, callback CAS một lần.

- [ ] **Step 7: Smoke acceptance**

Xác nhận:

- job/run/report exact V2/policy hash;
- `decision_basis.score_used_for_decision=false`;
- expected revision/hash match;
- callback creates one AI revision, same `run_id` idempotent;
- moderation state không đổi;
- không có full draft trong queue/audit;
- usage/cost event có provenance.

Nếu fail, giữ intake paused và rollback Task 10; không resume site.

- [ ] **Step 8: Resume intake**

Chỉ sau smoke pass, resume qua admin audited action. Ghi timestamp/profile/job/run IDs an toàn vào cutover evidence.

---

### Task 10: Rehearse rollback profile v1

**Files created:** `docs/evidence/publish-policy-v2-cutover.md`.

- [ ] **Step 1: Pause/drain v2**

Pause intake, zero queued/running V2. Không rollback application code trước khi drain vì code cũ không hiểu job V2.

- [ ] **Step 2: Rollback assignment transaction**

```powershell
.\.venv\Scripts\python.exe scripts\policy_release.py rollback --site drupal-vn-primary --profile-code cam-nang-vn --manifest ..\docs\evidence\publish-policy-v2-manifest.json
```

Verify v1 active exact one, v2 inactive, audit `policy_rolled_back`, all v2 job/run rows preserved.

- [ ] **Step 3: Legacy compatibility regression**

Run one fixture/previous rehearsal path proving hash version 1 still goes through worker and callback CAS. Không cần paid model nếu dùng saved/fake result; không tuyên bố fixture là scoring result.

- [ ] **Step 4: Chọn trạng thái cuối có chủ đích**

Nếu limited pilot tiếp tục V2, activate lại theo exact audited procedure (không cần paid smoke thứ hai nếu artifacts/code/site unchanged và first smoke evidence valid). Nếu kết thúc rehearsal ở V1, ghi rõ V2 staged/inactive. Không để assignment ở trạng thái tình cờ.

- [ ] **Step 5: Commit evidence/docs**

Update technical debt §8 với trạng thái cuối thật, metrics/cost/limits và links. Commit cutover evidence; không commit secrets/full content.

---

### Task 11: Final verification and handoff

- [ ] **Step 1: Full offline**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: 0 fail, 0 skip.

- [ ] **Step 2: Five DDEV tests**

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_result_callback.php
ddev exec php scripts/test_ai_roles.php
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev exec php scripts/test_ai_report_renderer.php
```

- [ ] **Step 3: Evidence integrity**

Recompute hashes; ensure manifest refers exact existing files/commits, no `is_fixture=true` in paid result, no old prompt hash mislabeled V2, no V1/V1.4 labels mixed. `git diff --check` clean.

- [ ] **Step 4: Handoff summary**

Nêu outcome trước: profile active cuối là gì; gates pass/fail; metrics/cost; known limitations; rollback command/status. Không phát biểu “AI đồng thuận với người” nếu chỉ có same-person test–retest; dùng đúng “AI–gold agreement” và nêu gold một annotator.

## Stop conditions

Dừng ngay và không tự đi tiếp khi:

- guideline/retest Kappa <0.80 hoặc undefined;
- v1 prompt hash đổi;
- score path dirty sau manifest commit;
- embedding backend khác manifest;
- bất kỳ paid gate chưa được user duyệt đúng lượt;
- E1/gold/functional automatic gate fail;
- policy/profile snapshot mismatch;
- site chưa pause hoặc còn queued/running policy cũ;
- callback CAS/capability/legacy hash regression fail;
- tài liệu/code/evidence mâu thuẫn version/hash.

Một stop condition không được “giải quyết” bằng sửa evidence, đổi nhãn theo AI, hạ gate sau output, dùng functional-clean làm gold hoặc bật `meta.calibrated=true`.
