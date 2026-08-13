# Platform Hardening and Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện khả năng quan sát, bảo mật, quyền Drupal, kiểm thử tích hợp, diễn tập backup/rollback và tài liệu vận hành để nền tảng độc lập đủ điều kiện bàn giao MVP.

**Architecture:** Hardening bổ sung ở lớp bao quanh engine: heartbeat trong database, correlation/usage collector theo context của worker, middleware redaction/security và runbook triển khai. Không sửa graph, prompt, agent, rubric hoặc scoring; staging rollout theo thứ tự database → API/admin → worker → Drupal và luôn giữ đường rollback ứng dụng.

**Tech Stack:** FastAPI/Starlette middleware, Python `contextvars`/`logging`, psycopg 3, PostgreSQL, Drupal Drush/PHP, PowerShell runbook.

**Depends on:** Foundation, Admin Auth, Admin Operations và API/Drupal Connector đã qua checkpoint.

**Quy ước chạy lệnh:** Mỗi code block PowerShell bắt đầu với working directory `D:\drupal-multiagent-seo\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

## Global Constraints

- Không chạy E1/E5/E3/E6 và không gọi Anthropic trong plan này. Mọi test engine dùng fake transport/output.
- Score-path diff so với `04f10e1` phải rỗng. Đặc biệt không sửa `ai_core.py`, `graph.py`, `src/agents/`, retrieval, KB, rules hoặc `scoring.yaml`.
- Gắn nhãn usage bằng wrapper cài từ worker vào các binding `call_agent` đã import; không đổi chữ ký/hành vi của agent. Nếu cách này không giữ output regression hoặc không hoạt động với executor thật, dừng và đưa per-agent attribution thành nợ kỹ thuật thay vì sửa score path.
- Correlation ID do API tạo, bất biến qua job/run/write-back. Giá trị client gửi không được dùng làm ID tin cậy.
- Heartbeat quá 30 giây được coi stale; không được suy worker khỏe chỉ vì process/API còn sống.
- Không log body bài, prompt, output đầy đủ, Authorization, cookie, password, token/hash, secret reference value hoặc database URL.
- `/health` public chỉ liveness tối thiểu. Health chi tiết chỉ ở admin đã xác thực.
- Không drop migration/table/cột khi rollback. Restore rehearsal dùng database/schema test, không đè database dev/production.
- Evidence chỉ ghi ID/hash/count/status/timestamp/safe error; không chép nội dung bài hoặc secret.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/migrations/0004_platform_observability.sql` | Worker heartbeat, durable LLM usage event và index/constraint hardening |
| `multiagent/src/review_platform/worker_health.py` | Upsert/delete/read heartbeat |
| `multiagent/src/review_platform/usage.py` | Context attribution, per-call/per-agent token summary |
| `multiagent/src/review_platform/logging.py` | Structured event + recursive redaction |
| `multiagent/src/review_platform/security.py` | Request ID, headers, safe exception response |
| `drupal/scripts/configure_ai_roles.php` | Idempotent Drupal roles/permissions MVP |
| `multiagent/scripts/test_platform_end_to_end.py` | API → queue → fake engine → run → one write-back |
| `docs/operations.md` | Deploy, rotate, recover, backup và incident response |
| `docs/evidence/platform-mvp-acceptance.md` | Ma trận 11 tiêu chí và bằng chứng |

---

### Task 1: Migration 0004, durable LLM usage event và worker heartbeat

**Files:**
- Create: `multiagent/migrations/0004_platform_observability.sql`
- Create: `multiagent/src/review_platform/worker_health.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/templates/home.html`
- Modify: `multiagent/scripts/test_migrations.py`
- Create: `multiagent/scripts/test_worker_heartbeat.py`
- Modify: `multiagent/scripts/test_admin_dashboard.py`

**Interfaces:**
- `Heartbeat(instance_id, started_at, last_seen_at, version, current_job_id)`.
- `beat(conn, *, instance_id, started_at, version, current_job_id) -> None`.
- `list_worker_health(conn, *, now, stale_after=timedelta(seconds=30)) -> WorkerHealthView`.

- [ ] **Step 1: RED schema/migration**

Assert migration creates:

```sql
CREATE TABLE worker_heartbeat (
  instance_id text PRIMARY KEY,
  started_at timestamptz NOT NULL,
  last_seen_at timestamptz NOT NULL,
  version text NOT NULL,
  current_job_id uuid REFERENCES review_job(public_id) ON DELETE SET NULL,
  CONSTRAINT worker_heartbeat_instance_len CHECK (char_length(instance_id) BETWEEN 1 AND 128),
  CONSTRAINT worker_heartbeat_version_len CHECK (char_length(version) BETWEEN 1 AND 128)
);
CREATE INDEX worker_heartbeat_last_seen_idx ON worker_heartbeat (last_seen_at);

CREATE TABLE llm_usage_event (
  id bigserial PRIMARY KEY,
  job_id bigint NOT NULL REFERENCES review_job(id),
  attempt smallint NOT NULL,
  sequence_no smallint NOT NULL,
  correlation_id uuid NOT NULL,
  agent text NOT NULL,
  phase text NOT NULL,
  model text NOT NULL,
  input_tokens integer NOT NULL CHECK (input_tokens >= 0),
  output_tokens integer NOT NULL CHECK (output_tokens >= 0),
  is_fixture boolean NOT NULL DEFAULT false,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (job_id, attempt, sequence_no)
);
CREATE INDEX llm_usage_event_recorded_at_idx ON llm_usage_event (recorded_at);
```

Upgrade preserves every existing job/run/KB/auth row; second migration run is no-op through `schema_migration`. `llm_usage_event` không có payload/prompt/output text và không FK vào `run_log`, vì engine attempt có thể lỗi trước khi run tồn tại.

- [ ] **Step 2: RED repository/time semantics**

Test new instance = healthy; 31-second-old = stale; no row = unavailable. Upsert never changes `started_at`; current job changes nullable; cleanup only deletes rows older than 7 days. Use injected `now`, not wall clock in assertions.

- [ ] **Step 3: Implement heartbeat loop without blocking claim**

Worker chooses `VF_WORKER_INSTANCE_ID` or default `<hostname>:<pid>`, version from `VF_RELEASE_SHA` or `unknown`. Beat once at start, every 10 seconds while idle and before/after each job. While graph runs, daemon heartbeat thread uses its own short database connection; stop event joins at shutdown. Heartbeat failure logs safe warning and worker continues, but dashboard shows stale—không báo khỏe giả.

- [ ] **Step 4: Dashboard uses real health**

Replace `Chưa xác minh` worker card with `Đang chạy`, `Quá hạn` or `Không có heartbeat`; show last seen/instance count/current job link where allowed. API/DB/connector cards remain governed by their real checks.

- [ ] **Step 5: GREEN + commit**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\test_worker_heartbeat.py
.\.venv\Scripts\python.exe scripts\test_admin_dashboard.py
.\.venv\Scripts\python.exe scripts\migrate.py apply
git add migrations/0004_platform_observability.sql src/review_platform/worker_health.py src/worker.py src/review_platform/admin/queries.py src/review_platform/admin/templates/home.html scripts/test_migrations.py scripts/test_worker_heartbeat.py scripts/test_admin_dashboard.py
git commit -m "feat: report durable worker heartbeats"
```

---

### Task 2: Structured logging, recursive redaction và security middleware

**Files:**
- Create: `multiagent/src/review_platform/logging.py`
- Create: `multiagent/src/review_platform/security.py`
- Modify: `multiagent/src/api.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/connectors/drupal.py`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php`
- Create: `multiagent/scripts/test_platform_logging.py`
- Create: `multiagent/scripts/test_security_middleware.py`
- Modify: `multiagent/scripts/test_drupal_connector.py`
- Modify: `drupal/scripts/test_vf_ai_trigger.php`

**Interfaces:**
- `redact(value: object, *, max_depth=6, max_items=100) -> object`.
- `event(logger, name: str, **safe_fields) -> None` outputs one JSON object/line.
- Middleware: request ID, safe exception response và response security headers.

- [ ] **Step 1: RED recursive redaction**

Cover nested dict/list/tuple, mixed-case keys and string secrets. Keys containing `authorization|cookie|password|passwd|secret|token|api_key|database_url` become `[REDACTED]`; Bearer/basic auth/JWT-like values inside arbitrary messages are masked. Truncate strings to 2000 chars, collections to 100 items/depth 6. Assert original object is not mutated and valid IDs/hash prefixes remain usable.

- [ ] **Step 2: RED HTTP exception boundary/headers**

Unhandled API exception returns JSON `{code:"internal_error", correlation_id}` with 500, never exception/traceback. Admin returns escaped generic error page with same correlation. All admin responses carry:

```text
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

Session cookie remains `Secure`, `HttpOnly`, `SameSite=Lax`. `Strict-Transport-Security` chỉ bật khi `VF_HTTPS_ONLY=1`, tránh nói dối trên local HTTP.

Admin POST body tối đa 65536 byte bằng cùng ASGI streaming limiter pattern của `/api/v1`; cả Content-Length lớn và chunked body vượt ngưỡng đều trả 413 trước form parser. GET không bị buffer toàn response/request.

- [ ] **Step 3: Implement trusted correlation middleware**

Use existing API-generated correlation for `/api/v1/jobs`; other requests get UUIDv4. Ignore inbound `X-Request-ID` completely in MVP. Return trusted `X-Correlation-ID`; bind it to log context and clear in `finally`.

- [ ] **Step 4: Replace raw exception logging at platform boundaries**

API/admin/worker/connector log event name, correlation/job/site/credential prefix, safe error code and exception class—not content or `str(exception)` before redaction. Debug traceback may remain server-side only after recursive redaction filter is installed; production default `INFO`.

Mọi Drupal JSON:API GET/PATCH do connector thực hiện gửi trusted `X-Correlation-ID` của job. `ServiceClient.php` đọc `X-Correlation-ID` và `job_id` từ response enqueue để ghi watchdog metadata an toàn; không ghi request body/token. Khi request chết trước response, Drupal ghi local event ID và `correlation_id=unavailable`, không bịa ID server.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_platform_logging.py
.\.venv\Scripts\python.exe scripts\test_security_middleware.py
.\.venv\Scripts\python.exe scripts\test_api_v1.py
.\.venv\Scripts\python.exe scripts\test_admin_routes.py
.\.venv\Scripts\python.exe scripts\test_drupal_connector.py
Set-Location ..\drupal
ddev exec php scripts/test_vf_ai_trigger.php
Set-Location ..\multiagent
git -C .. add multiagent/src/review_platform/logging.py multiagent/src/review_platform/security.py multiagent/src/api.py multiagent/src/worker.py multiagent/src/review_platform/admin/router.py multiagent/src/review_platform/connectors/drupal.py multiagent/scripts/test_platform_logging.py multiagent/scripts/test_security_middleware.py multiagent/scripts/test_drupal_connector.py drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php drupal/scripts/test_vf_ai_trigger.php
git commit -m "feat: harden platform logs and HTTP responses"
```

---

### Task 3: Per-call/per-agent token, cost và correlation—không chạm score path

**Files:**
- Create: `multiagent/src/review_platform/usage.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/audit.py`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/templates/review_detail.html`
- Create: `multiagent/scripts/test_platform_usage.py`
- Modify: `multiagent/scripts/test_worker_graph_integration.py`
- Modify: `multiagent/scripts/test_admin_reviews.py`

**Interfaces:**
- `install_worker_usage_instrumentation() -> UsageCollector` is idempotent.
- `usage_scope(job_public_id, correlation_id, attempt, is_fixture=False)` context manager; collector chỉ cho một job active vì worker MVP xử lý tuần tự.
- Usage entry exact keys: `agent`, `phase`, `model`, `input_tokens`, `output_tokens`; internal context keys stripped before persistence.
- `record_usage_event(dsn, *, job_id, attempt, sequence_no, correlation_id, is_fixture, entry) -> None`; idempotent theo `(job_id, attempt, sequence_no)` và dùng short-lived connection riêng, không dùng worker connection chung giữa executor threads.
- Parent labels: `content_quality`, `seo`, `brand`, `compliance`; phases `main`, `fact_check_extract`, `fact_check_compare`.

- [ ] **Step 1: RED collector/context isolation**

Create fake module bindings matching current imports. Installation wraps đúng năm module binding, tạo sáu phase label:

```text
agents.content_quality.call_agent → content_quality/main
agents.seo.call_agent             → seo/main
agents.brand_voice.call_agent     → brand/main
agents.compliance.call_agent      → compliance/main
agents.fact_check.call_agent      → compliance/fact_check_extract|fact_check_compare
```

Because both fact-check phases use the same imported function, wrapper derives phase by SHA-256 of the exact `system_prompt` against the two current prompt objects loaded at installation; unknown prompt records `compliance/unknown` and emits warning, never guesses.

`UsageCollector` stores exactly one active job/correlation/attempt under a lock; `begin()` raises nếu một scope khác còn mở. Agent/phase là `ContextVar` được wrapper set/reset ngay trong chính executor thread gọi `ai_core.call_agent`, nên không phụ thuộc parent context có tự truyền qua thread hay không. Test cho nhiều agent thread trong cùng job và hai job tuần tự; entry không được lẫn agent/job/correlation. Mỗi append nhận sequence tăng trong attempt và gọi persistence sink ngay sau khi usage response tồn tại; sink mở connection riêng từ DSN vì worker connection hiện không an toàn để dùng đồng thời giữa thread. Insert lặp cùng key là no-op; lỗi DB làm attempt fail an toàn với safe error `usage_persistence_failed` thay vì mất chi phí im lặng.

- [ ] **Step 2: RED compatibility and output equivalence**

Replace `ai_core.USAGE_LOG` only inside worker with a list-compatible synchronized collector whose `append` enriches current context. Existing `.clear()`, iteration and list conversion still work. Fake `call_agent` return value, exception and argument identity must be unchanged before/after wrapper. `prompt_version()` remains `020738e209017213`; score-path diff remains empty.

- [ ] **Step 3: Implement worker lifecycle**

Install once at worker startup. Before graph invoke, enter single active usage scope with job/correlation/attempt; collector must be empty from lượt trước. Mỗi `append` ghi sanitized event vào `llm_usage_event` ngay, kể cả sau đó agent/graph fail và không có `run_log`. In `finally`, copy entries cho snapshot tương thích của run thành công, close scope và clear collector. `ghi_scoped` có thể giữ snapshot usage nhưng đó không còn là nguồn metric chính; never persist prompt/content/output. Saved-result write-back retry không tạo usage event mới.

- [ ] **Step 4: Admin aggregation/cost**

Dashboard/cost query dùng duy nhất `llm_usage_event WHERE is_fixture=false` cho dữ liệu mới, group token counts/cost by parent `agent`, phase, attempt và job; không cộng thêm `run_log.usage`. Legacy run chưa có event được đọc từ snapshot cũ trong một nhánh fallback có nhãn `legacy`, không union cả hai nguồn cho cùng job. Unknown agent/model remains “Không tính được”, not `$0`. Review detail hiển thị attempt lỗi dù không có run result; fixture detail có banner nhưng không vào production metric.

- [ ] **Step 5: Graph integration regression**

Run real graph topology with fake transport responses; assert labels/counts follow invoked calls, report/decision/write-back payload exactly match baseline fixture, one callback, same correlation in job/run/event/log fields. Thêm case một agent ghi usage rồi graph raise: không có run nhưng event/token/cost vẫn tồn tại đúng một lần; retry attempt mới có attempt number mới. Do not import or edit agent files to make test pass.

- [ ] **Step 6: GREEN + score gate + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_platform_usage.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
.\.venv\Scripts\python.exe scripts\test_admin_reviews.py
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'; print(e.prompt_version())"
git -C .. diff --exit-code 04f10e1 -- multiagent/src/agents multiagent/src/ai_core.py multiagent/src/brand_analysis.py multiagent/src/config.py multiagent/src/embeddings.py multiagent/src/graph.py multiagent/src/retrieval.py multiagent/src/scoring.py multiagent/src/seo_analysis.py multiagent/src/state.py multiagent/src/text_utils.py multiagent/src/kb multiagent/config/scoring.yaml
git -C .. add multiagent/src/review_platform/usage.py multiagent/src/worker.py multiagent/src/audit.py multiagent/src/review_platform/admin/queries.py multiagent/src/review_platform/admin/templates/review_detail.html multiagent/scripts/test_platform_usage.py multiagent/scripts/test_worker_graph_integration.py multiagent/scripts/test_admin_reviews.py
git commit -m "feat: attribute review usage without changing agents"
```

Nếu score diff không rỗng, output không tương đương hoặc attribution test lẫn context, **không commit Task 3**. Ghi rõ thiếu per-agent attribution vào `docs/technical-debt.md`; vẫn có tổng usage hiện hành nhưng chưa được tuyên bố đạt tiêu chí theo agent.

---

### Task 4: Cấu hình role Drupal và xác minh least privilege

**Files:**
- Create: `drupal/scripts/configure_ai_roles.php`
- Create: `drupal/scripts/test_ai_roles.php`
- Read/verify: `drupal/scripts/configure_ai_service_role.php`
- Read/verify: `drupal/scripts/test_ai_service_role.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.permissions.yml`
- Modify: `docs/operations.md`

**Interfaces:**
- Idempotently creates/updates `content_editor`, `site_admin`, `ai_service`.
- Produces a machine-readable permission matrix in test output; never creates a user/password.

- [ ] **Step 1: RED permission matrix**

Assert:

- `content_editor`: create/edit own article, use Needs Review transition, view AI report/status; no force-rescore/administer users/publish bypass.
- `site_admin`: Drupal/module/workflow management + `force ai rescore`; not automatically Administrator role bypass.
- `ai_service` giữ exact allowlist đã được Plan 4 áp dụng: `access content`, `view any unpublished content`, `view latest version`, `view article revisions`, `access vf ai integration feed`, `access vf ai integration capabilities`, `submit vf ai integration result`. Không có `edit any article content`, delete, workflow transition/publish, create content, administer users/site/config. Result callback là ranh giới duy nhất được quyền set bốn AI fields sau compare-and-set. Full role script không được mở rộng allowlist machine so với script Plan 4.

Test fails if `administer nodes`, `bypass node access`, `administer permissions`, `administer users` or delete permissions appear on `ai_service`.

- [ ] **Step 2: Implement idempotent Drush PHP script**

Use Drupal role/entity APIs and permission names that exist in installed modules; fail closed if a required permission/transition is missing. Script đọc biến `$extra` do `drush php:script ... -- --apply` cung cấp; chỉ update sau khi đã in diff và thấy đúng literal `--apply`, còn mặc định là dry-run. It never changes UID 1 or provisions credentials.

- [ ] **Step 3: Document callback privilege boundary**

Operations doc states JSON:API is read-only for `ai_service`; write-back only goes through `/vf-ai/integration/v1/results`. Callback rejects extra fields, checks revision/hash atomically and is idempotent by run ID. Compensating controls remain: dedicated non-publishing account, long random password in secret store, log/audit, no UI login for service account and rotate procedure. Any reintroduction of `edit any article content` fails the least-privilege test and requires a new design review.

- [ ] **Step 4: GREEN on DDEV + commit**

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_roles.php
ddev drush php:script scripts/configure_ai_roles.php -- --apply
ddev exec php scripts/test_ai_roles.php
git -C .. add drupal/scripts/configure_ai_roles.php drupal/scripts/test_ai_roles.php drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.permissions.yml docs/operations.md
git commit -m "feat: codify least-privilege Drupal roles"
```

Run first on local/staging only; production role diff requires site owner approval.

---

### Task 5: Full fake end-to-end, failure matrix và secret/content leak tests

**Files:**
- Create: `multiagent/scripts/test_platform_end_to_end.py`
- Create: `multiagent/scripts/test_platform_failure_matrix.py`
- Create: `multiagent/scripts/test_no_sensitive_persistence.py`
- Modify: `multiagent/scripts/test_moi_test_deu_chay.py`

**Interfaces:**
- One deterministic harness with real API router, PostgreSQL queue/repository, worker orchestration and fake connector/engine.
- Zero network and zero Anthropic calls.

- [ ] **Step 1: RED happy path contract**

With site token and exact revision/fingerprint: POST returns 202 + trusted correlation; duplicate returns same effective job; worker fetches once, invokes fake engine once, writes run once, callback applies once and completes. Assert site/profile/policy/revision/hash version/correlation across job/run/usage event/response. Assert response/admin HTML escapes LLM-like `<script>`.

- [ ] **Step 2: RED failure matrix**

Table-drive these cases with expected state/retry/invoke/callback counts:

| Case | State | Auto retry | Engine | Callback apply |
|---|---|---:|---:|---:|
| Site paused | no new job / queued held | no | 0 | 0 |
| Wrong/revoked token | 401/no job | no | 0 | 0 |
| Profile missing | 422/no job | no | 0 | 0 |
| Revision 404 | failed | no | 0 | 0 |
| Fingerprint mismatch | failed | no | 0 | 0 |
| Connector timeout before engine | queued/backoff | yes ≤3 | 0 | 0 |
| Engine transient error | queued/backoff | yes ≤3 | 1/attempt | 0 |
| Engine records usage then fails | queued/backoff | yes ≤3 | 1/attempt; usage durable | 0 |
| Result callback applied but response lost | queued write-back retry | yes ≤3 | 1 total | 1 total; retry `already_applied` |
| Older revision finishes after newer revision | superseded | no | 1 | 0 |
| Legacy v1 rollback job | done | normal | 1 using v1 hash | 1 |
| Lease crash after run saved, before/during callback | running→queued→done | reclaim | 1 total via pending-run reuse | 1 apply max |
| Lease crash before run saved | running→queued→done | reclaim | controlled per attempt | 1 success |
| Dead-letter manual retry | new linked job | explicit | depends saved result | controlled |

- [ ] **Step 3: RED persistence/log/HTML leak scan**

Use canary strings for title/body/prompt/token/password/cookie/database URL. After all cases, inspect `review_job`, `run_log`, `llm_usage_event`, `admin_audit_log`, captured logs and rendered admin HTML. Full draft/prompt/secrets must be absent; allowed are content hash, safe excerpt/evidence already part of report policy, token prefix and secret **name**. This test must fail if canary appears anywhere outside the in-memory fake connector. Cost assertion sums `llm_usage_event` exactly once, includes failed attempts and does not add duplicate `run_log.usage` snapshots.

- [ ] **Step 4: Trả failure về đúng task sở hữu**

Task này không có production implementation mơ hồ. Nếu harness phát hiện lỗi, không weaken assertion hoặc thêm mock branch; quay lại task sở hữu file (Foundation, API/Connector hoặc Hardening Task 1–3), bổ sung RED case ở đó, sửa đúng file đã liệt kê rồi mới trở lại chạy E2E. `test_moi_test_deu_chay.py` phải xác nhận mọi `test_*` mới được gọi.

- [ ] **Step 5: GREEN + commit**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\test_platform_end_to_end.py
.\.venv\Scripts\python.exe scripts\test_platform_failure_matrix.py
.\.venv\Scripts\python.exe scripts\test_no_sensitive_persistence.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
git add scripts/test_platform_end_to_end.py scripts/test_platform_failure_matrix.py scripts/test_no_sensitive_persistence.py scripts/test_moi_test_deu_chay.py
git commit -m "test: cover platform end-to-end and failure recovery"
```

---

### Task 6: Reproducible offline test runner và CI không dùng secret trả phí

**Files:**
- Create: `multiagent/scripts/test_groups.json`
- Create: `multiagent/scripts/run_test_group.py`
- Create: `.github/workflows/platform-offline-tests.yml`
- Create: `multiagent/scripts/test_test_group_runner.py`

**Interfaces:**
- CLI `run_test_group.py pure|postgres|all-offline`.
- Every `scripts/test_*.py` belongs to exactly one group or explicit `manual_ddev`; no silent omission.

- [ ] **Step 1: RED manifest coverage**

Runner scans `scripts/test_*.py`; fails on duplicate/unlisted/nonexistent entry. `test_moi_test_deu_chay.py` stays in pure. Tests that need Drupal DDEV are documented `manual_ddev`, not reported PASS in CI. Exit nonzero on fail/timeout/skip-unexpected; JSON summary contains command, duration, exit status but no environment dump.

- [ ] **Step 2: Implement sequential runner**

Use `subprocess.run` list arguments, working directory `multiagent`, UTF-8, timeout 300s/test. Set `HF_HUB_OFFLINE=1`; remove `ANTHROPIC_API_KEY` from child env; set `VF_ALLOW_PAID_EVAL=0`. `all-offline` runs pure then PostgreSQL. Do not run scripts named `eval_*`, `smoke_test_*`, `run_all_samples.py` or `seed_*`.

- [ ] **Step 3: CI PostgreSQL/pgvector service**

Workflow triggers `pull_request`/`push` (không dùng `pull_request_target`), sets `permissions: contents: read`, Python 3.12, installs `requirements.txt` + `requirements-dev.txt`, starts `pgvector/pgvector:pg17`, applies migrations, runs `all-offline`. Pin action bằng full SHA:

```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
- uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
  with:
    python-version: "3.12"
    cache: pip
    cache-dependency-path: |
      multiagent/requirements.txt
      multiagent/requirements-dev.txt
```

Secrets are not referenced. A skipped test makes job yellow/fail by explicit runner policy, not green giả. Image pgvector vẫn theo tag hiện hành của `docker-compose.yml`; việc pin image digest thuộc H4 và plan không được đánh dấu H4 đã đóng.

- [ ] **Step 4: GREEN locally + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_test_group_runner.py
.\.venv\Scripts\python.exe scripts\run_test_group.py pure
.\.venv\Scripts\python.exe scripts\run_test_group.py postgres
git -C .. add multiagent/scripts/test_groups.json multiagent/scripts/run_test_group.py multiagent/scripts/test_test_group_runner.py .github/workflows/platform-offline-tests.yml
git commit -m "ci: run complete offline platform test groups"
```

`test_embeddings.py` trong CI chỉ chạy fake path mặc định; invocation `test_embeddings.py real` dùng BGE-M3 thật vẫn là manual integration ngoài group, được ghi rõ chứ không báo PASS từ fake path.

---

### Task 7: Deployment, backup/restore và rollback rehearsal

**Files:**
- Modify: `README.md`
- Modify: `docs/operations.md`
- Modify: `docs/pre-demo-checklist.md`
- Create: `docs/evidence/platform-backup-restore-rehearsal.txt`
- Create: `docs/evidence/platform-rollout-smoke.txt`

**Interfaces:**
- Produces exact deploy/rollback order and recovery evidence; no production mutation is implied by the document.

- [ ] **Step 1: Write environment and process contract**

Document required/optional env by process, owner and secret status: database URL, Anthropic key/model, admin session settings, HTTPS flag, worker instance/release, `DRUPAL_BASE_URL`, outbound secret reference and site inbound credential. Include `site_config.py set-from-env/show` trước API/worker, capability test, start commands, migration `status/apply`, readiness checks and log locations. Mọi môi trường phải khớp allowlist của chính nó; production fail nếu là `.ddev.site`, local DDEV được phép khi được ghi rõ là local, staging DDEV chỉ hợp lệ cho rehearsal nội bộ đã khai báo chứ không được gọi là production-like. Never show real secret values.

- [ ] **Step 2: Pre-migration backup on local/staging**

Create custom-format `pg_dump` outside Git; record timestamp/database/schema_migration status/SHA-256/file size only. Verify archive with `pg_restore --list`. Do not store dump in `docs/evidence`.

Local rehearsal uses exact container path outside mounted repository:

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
docker compose exec -T db pg_dump -U vf_agent -d vf_agent -Fc -f /tmp/platform_pre_rollout.dump
docker compose exec -T db pg_restore --list /tmp/platform_pre_rollout.dump
docker compose exec -T db sha256sum /tmp/platform_pre_rollout.dump
docker compose exec -T db stat -c %s /tmp/platform_pre_rollout.dump
```

Mọi lệnh phải exit 0; archive list rỗng hoặc size 0 chặn bước restore/rollout.

- [ ] **Step 3: Restore to a newly named rehearsal database**

Resolve exact target `vf_agent_restore_rehearsal`; abort if target equals configured dev/prod DB. Create empty DB, restore dump, apply pending migrations, compare counts and invariant queries for site/profile/job/run/KB/auth/heartbeat. Drop rehearsal DB only after evidence and only by exact literal name; if deletion is not approved, retain and record cleanup owner.

```powershell
$exists = docker compose exec -T db psql -U vf_agent -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname='vf_agent_restore_rehearsal'"
if ($exists.Trim() -eq '1') { throw 'vf_agent_restore_rehearsal đã tồn tại; không tự ghi đè/drop' }
docker compose exec -T db psql -U vf_agent -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE vf_agent_restore_rehearsal OWNER vf_agent"
docker compose exec -T db pg_restore -U vf_agent -d vf_agent_restore_rehearsal --exit-on-error /tmp/platform_pre_rollout.dump
$oldPgDsn = $env:PG_DSN
$env:PG_DSN = 'postgresql://vf_agent:vf_agent@127.0.0.1:5433/vf_agent_restore_rehearsal'
try {
  .\.venv\Scripts\python.exe scripts\migrate.py status
  .\.venv\Scripts\python.exe scripts\migrate.py apply
  .\.venv\Scripts\python.exe scripts\migrate.py status
} finally {
  $env:PG_DSN = $oldPgDsn
}
```

Trước `CREATE DATABASE`, query `pg_database` và dừng nếu target đã tồn tại; không tự drop một rehearsal cũ vì có thể là evidence của người khác. Count/invariant query chạy bằng `psql -v ON_ERROR_STOP=1` trên literal target và được ghi vào evidence sau khi đã lọc dữ liệu nhạy cảm.

- [ ] **Step 4: Staging rollout in reversible order**

1. backup + migration status;
2. apply append-only migrations;
3. deploy API/admin, verify public/minimal and authenticated health;
4. deploy worker, wait heartbeat healthy;
5. test Drupal connection;
6. deploy Drupal module/roles;
7. one non-gold staging article Needs Review, xử lý bằng `staging_connector_smoke.py` fake engine—không gọi Anthropic;
8. verify one job/run/PATCH, correlation và no content leak; token/cost per-agent đã được khóa bằng Task 3 fake-transport regression, không bịa số cost từ staging fixture.

Record release SHA, IDs/hash/count/status only. Do not run on production without explicit owner approval. Actual-LLM production pilot là hoạt động riêng cần cost gate của người dùng, không nằm trong plan hardening này.

- [ ] **Step 5: Rollback rehearsal**

Stop new intake via admin, let running job finish, revert client cutover/application commits in reverse deploy order nhưng giữ Drupal result/capability endpoints cho worker mới trong rollback window, keep migrations/data, restore prior API/worker version only according to the compatibility matrix. Resume only after a real legacy v1 job reaches done through v1 fingerprint + callback; HTTP acceptance alone is not green. Database restore is disaster recovery—not normal app rollback. Rotate any credential exposed during rehearsal.

- [ ] **Step 6: Commit docs/evidence**

```powershell
git -C .. add README.md docs/operations.md docs/pre-demo-checklist.md docs/evidence/platform-backup-restore-rehearsal.txt docs/evidence/platform-rollout-smoke.txt
git commit -m "docs: rehearse platform deployment and recovery"
```

---

### Task 8: MVP acceptance matrix, technical debt và AI handoff

**Files:**
- Create: `docs/evidence/platform-mvp-acceptance.md`
- Modify: `docs/architecture.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/technical-debt.md`
- Modify: `docs/evaluation-plan.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- One traceable matrix maps each design criterion to automated test, manual evidence, status and remaining risk.

- [ ] **Step 1: Build 11-row acceptance matrix**

For each criterion in design spec §14, record `criterion`, `automated_test`, `evidence_path`, `status(pass|fail|blocked)`, `verified_commit`, `verified_at`, `residual_risk`. A criterion cannot be PASS with missing test/evidence or `[SKIP]`.

- [ ] **Step 2: Update status without rewriting history**

Architecture links to design + umbrella plan and marks modules actually present. Roadmap/technical debt mark completed tasks with commit/evidence and retain open limitations: one site/market, local auth/no SSO, legacy endpoint removal và H4 dependency lock. Result callback không còn được ghi như nợ post-MVP sau khi Task 7 Plan 4 triển khai; residual risk đúng là callback custom phải được security-test và duy trì contract. Plan này không tạo lock file nên H4 vẫn mở. Evaluation plan retains test–retest → E1 → E5 and does not claim paid results from this rollout.

- [ ] **Step 3: AI handoff guardrails**

Document module boundaries, source-of-truth files, migration rules, score freeze, no-paid-test default, two independent identity stores, site-derived scope, no full-content persistence, exact commands/checkpoints and what remains unimplemented. Do not copy secrets or claim planned files exist before their implementing commit.

- [ ] **Step 4: Final verification**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'; print(e.prompt_version())"
Set-Location ..\drupal
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev exec php scripts/test_ai_roles.php
Set-Location ..
git diff --check
git diff --exit-code 04f10e1 -- multiagent/src/agents multiagent/src/ai_core.py multiagent/src/brand_analysis.py multiagent/src/config.py multiagent/src/embeddings.py multiagent/src/graph.py multiagent/src/retrieval.py multiagent/src/scoring.py multiagent/src/seo_analysis.py multiagent/src/state.py multiagent/src/text_utils.py multiagent/src/kb multiagent/config/scoring.yaml
```

- [ ] **Step 5: Commit acceptance evidence**

```powershell
git -C D:\drupal-multiagent-seo add docs/evidence/platform-mvp-acceptance.md docs/architecture.md docs/roadmap.md docs/technical-debt.md docs/evaluation-plan.md README.md AGENTS.md CLAUDE.md
git commit -m "docs: hand off standalone platform MVP"
```

---

## Plan 5 Completion Gate

- [ ] Migration 0004 applied/rehearsed; heartbeat real and stale semantics proven.
- [ ] Security headers, exception boundary and recursive redaction tests green.
- [ ] Per-agent usage attributed without any score-path diff; otherwise criterion explicitly blocked, not silently downgraded to per-job only.
- [ ] Drupal roles pass least-privilege test on DDEV/staging.
- [ ] Full fake E2E/failure/privacy matrix green with zero paid call.
- [ ] CI/test manifest accounts for every test script and distinguishes manual DDEV.
- [ ] Backup restore and application rollback rehearsed outside production.
- [ ] 11/11 acceptance rows have honest status and traceable evidence.
- [ ] Documentation and AI handoff describe implemented state, remaining debt and unchanged evaluation order.
