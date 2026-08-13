# Platform Admin Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến admin shell thành giao diện vận hành đọc dữ liệu thật: dashboard, jobs, review history, users, config/KB/evaluation và audit, với action đúng role và có cảnh báo chi phí.

**Architecture:** Query/read-model được tách khỏi route và template; route được chia theo màn hình thay vì tiếp tục phình `admin/router.py` đang chứa auth. Mọi list dùng pagination ổn định. Jinja render full page, HTMX chỉ thay fragment cho filter/action nhỏ và có standard-form fallback; không có frontend build chain hoặc SPA.

**Tech Stack:** FastAPI, Jinja2, HTMX 2.0.10 vendored, psycopg 3, YAML/JSON read-only, CSS thuần.

**Depends on:** Foundation và Admin Auth đã qua checkpoint.

**Quy ước chạy lệnh:** Mỗi code block PowerShell chạy tại `D:\drupal-multiagent-seo\.worktrees\platform-admin-operations\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

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
- P3 không tạo migration/schema mới; migration `0004` được giữ cho P4 API/connector. Trước khi cột bền vững tồn tại, P3 đọc marker tương thích `run_log.config_meta.is_fixture`; P4 chuyển query sang cột `run_log.is_fixture`, P5 chuyển cost sang `llm_usage_event.is_fixture`.
- Dashboard/cost/decision mặc định loại đúng các run có `config_meta.is_fixture=true`; review history vẫn cho điều tra nhưng detail phải cảnh báo rõ đây là fixture, không phải kết quả AI thật.
- Mọi state change của admin và audit tương ứng phải commit/rollback trong cùng transaction PostgreSQL.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/src/review_platform/admin/rendering.py` | Jinja environment và đường dẫn template/static dùng chung, tránh circular import |
| `multiagent/src/review_platform/admin/*_routes.py` | Route theo màn hình: dashboard, jobs, reviews, users, read-only, audit |
| `multiagent/src/review_platform/admin/queries.py` | Dashboard/jobs/runs/audit read models |
| `multiagent/src/review_platform/admin/sanitization.py` | Làm sạch error/audit/legacy text trước khi render |
| `multiagent/src/review_platform/admin/evaluation.py` | Load/validate evidence manifest allowlist |
| `multiagent/src/review_platform/reviews.py` | Retry service + transaction/audit |
| `multiagent/src/review_platform/pricing.py` | Token → estimated USD từ config versioned |
| `multiagent/config/model_pricing.yaml` | Giá model + effective date + official source |
| `docs/evidence/evaluation-manifest.json` | Trạng thái E1–E6 machine-readable |
| `multiagent/src/review_platform/admin/templates/*.html` | Dashboard/list/detail/users/read-only pages |
| `multiagent/src/review_platform/admin/static/vendor/htmx-2.0.10.min.js` | HTMX vendored, không CDN runtime |
| `multiagent/src/review_platform/admin/static/admin.css` | Layout/table/badge/form responsive |

`multiagent/src/review_platform/admin/router.py` tiếp tục sở hữu login/logout/change-password và `forbidden_response`; cuối file include các child router. Child router chỉ import `dependencies` + `rendering`, không import parent router, để không có vòng import.

---

### Task 1: Chốt UI shell và vendor HTMX

**Files:**
- Create: `multiagent/src/review_platform/admin/static/vendor/htmx-2.0.10.min.js`
- Create: `multiagent/src/review_platform/admin/rendering.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Modify: `multiagent/src/review_platform/admin/static/admin.css`
- Create: `multiagent/scripts/test_admin_assets.py`

**Interfaces:**
- Produces: local static asset `/admin/static/vendor/htmx-2.0.10.min.js`.
- Produces: `render_template(request, name, *, status_code=200, **context)` và các hằng đường dẫn dùng chung.
- Produces: base layout có nav theo role, flash/error region, responsive main.

- [ ] **Step 1: Dùng frontend skill để tạo concept và khóa tokens**

Không sửa route/data ở bước này. Concept phải giữ: tiếng Việt, desktop-first nhưng dùng được 360px, high contrast, không gradient trang trí, không “AI neon”. Chốt CSS custom properties cho màu nền/card/text/muted/border/success/warning/danger, spacing, radius và max content width.

- [ ] **Step 2: Tải đúng HTMX và kiểm integrity trước khi add**

```powershell
$target = 'src/review_platform/admin/static/vendor/htmx-2.0.10.min.js'
New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
Invoke-WebRequest 'https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js' -OutFile $target
$bytes = [IO.File]::ReadAllBytes((Resolve-Path $target))
$sha = [Convert]::ToBase64String([Security.Cryptography.SHA384]::HashData($bytes))
if ($sha -ne 'H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V') { throw "HTMX integrity mismatch: $sha" }
```

Lệnh tải cần phê duyệt mạng khi execution. Runtime không gọi CDN vì file được commit.

- [ ] **Step 3: RED asset/template test**

Test base HTML chỉ tham chiếu path local, không chứa `http://`/`https://` script; mọi nav item đã hiển thị phải có route thật, active marker và role condition. Test CSS có `:focus-visible`, media query ≤700px và `.sr-only`. Test `rendering.py` giữ Jinja autoescape cho HTML/XML. Test auth route cũ vẫn import/re-export được `STATIC_DIR` để không phá app/test hiện có.

- [ ] **Step 4: Implement base shell**

Tách Jinja setup/`TEMPLATE_DIR`/`STATIC_DIR` khỏi `router.py` sang `rendering.py`; parent router dùng helper mới nhưng vẫn re-export `STATIC_DIR`. Ở commit độc lập này nav chỉ hiển thị các route đã tồn tại: Tổng quan và Đổi mật khẩu. Header hiển thị username/role và form logout POST có CSRF. Mỗi task sau chỉ thêm nav item trong cùng commit tạo route tương ứng, nên không có giai đoạn link 404. Không render nav operation nếu role thiếu, nhưng server gate vẫn là nguồn quyền.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_assets.py
git -C .. add multiagent/src/review_platform/admin/rendering.py multiagent/src/review_platform/admin/router.py multiagent/src/review_platform/admin/static multiagent/src/review_platform/admin/templates/base.html multiagent/scripts/test_admin_assets.py
git commit -m "feat: add accessible admin UI shell"
```

---

### Task 2: Pricing versioned và dashboard query

**Files:**
- Create: `multiagent/config/model_pricing.yaml`
- Create: `multiagent/src/review_platform/pricing.py`
- Create: `multiagent/src/review_platform/admin/queries.py`
- Create: `multiagent/scripts/test_admin_dashboard.py`

**Interfaces:**
- Produces dataclass: `PageView(items: tuple, page: int, page_size: int, total: int, total_pages: int)`; các list read-model dùng chung kiểu này.
- Produces: `estimate_usage(usage: list[dict], pricing_path: Path) -> CostEstimate`.
- Produces: `dashboard(conn, *, date_from: date, date_to: date, include_fixtures: bool = False) -> DashboardView`.

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
`effective_at=2025-10-15` và mức `$1/M input`, `$5/M output` được khóa theo trang chính thức Anthropic; test config bắt URL HTTPS + effective date, không chỉ kiểm con số.

- [ ] **Step 2: RED pricing**

Test 1.000.000 input + 1.000.000 output = 6 USD; nhiều call được sum; unknown model trả `estimated_usd=None` + list unknown, không tính 0 giả; negative/missing token bị validation error.

- [ ] **Step 3: Implement pricing immutable Decimal**

Dùng `Decimal`, không float cho USD. `CostEstimate` gồm input_tokens, output_tokens, estimated_usd, pricing_version/effective_at, unknown_models. UI luôn thêm chữ “ước tính”.

- [ ] **Step 4: RED dashboard SQL**

Seed run ở trong/ngoài date range, đủ decision, NULL score, usage unknown model và một run có `config_meta={"is_fixture": true}`. Assert:

- queue counts theo status;
- total reviews;
- decision distribution;
- p50/p95 duration bằng `percentile_cont`;
- token/cost chỉ từ rows trong range;
- mặc định fixture không đi vào total/decision/duration/token/cost; `include_fixtures=True` chỉ dùng cho test/read-model nội bộ và phải cộng lại đúng;
- write-back outcome distribution tách `succeeded|failed|superseded`; success rate chỉ lấy mẫu số `succeeded+failed`, còn `unknown|pending|superseded` bị loại khỏi rate. Legacy `unknown` không được trình bày là thành công;
- health không tự bịa worker/connector ở phase này: status `unknown` đến Plan 4–5.

- [ ] **Step 5: Implement dashboard read model**

Date range là `[from 00:00 UTC, to+1 day 00:00 UTC)`. Tối đa 93 ngày/request. Điều kiện loại fixture dùng phép so sánh an toàn trên JSON text (`lower(coalesce(config_meta->>'is_fixture','false')) <> 'true'`), không cast boolean để row legacy malformed không làm hỏng dashboard. Query aggregate SQL, không load toàn `agent_results`. Giá ở P3 mới tính từ aggregate `run_log.usage` và UI ghi rõ đây là usage của run đã lưu; P5 chuyển nguồn metric sang `llm_usage_event` để bao gồm attempt lỗi và chống cộng trùng. Với quy mô hiện tại có thể query `jsonb_array_elements(usage)`.

- [ ] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_dashboard.py
git -C .. add multiagent/config/model_pricing.yaml multiagent/src/review_platform/pricing.py multiagent/src/review_platform/admin/queries.py multiagent/scripts/test_admin_dashboard.py
git commit -m "feat: add traceable dashboard metrics and cost estimates"
```

---

### Task 3: Dashboard route/template

**Files:**
- Create: `multiagent/src/review_platform/admin/dashboard_routes.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/home.html`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Create: `multiagent/src/review_platform/admin/templates/partials/dashboard_metrics.html`
- Modify: `multiagent/scripts/test_admin_routes.py`

**Interfaces:**
- Route: `GET /admin?from=YYYY-MM-DD&to=YYYY-MM-DD` viewer+.
- Fragment: cùng route trả partial khi header `HX-Request: true`.

- [ ] **Step 1: RED render/no-data/invalid-range**

Test viewer 200; unauth redirect; invalid/missing-bound date trả trang HTML 422 có error (không rơi ra JSON validation mặc định); range >93 ngày bị từ chối; no-data không chứa `0 ms`/`$0` gây hiểu lầm mà có “Chưa có dữ liệu”. HTMX response không chứa full `<html>`. Fixture-only range cũng phải hiện no-data ở metric chấm.

- [ ] **Step 2: Implement route**

`dashboard_routes.py` parse hai query string cùng nhau rồi gọi read-model; default 7 ngày gần nhất UTC. Template cards: API status từ chính request hiện hành, DB status từ query thành công, worker/connector `Chưa xác minh`; queue; total; decision; tokens; estimated USD; p50/p95. Mỗi metric có `title`/caption nguồn dữ liệu và ghi fixture bị loại mặc định. Thêm nav “Tổng quan” active vào `base.html`; parent `router.py` include child router sau khi định nghĩa xong auth routes.

- [ ] **Step 3: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_routes.py
git -C .. add multiagent/src/review_platform/admin/dashboard_routes.py multiagent/src/review_platform/admin/router.py multiagent/src/review_platform/admin/templates multiagent/scripts/test_admin_routes.py
git commit -m "feat: render operational dashboard from run data"
```

---

### Task 4: Jobs list/detail và retry service

**Files:**
- Create: `multiagent/src/review_platform/reviews.py`
- Create: `multiagent/src/review_platform/admin/job_routes.py`
- Create: `multiagent/src/review_platform/admin/sanitization.py`
- Create: `multiagent/src/review_platform/admin/templates/jobs.html`
- Create: `multiagent/src/review_platform/admin/templates/job_detail.html`
- Create: `multiagent/src/review_platform/admin/templates/partials/jobs_table.html`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Modify: `multiagent/src/review_platform/auth/audit_log.py`
- Create: `multiagent/scripts/test_admin_jobs.py`

**Interfaces:**
- Query: `list_jobs(conn, filters: JobFilters, page: int, page_size: int) -> PageView`.
- Query: `get_job(conn, public_id: UUID) -> JobDetail | None`.
- Service: `retry_failed(conn, *, job_public_id: UUID, actor: AdminUser, reason: str | None) -> RetryResult`.
- Routes: `GET /admin/jobs`, `GET /admin/jobs/{public_id}`, `POST /admin/jobs/{public_id}/retry`.

- [ ] **Step 1: RED filter/sort/site isolation**

Allow status exact queue states, site UUID/slug exact, source, external ID substring tối đa 100 chars, date range. Page là số nguyên ≥1, page size mặc định 25/tối đa 100; sort cố định `created_at DESC, id DESC`. Invalid filter trả HTML 422. Query uses parameter binding. Detail returns run linkage và `last_error` đã làm sạch, không bao giờ render raw traceback/Authorization/cookie/token.

`sanitization.py` cung cấp `sanitize_text(value, max_length=1000)` và `sanitize_mapping(value, *, max_depth=3, max_items=50)`: key được casefold/bỏ dấu phân cách trước khi dò `password|token|authorization|cookie|secret|apikey`, rồi thay value bằng `[đã ẩn]`; chuỗi che `Bearer ...` và các cặp header/key nhạy cảm trước khi truncate. Dữ liệu sai kiểu không gây 500. Test cả secret ở key, ở scalar string và legacy nested metadata.

- [ ] **Step 2: RED retry permissions/state/cost audit**

Viewer POST → 403; operator without CSRF → 403; thiếu `confirm_cost=yes` → 400; retry non-failed → 409; failed → new queued job linked `supersedes_job_id`. `saved_result_available=true` chỉ khi failed job có run `writeback_status='failed'`; lỗi connector/engine chưa có reusable run phải false. Response/audit ghi bool, new job public ID và reason đã làm sạch/tối đa 500 ký tự, không chứa payload.

Thêm `AuditAction.JOB_RETRIED = "job_retried"` với allowlist đúng ba key `saved_result_available`, `new_job_public_id`, `reason`. Test audit insert fail làm rollback job mới; không được trả thành công khi chỉ enqueue hoặc chỉ audit đã commit.

- [ ] **Step 3: Implement retry transaction**

Trong một outer `conn.transaction()`: lock failed job theo `public_id`, đọc site/profile đúng `site_id`/`profile_id` snapshot và xác nhận `policy_version`, content type, language khớp job; reject nếu site inactive hoặc snapshot không còn hợp lệ. Query reusable run của chính failed job để quyết warning, rồi call `enqueue_scoped(... force=True, supersedes_job_id=failed_job.id)` với source `admin_retry`; sau đó ghi `JOB_RETRIED` trong cùng transaction. Worker vẫn kiểm lại eligibility trước reuse; web request không import/gọi engine hay LLM.

- [ ] **Step 4: Implement UI**

`job_routes.py` sở hữu ba route và được parent include. List columns: time, site, external ID, status, attempts, source, policy. Detail: correlation, revision, error đã làm sạch, run link, write-back status. Filter form chạy được như GET chuẩn; khi có `HX-Request: true` chỉ trả `partials/jobs_table.html`. Retry form chỉ operator/admin thấy, có checkbox xác nhận câu chi phí và CSRF; server bắt `confirm_cost=yes`, không chỉ JavaScript confirm. Thêm nav “Jobs” trong cùng commit; POST success redirect 303 về detail job mới để refresh không retry lần hai.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_jobs.py
.\.venv\Scripts\python.exe scripts\test_admin_routes.py
git -C .. add multiagent/src/review_platform/reviews.py multiagent/src/review_platform/auth/audit_log.py multiagent/src/review_platform/admin multiagent/scripts/test_admin_jobs.py
git commit -m "feat: add admin job inspection and audited retry"
```

---

### Task 5: Review history list/detail

**Files:**
- Create: `multiagent/src/review_platform/admin/review_routes.py`
- Create: `multiagent/src/review_platform/admin/templates/reviews.html`
- Create: `multiagent/src/review_platform/admin/templates/review_detail.html`
- Create: `multiagent/src/review_platform/admin/templates/partials/reviews_table.html`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Create: `multiagent/scripts/test_admin_reviews.py`

**Interfaces:**
- Query: `list_reviews(conn, filters: ReviewFilters, page: int, page_size: int) -> PageView`.
- Query: `get_review(conn, public_id: UUID) -> ReviewDetail | None`.
- Routes: `GET /admin/reviews`, `GET /admin/reviews/{public_id}` viewer+.

- [ ] **Step 1: RED read model**

Assert list lọc decision/site/external ID/date, pagination ổn định 25/100 và viewer+ access. Detail có agent scores/criteria/issues/evidence/veto/missing/model/config meta/profile/policy/token/cost/duration/write-back/link Drupal. `writeback_status='unknown'` và missing/legacy fields render `Không có dữ liệu`, không KeyError; không dùng badge thành công cho `unknown`. Run có `config_meta.is_fixture=true` vẫn tra cứu được nhưng phải có cảnh báo nổi bật “Dữ liệu fixture — không phải kết quả AI thật”.

- [ ] **Step 2: Implement safe normalization**

`normalize_agent_results(jsonb)` chỉ chấp nhận dict/list/scalar và giới hạn hiển thị: max 4 agents, max 50 criteria/issues mỗi agent, mỗi text 2000 chars qua helper sanitization. Không mutate DB. Drupal URL được dựng từ origin đã validate của `site.base_url` + `/node/<external>` chỉ khi external ID chỉ gồm chữ số; template không nhận URL tùy ý từ JSON. Với UUID, context phải lưu `source_url` ở P4; trước đó hiển thị external ID không link.

- [ ] **Step 3: Implement UI + GREEN**

`review_routes.py` sở hữu hai GET route và được parent include. Filter form chạy được như GET chuẩn; HTMX chỉ thay `partials/reviews_table.html`. Table/filter và accordion `<details>` semantic; không render raw HTML evidence. Token/cost có pricing version/effective date và nhãn “ước tính”. Thêm nav “Lịch sử chấm” trong cùng commit.

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_reviews.py
git -C .. add multiagent/src/review_platform/admin multiagent/scripts/test_admin_reviews.py
git commit -m "feat: add explainable review history pages"
```

---

### Task 6: User management UI đúng last-admin invariant

**Files:**
- Create: `multiagent/src/review_platform/admin/user_routes.py`
- Create: `multiagent/src/review_platform/admin/templates/users.html`
- Create: `multiagent/src/review_platform/admin/templates/user_form.html`
- Create: `multiagent/src/review_platform/admin/templates/user_temporary_password.html`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Create: `multiagent/scripts/test_admin_user_routes.py`

**Interfaces:**
- Query: `list_users(conn, *, page: int, page_size: int) -> PageView`, sort `created_at DESC, id DESC`.
- Routes admin-only: `GET /admin/users`, `GET /admin/users/new`, `POST /admin/users`, `POST /admin/users/{id}/role`, `/lock`, `/unlock`, `/reset-password`.

- [ ] **Step 1: RED role/server enforcement**

Viewer/operator GET/POST users → 403. Admin create normalizes username, role allowlist. Invalid UUID/user/role có response HTML an toàn. Reset/create trả temporary password chỉ trong response POST thành công; subsequent GET/list/detail không có field để hiện lại. Last active admin không thể bị lock/hạ role, kể cả hai request đồng thời.

- [ ] **Step 2: Implement forms**

`user_routes.py` sở hữu routes và được parent include. Tất cả POST có CSRF. Create/reset generate temporary password bằng `secrets.token_urlsafe(18)`, set must-change. POST success render `user_temporary_password.html` trực tiếp với header `Cache-Control: no-store, private` và `Pragma: no-cache`; page nói rõ phải truyền password qua kênh an toàn. Không lưu temporary password vào cookie/session/audit/log và không gửi email. Thêm nav “Người dùng” chỉ cho admin trong cùng commit.

- [ ] **Step 3: Audit và GREEN**

Mỗi create/role/lock/unlock/reset bọc repository call + `audit_log.write_event()` trong cùng outer transaction; audit failure phải rollback thay đổi user/session. Nếu repository từ chối last-admin và rollback, mở transaction mới chỉ để ghi `LAST_ADMIN_DENIED`, rồi trả 409. Assert audit action/outcome/old-new role; no temp password in audit/log/HTML ngoài đúng response POST đầu tiên.

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_user_routes.py
git -C .. add multiagent/src/review_platform/admin multiagent/scripts/test_admin_user_routes.py
git commit -m "feat: add guarded admin user management"
```

---

### Task 7: Config và KB read-only

**Files:**
- Create: `multiagent/src/review_platform/admin/read_only_sources.py`
- Create: `multiagent/src/review_platform/admin/read_only_routes.py`
- Create: `multiagent/src/review_platform/admin/templates/config_kb.html`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Create: `multiagent/scripts/test_admin_read_only.py`

**Interfaces:**
- Route: `GET /admin/config-kb` viewer+.
- No POST/PUT/PATCH/DELETE route under this path.

- [ ] **Step 1: RED allowlist/path traversal**

Loader API không nhận path từ route. `REPO_ROOT` được suy từ `Path(__file__).resolve()`, rồi compile-time allowlist chỉ gồm `config/scoring.yaml`, `src/agents/compliance_rules.json`, `src/agents/brand_rules.json`, `src/kb/specs.json`; resolve mỗi file phải còn trong repository. KB DB query chỉ aggregate collection/content_type/langcode/count + metadata excerpt đã sanitize tối đa 500 chars, không select/render cột `document` hoặc vector. Request `?path=../../.env` không ảnh hưởng output và không mở file.

- [ ] **Step 2: Implement read-only snapshot**

Parse YAML bằng `yaml.safe_load` và JSON phòng thủ, trả file SHA-256, modified timestamp UTC và metadata allowlist cần hiển thị; không đưa full prompt/rule corpus. KB show collection counts, embedding dimension/model từ metadata nếu có; nếu thiếu ghi “Chưa version hóa”, không bịa. `read_only_routes.py` sở hữu GET route, parent include và base thêm nav “Cấu hình & KB”.

- [ ] **Step 3: Route method regression**

Assert GET 200; POST 405; HTML không có `Save`, textarea editable, secret ref value hoặc full environment.

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_read_only.py
git -C .. add multiagent/src/review_platform/admin/read_only_sources.py multiagent/src/review_platform/admin/read_only_routes.py multiagent/src/review_platform/admin/templates/config_kb.html multiagent/src/review_platform/admin/templates/base.html multiagent/src/review_platform/admin/router.py multiagent/scripts/test_admin_read_only.py
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
- Create: `multiagent/src/review_platform/admin/evaluation.py`
- Create: `multiagent/src/review_platform/admin/evaluation_routes.py`
- Create: `multiagent/src/review_platform/admin/templates/evaluation.html`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Create: `multiagent/scripts/test_admin_evaluation.py`

**Interfaces:**
- Route: `GET /admin/evaluation` viewer+.
- Route: `GET /admin/evaluation/evidence/{experiment}` viewer+, chỉ map E1–E6 qua manifest; không nhận file path.
- Loader: `load_manifest(path=REPO/docs/evidence/evaluation-manifest.json) -> tuple[ExperimentView, ...]`.

- [ ] **Step 1: RED rồi refactor hai phép E2 thành hàm trả dữ liệu**

Viết test fixture trước, chạy để thấy fail vì chưa có `evaluate()`/export schema, sau đó mới thêm implementation:

Giữ output CLI và exit code hiện hành, nhưng thêm:

- `eval_retrieval.evaluate() -> dict`: `query_count`, `recall_at_1`, `recall_at_3`, `threshold=0.9`, `passed`;
- `eval_brand_retrieval.evaluate() -> dict`: `query_count`, `top_k=3`, `same_topic_hits`, `total_chunks`, `same_topic_rate`, `random_baseline`, `ratio_to_baseline`, `threshold_ratio=1.5`, `passed`.

Không đổi pairs, ground truth, chunking, embedding hoặc retrieval. `test_e2_evidence_export.py` monkeypatch retrieval/DB bằng fixture tất định để chứng minh refactor chỉ tách dữ liệu khỏi `print` và schema summary đúng.

- [ ] **Step 2: GREEN refactor rồi commit code trước khi đo**

```powershell
.\.venv\Scripts\python.exe scripts\test_e2_evidence_export.py
git -C .. add multiagent/scripts/eval_retrieval.py multiagent/scripts/eval_brand_retrieval.py multiagent/scripts/export_e2_evidence.py multiagent/scripts/test_e2_evidence_export.py
git commit -m "refactor: make E2 evidence exportable"
```

Phải có commit này trước khi export để `head_commit` trong evidence thật sự chứa code vừa đo; không ghi SHA của commit cũ khi refactor còn uncommitted.

- [ ] **Step 3: Export E2 evidence $0 với tên cố định**

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

Sau export, test xác nhận `head_commit` đúng `git rev-parse HEAD`, file UTF-8/JSON hợp lệ và không có dữ liệu secret. Tuyệt đối không chạy E1/E5/E3/E6 trong task này.

- [ ] **Step 4: Tạo manifest đúng trạng thái hiện hành**

Schema mỗi entry: `experiment`, `status` (`valid|pending|historical_invalid`), `score_path_snapshot`, `head_commit`, `prompt_version`, `model`, `run_at`, `evidence_path`, `metadata_complete`, `summary`. Field provenance không có trong evidence cũ phải để `null` và `metadata_complete=false`, không suy từ file hiện hành.

E1/E3/E6 pending và có `evidence_path=null`, `run_at=null`. E2 trỏ chính xác `docs/evidence/e2_retrieval_summary.json`. E4 trỏ `docs/evidence/e1_e4_report.txt`; do evidence E4 cũ không nhúng commit/prompt exact, các field đó để null và page cảnh báo provenance chưa đầy đủ dù phép đo chi phí vẫn được evaluation plan công nhận. E5 trỏ `docs/evidence/e5_sau_sua_cp3_cp4.json`, prompt `0bdc5ab12ec65f89`, model `claude-haiku-4-5-20251001`, status historical invalid và summary nói rõ không phải code hiện hành. Không tự chạy E1/E5.

- [ ] **Step 5: RED loader security**

Reject duplicate experiment, unknown status, non-E1..E6, evidence path tuyệt đối/`..`/ngoài `docs/evidence`, missing file cho valid/invalid status. Pending bắt evidence/run_at null. `metadata_complete=true` bắt buộc mọi provenance field non-null; false phải hiển thị warning. Manifest không được tham chiếu `.env`. Evidence route lấy path từ entry đã validate, E pending/không tồn tại trả 404; response chỉ `text/plain` hoặc `application/json`, có `X-Content-Type-Options: nosniff` và `Cache-Control: no-store`.

- [ ] **Step 6: Implement page**

`evaluation_routes.py` sở hữu hai GET route và được parent include. Hiển thị badge trạng thái, snapshot/prompt/model/run/evidence link qua route allowlist. Historical invalid có cảnh báo rõ “không phải kết quả code hiện hành”. Không có form/button chạy test, không import eval scripts vào web process. Thêm nav “Đánh giá” trong cùng commit.

- [ ] **Step 7: GREEN + commit evidence/page**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_evaluation.py
.\.venv\Scripts\python.exe scripts\test_e2_evidence_export.py
git -C .. add docs/evidence/evaluation-manifest.json docs/evidence/e2_retrieval_summary.json multiagent/src/review_platform/admin/evaluation.py multiagent/src/review_platform/admin/evaluation_routes.py multiagent/src/review_platform/admin/templates/evaluation.html multiagent/src/review_platform/admin/templates/base.html multiagent/src/review_platform/admin/router.py multiagent/scripts/test_admin_evaluation.py
git commit -m "feat: show versioned evaluation evidence read-only"
```

---

### Task 9: Audit log page

**Files:**
- Create: `multiagent/src/review_platform/admin/audit_routes.py`
- Create: `multiagent/src/review_platform/admin/templates/audit.html`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/templates/base.html`
- Create: `multiagent/scripts/test_admin_audit_page.py`

**Interfaces:**
- Query: `list_audit_events(conn, filters: AuditFilters, page: int, page_size: int) -> PageView`.
- Route: `GET /admin/audit` admin-only.

- [ ] **Step 1: RED permissions/redaction/pagination**

Viewer/operator 403. Admin filter action từ `AuditAction`, outcome allowlist, actor substring tối đa 100, date; invalid filter trả HTML 422. Pagination 25/tối đa 100, sort `created_at DESC, id DESC`. Metadata output qua `sanitize_mapping`, không chứa keys/values matching secret patterns; malformed legacy metadata rendered as `[đã ẩn]` thay vì gây 500.

- [ ] **Step 2: Implement query/template**

`audit_routes.py` sở hữu GET route, require admin và được parent include. Show actor snapshot, action, target, outcome, safe metadata, timestamp. Thêm nav “Nhật ký” chỉ cho admin. No delete/export endpoint in MVP.

- [ ] **Step 3: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_audit_page.py
git -C .. add multiagent/src/review_platform/admin multiagent/scripts/test_admin_audit_page.py
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

Chạy `test_admin_*.py`, meta-test, rồi mọi `test_*.py`; ghi pass/skip/fail theo file thật, `[SKIP]` không được tính `[PASS]`:

```powershell
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
Get-ChildItem scripts\test_*.py | Sort-Object Name | ForEach-Object {
  & .\.venv\Scripts\python.exe $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "test failed: $($_.Name)" }
}
```

- [ ] **Step 2: Browser/manual accessibility smoke**

Dùng `build-web-apps:frontend-testing-debugging`: kiểm Browser plugin trước; nếu không có thì ghi lý do và dùng Playwright/Edge headless fallback. Khởi động service local, kiểm login/dashboard/jobs/reviews/users/config/eval/audit ở 1280px và 360px; tab keyboard, focus visible, error alert, viewer/operator/admin. Không bấm retry trên job thật; retry seeded failed row và dừng worker để bảo đảm không thể gọi LLM.

- [ ] **Step 3: Security/source assertions**

Search HTML/log response không có `ANTHROPIC_API_KEY`, Authorization, password/token hash, `.env`, raw cookie. POST config/eval trả 405.

- [ ] **Step 4: Score freeze và evidence commit**

Chạy prompt version, score gate đầy đủ dưới đây và `git diff --check`; ghi code HEAD, commit list, HTMX SHA-384, pricing version/effective/source, migration status 0001–0003, fixture assertions và evidence E2. Không chạy E1/E5/E3/E6, không gọi Anthropic.

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'"
git -C .. diff --exit-code 04f10e1 -- multiagent/src/agents multiagent/src/ai_core.py multiagent/src/brand_analysis.py multiagent/src/config.py multiagent/src/embeddings.py multiagent/src/graph.py multiagent/src/retrieval.py multiagent/src/scoring.py multiagent/src/seo_analysis.py multiagent/src/state.py multiagent/src/text_utils.py multiagent/src/kb multiagent/config/scoring.yaml
git -C .. diff --check
```

```powershell
git -C .. add docs/evidence/platform-admin-operations-verification.txt docs/technical-debt.md
git commit -m "docs: record admin operations verification"
```

Chỉ sau khi evidence có PASS thật và code review không còn Critical/Important mới đổi `technical-debt.md` từ “P3 chưa triển khai” thành “P3 đã qua checkpoint”; vẫn phải ghi P4/P5 chưa làm.
