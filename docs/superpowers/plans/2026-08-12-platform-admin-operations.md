# Platform Admin Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến admin shell thành giao diện vận hành đọc dữ liệu thật: dashboard, jobs, review history, users, config/KB/evaluation và audit, với action đúng role và có cảnh báo chi phí.

**Architecture:** Query/read-model được tách khỏi route và template; mọi list dùng pagination ổn định. Jinja render full page, HTMX chỉ thay fragment cho filter/action nhỏ và có standard-form fallback; không có frontend build chain hoặc SPA.

**Tech Stack:** FastAPI, Jinja2, HTMX 2.0.10 vendored, psycopg 3, YAML/JSON read-only, CSS thuần.

**Depends on:** Foundation và Admin Auth đã qua checkpoint.

**Quy ước chạy lệnh:** Mỗi code block PowerShell bắt đầu với working directory `D:\drupal-multiagent-seo\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

## Global Constraints

- Trước khi triển khai UI dashboard, phải đọc và áp dụng `build-web-apps:frontend-app-builder`; không thay đổi chức năng/spec đã duyệt.
- Không dùng mock metric trong production route. Không có dữ liệu thì hiển thị “Chưa có dữ liệu”.
- Mọi filter được allowlist; sort column không nội suy trực tiếp từ query string.
- Pagination mặc định 25, tối đa 100; thứ tự ổn định `created_at DESC, id DESC`.
- Viewer chỉ GET/read; operator có retry; admin có user management. Endpoint kiểm role độc lập với nút hiển thị.
- Retry POST phải nói rõ “có thể gọi LLM và phát sinh chi phí”; saved result có sẵn thì worker tái dùng, không gọi LLM.
- Config/KB/evaluation loader chỉ đọc đường dẫn compile-time/allowlist, không nhận path tùy ý từ request.
- Jinja autoescape; không dùng `|safe` với error/evidence/suggestion/username.
- Giá USD là ước tính theo bảng giá versioned, không được ghi nhãn “chi phí hóa đơn thực tế”.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/src/platform/admin/queries.py` | Dashboard/jobs/runs/audit read models |
| `multiagent/src/platform/admin/evaluation.py` | Load/validate evidence manifest allowlist |
| `multiagent/src/platform/reviews.py` | Retry service + transaction/audit |
| `multiagent/src/platform/pricing.py` | Token → estimated USD từ config versioned |
| `multiagent/config/model_pricing.yaml` | Giá model + effective date + official source |
| `docs/evidence/evaluation-manifest.json` | Trạng thái E1–E6 machine-readable |
| `multiagent/src/platform/admin/templates/*.html` | Dashboard/list/detail/users/read-only pages |
| `multiagent/src/platform/admin/static/vendor/htmx.min.js` | HTMX vendored, không CDN runtime |
| `multiagent/src/platform/admin/static/admin.css` | Layout/table/badge/form responsive |

---

### Task 1: Chốt UI shell và vendor HTMX

**Files:**
- Create: `multiagent/src/platform/admin/static/vendor/htmx-2.0.10.min.js`
- Modify: `multiagent/src/platform/admin/templates/base.html`
- Modify: `multiagent/src/platform/admin/static/admin.css`
- Create: `multiagent/scripts/test_admin_assets.py`

**Interfaces:**
- Produces: local static asset `/admin/static/vendor/htmx-2.0.10.min.js`.
- Produces: base layout có nav theo role, flash/error region, responsive main.

- [ ] **Step 1: Dùng frontend skill để tạo concept và khóa tokens**

Không sửa route/data ở bước này. Concept phải giữ: tiếng Việt, desktop-first nhưng dùng được 360px, high contrast, không gradient trang trí, không “AI neon”. Chốt CSS custom properties cho màu nền/card/text/muted/border/success/warning/danger, spacing, radius và max content width.

- [ ] **Step 2: Tải đúng HTMX và kiểm integrity trước khi add**

```powershell
$target = 'src/platform/admin/static/vendor/htmx-2.0.10.min.js'
New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
Invoke-WebRequest 'https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js' -OutFile $target
$bytes = [IO.File]::ReadAllBytes((Resolve-Path $target))
$sha = [Convert]::ToBase64String([Security.Cryptography.SHA384]::HashData($bytes))
if ($sha -ne 'H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V') { throw "HTMX integrity mismatch: $sha" }
```

Lệnh tải cần phê duyệt mạng khi execution. Runtime không gọi CDN vì file được commit.

- [ ] **Step 3: RED asset/template test**

Test base HTML chỉ tham chiếu path local, không chứa `http://`/`https://` script; mọi nav item có route, active marker và role condition. Test CSS có `:focus-visible`, media query ≤700px và `.sr-only`.

- [ ] **Step 4: Implement base shell**

Nav: Tổng quan, Jobs, Lịch sử chấm, Cấu hình & KB, Đánh giá; Admin thấy thêm Người dùng, Nhật ký. Header hiển thị username/role và form logout POST có CSRF. Không render nav operation nếu role thiếu, nhưng server gate vẫn là nguồn quyền.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_assets.py
git -C .. add multiagent/src/platform/admin/static multiagent/src/platform/admin/templates/base.html multiagent/scripts/test_admin_assets.py
git commit -m "feat: add accessible admin UI shell"
```

---

### Task 2: Pricing versioned và dashboard query

**Files:**
- Create: `multiagent/config/model_pricing.yaml`
- Create: `multiagent/src/platform/pricing.py`
- Create: `multiagent/src/platform/admin/queries.py`
- Create: `multiagent/scripts/test_admin_dashboard.py`

**Interfaces:**
- Produces: `estimate_usage(usage: list[dict], pricing_path: Path) -> CostEstimate`.
- Produces: `dashboard(conn, *, date_from: date, date_to: date) -> DashboardView`.

- [ ] **Step 1: Tạo pricing config có xuất xứ**

```yaml
version: 1
currency: USD
effective_at: "2025-10-15"
source: "https://www.anthropic.com/claude/haiku"
models:
  claude-haiku-4-5-20251001:
    input_usd_per_million: 1.00
    output_usd_per_million: 5.00
```

Không dùng giá cache/batch vì code hiện không bật hai chế độ đó.

- [ ] **Step 2: RED pricing**

Test 1.000.000 input + 1.000.000 output = 6 USD; nhiều call được sum; unknown model trả `estimated_usd=None` + list unknown, không tính 0 giả; negative/missing token bị validation error.

- [ ] **Step 3: Implement pricing immutable Decimal**

Dùng `Decimal`, không float cho USD. `CostEstimate` gồm input_tokens, output_tokens, estimated_usd, pricing_version/effective_at, unknown_models. UI luôn thêm chữ “ước tính”.

- [ ] **Step 4: RED dashboard SQL**

Seed run ở trong/ngoài date range, đủ decision, NULL score, usage unknown model. Assert:

- queue counts theo status;
- total reviews;
- decision distribution;
- p50/p95 duration bằng `percentile_cont`;
- token/cost chỉ từ rows trong range;
- health không tự bịa worker/connector ở phase này: status `unknown` đến Plan 4–5.

- [ ] **Step 5: Implement dashboard read model**

Date range là `[from 00:00 UTC, to+1 day 00:00 UTC)`. Tối đa 93 ngày/request. Query aggregate SQL, không load toàn `agent_results`. Giá tính từ aggregate usage entries; với quy mô hiện tại có thể query `jsonb_array_elements(usage)`.

- [ ] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_dashboard.py
git -C .. add multiagent/config/model_pricing.yaml multiagent/src/platform/pricing.py multiagent/src/platform/admin/queries.py multiagent/scripts/test_admin_dashboard.py
git commit -m "feat: add traceable dashboard metrics and cost estimates"
```

---

### Task 3: Dashboard route/template

**Files:**
- Modify: `multiagent/src/platform/admin/router.py`
- Modify: `multiagent/src/platform/admin/templates/home.html`
- Create: `multiagent/src/platform/admin/templates/partials/dashboard_metrics.html`
- Modify: `multiagent/scripts/test_admin_routes.py`

**Interfaces:**
- Route: `GET /admin?from=YYYY-MM-DD&to=YYYY-MM-DD` viewer+.
- Fragment: cùng route trả partial khi header `HX-Request: true`.

- [ ] **Step 1: RED render/no-data/invalid-range**

Test viewer 200; unauth redirect; invalid date 422 page có error; no-data không chứa `0 ms`/`$0` gây hiểu lầm mà có “Chưa có dữ liệu”. HTMX response không chứa full `<html>`.

- [ ] **Step 2: Implement route**

Default 7 ngày gần nhất UTC. Template cards: API/DB status, worker/connector `Chưa xác minh`; queue; total; decision; tokens; estimated USD; p50/p95. Mỗi metric có `title`/caption nguồn dữ liệu.

- [ ] **Step 3: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_routes.py
git -C .. add multiagent/src/platform/admin/router.py multiagent/src/platform/admin/templates multiagent/scripts/test_admin_routes.py
git commit -m "feat: render operational dashboard from run data"
```

---

### Task 4: Jobs list/detail và retry service

**Files:**
- Create: `multiagent/src/platform/reviews.py`
- Create: `multiagent/src/platform/admin/templates/jobs.html`
- Create: `multiagent/src/platform/admin/templates/job_detail.html`
- Create: `multiagent/src/platform/admin/templates/partials/jobs_table.html`
- Modify: `multiagent/src/platform/admin/queries.py`
- Modify: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/scripts/test_admin_jobs.py`

**Interfaces:**
- Query: `list_jobs(conn, filters: JobFilters, page: int, page_size: int) -> Page[JobRow]`.
- Query: `get_job(conn, public_id: UUID) -> JobDetail | None`.
- Service: `retry_failed(conn, *, job_public_id: UUID, actor: AdminUser, reason: str | None) -> RetryResult`.
- Routes: `GET /admin/jobs`, `GET /admin/jobs/{public_id}`, `POST /admin/jobs/{public_id}/retry`.

- [ ] **Step 1: RED filter/sort/site isolation**

Allow status exact queue states, source, external ID substring tối đa 100 chars, date range. Invalid status 422. Query uses parameter binding. Detail returns run linkage and sanitized last_error, never raw traceback/Authorization.

- [ ] **Step 2: RED retry permissions/state/cost audit**

Viewer POST → 403; operator without CSRF → 403; retry non-failed → 409; failed → new queued job linked `supersedes_job_id`. `saved_result_available=true` chỉ khi failed job có run `writeback_status='failed'`; lỗi connector/engine chưa có reusable run phải false. Response/audit ghi bool và reason, không chứa payload.

- [ ] **Step 3: Implement retry transaction**

Lock failed job; reconstruct `ReviewContext` from snapshot IDs, check site active; query reusable run của chính failed job để quyết warning, rồi call `enqueue_scoped(... force=True, supersedes_job_id=failed_job.id)` với source `admin_retry`. Worker vẫn kiểm lại eligibility trong transaction trước reuse; web request không gọi engine.

- [ ] **Step 4: Implement UI**

List columns: time, site, external ID, status, attempts, source, policy. Detail: correlation, revision, error đã làm sạch, run link, write-back status. Retry form chỉ operator/admin thấy, có checkbox xác nhận câu chi phí và CSRF; server bắt `confirm_cost=yes`, không chỉ JavaScript confirm.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_jobs.py
.\.venv\Scripts\python.exe scripts\test_admin_routes.py
git -C .. add multiagent/src/platform/reviews.py multiagent/src/platform/admin multiagent/scripts/test_admin_jobs.py
git commit -m "feat: add admin job inspection and audited retry"
```

---

### Task 5: Review history list/detail

**Files:**
- Create: `multiagent/src/platform/admin/templates/reviews.html`
- Create: `multiagent/src/platform/admin/templates/review_detail.html`
- Create: `multiagent/src/platform/admin/templates/partials/reviews_table.html`
- Modify: `multiagent/src/platform/admin/queries.py`
- Modify: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/scripts/test_admin_reviews.py`

**Interfaces:**
- Routes: `GET /admin/reviews`, `GET /admin/reviews/{public_id}` viewer+.

- [ ] **Step 1: RED read model**

Assert detail có agent scores/criteria/issues/evidence/veto/missing/model/config meta/profile/policy/token/cost/duration/write-back/link Drupal. Missing/legacy fields render `Không có dữ liệu`, không KeyError.

- [ ] **Step 2: Implement safe normalization**

`normalize_agent_results(jsonb)` chỉ chấp nhận dict/list/scalar và giới hạn hiển thị: max 4 agents, max 50 criteria/issues mỗi agent, mỗi text 2000 chars. Không mutate DB. Drupal URL được dựng `site.base_url + /node/<external>` chỉ khi external ID là numeric; với UUID dùng URL JSON:API không phù hợp người dùng, nên context phải lưu `source_url` ở Plan 4. Trước đó hiển thị external ID không link.

- [ ] **Step 3: Implement UI + GREEN**

Table/filter và accordion `<details>` semantic; không render raw HTML evidence. Token/cost có pricing version/effective date.

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_reviews.py
git -C .. add multiagent/src/platform/admin multiagent/scripts/test_admin_reviews.py
git commit -m "feat: add explainable review history pages"
```

---

### Task 6: User management UI đúng last-admin invariant

**Files:**
- Create: `multiagent/src/platform/admin/templates/users.html`
- Create: `multiagent/src/platform/admin/templates/user_form.html`
- Modify: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/scripts/test_admin_user_routes.py`

**Interfaces:**
- Routes admin-only: list/create/set-role/lock/unlock/reset-password.

- [ ] **Step 1: RED role/server enforcement**

Viewer/operator GET/POST users → 403. Admin create normalizes username, role allowlist. Reset returns temporary password only trong response success một lần; subsequent GET never shows it. Cannot act on last active admin.

- [ ] **Step 2: Implement forms**

Tất cả POST có CSRF. Create/reset generate temporary password bằng `secrets.token_urlsafe(18)`, set must-change. Confirmation page nói rõ phải truyền password an toàn; response header `Cache-Control: no-store`. Không gửi email.

- [ ] **Step 3: Audit và GREEN**

Assert audit action/outcome/old-new role; no temp password in audit/log captured.

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_user_routes.py
git -C .. add multiagent/src/platform/admin multiagent/scripts/test_admin_user_routes.py
git commit -m "feat: add guarded admin user management"
```

---

### Task 7: Config và KB read-only

**Files:**
- Create: `multiagent/src/platform/admin/read_only_sources.py`
- Create: `multiagent/src/platform/admin/templates/config_kb.html`
- Modify: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/scripts/test_admin_read_only.py`

**Interfaces:**
- Route: `GET /admin/config-kb` viewer+.
- No POST/PUT/PATCH/DELETE route under this path.

- [ ] **Step 1: RED allowlist/path traversal**

Loader API không nhận path từ route. Compile-time allowlist chỉ gồm `config/scoring.yaml`, `src/agents/compliance_rules.json`, `src/agents/brand_rules.json`, `src/kb/specs.json`; KB DB query chỉ aggregate collection/content_type/langcode/count + metadata excerpt max 500 chars. Request `?path=../../.env` không ảnh hưởng output và không mở file.

- [ ] **Step 2: Implement read-only snapshot**

Parse YAML/JSON phòng thủ, trả file SHA-256, modified timestamp và metadata cần hiển thị; không đưa full prompt. KB show collection counts, embedding dimension/model từ metadata nếu có; nếu thiếu ghi “Chưa version hóa”, không bịa.

- [ ] **Step 3: Route method regression**

Assert GET 200; POST 405; HTML không có `Save`, textarea editable, secret ref value hoặc full environment.

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_read_only.py
git -C .. add multiagent/src/platform/admin/read_only_sources.py multiagent/src/platform/admin/templates/config_kb.html multiagent/src/platform/admin/router.py multiagent/scripts/test_admin_read_only.py
git commit -m "feat: expose read-only policy and KB metadata"
```

---

### Task 8: Evaluation manifest và read-only page

**Files:**
- Create: `docs/evidence/evaluation-manifest.json`
- Create: `docs/evidence/e2_retrieval_summary.json`
- Modify: `multiagent/scripts/eval_retrieval.py`
- Modify: `multiagent/scripts/eval_brand_retrieval.py`
- Create: `multiagent/scripts/export_e2_evidence.py`
- Create: `multiagent/scripts/test_e2_evidence_export.py`
- Create: `multiagent/src/platform/admin/evaluation.py`
- Create: `multiagent/src/platform/admin/templates/evaluation.html`
- Modify: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/scripts/test_admin_evaluation.py`

**Interfaces:**
- Route: `GET /admin/evaluation` viewer+.
- Loader: `load_manifest(path=REPO/docs/evidence/evaluation-manifest.json) -> tuple[ExperimentView, ...]`.

- [ ] **Step 1: Refactor hai phép E2 thành hàm trả dữ liệu**

Giữ output CLI và exit code hiện hành, nhưng thêm:

- `eval_retrieval.evaluate() -> dict`: `query_count`, `recall_at_1`, `recall_at_3`, `threshold=0.9`, `passed`;
- `eval_brand_retrieval.evaluate() -> dict`: `query_count`, `top_k=3`, `same_topic_hits`, `total_chunks`, `same_topic_rate`, `random_baseline`, `ratio_to_baseline`, `threshold_ratio=1.5`, `passed`.

Không đổi pairs, ground truth, chunking, embedding hoặc retrieval. `test_e2_evidence_export.py` monkeypatch retrieval/DB bằng fixture tất định để chứng minh refactor chỉ tách dữ liệu khỏi `print` và schema summary đúng.

- [ ] **Step 2: Export E2 evidence $0 với tên cố định**

`export_e2_evidence.py` gọi hai hàm trên, ghi atomically đúng `docs/evidence/e2_retrieval_summary.json` với schema:

```json
{
  "experiment": "E2",
  "run_at": "UTC ISO-8601",
  "head_commit": "40-char SHA",
  "factcheck": {},
  "brand": {},
  "passed": true
}
```

`passed` tổng chỉ true khi cả hai nhánh true. Script yêu cầu PostgreSQL/KB hiện hành, đặt `HF_HUB_OFFLINE=1`, không import `ai_core` và không gọi LLM. Ghi temp cùng thư mục rồi `os.replace`; failure không để file JSON nửa chừng.

```powershell
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\test_e2_evidence_export.py
.\.venv\Scripts\python.exe scripts\export_e2_evidence.py
```

- [ ] **Step 3: Tạo manifest đúng trạng thái hiện hành**

Schema mỗi entry: `experiment`, `status` (`valid|pending|historical_invalid`), `score_path_snapshot`, `head_commit`, `prompt_version`, `model`, `run_at`, `evidence_path`, `metadata_complete`, `summary`. Field provenance không có trong evidence cũ phải để `null` và `metadata_complete=false`, không suy từ file hiện hành.

E1/E3/E6 pending và có `evidence_path=null`, `run_at=null`. E2 trỏ chính xác `docs/evidence/e2_retrieval_summary.json`. E4 trỏ `docs/evidence/e1_e4_report.txt`; do evidence E4 cũ không nhúng commit/prompt exact, các field đó để null và page cảnh báo provenance chưa đầy đủ dù phép đo chi phí vẫn được evaluation plan công nhận. E5 trỏ `docs/evidence/e5_sau_sua_cp3_cp4.json`, prompt `0bdc5ab12ec65f89`, model `claude-haiku-4-5-20251001`, status historical invalid và summary nói rõ không phải code hiện hành. Không tự chạy E1/E5.

- [ ] **Step 4: RED loader security**

Reject duplicate experiment, unknown status, non-E1..E6, evidence path tuyệt đối/`..`/ngoài `docs/evidence`, missing file cho valid/invalid status. Pending bắt evidence/run_at null. `metadata_complete=true` bắt buộc mọi provenance field non-null; false phải hiển thị warning. Manifest không được tham chiếu `.env`.

- [ ] **Step 5: Implement page**

Hiển thị badge trạng thái, snapshot/prompt/model/run/evidence link. Historical invalid có cảnh báo rõ “không phải kết quả code hiện hành”. Không có form/button chạy test, không import eval scripts vào web process.

- [ ] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_evaluation.py
.\.venv\Scripts\python.exe scripts\test_e2_evidence_export.py
git -C .. add docs/evidence/evaluation-manifest.json docs/evidence/e2_retrieval_summary.json multiagent/scripts/eval_retrieval.py multiagent/scripts/eval_brand_retrieval.py multiagent/scripts/export_e2_evidence.py multiagent/scripts/test_e2_evidence_export.py multiagent/src/platform/admin/evaluation.py multiagent/src/platform/admin/templates/evaluation.html multiagent/src/platform/admin/router.py multiagent/scripts/test_admin_evaluation.py
git commit -m "feat: show versioned evaluation evidence read-only"
```

---

### Task 9: Audit log page

**Files:**
- Create: `multiagent/src/platform/admin/templates/audit.html`
- Modify: `multiagent/src/platform/admin/queries.py`
- Modify: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/scripts/test_admin_audit_page.py`

**Interfaces:**
- Route: `GET /admin/audit` admin-only.

- [ ] **Step 1: RED permissions/redaction/pagination**

Viewer/operator 403. Admin filter action/outcome/actor/date. Metadata output never contains keys/values matching secret patterns; malformed legacy metadata rendered as `[đã ẩn]`.

- [ ] **Step 2: Implement query/template**

Show actor snapshot, action, target, outcome, safe metadata, timestamp. No delete/export endpoint in MVP.

- [ ] **Step 3: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_audit_page.py
git -C .. add multiagent/src/platform/admin multiagent/scripts/test_admin_audit_page.py
git commit -m "feat: add admin-only operational audit page"
```

---

### Task 10: Admin operations checkpoint

**Files:**
- Create: `docs/evidence/platform-admin-operations-verification.txt`
- Modify: `docs/technical-debt.md`

**Interfaces:**
- Produces evidence cho cutover API/connector.

- [ ] **Step 1: Chạy mọi admin test + full offline suite**

Chạy `test_admin_*.py`, meta-test, full `test_*.py`; ghi pass/skip/fail thật.

- [ ] **Step 2: Browser/manual accessibility smoke**

Khởi động service local, kiểm login/dashboard/jobs/reviews/users/config/eval/audit ở 1280px và 360px; tab keyboard, focus visible, error alert, viewer/operator/admin. Không bấm retry trên job thật nếu chưa muốn phát sinh LLM; dùng seeded test row.

- [ ] **Step 3: Security/source assertions**

Search HTML/log response không có `ANTHROPIC_API_KEY`, Authorization, password/token hash, `.env`, raw cookie. POST config/eval trả 405.

- [ ] **Step 4: Score freeze và evidence commit**

Chạy parent score gate, `git diff --check`, ghi commit/assets hash/pricing source/evidence.

```powershell
git -C .. add docs/evidence/platform-admin-operations-verification.txt docs/technical-debt.md
git commit -m "docs: record admin operations verification"
```
