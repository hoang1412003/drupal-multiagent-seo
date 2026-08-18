# Publish Blocking Decision Policy v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Chỉ dùng `superpowers:subagent-driven-development` khi chủ dự án yêu cầu rõ việc chia cho sub-agent. Mỗi bước dùng checkbox (`- [ ]`) để theo dõi.

**Goal:** Phát hành `cam-nang-vn-v2` dùng blocking rule A/B/assurance để đề xuất quyết định, giữ `final_score` chỉ làm số mô tả, đồng thời bảo toàn khả năng tái lập mọi run `cam-nang-vn-v1`.

**Architecture:** Job tiếp tục snapshot exact `policy_version` từ `review_profile`. Worker xác minh release trước LLM và truyền version/ngày đánh giá vào graph. Bốn agent chọn đúng prompt bundle theo version và trả coverage có phân biệt `NA` nghiệp vụ với lỗi hạ tầng. Aggregator vẫn tính điểm nhưng giao quyết định cho evaluator thuần, khai báo trong `decision_policy.yaml`. Candidate chỉ được gắn profile active sau chuỗi guideline v1.4 → gán lại 33 bài mù → test–retest ≥3 ngày → đánh giá v2 → functional-clean → cutover có audit.

**Tech Stack:** Python 3.12, LangGraph, YAML/JSON, psycopg 3, PostgreSQL 17, các test script assert thuần hiện hành, Drupal 10/DDEV chỉ dùng để regression callback/report.

**Spec:** `docs/superpowers/specs/2026-08-17-publish-blocking-decision-policy-design.md` — đã được chủ dự án duyệt ngày 2026-08-17.

**Current baseline:** HEAD lúc lập plan là `b0fa1c8`; policy active là `cam-nang-vn-v1`; prompt hash v1 là `020738e209017213`; `scoring.yaml.meta.calibrated` vẫn phải là `false`. E1/E5/E6 ngày 2026-08-16 chỉ thuộc v1.

## Global Constraints

- Không gọi API trả phí trong Plan Core. Bốn lượt có thể phát sinh phí ở Plan Evaluation — E1 v2, gold v2, functional-clean v2 và smoke job thật sau cutover — phải được người dùng xác nhận chi phí riêng cho đúng từng lượt.
- Không sửa hoặc xoá evidence v1, không sửa migration `0001`, không đổi row/job/run lịch sử thành v2 và không resume output v1 vào file v2.
- `cam-nang-vn-v1` phải giữ system prompt và quyết định hiện hành. Test bắt buộc khóa `prompt_version("cam-nang-vn-v1") == "020738e209017213"` và các acceptance vector v1 trước khi thêm v2.
- Exact `policy_version` chọn cả prompt, rubric semantics, required checks và evaluator. Không có `default`, `latest`, prefix match hoặc fallback từ version lạ.
- Policy v2 không đọc `publish_min`, `needs_revision_min` hay `compliance_veto_below` để quyết định. Không xoá các số v1 khỏi `scoring.yaml`, không bật `meta.calibrated`.
- `rejected` chỉ do finding `reject` đủ assurance; finding B là `revise`; nghi vấn A chỉ từ LLM là `manual_review`; C/advisory không chặn.
- Thiếu agent/check do hạ tầng chặn `publish`. `NA` vì không áp dụng vẫn là assessment hoàn tất và không được coi là lỗi hạ tầng.
- `CQ9`, `SEO11`, `CP9`, `CP10` là decision-only checks, không được đưa vào `score_from_criteria()` hoặc mẫu số điểm.
- CP3 chỉ có quyền `reject` khi occurrence mang provenance `verified=true`; nếu không, cùng mức 0 chỉ được `manual_review`.
- CP5/B15 phải sửa và có literal regression trên P-006a trước khi B1 được trao quyền chặn trong v2.
- Guideline v1.4 và rubric v2 phải được khóa trước khi xem output AI v2 trên gold set. Không bulk-edit `guideline_version` của 33 nhãn cũ.
- Không sửa JS/CSS/PHP UI trong chương trình này. JSON v2 được phép thêm key mà renderer hiện tại bỏ qua; không tuyên bố UI đã hiển thị `decision_basis`.
- API/connector giữ nguyên callback CAS, idempotency `run_id`, exact revision/hash v2 và compatibility hash v1 trong cửa sổ rollback.
- Không lưu toàn văn draft mới vào queue/audit/profile snapshot. Evidence excerpt hiện có tiếp tục theo hợp đồng tối thiểu của agent/report.
- Test Python mới phải nằm trong `multiagent/scripts/test_*.py`, được thêm đúng một lần vào `test_groups.json`, tự chạy mọi `test_*`, in `[PASS]/[FAIL]`, không skip im lặng.
- Mỗi task theo TDD: RED đúng nguyên nhân → code tối thiểu → GREEN → regression liên quan → commit nhỏ. Không dùng output gold để điều chỉnh rule trong cùng release.

## Bốn check mới/được chính thức hoá

| Check | Cách chốt candidate | Mapping v2 | Điểm |
|---|---|---|---|
| `CQ9` / A5 | Chia body thành section ổn định, LLM chỉ ra section không thực hiện lời hứa của title; code tính tỷ lệ tiếng của section phải viết lại. `> 50%` → mức 0 | `manual_review`, assurance `hybrid`; mức 1 chỉ advisory | Không tham gia |
| `SEO11` / B4 | Chỉ xét năm 4 chữ số trong title so với `assessment_as_of`; LLM phân loại `freshness_marker` với ngữ cảnh lịch sử. Năm cũ + freshness marker → mức 0 | `revise`, assurance `hybrid` | Không tham gia |
| `CP9` / A7 | Detector hiện hành tìm văn xuôi ẩn sau khi loại CSS/tracking/URL/marker; luôn trả decision check mức 0 hoặc 2 và flag giữ compatibility | mức 0 `reject`, assurance `deterministic` | Không tham gia |
| `CP10` / A6 | LLM nêu exact evidence của hướng dẫn kỹ thuật có rủi ro; candidate không có safety KB đủ provenance nên chỉ phát mức 1/2/NA | mức 1 `manual_review`, assurance `llm_evidence`; không tự sinh mức 0 | Không tham gia |

`CQ9` không dùng số section thuần: denominator là tổng số tiếng trong các section có nội dung; numerator là tổng số tiếng của section được LLM đánh dấu cần viết lại và có evidence hợp lệ. Section ID lạ hoặc evidence không nằm trong section làm `CQ9` unavailable, không được coi là sạch.

`SEO11` dùng ngày tạo job đã snapshot, không dùng năm hiện tại ngầm trong prompt. `historical` là đạt/không finding; `unclear` là unavailable để fail-closed, không tự gán B4.

`CP10` candidate cố ý không có đường `reject`: mức 0 chỉ được mở ở release tương lai khi có nguồn kỹ thuật chính thức, retrieval đúng phạm vi và provenance được kiểm. Không dùng lời khẳng định của LLM làm “verified”.

## Thứ tự plan bắt buộc

| Thứ tự | Plan | Sản phẩm | Cổng kết thúc |
|---:|---|---|---|
| 1 | [`2026-08-17-publish-blocking-policy-v2-core.md`](2026-08-17-publish-blocking-policy-v2-core.md) | Guideline/rubric/protocol đã version; policy engine v1/v2; agent coverage; graph/worker exact version; release CLI; toàn bộ test offline | Không gọi LLM; v1 regression nguyên; suite offline 0 hỏng/0 skip |
| 2 | [`2026-08-17-publish-blocking-policy-v2-evaluation-cutover.md`](2026-08-17-publish-blocking-policy-v2-evaluation-cutover.md) | Nhãn v1.4 độc lập; test–retest; E1/E5/functional-clean v2; manifest bằng chứng; stage/activate/rollback profile | Các gate đã đăng ký trước đều đạt và chủ dự án duyệt cutover |

Không chạy phần paid evaluation hoặc activation khi Plan Core chưa qua checkpoint. Có thể chuẩn bị/gán nhãn v1.4 sau khi Task 1 của Plan Core đã commit, nhưng tuyệt đối không mở output AI v2 trước khi test–retest được khóa.

## File Structure mục tiêu

```text
docs/
├── evaluation-plan.md
├── rubrics.md
├── technical-debt.md
├── goldset/
│   ├── annotation-guideline.md
│   ├── labels.csv                         # giữ lịch sử v1.3
│   └── labels-v1.4.csv                    # lượt gán mới, không copy nhãn
├── evidence/
│   ├── publish-policy-v2-protocol.md
│   ├── publish-policy-v2-manifest.json
│   ├── test-retest-v1.4-*.csv/.md
│   ├── e1-policy-v2-*.json/.md
│   ├── e5-policy-v2-*.json/.md
│   └── functional-clean-policy-v2-*.json/.md
└── superpowers/plans/
    ├── 2026-08-17-publish-blocking-decision-policy.md
    ├── 2026-08-17-publish-blocking-policy-v2-core.md
    └── 2026-08-17-publish-blocking-policy-v2-evaluation-cutover.md

multiagent/
├── config/decision_policy.yaml
├── migrations/0006_review_profile_immutability.sql
├── src/
│   ├── decision_policy.py
│   ├── prompt_registry.py
│   ├── state.py
│   ├── graph.py
│   ├── worker.py
│   ├── job_queue.py
│   ├── compliance_analysis.py
│   ├── retrieval.py
│   └── agents/
│       ├── content_quality.py
│       ├── seo.py
│       ├── brand_voice.py
│       ├── compliance.py
│       └── fact_check.py
└── scripts/
    ├── policy_release.py
    ├── eval_policy_v2.py
    ├── eval_stability.py
    ├── eval_functional_clean.py
    ├── test_decision_policy.py
    ├── test_*_rubric.py
    ├── test_worker*.py
    ├── test_migrations.py
    ├── test_policy_release.py
    └── test_groups.json
```

## Checkpoints

### Checkpoint A — normative contract

- [ ] Guideline v1.4 có A7/B11, B7 `>75`, B9 `>500 tiếng và không H2`, không còn mapping SEO4→B3/BV4→B5.
- [ ] Rubric v2 định nghĩa CP7 v2 và ba decision-only checks mới; không cho chúng vào điểm.
- [ ] Protocol v2 đăng ký metrics/gates trước output; `labels.csv` v1.3 chưa bị sửa.

### Checkpoint B — core offline

- [ ] Version lạ fail trước agent; v1 hash và decision vectors giữ nguyên.
- [ ] V2 policy evaluator thuần qua đủ reject/revise/manual/advisory/incomplete/dedup/drift cases.
- [ ] C-006 fixture theo CP7 v2 là `NA`; P-006a literal không còn nổ CP5 vì tỷ lệ/chi phí; CP9 có `criterion_id`.
- [ ] `CQ9/SEO11/CP10` có coverage status và không đổi score denominator.
- [ ] Worker truyền exact policy/ngày tạo job; report v2 có `policy_version`, `policy_hash`, `decision_basis`; report v1 giữ version 1.
- [ ] Full offline suite bằng một lệnh đạt 0 hỏng/0 skip. Tổng file lấy từ manifest thực tế, không giữ cứng số 72 sau khi thêm test.

### Checkpoint C — labels độc lập

- [ ] 33/33 dòng v1.4 do người gán rà lại mù; không sao chép nhãn/codes/notes cũ hàng loạt.
- [ ] Test–retest chọn 3–4 bài bằng seed đã commit, cách lượt đầu ít nhất 72 giờ, evidence lượt hai khóa trước khi mở nhãn lượt một.
- [ ] Kappa test–retest ≥0,80; nếu thấp hơn thì tăng guideline version và gán lại, không chạy AI v2.

### Checkpoint D — evidence v2

- [ ] Provenance tuple khóa đủ policy/prompt/rubric/guideline/model/scoring/KB/embedding/HEAD.
- [ ] E1 v2 và gold v2 dùng hai phê duyệt chi phí riêng; functional-clean dùng phê duyệt riêng thứ ba.
- [ ] Không có coverage failure trong run hợp lệ; không có policy drift/unknown check.
- [ ] Kappa quyết định ≥0,60; recall `rejected` ≥0,80; recall `needs_revision` ≥0,80; false-publish = 0/33.
- [ ] Functional-clean publish = 10/10, báo cáo riêng; không nhập vào Kappa 33 bài.
- [ ] Decision consistency E1 ≥90% trên 10 bài × 5 lượt. σ `final_score` vẫn báo cáo nhưng không còn là gate quyết định v2.

Các ngưỡng Checkpoint D là gate cho limited pilot của chính corpus này, không phải tuyên bố tổng quát hoá. Nếu không đạt, release v2 giữ bất biến và không active; mọi sửa hành vi phải phát hành version kế tiếp, không ghi đè artifact đã đo.

### Checkpoint E — stage/cutover

- [ ] Profile v2 được stage từ clean committed tree; snapshot hash khớp manifest evidence.
- [ ] Site pause intake; không còn job `queued/running` của policy cũ; capability test xanh.
- [ ] Transaction cutover deactivate assignment v1 và activate v2, ghi audit; site vẫn pause để chạy smoke.
- [ ] Sau xác nhận chi phí riêng thứ tư, một smoke job thật giữ moderation state, callback đúng một lần, report mang v2; sau đó mới resume intake.
- [ ] Rollback profile v1 được rehearsal mà không đổi callback CAS/hash compatibility hoặc xóa job/run v2.

## Regression commands bắt buộc

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: tất cả file trong manifest chạy, `hong: 0`, `co [SKIP]: 0`.

Vì không sửa PHP/JS, vẫn chạy năm test DDEV để chứng minh report key mới không phá callback/renderer hiện hành:

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_result_callback.php
ddev exec php scripts/test_ai_roles.php
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev exec php scripts/test_ai_report_renderer.php
```

Không cần browser visual QA nếu diff xác nhận không có thay đổi `drupal/web/modules/custom/vf_ai_review/js/` hoặc CSS/PHP UI. Nếu phạm vi đổi sang UI, dừng plan và làm theo `docs/editor-ui-design.md` mục 10, gồm kiểm mắt thật.

## Rollback

- Rollback nghiệp vụ ưu tiên đổi active assignment về profile v1 trong transaction, không revert/xóa migration và không sửa job/run lịch sử.
- Trước rollback application về commit không hiểu v2: pause intake, drain mọi job v2 `queued/running`, xác nhận callback đã hoàn tất; nếu không thì giữ worker mới để xử lý job đã snapshot v2.
- Profile/policy artifact đã có evidence là append-only. Release thất bại không bị sửa tại chỗ; version sau chứa fix và đo lại.
- Endpoint legacy/hash v1 và result callback CAS vẫn tồn tại xuyên suốt. Không dùng rollback policy làm lý do đổi API write-back.

## Definition of Done

- [ ] Hai plan con hoàn tất, mọi checkpoint có evidence trỏ được tới commit/hash cụ thể.
- [ ] V1 tái lập được; v2 exact-selected, fail-closed và score-independent.
- [ ] Coverage ngược A1–A7/B1–B11 không có mã mồ côi; criterion advisory ghi rõ không có quyền chặn.
- [ ] Nhãn v1.4/test–retest và AI v2 được tạo theo đúng thứ tự mù; không có synthetic/functional data giả làm human gold.
- [ ] Full offline + năm test DDEV xanh; không báo fixture/preflight thành thí nghiệm.
- [ ] Profile v2 chỉ active nếu Checkpoint D đạt và cutover đã có audit/rehearsal.
- [ ] `docs/technical-debt.md` mục 8 được cập nhật theo trạng thái thật, không ghi “xong” trước evidence.
