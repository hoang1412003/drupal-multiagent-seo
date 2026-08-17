# Corrected Publish & Criterion Coverage v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây 20 bản `GC` expected-publish và 11 bản `CV` một lỗi, khóa provenance/checksum, rồi đo policy v2 trên bộ chính 63 và coverage riêng 11 mà không sửa gold/evidence v1.

**Architecture:** Chương trình được chia thành hai pha có checkpoint độc lập. Pha Data tạo và xác minh dữ liệu hoàn toàn offline; Pha Evaluation chỉ dùng runner/paid guard chung của `cam-nang-vn-v2`, preregister metric trước output và tách hai lượt trả phí corrected/coverage. Các mẫu synthetic không đi vào Kappa gold và không được dùng để fit `publish_min`.

**Tech Stack:** Python 3.12, CSV/JSON, SHA-256, các script kiểm thử standalone hiện hành, PowerShell, Git, pipeline policy v2.

**Spec:** `docs/superpowers/specs/2026-08-17-corrected-publish-criterion-coverage-design.md` tại commit `8c3b001`.

## Global Constraints

- Giao tiếp, tài liệu nghiệp vụ và evidence bằng tiếng Việt Nam.
- Không sửa `docs/goldset/raw/G-*.txt`, `docs/goldset/labels.csv`, `docs/functional-tests/clean/C-*.txt` hoặc evidence E1/E5/E6 v1.
- `G/P` = dữ liệu gốc; `C/GC` = corrected expected-publish; `CV` = criterion coverage synthetic.
- Bộ chính giữ đúng 63 mẫu: 30 `publish`, 23 `needs_revision`, 10 `rejected`.
- Bộ coverage giữ đúng 11 mẫu: 7 `rejected`, 4 `needs_revision`; không cộng vào metric tổng 63.
- CV chỉ được sinh từ parent `C/GC` đã sạch và chỉ có đúng một target code.
- Giữ `scoring.yaml.meta.calibrated=false`; policy v2 không fit hoặc sử dụng `publish_min` để quyết định.
- Mọi sửa file dùng `apply_patch`; không dùng lệnh shell để ghi nội dung bài/CSV/Markdown.
- Không gọi model/API trả phí trong Pha Data, test, preflight hoặc report-only.
- Mỗi lượt trả phí cần xác nhận riêng: E1 v2, gold v2, corrected-publish 30, coverage 11 và smoke cutover.
- Không xem output rồi thêm/xóa/sửa mẫu trong cùng version để làm đẹp điểm; lỗi dữ liệu phải tăng version manifest và giữ evidence cũ.
- AI v1.4 là `AI-annotated-partially-exposed`; `independent_label_reliability=not_demonstrated` cho tới khi có lượt gán độc lập hợp lệ.
- Full offline suite dùng `cd multiagent && .venv\Scripts\python.exe scripts\run_test_group.py all-offline`; số file lấy từ manifest thực tế, yêu cầu 0 fail/0 skip.

## Plan Map

1. [`2026-08-17-corrected-publish-criterion-coverage-data.md`](2026-08-17-corrected-publish-criterion-coverage-data.md) — khóa nhãn candidate, validator, 20 GC, 11 CV và integrity evidence; không API.
2. [`2026-08-17-corrected-publish-criterion-coverage-evaluation.md`](2026-08-17-corrected-publish-criterion-coverage-evaluation.md) — metric/runner/preflight, hai paid run mới và báo cáo Mức A/B/C.

Pha Evaluation phụ thuộc:

- Pha Data đã commit đủ 20 + 11 và integrity test xanh;
- Core policy `cam-nang-vn-v2` cùng `eval_policy_v2.py`/paid guard đã qua checkpoint offline;
- exact guideline/rubric/prompt/policy/KB/embedding provenance đã khóa.

## Checkpoints

### Checkpoint A — baseline/provenance

- [ ] Guideline candidate v1.4, `labels-ai-v1.4.csv` và evidence AI relabel được commit cùng provenance `partially exposed`.
- [ ] 33 gold gốc bất biến; nhãn candidate đúng 23/10/0 và không bị gọi là independent agreement.

### Checkpoint B — corrected publish

- [ ] 20/20 `GC` tồn tại, parent/checksum hợp lệ, không còn mã A/B theo contract v1.4.
- [ ] 10 `C` hiện có được rà xác nhận lại theo v1.4 nhưng không sửa nội dung/expected label hàng loạt.
- [ ] Bộ expected-publish có đúng 30 ID và không ID nào lọt vào gold calibration.

### Checkpoint C — criterion coverage

- [ ] 11/11 `CV` có parent sạch, đúng một target code, đúng expected label và checksum.
- [ ] Coverage tổng đạt tối thiểu hai ca cho A1–A7/B1–B11 theo inventory đã khóa.
- [ ] Mọi A6/A7 fixture có cảnh báo test-only và không được seed sang Drupal/production.

### Checkpoint D — evaluation preregistered

- [ ] Pure metrics/fake runner tests xanh; report-only không import/call paid model.
- [ ] Protocol/manifest commit trước output và chứa đúng gate 30/30, 20/20, 11/11 cùng các gate gold/stability.
- [ ] Preflight sinh token/cost riêng cho corrected và coverage; usage vẫn 0.

### Checkpoint E — evidence

- [ ] Kết quả Mức A luôn được báo pass/fail trung thực sau khi đủ run được phép.
- [ ] Mức B chỉ `passed` khi tất cả gate preregistered đạt; nếu trượt, giữ release/evidence bất biến và không cutover.
- [ ] Mức C ghi `not_demonstrated`, không suy từ synthetic hoặc 33/33 AI khớp nhãn cũ.

### Task 1: Execute Offline Data Plan

**Files:** Theo child plan Data.

**Interfaces:** Produces committed manifests/content/integrity report consumed verbatim by Evaluation Plan.

- [ ] **Step 1:** Thực hiện từng task của child plan Data theo thứ tự, dừng ở mọi RED không đúng nguyên nhân dự kiến.
- [ ] **Step 2:** Review riêng sau mỗi batch GC/CV; không sửa batch trước từ output model vì chưa có paid output.
- [ ] **Step 3:** Chỉ chuyển checkpoint khi full offline suite có tổng kết 0 fail/0 skip.

### Task 2: Execute Evaluation Plan

**Files:** Theo child plan Evaluation.

**Interfaces:** Consumes immutable Data commit; produces raw/report/manifest provenance for Mức A/B/C.

- [ ] **Step 1:** Xác minh prerequisites và preregister protocol từ clean committed tree.
- [ ] **Step 2:** Chạy từng USER GATE chi phí riêng; không gộp confirmation token.
- [ ] **Step 3:** Commit cả evidence âm nếu metric trượt; không chỉnh sample/release tại chỗ.
- [ ] **Step 4:** Chỉ đề xuất cutover khi Mức B đạt; Mức C vẫn phải ghi đúng giới hạn.

### Task 3: Final Handoff

**Files:**
- Modify: `docs/technical-debt.md` mục 8 sau khi đối chiếu bản dirty/latest trên main.
- Create: evidence summary theo child plan Evaluation.

**Interfaces:** Consumes final evidence hashes; produces single current-state handoff without overwriting historical numbers.

- [ ] **Step 1:** Đối chiếu HEAD, hashes, cost và mọi status với file evidence; không chép số từ terminal memory.
- [ ] **Step 2:** Cập nhật mục 8 bằng `apply_patch`, tách rõ v1 lịch sử, v2 measured status và synthetic limitation.
- [ ] **Step 3:** Chạy `git diff --check`, integrity validator và full offline suite lần cuối.
- [ ] **Step 4:** Commit handoff riêng; không gộp file ngoài scope.
