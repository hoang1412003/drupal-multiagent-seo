# Standalone Multi-Agent Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển phần Multi-Agent hiện tại thành service độc lập có schema site/profile, API Drupal có version, trang quản trị local-auth và bộ công cụ vận hành, trong khi giữ nguyên hành vi chấm điểm của Sprint 3.

**Architecture:** Triển khai theo modular monolith trong `multiagent/src/review_platform/`, giữ `multiagent/src/api.py` làm entrypoint FastAPI và worker là tiến trình riêng. Năm plan con tạo các lát phần mềm chạy được độc lập: nền dữ liệu → auth/admin shell → admin vận hành → API/connector Drupal → hardening và rollout.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, HTMX 2.0.10, Argon2id, psycopg 3, PostgreSQL 17 + pgvector, Drupal 10.6, DDEV/PHP 8.4.

**Spec:** `docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md` — đã duyệt ngày 2026-08-12.

## Global Constraints

- Chưa được gọi Anthropic hoặc chạy E1/E5/E3/E6 trong bất kỳ task triển khai nào; test mặc định phải offline và không cần secret trả phí.
- Score-path snapshot là `04f10e1`; `prompt_version` phải giữ `020738e209017213`. Không sửa prompt, rubric, 4 agent, `fact_check.py`, `scoring.py`, Aggregator, rule, KB hay `scoring.yaml`.
- Nếu một task bắt buộc chạm score path hoặc làm output report thay đổi với cùng input, dừng plan và xin duyệt lại; không tự hợp thức hóa bằng cách cập nhật snapshot.
- Drupal là nguồn sự thật của nội dung. PostgreSQL không lưu title/body/summary/meta/alt toàn phần; chỉ lưu external ID/revision/hash, kết quả, evidence và metadata vận hành.
- MVP chỉ có site `drupal-vn-primary`, profile `cam-nang-vn`, market `VN`, language `vi`, content type `cam_nang`; không thêm CMS/thị trường thứ hai.
- API xác định site từ Bearer credential; mọi body có `site_id` phải bị từ chối hoặc bỏ qua theo contract, tuyệt đối không dùng làm scope truy vấn.
- Write-back MVP phải đi qua Drupal result callback có compare-and-set theo expected revision/hash và idempotency theo `run_id`; không PATCH generic JSON:API article.
- Endpoint legacy/hash version 1 phải chạy được trong toàn bộ cửa sổ rollback; worker chọn thuật toán fingerprint theo `content_hash_version`, không ép v1 qua v2.
- `base_url` DDEV trong seed chỉ là bootstrap local. Mỗi staging/production phải cấu hình site bằng CLI và capability test trước khi khởi động worker mới.
- Admin config/KB/evaluation chỉ đọc; không có prompt editor và không chạy phép đo từ web.
- Mọi thao tác có hiệu ứng phụ dùng POST, kiểm RBAC ở server, CSRF và audit; không dựa vào việc ẩn nút.
- Test Python mới theo convention hiện tại: `multiagent/scripts/test_*.py`, assert thuần, tự gọi mọi `test_*` trong `__main__`, in `[PASS]/[FAIL]`; meta-test `test_moi_test_deu_chay.py` phải xanh.
- Comment/tên hàm nghiệp vụ trong Python tiếp tục dùng tiếng Việt không dấu khi hợp với file hiện hành; public HTTP/DB identifier dùng tiếng Anh ổn định.
- Mỗi task theo TDD: thấy RED đúng nguyên nhân → code tối thiểu → GREEN → regression liên quan → commit nhỏ.

---

## Thứ tự plan bắt buộc

| Thứ tự | Plan | Sản phẩm chạy được | Phụ thuộc |
|---|---|---|---|
| 1 | [`2026-08-12-platform-foundation.md`](2026-08-12-platform-foundation.md) | Migration versioned, site/profile context, queue/audit scoped | Không |
| 2 | [`2026-08-12-platform-admin-auth.md`](2026-08-12-platform-admin-auth.md) | Local auth, session, CSRF, RBAC, login/admin shell | Plan 1 |
| 3 | [`2026-08-12-platform-admin-operations.md`](2026-08-12-platform-admin-operations.md) | Dashboard, jobs/history, users, config/KB/evaluation/audit read-only | Plan 1–2 |
| 4 | [`2026-08-12-platform-api-drupal-connector.md`](2026-08-12-platform-api-drupal-connector.md) | `/api/v1`, per-site credential, connector revision-aware, Drupal cutover, pause/retry | Plan 1–3 |
| 5 | [`2026-08-12-platform-hardening-rollout.md`](2026-08-12-platform-hardening-rollout.md) | Heartbeat, cost/latency, security, role script, rehearsal và tài liệu bàn giao | Plan 1–4 |

Không chạy Plan 2–5 khi plan phụ thuộc chưa qua checkpoint cuối. Mỗi plan có commit riêng theo task; không squash giữa chừng vì migration/security cần lịch sử review rõ.

---

## File Structure mục tiêu

```text
multiagent/
├── migrations/
│   ├── 0001_platform_foundation.sql
│   ├── 0002_admin_auth.sql
│   ├── 0003_api_connector.sql
│   └── 0004_platform_observability.sql
├── config/
│   ├── scoring.yaml                 # giữ nguyên
│   └── model_pricing.yaml           # read-only, có effective date/source
├── src/
│   ├── api.py                       # entrypoint + include routers
│   ├── job_queue.py                 # queue SQL, site/profile-aware
│   ├── audit.py                     # run log, site/profile-aware
│   ├── worker.py                    # claim → connector → engine → audit → write-back
│   └── platform/
│       ├── migrations.py
│       ├── database.py
│       ├── context.py
│       ├── sites.py
│       ├── reviews.py
│       ├── pricing.py
│       ├── worker_health.py
│       ├── usage.py
│       ├── logging.py
│       ├── security.py
│       ├── api/
│       │   ├── auth.py
│       │   ├── models.py
│       │   └── router.py
│       ├── auth/
│       │   ├── passwords.py
│       │   ├── users.py
│       │   ├── sessions.py
│       │   ├── csrf.py
│       │   ├── throttle.py
│       │   └── rbac.py
│       ├── connectors/
│       │   ├── base.py
│       │   ├── secrets.py
│       │   └── drupal.py
│       └── admin/
│           ├── router.py
│           ├── dependencies.py
│           ├── queries.py
│           ├── evaluation.py
│           ├── templates/
│           └── static/
└── scripts/
    ├── migrate.py
    ├── admin_user.py
    ├── site_config.py
    └── site_credential.py
```

Không tạo `review_platform/engine/` bằng một lần di chuyển hàng loạt. Trong MVP, engine boundary là adapter gọi `graph.build_graph(include_write_back=False)`; chỉ di chuyển agent/graph sau Sprint 3 bằng refactor riêng nếu thật sự cần.

---

## Checkpoint liên plan

- [x] **Sau Plan 1:** migration nâng được schema cũ; dữ liệu không mất; legacy API/worker tests xanh; score-path diff rỗng. Evidence: `docs/evidence/platform-foundation-verification.txt`.
- [ ] **Sau Plan 2:** đăng nhập/logout/đổi mật khẩu/RBAC/CSRF/rate-limit hoạt động; chưa có action vận hành ngoài logout/password.
- [ ] **Sau Plan 3:** viewer xem được dữ liệu thật; operator/admin action đúng quyền; config/KB/evaluation không có đường ghi.
- [ ] **Sau Plan 4:** Drupal Needs Review tạo đúng một scoped job, fetch đúng revision, result callback CAS/idempotent chỉ ghi một lần; job cũ không ghi đè job mới; endpoint/hash v1 vẫn chạy trong cửa sổ rollback.
- [ ] **Sau Plan 5:** security/integration suite xanh; usage của attempt lỗi được ghi bền vững; migration, site configuration và rollback rehearsal có evidence; tài liệu khởi động/rotate/recover hoàn chỉnh.

Tại mọi checkpoint chạy:

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'; print(e.prompt_version())"
git -C .. diff --exit-code 04f10e1 -- multiagent/src/agents multiagent/src/ai_core.py multiagent/src/brand_analysis.py multiagent/src/config.py multiagent/src/embeddings.py multiagent/src/graph.py multiagent/src/retrieval.py multiagent/src/scoring.py multiagent/src/seo_analysis.py multiagent/src/state.py multiagent/src/text_utils.py multiagent/src/kb multiagent/config/scoring.yaml
```

Expected: in ra `020738e209017213`; `git diff --exit-code` trả 0. Nếu không, dừng trước khi chạy test tiếp theo.

---

## Ma trận phủ 11 tiêu chí MVP

| # | Tiêu chí design spec §14 | Task triển khai chính | Bằng chứng khóa |
|---:|---|---|---|
| 1 | Người viết chỉ dùng Drupal; một Needs Review tạo một job | API/Connector Task 4, 7, 9 | Hardening Task 5, 7 |
| 2 | Job đúng site/profile/policy và dedup | Foundation Task 3–4; API/Connector Task 2 | Hardening Task 5 |
| 3 | Một lượt thành công chỉ write-back một lần, không ghi đè revision mới | Foundation Task 5; API/Connector Task 4–5, 7 | Hardening Task 5 |
| 4 | Viewer/operator/admin đúng quyền ở UI và server | Admin Auth Task 2–5; Admin Operations Task 4, 6, 9 | Auth/Operations checkpoint |
| 5 | Dashboard/jobs/history đọc dữ liệu thật, không giả legacy status/chi phí | Foundation Task 2; Admin Operations Task 2–5; Hardening Task 1, 3 | Admin Operations Task 10; Hardening Task 5 |
| 6 | Retry lỗi write-back không gọi LLM lần hai | Foundation Task 5; API/Connector Task 5, 9 | Hardening Task 5 failure matrix |
| 7 | Config, KB, evaluation chỉ đọc | Admin Operations Task 7–8 | POST regression + Operations checkpoint |
| 8 | Không lưu toàn văn/secret | Foundation Task 5; API/Connector Task 1–5 | Hardening Task 2, 5 |
| 9 | Nâng database không mất dữ liệu | Foundation Task 1–2 | Hardening Task 7 restore rehearsal |
| 10 | Offline regression xanh, engine/prompt không đổi | Mọi checkpoint score gate | Hardening Task 3, 6, 8 |
| 11 | Tài liệu/handoff phản ánh đúng trạng thái | Mọi checkpoint docs | Hardening Task 8 acceptance matrix |

Một hàng chỉ được đánh PASS cuối chương trình khi test và evidence thật tồn tại ở commit được ghi nhận. Plan/task chưa chạy không phải bằng chứng hoàn thành.

---

## Điểm dừng và rollback

- Trước khi cutover Drupal ở Plan 4, endpoint `/jobs` và `/jobs/by-node/...` vẫn chạy với `VF_SERVICE_TOKEN`.
- Cutover chỉ diễn ra sau khi site `base_url`/`secret_ref` đã được cấu hình cho đúng môi trường, per-site credential đã import, capability test + `/api/v1` smoke xanh và migration backup được xác minh.
- Trong cửa sổ rollback, đổi `ServiceClient.php` về endpoint cũ hoặc revert đúng commit cutover; không rollback migration bằng cách xóa cột/bảng.
- Worker mới phải tiếp tục xử lý job legacy `content_hash_version=1` bằng hash bốn field và working-copy fetch; rollback không đạt nếu chỉ endpoint cũ nhận request nhưng worker từ chối hash.
- Migration đã apply là append-only; sửa lỗi bằng migration số mới, không chỉnh nội dung file đã ghi trong `schema_migration`.
- Không xóa job/run cũ. Rollback ứng dụng phải đọc được row đã backfill về default site/profile.

---

## Điều kiện hoàn thành toàn chương trình

- [ ] 11 tiêu chí MVP ở design spec mục 14 đều có test/evidence trỏ được tới task cụ thể.
- [ ] Full offline suite xanh; các test cần PostgreSQL/Drupal báo trạng thái riêng, không biến `[SKIP]` thành `[PASS]`.
- [ ] Không có secret/toàn văn draft trong Git, log, audit hoặc admin HTML.
- [ ] Stale-write race, callback idempotency, legacy v1 rollback, non-DDEV site configuration, capability health và failed-attempt usage đều có regression/evidence.
- [ ] `git diff --check` sạch; worktree chỉ còn thay đổi đã biết.
- [ ] `prompt_version` và output regression giữ nguyên.
- [ ] `docs/technical-debt.md` mục 8 vẫn giữ thứ tự test–retest → E1 → E5; productization không tự chạy thí nghiệm.
