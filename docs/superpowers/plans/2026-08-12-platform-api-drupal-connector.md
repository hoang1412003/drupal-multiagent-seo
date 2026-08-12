# Platform API and Drupal Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa Drupal sang `/api/v1` với credential riêng theo site, fetch đúng revision Needs Review, connector boundary và worker site/profile-aware, vẫn giữ endpoint cũ để rollback trong cửa sổ chuyển đổi.

**Architecture:** API auth suy site từ hash token; profile được chọn từ assignment bằng `content_type/langcode` tường minh. Worker prefetch nội dung qua connector, kiểm fingerprint trước LLM, kích hoạt connector bằng context local cho graph hiện hành, audit rồi write-back đúng một lần.

**Tech Stack:** FastAPI/Pydantic, psycopg 3, requests, Drupal JSON:API resource versions, Drupal PHP/Guzzle.

**Depends on:** Foundation, Auth và Admin Operations đã qua checkpoint.

**Quy ước chạy lệnh:** Mỗi code block PowerShell bắt đầu với working directory `D:\drupal-multiagent-seo\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

## Global Constraints

- Body `/api/v1/jobs` không có `site_id`; site luôn lấy từ credential.
- API metadata tối đa 16 KiB; `content_hash` là SHA-256 lowercase 64 hex; API không nhận toàn văn bài.
- Drupal event gửi UUID, numeric revision ID, `cam_nang`, langcode thật, hash version 2.
- Connector phải GET `?resourceVersion=id:{revision_id}` khi biết revision. Reconciliation discover qua Drupal pending feed rồi fetch exact revision; `rel:working-copy` chỉ fallback cho legacy item không có revision ID.
- Worker kiểm fingerprint trước khi gọi graph/LLM. Mismatch không được audit như đã chấm đúng nội dung.
- Mỗi run chỉ PATCH một lần; write-back retry dùng saved payload.
- Secret DB chỉ có token SHA-256 + prefix; outbound Drupal password lấy từ env prefix `secret_ref`.
- Legacy endpoint/token không xóa trước cutover verification và rollback window.
- Không đổi `text_utils.content_hash()` trong plan này; fingerprint v2 mới nằm ở platform connector để score-path diff giữ rỗng.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/migrations/0003_api_connector.sql` | Site credential, connector health, hash version/source URL |
| `multiagent/src/platform/api/auth.py` | Bearer token → `SitePrincipal` |
| `multiagent/src/platform/api/models.py` | Pydantic request/response v1 |
| `multiagent/src/platform/api/router.py` | `/api/v1/jobs` routes |
| `multiagent/src/platform/connectors/base.py` | Protocol/dataclass connector |
| `multiagent/src/platform/connectors/secrets.py` | Resolve env secret prefix |
| `multiagent/src/platform/connectors/drupal.py` | Revision-aware fetch/list/write/health |
| `multiagent/src/platform/connectors/runtime.py` | Context-local prepared document cho graph wrapper |
| `multiagent/src/platform/fingerprint.py` | Canonical six-field fingerprint v2 |
| `multiagent/scripts/site_credential.py` | Import/rotate/revoke token, plaintext shown once |
| `drupal/.../vf_ai_trigger/ServiceClient.php` | Gọi `/api/v1`, payload mới |
| `drupal/.../vf_ai_review/AiInputFingerprint.php` | Fingerprint v2 khớp Python |

---

### Task 1: Migration 0003 và per-site credential repository

**Files:**
- Create: `multiagent/migrations/0003_api_connector.sql`
- Create: `multiagent/src/platform/api/__init__.py`
- Create: `multiagent/src/platform/api/auth.py`
- Create: `multiagent/scripts/site_credential.py`
- Modify: `multiagent/scripts/test_migrations.py`
- Create: `multiagent/scripts/test_site_credentials.py`

**Interfaces:**
- Produces: `SitePrincipal(site: SiteContext, credential_id: UUID, token_prefix: str)`.
- Produces: `authenticate_bearer(conn, authorization: str) -> SitePrincipal`.
- CLI: `import-env`, `rotate`, `revoke`, `list`.

- [ ] **Step 1: RED migration/auth storage**

Assert schema:

```sql
CREATE TABLE site_api_credential (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid NOT NULL REFERENCES site(id),
  token_prefix text NOT NULL,
  token_hash char(64) NOT NULL UNIQUE,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);
CREATE INDEX site_api_credential_prefix
ON site_api_credential (token_prefix) WHERE active=true;
```

Migration thêm `content_hash_version smallint NOT NULL DEFAULT 1` vào job/run, `source_url text` và `is_fixture boolean NOT NULL DEFAULT false` vào run, cùng `last_health_status`, `last_health_checked_at`, `last_health_error` vào site. Check hash version `IN (1,2)`. Dashboard/cost query phải luôn loại `run_log.is_fixture=true` khỏi production metrics.

- [ ] **Step 2: Implement 0003 + apply test**

Existing rows giữ version 1; không rewrite hash lịch sử. Fresh/upgrade/idempotent/checksum test phải xanh rồi mới apply DB dev.

- [ ] **Step 3: RED token auth**

Generate 32-byte token; DB chỉ chứa `sha256(token)`, prefix 12 ký tự đầu. Missing/malformed/wrong/revoked/inactive-site đều cùng 401 generic ở HTTP layer; repository exception nội bộ có reason cho audit nhưng không trả client. `last_used_at` touch tối đa mỗi 5 phút.

- [ ] **Step 4: Implement constant-time auth**

Parse đúng `Bearer <token>` không chấp nhận token rỗng/multiple scheme. Query active credentials bằng prefix; hash candidate rồi `hmac.compare_digest` với từng row tối đa collision list. Không lookup bằng full raw token.

- [ ] **Step 5: CLI không nhận raw token qua argument**

- `import-env --site drupal-vn-primary --env VF_SERVICE_TOKEN`: đọc env, hash, không in raw.
- `rotate --site ...`: tạo token, revoke credential active trong transaction, insert mới, commit rồi in plaintext đúng một lần.
- `revoke --credential <uuid>`: revoke nhưng từ chối nếu site không còn credential active khác, trừ `--allow-no-active` được dùng có chủ đích lúc disable site.
- `list`: chỉ prefix/status/time.

- [ ] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\test_site_credentials.py
.\.venv\Scripts\python.exe scripts\migrate.py apply
git -C .. add multiagent/migrations/0003_api_connector.sql multiagent/src/platform/api multiagent/scripts/site_credential.py multiagent/scripts/test_migrations.py multiagent/scripts/test_site_credentials.py
git commit -m "feat: add per-site API credentials"
```

---

### Task 2: API v1 contract và site-derived profile

**Files:**
- Create: `multiagent/src/platform/api/models.py`
- Create: `multiagent/src/platform/api/router.py`
- Modify: `multiagent/src/api.py`
- Create: `multiagent/scripts/test_api_v1.py`

**Interfaces:**
- `POST /api/v1/jobs`.
- `GET /api/v1/jobs/{job_id:uuid}`.
- `GET /api/v1/jobs/by-content/{external_content_id}`.

- [ ] **Step 1: RED request validation/auth/scope**

`JobCreate` exact fields:

```python
class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_content_id: str = Field(min_length=1, max_length=128)
    external_revision_id: str | None = Field(default=None, max_length=64)
    content_type: str = Field(min_length=1, max_length=64)
    langcode: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash_version: Literal[2]
    source: Literal["event", "manual", "reconcile"] = "event"
    force: bool = False
```

Test body có `site_id`, field lạ, uppercase hash, invalid lang/revision bị 422. Token site A không GET job site B (trả 404, không 403 để tránh enumeration).

- [ ] **Step 2: RED status semantics**

- queued 202;
- duplicate 200;
- dead-letter cùng scoped key trả 409 khi `force=false`; `force=true` tạo job mới linked tới failed row và audit source `manual`;
- site paused 423;
- no profile match 422 với code `profile_not_found`, không default;
- database failure 503, không báo queued giả.

- [ ] **Step 3: Implement dependency + router**

Auth dependency dùng request-scoped conn; lấy `SitePrincipal`; `select_review_context` bằng site principal + body content/lang. Correlation ID server generate UUID; không nhận từ body ở MVP. Response có `job_id` public UUID, status, duplicate bool, policy_version; không trả DB numeric id/secret.

GET status lọc site. `last_error` chỉ trả code sanitized (`connector_auth`, `input_hash_mismatch`, `llm_transient`, `writeback_failed`, `internal`), không raw exception.

- [ ] **Step 4: Request-size middleware**

Chỉ áp `/api/v1`: Content-Length >16384 trả 413 trước parse; thiếu Content-Length vẫn đọc qua ASGI limiter tối đa 16384+1, không tin header để bypass.

- [ ] **Step 5: Include router, giữ legacy**

`api.py` include v1 router; `/jobs` và `/jobs/by-node` vẫn tồn tại, response có header `Deprecation: true`. MVP không phát `Sunset` khi chưa có ngày loại bỏ được phê duyệt riêng.

- [ ] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_api_v1.py
.\.venv\Scripts\python.exe scripts\test_api.py
git -C .. add multiagent/src/platform/api multiagent/src/api.py multiagent/scripts/test_api_v1.py
git commit -m "feat: expose site-scoped review API v1"
```

---

### Task 3: Connector protocol, env secrets và Drupal revision fetch

**Files:**
- Create: `multiagent/src/platform/connectors/__init__.py`
- Create: `multiagent/src/platform/connectors/base.py`
- Create: `multiagent/src/platform/connectors/secrets.py`
- Create: `multiagent/src/platform/connectors/drupal.py`
- Create: `multiagent/src/platform/connectors/runtime.py`
- Create: `multiagent/scripts/test_drupal_connector.py`

**Interfaces:**
- `ContentDocument(fields: dict[str,str], raw_content: dict, source_url: str | None, external_revision_id: str | None, content_type: str, langcode: str)`.
- `PendingContent(external_content_id, external_revision_id, content_hash, content_type, langcode, source_url)`; feed không mang full fields.
- `ConnectorHealth(ok: bool, status_code: int | None, checked_at: datetime, error_code: str | None)`.
- Protocol methods `fetch_content`, `write_back`, `list_pending`, `health`.

- [ ] **Step 1: RED secret resolver**

For `secret_ref='DRUPAL'`, read `DRUPAL_USER`, `DRUPAL_PASSWORD`; missing one raises `ConnectorSecretError` listing env name but not value. Reject secret_ref not matching `^[A-Z][A-Z0-9_]{0,63}$` to prevent arbitrary env lookup from compromised DB.

- [ ] **Step 2: RED exact revision URL và six fields**

Fake requests assert:

```text
/jsonapi/node/article/{uuid}?resourceVersion=id:123
```

When revision None and working copy requested:

```text
?resourceVersion=rel:working-copy
```

Normalize title/body/summary/url_alias/meta_description/image_alt exactly as existing `_fields_tu_resource`. `source_url` derives from `attributes.drupal_internal__nid` as `{base_url}/node/{nid}`; no nid thì None.

`list_pending(after_revision_id, limit)` gọi `/vf-ai/integration/v1/pending?after_revision_id=<int>&limit=<1..50>`, validate schema/next cursor và không chấp nhận title/body/summary trong feed. Mỗi item bình thường phải có revision ID; chỉ item legacy được đánh dấu explicit mới cho phép null và fetch `rel:working-copy`.

- [ ] **Step 3: RED error classification và retry một tầng**

401/403 → `ConnectorAuthError`, no retry. 404 revision → `ConnectorRevisionNotFound`, no retry. Timeout/429/5xx → `ConnectorTransientError(retry_after_seconds)` sau đúng **một** HTTP call; parse `Retry-After` dạng delta-seconds, clamp 0–600 và bỏ qua date/malformed. Schema response missing `data` → `ConnectorPayloadError`, no blind retry. Queue `fail()` ở Foundation mới sở hữu tối đa 3 attempt + jitter, tránh 3×3 nested calls.

- [ ] **Step 4: Implement connector**

Không import env tại module load. `DrupalConnector(site, credentials, request_fn=requests.request)` giữ base URL/site context. Mỗi method gọi transport một lần và trả/raise typed result; write-back chỉ 4 AI fields, không moderation state.

- [ ] **Step 5: Runtime prepared document**

`runtime.activate(connector, prepared_document)` dùng `ContextVar` token/reset trong `finally`. Compatibility `drupal_client.fetch_content(node_id)` ở Task 5 sẽ đọc prepared doc; nếu không active vẫn dùng legacy client.

- [ ] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_drupal_connector.py
git -C .. add multiagent/src/platform/connectors multiagent/scripts/test_drupal_connector.py
git commit -m "feat: add revision-aware Drupal connector"
```

---

### Task 4: Fingerprint v2 phủ đủ sáu input, khớp Python/PHP

**Files:**
- Create: `multiagent/src/platform/fingerprint.py`
- Create: `multiagent/scripts/test_platform_fingerprint.py`
- Create: `drupal/web/modules/custom/vf_ai_review/src/AiInputFingerprint.php`
- Create: `drupal/scripts/input_fingerprint_v2_fixture.json`
- Create: `drupal/scripts/test_ai_input_fingerprint.php`
- Modify: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`
- Modify: `drupal/scripts/test_ai_report_renderer.php`
- Modify: `drupal/scripts/test_vf_ai_trigger.php`

**Interfaces:**
- Produces Python `input_fingerprint(fields: Mapping[str, object]) -> str`.
- Produces PHP `AiInputFingerprint::hash(array $fields): string`.
- Exact order: title, body, summary, url_alias, meta_description, image_alt.

- [ ] **Step 1: Tạo cross-language fixture literal**

Fixture dùng Vietnamese Unicode, body HTML, URL alias, two-line image alt và expected:

```json
{
  "version": 2,
  "fields": {
    "title": "Hướng dẫn sạc pin ô tô điện VinFast",
    "body": "<p>Nội dung bài viết mẫu.</p>",
    "summary": "Tóm tắt ngắn",
    "url_alias": "/huong-dan-sac-pin",
    "meta_description": "Mô tả cho SEO",
    "image_alt": "Ảnh đại diện: Xe điện đang sạc\nẢnh 1 trong bài: Cổng sạc VF e34"
  },
  "expected_sha256": "7535d604a944a7b8c9529d7f2b7d518e491c2730866413227fce265bc00fb9f6"
}
```

- [ ] **Step 2: RED Python/PHP**

Canonical bytes là `b"v2\n" + UTF-8(json)` với compact JSON, unescaped Unicode/slashes và insertion order exact. Missing/None field becomes empty string. Thay riêng `url_alias` hoặc `image_alt` phải đổi hash — khóa nợ N2.

- [ ] **Step 3: Implement both languages**

Python dùng `json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))`. PHP dùng ordered associative array + `json_encode(JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)`, prefix `"v2\n"`.

Tạo `vf_ai_review_input_fields(NodeInterface $node): array` lấy sáu input từ node: alias qua `path_alias.manager`; ảnh đại diện lấy `field_image.alt`; ảnh body dùng cùng label/order với Python `_extract_image_alt`. Test thẻ alt double/single/unquoted/missing, không nhầm `data-alt`, và test riêng featured image đứng trước body image.

Stale banner phải tương thích lịch sử: report có `content_hash_version=2` dùng `AiInputFingerprint::hash(vf_ai_review_input_fields($node))`; report thiếu version/`version=1` tiếp tục dùng `AiReportRenderer::contentHash(vf_ai_review_hash_fields($node))`. Trigger mới chỉ coi “đã chấm” khi report version 2 và hash v2 khớp; report v1 sẽ enqueue đúng một lượt nâng cấp khi bài được lưu lại, không bị hiểu nhầm là v2.

- [ ] **Step 4: GREEN cross-language**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_platform_fingerprint.py
Set-Location ..\drupal
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_ai_report_renderer.php
ddev exec php scripts/test_vf_ai_trigger.php
```

Expected: hai bên cùng literal expected.

- [ ] **Step 5: Commit**

```powershell
git -C .. add multiagent/src/platform/fingerprint.py multiagent/scripts/test_platform_fingerprint.py drupal/web/modules/custom/vf_ai_review/src/AiInputFingerprint.php drupal/web/modules/custom/vf_ai_review/vf_ai_review.module drupal/scripts/input_fingerprint_v2_fixture.json drupal/scripts/test_ai_input_fingerprint.php drupal/scripts/test_ai_report_renderer.php drupal/scripts/test_vf_ai_trigger.php
git commit -m "fix: fingerprint every field used by review engine"
```

---

### Task 5: Worker prefetch/verify rồi chạy graph qua connector context

**Files:**
- Modify: `multiagent/src/drupal_client.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/job_queue.py`
- Modify: `multiagent/src/audit.py`
- Modify: `multiagent/src/platform/admin/queries.py`
- Modify: `multiagent/src/platform/admin/templates/review_detail.html`
- Modify: `multiagent/scripts/test_worker.py`
- Modify: `multiagent/scripts/test_worker_graph_integration.py`
- Modify: `multiagent/scripts/test_drupal_client_worker.py`
- Modify: `multiagent/scripts/test_admin_dashboard.py`
- Modify: `multiagent/scripts/test_admin_reviews.py`

**Interfaces:**
- Produces: `fail_permanent(conn, job_id, error_code, safe_message)`.
- Produces: connector factory from job site.
- Keeps graph input/output behavior for `cam_nang/vi`.
- `worker.chay_mot_job(..., fixture_run: bool = False)`; production loop không truyền true.

- [ ] **Step 1: RED “mismatch before LLM”**

Fake connector returns fields hash khác job. Spy invoke must remain zero calls; job becomes failed code `input_hash_mismatch`; no run_log result. Test exact revision fetch occurs before invoke.

- [ ] **Step 2: RED prepared document/one fetch**

Success path: connector fetch count 1; graph fetch node reads prepared doc through compatibility wrapper, not second HTTP; invoke receives `node_id`, `content_type`, `langcode`; connector write-back count 1 after audit.

- [ ] **Step 3: Implement compatibility delegation**

`drupal_client.fetch_content()` first checks active runtime prepared document for matching external ID; returns `{fields, raw_content}`. Không active thì legacy code unchanged. `write_back` compatibility remains for manual graph scripts.

- [ ] **Step 4: Implement worker sequence**

1. claim scoped job;
2. gọi `find_reusable_writeback`: chỉ nhánh write-back retry đủ điều kiện mới PATCH saved payload và kết thúc, không fetch/LLM/run mới;
3. load site + credentials, build connector;
4. prefetch exact revision;
5. calculate v2 fingerprint and compare;
6. activate runtime prepared document;
7. invoke graph without write-back with explicit profile keys;
8. build payload, replace `report_json.content_hash` with v2 job hash and add `content_hash_version=2` only to report metadata;
9. `ghi_scoped` with source URL/revision;
10. connector PATCH once; mark writeback/complete hoặc để chính job retry saved payload.

Không thêm full fields/raw content vào job/run/audit. `source='manual', force=true` sau run succeeded luôn đi qua bước 3–10 để chấm mới; không bị nhánh reuse nuốt mất ý nghĩa “chấm lại”. `fixture_run` được truyền vào `ghi_scoped(is_fixture=...)`; production worker loop luôn default false.

Admin dashboard/cost/decision aggregates thêm `WHERE is_fixture=false`. Review detail vẫn cho xem fixture nhưng hiển thị badge/banner “STAGING FIXTURE — không phải đánh giá AI”; test seed một fixture run để chứng minh metric không tăng.

- [ ] **Step 5: Error classification**

Auth/revision/payload/hash mismatch → permanent failed without 3 blind LLM attempts. Timeout/429/5xx → `q.fail(..., retry_after_seconds=exc.retry_after_seconds)`; queue là tầng duy nhất quyết backoff/max 3. Unexpected programming → internal retry capped bởi cùng queue attempts. Every last_error stored as safe code + short message; raw exception only server log sau redaction Plan 5.

- [ ] **Step 6: GREEN regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_worker.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
.\.venv\Scripts\python.exe scripts\test_drupal_client_worker.py
```

Expected: one fetch, one PATCH, mismatch zero invoke.

- [ ] **Step 7: Commit**

```powershell
git -C .. add multiagent/src/drupal_client.py multiagent/src/worker.py multiagent/src/job_queue.py multiagent/src/audit.py multiagent/src/platform/admin/queries.py multiagent/src/platform/admin/templates/review_detail.html multiagent/scripts/test_worker.py multiagent/scripts/test_worker_graph_integration.py multiagent/scripts/test_drupal_client_worker.py multiagent/scripts/test_admin_dashboard.py multiagent/scripts/test_admin_reviews.py
git commit -m "refactor: run worker through scoped Drupal connector"
```

---

### Task 6: Reconciliation theo site/profile và pause

**Files:**
- Modify: `multiagent/src/reconcile.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/scripts/test_reconcile.py`

**Interfaces:**
- `quet(conn, *, site_loader, connector_factory, enqueue_fn, ...) -> ReconcileSummary`.

- [ ] **Step 1: RED multi-site/pause/dead-letter**

Active site A enqueue; paused B không gọi connector; inactive C bỏ qua. Pending working copy chọn profile explicit, fingerprint v2. Dead-letter đúng scoped key không hồi sinh. Một site connector lỗi không làm bỏ site sau.

- [ ] **Step 2: Implement reconciliation**

Load active non-paused sites; page connector `list_pending` đến khi `next_after_revision_id=null`, tối đa 50 item/page. Profile select từng item, đối chiếu `content_type/langcode`, enqueue source reconcile với revision ID + fingerprint v2 do Drupal feed gửi. Legacy item explicit không có revision mới dùng `external_revision_id=null` và worker fetch `rel:working-copy`; feed MVP mới luôn có revision ID.

- [ ] **Step 3: Worker pause semantics**

Queue claim đã bỏ paused rows từ Plan 1. Reconcile cũng bỏ pause. In-progress không bị kill. Resume không enqueue hàng loạt trùng vì scoped dedup.

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_reconcile.py
git -C .. add multiagent/src/reconcile.py multiagent/src/worker.py multiagent/scripts/test_reconcile.py
git commit -m "feat: reconcile pending content per active site"
```

---

### Task 7: Drupal module gửi API v1 payload/revision/profile

**Files:**
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/ChamLaiController.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/TrangThaiController.php`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/PendingController.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.info.yml`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.routing.yml`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.permissions.yml`
- Modify: `drupal/scripts/test_vf_ai_trigger.php`

**Interfaces:**
- `guiJob(uuid, revisionId, contentType, langcode, hash, source, force)`.
- Status endpoint `/api/v1/jobs/by-content/{uuid}`.

- [ ] **Step 1: RED payload contract**

Expected keys exact:

```php
[
  'external_content_id' => $uuid,
  'external_revision_id' => (string) $revision_id,
  'content_type' => 'cam_nang',
  'langcode' => 'vi',
  'content_hash' => $hash,
  'content_hash_version' => 2,
  'source' => 'event',
  'force' => FALSE,
]
```

Assert no `site_id`, UUID not nid, revision numeric nonzero, hash fixture v2.

- [ ] **Step 2: Implement hook/controller mapping**

Article maps `cam_nang`; `$node->language()->getId()`; `$node->getRevisionId()`. Hash fields from shared v2 helper. Manual rescore same revision + source manual + force true. Endpoint URL `/api/v1/jobs` and status escaped UUID path.

- [ ] **Step 3: Preserve save failure isolation**

All network error still swallowed/logged; Drupal save never throws. 423 pause logs notice “intake paused”; 409 dead letter behavior giữ. 401/403 warning rõ integration credential, không log token.

- [ ] **Step 4: Implement pending metadata feed**

`vf_ai_trigger.info.yml` khai báo dependency `drupal:basic_auth`. Route `GET /vf-ai/integration/v1/pending` chỉ cho `_auth: ['basic_auth']`, yêu cầu permission mới restricted `access vf ai integration feed`, tắt cache theo user và response `Cache-Control: no-store`. Controller clamp `limit` 1–50, validate `after_revision_id>=0`, query node với `accessCheck(TRUE)`, `latestRevision()`, bundle article, moderation `needs_review`, `vid > after`, sort vid tăng dần, rồi load đúng revision. Mỗi item chỉ có `external_content_id` UUID, `external_revision_id`, `content_type='cam_nang'`, `langcode`, `content_hash`, `content_hash_version=2`, `source_url`; response có `next_after_revision_id` hoặc null. Không serialize field nội dung/AI/secret.

Test có một published default + pending non-default và chứng minh feed trả pending revision mới nhất; article đã rời Needs Review không xuất hiện; pagination không lặp revision.

- [ ] **Step 5: GREEN Drupal tests**

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev drush cr
```

- [ ] **Step 6: Commit**

```powershell
git -C .. add drupal/web/modules/custom/vf_ai_trigger drupal/scripts/test_vf_ai_trigger.php
git commit -m "feat: send revision-aware jobs to API v1"
```

---

### Task 8: Connection page, test connection và pause/resume

**Files:**
- Create: `multiagent/src/platform/admin/templates/connection.html`
- Modify: `multiagent/src/platform/admin/router.py`
- Modify: `multiagent/src/platform/admin/queries.py`
- Create: `multiagent/scripts/test_admin_connection.py`

**Interfaces:**
- `GET /admin/connection` viewer+.
- `POST /admin/connection/test` operator+.
- `POST /admin/connection/pause`, `/resume` operator+.

- [ ] **Step 1: RED RBAC/CSRF/semantics**

Viewer sees status but POST 403. Operator without CSRF 403. Test connection updates `last_health_*`, audit outcome, never returns credential value. Pause leaves running job, keeps queued, blocks claim/API/reconcile; resume restores.

- [ ] **Step 2: Implement connection service**

Health checks authenticated JSON:API GET page limit 1 with 2s timeout, no LLM. Store code `ok|auth_failed|timeout|server_error|payload_error`, checked time và safe message. Admin HTML shows site slug/base URL/secret ref **name only**, active profile/policy, token prefix active list, last result.

- [ ] **Step 3: Implement pause transaction/audit**

Lock site row; idempotent pause/resume returns 200/303; reason optional max 300. Do not update queued rows. Dashboard connector health reads saved status.

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_connection.py
git -C .. add multiagent/src/platform/admin multiagent/scripts/test_admin_connection.py
git commit -m "feat: operate Drupal connection and intake pause"
```

---

### Task 9: Credential import, cutover smoke và rollback window

**Files:**
- Modify: `README.md`
- Modify: `docs/operations.md`
- Modify: `docs/pre-demo-checklist.md`
- Create: `multiagent/scripts/staging_connector_smoke.py`
- Create: `multiagent/scripts/test_staging_connector_smoke.py`
- Create: `docs/evidence/platform-api-cutover-verification.txt`

**Interfaces:**
- Produces: repeatable cutover/rollback instructions; no code behavior change.

- [ ] **Step 1: Import current token before deploying Drupal change**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\site_credential.py import-env --site drupal-vn-primary --env VF_SERVICE_TOKEN
```

Expected: print prefix/id only. Smoke POST `/api/v1/jobs` với một fake external ID/hash vào test DB/schema, không production queue.

- [ ] **Step 2: Deploy API/worker first**

Restart API/worker, health current, legacy endpoint vẫn pass. Test connection admin success. Không đổi Drupal trước bước này.

- [ ] **Step 3: Deploy Drupal module + one-article smoke không gọi LLM**

Tạo `staging_connector_smoke.py` dùng dependency injection hiện có của worker với fake engine output đánh dấu rõ `fixture=true`, `note="STAGING FIXTURE — không phải đánh giá AI"`, đồng thời gọi worker với `fixture_run=true`. Script bắt buộc `--job-id <uuid> --confirm-staging-fixture`, từ chối nếu site base URL không phải `.ddev.site`/allowlist staging và từ chối nếu queue có job queued/running khác. Worker hiện import `ai_core` ở module load, nên test thay `ai_core.get_client` bằng hàm raise và assert không bao giờ được gọi; không dùng API key. `test_staging_connector_smoke.py` khóa các guard này, `run_log.is_fixture=true` và output shape.

Stop worker staging, chọn article không thuộc gold/E1, record UUID/revision/hash, chuyển Needs Review, lấy job ID từ admin/watchdog, rồi chạy script. Verify exactly one scoped job, connector fetch đúng revision, one fixture run, one PATCH/revision AI và editor report hiện banner fixture. Khởi động lại worker sau khi queue sạch. Không trình bày fixture score như kết quả chất lượng.

- [ ] **Step 4: Test write-back reuse**

Trong `test_staging_connector_smoke.py` + fake transport, làm PATCH fail sau run rồi retry; assert run payload reused và engine invocation vẫn đúng 1, usage không tăng. Không cố tình làm thất bại trên Drupal staging thật.

- [ ] **Step 5: Rollback rehearsal**

Revert riêng Drupal ServiceClient commit hoặc cấu hình module về endpoint legacy; verify save vẫn enqueue legacy. Roll forward lại. Không rollback/drop migration.

- [ ] **Step 6: Ghi nhận deprecation nhưng không tự đặt Sunset**

Legacy response tiếp tục chỉ có `Deprecation: true`. Tài liệu ghi endpoint removal là nợ sau MVP; `Sunset` và việc xóa endpoint cần quyết định/plan riêng sau khi production đã qua cửa sổ rollback, không nằm trong commit cutover.

- [ ] **Step 7: Evidence + commit**

Evidence ghi request IDs/counts/timestamps/status, không ghi token/content.

```powershell
git -C .. add README.md docs/operations.md docs/pre-demo-checklist.md multiagent/scripts/staging_connector_smoke.py multiagent/scripts/test_staging_connector_smoke.py docs/evidence/platform-api-cutover-verification.txt
git commit -m "docs: record API v1 cutover and rollback rehearsal"
```

---

### Task 10: API/connector checkpoint

**Files:**
- Modify: `docs/technical-debt.md`
- Create: `docs/evidence/platform-api-connector-verification.txt`

**Interfaces:**
- Produces evidence cho hardening plan.

- [ ] **Step 1: Focused tests**

Chạy migration, site credential, API v1, fingerprint Python/PHP, connector, worker integration, reconcile, admin connection, legacy API/Drupal tests.

- [ ] **Step 2: Full offline suite và score gate**

Chạy toàn `scripts/test_*.py`, Drupal PHP tests, parent `prompt_version`/score-path diff. `text_utils.py`, graph/agents/config phải không đổi.

- [ ] **Step 3: Data/privacy assertions**

SQL/HTML/log scan xác nhận không có body/title/Authorization/password/session raw. Assert every new job/run có site/profile/policy/revision/hash version/correlation; one write-back.

- [ ] **Step 4: Evidence/docs commit**

```powershell
git -C .. add docs/evidence/platform-api-connector-verification.txt docs/technical-debt.md
git commit -m "docs: record API and connector verification"
```
