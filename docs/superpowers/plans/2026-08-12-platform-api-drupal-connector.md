# Platform API and Drupal Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa Drupal sang `/api/v1` với credential riêng theo site, fetch đúng revision Needs Review, connector boundary và worker site/profile-aware, vẫn giữ endpoint cũ để rollback trong cửa sổ chuyển đổi.

**Architecture:** API auth suy site từ hash token; profile được chọn từ assignment bằng `content_type/langcode` tường minh. Worker prefetch nội dung qua connector, kiểm fingerprint đúng version trước LLM, kích hoạt connector bằng context local cho graph hiện hành, audit rồi gọi Drupal result callback compare-and-set/idempotent. Callback là chủ sở hữu write-back để job revision cũ không thể ghi đè report mới.

**Tech Stack:** FastAPI/Pydantic, psycopg 3, requests, Drupal JSON:API resource versions, Drupal PHP/Guzzle.

**Depends on:** Foundation, Auth và Admin Operations đã qua checkpoint.

**Implementation status (2026-08-14):** ✅ Toàn bộ Task 1–10 đã thực thi và qua checkpoint. Evidence: `docs/evidence/platform-api-cutover-verification.txt` (cutover + rollback rehearsal trên Drupal thật) và `docs/evidence/platform-api-connector-verification.txt` (checkpoint, score gate, privacy scan). Hai lệch có chủ đích so với plan, đã ghi rõ trong evidence: (1) `test_ai_result_callback.php` chạy bằng `ddev drush php:script` chứ không phải `ddev exec php`, vì nó cần bootstrap Drupal để tạo revision thật; (2) `job_queue.py` được mở rộng ở Task 2 (thêm `content_hash_version`) dù file này chỉ được liệt kê ở Task 5 — phải lưu version ngay lúc enqueue, không thể để đến lúc claim.

**Quy ước chạy lệnh:** Mỗi code block PowerShell bắt đầu với working directory `D:\drupal-multiagent-seo\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

## Global Constraints

- Body `/api/v1/jobs` không có `site_id`; site luôn lấy từ credential.
- API metadata tối đa 16 KiB; `content_hash` là SHA-256 lowercase 64 hex; API không nhận toàn văn bài.
- Drupal result callback request tối đa 512 KiB, `suggestions` tối đa 64 KiB và serialized `report_json` tối đa 384 KiB; unknown key bị từ chối, không truncate rồi ghi dữ liệu nửa vời.
- Drupal event gửi UUID, numeric revision ID, `cam_nang`, langcode thật, hash version 2.
- Connector phải GET `?resourceVersion=id:{revision_id}` khi biết revision. Reconciliation discover qua Drupal pending feed rồi fetch exact revision; `rel:working-copy` chỉ fallback cho legacy item không có revision ID.
- Worker kiểm fingerprint trước khi gọi graph/LLM. Mismatch không được audit như đã chấm đúng nội dung.
- Mỗi run chỉ được callback áp dụng một lần; write-back retry dùng saved payload + cùng `run_id` để nhận `already_applied`, không gọi LLM lại.
- Callback phải kiểm tra atomically expected revision + content hash/version trước khi ghi. Conflict `content_superseded` kết thúc job cũ, không retry payload cũ.
- Worker phải chạy cả hash v1 và v2 trong cửa sổ rollback: v1 dùng bốn field/working copy, v2 dùng sáu field/exact revision.
- `base_url` DDEV trong seed không được dùng ngầm ở staging/production; site config CLI và capability test là gate trước worker mới.
- Secret DB chỉ có token SHA-256 + prefix; outbound Drupal password lấy từ env prefix `secret_ref`.
- Legacy endpoint/token không xóa trước cutover verification và rollback window.
- Không đổi `text_utils.content_hash()` trong plan này; fingerprint v2 mới nằm ở platform connector để score-path diff giữ rỗng.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/migrations/0004_api_connector.sql` | Site credential, connector health, hash version/source URL |
| `multiagent/src/review_platform/api/auth.py` | Bearer token → `SitePrincipal` |
| `multiagent/src/review_platform/api/models.py` | Pydantic request/response v1 |
| `multiagent/src/review_platform/api/router.py` | `/api/v1/jobs` routes |
| `multiagent/src/review_platform/connectors/base.py` | Protocol/dataclass connector |
| `multiagent/src/review_platform/connectors/secrets.py` | Resolve env secret prefix |
| `multiagent/src/review_platform/connectors/drupal.py` | Revision-aware fetch/list/write/health |
| `multiagent/src/review_platform/connectors/runtime.py` | Context-local prepared document cho graph wrapper |
| `multiagent/src/review_platform/fingerprint.py` | Canonical six-field fingerprint v2 |
| `multiagent/scripts/site_config.py` | Cấu hình/kiểm tra base URL và secret reference theo môi trường |
| `multiagent/scripts/site_credential.py` | Import/rotate/revoke token, plaintext shown once |
| `drupal/.../vf_ai_trigger/ServiceClient.php` | Gọi `/api/v1`, payload mới |
| `drupal/.../vf_ai_review/AiInputFingerprint.php` | Fingerprint v2 khớp Python |
| `drupal/.../vf_ai_trigger/src/Service/AiResultWriter.php` | Callback CAS/idempotent chỉ ghi bốn field AI |

---

### Task 1: Migration 0004, per-site credential và cấu hình connector

**Files:**
- Create: `multiagent/migrations/0004_api_connector.sql`
- Create: `multiagent/src/review_platform/api/__init__.py`
- Create: `multiagent/src/review_platform/api/auth.py`
- Create: `multiagent/scripts/site_config.py`
- Create: `multiagent/scripts/site_credential.py`
- Modify: `multiagent/scripts/test_migrations.py`
- Create: `multiagent/scripts/test_site_config.py`
- Create: `multiagent/scripts/test_site_credentials.py`

**Interfaces:**
- Produces: `SitePrincipal(site: SiteContext, credential_id: UUID, token_prefix: str)`.
- Produces: `authenticate_bearer(conn, authorization: str) -> SitePrincipal`.
- Site config CLI: `set-from-env`, `show`.
- Credential CLI: `import-env`, `rotate`, `revoke`, `list`.

- [x] **Step 1: RED migration/auth storage**

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

- [x] **Step 2: Implement 0003 + apply test**

Existing rows giữ version 1; không rewrite hash lịch sử. Fresh/upgrade/idempotent/checksum test phải xanh rồi mới apply DB dev.

- [x] **Step 3: RED token auth**

Generate 32-byte token; DB chỉ chứa `sha256(token)`, prefix 12 ký tự đầu. Missing/malformed/wrong/revoked/inactive-site đều cùng 401 generic ở HTTP layer; repository exception nội bộ có reason cho audit nhưng không trả client. `last_used_at` touch tối đa mỗi 5 phút.

- [x] **Step 4: Implement constant-time auth**

Parse đúng `Bearer <token>` không chấp nhận token rỗng/multiple scheme. Query active credentials bằng prefix; hash candidate rồi `hmac.compare_digest` với từng row tối đa collision list. Không lookup bằng full raw token.

- [x] **Step 5: CLI không nhận raw token qua argument**

- `import-env --site drupal-vn-primary --env VF_SERVICE_TOKEN`: đọc env, hash, không in raw.
- `rotate --site ...`: tạo token, revoke credential active trong transaction, insert mới, commit rồi in plaintext đúng một lần.
- `revoke --credential <uuid>`: revoke nhưng từ chối nếu site không còn credential active khác, trừ `--allow-no-active` được dùng có chủ đích lúc disable site.
- `list`: chỉ prefix/status/time.

- [x] **Step 6: RED/GREEN site config theo môi trường**

`site_config.py set-from-env --site drupal-vn-primary --base-url-env DRUPAL_BASE_URL --secret-ref DRUPAL` đọc URL từ env, không nhận password/token và không in secret value. Validate absolute `http|https`, host bắt buộc, không userinfo/query/fragment; bỏ trailing slash. `show --site ...` chỉ in slug/base URL/secret-ref **name**/active/pause. Test chứng minh missing env hoặc URL sai không update DB, staging URL thay giá trị DDEV, và output không chứa `DRUPAL_PASSWORD`.

- [x] **Step 7: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\test_site_config.py
.\.venv\Scripts\python.exe scripts\test_site_credentials.py
.\.venv\Scripts\python.exe scripts\migrate.py apply
git -C .. add multiagent/migrations/0004_api_connector.sql multiagent/src/review_platform/api multiagent/scripts/site_config.py multiagent/scripts/site_credential.py multiagent/scripts/test_migrations.py multiagent/scripts/test_site_config.py multiagent/scripts/test_site_credentials.py
git commit -m "feat: add per-site API credentials and connector config"
```

---

### Task 2: API v1 contract và site-derived profile

**Files:**
- Create: `multiagent/src/review_platform/api/models.py`
- Create: `multiagent/src/review_platform/api/router.py`
- Modify: `multiagent/src/api.py`
- Create: `multiagent/scripts/test_api_v1.py`

**Interfaces:**
- `POST /api/v1/jobs`.
- `GET /api/v1/jobs/{job_id:uuid}`.
- `GET /api/v1/jobs/by-content/{external_content_id}`.

- [x] **Step 1: RED request validation/auth/scope**

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

- [x] **Step 2: RED status semantics**

- queued 202;
- duplicate 200;
- dead-letter cùng scoped key trả 409 khi `force=false`; `force=true` tạo job mới linked tới failed row và audit source `manual`;
- site paused 423;
- no profile match 422 với code `profile_not_found`, không default;
- database failure 503, không báo queued giả.

- [x] **Step 3: Implement dependency + router**

Auth dependency dùng request-scoped conn; lấy `SitePrincipal`; `select_review_context` bằng site principal + body content/lang. Correlation ID server generate UUID; không nhận từ body ở MVP. Response có `job_id` public UUID, status, duplicate bool, policy_version; không trả DB numeric id/secret.

GET status lọc site. `last_error` chỉ trả code sanitized (`connector_auth`, `input_hash_mismatch`, `llm_transient`, `writeback_failed`, `internal`), không raw exception.

- [x] **Step 4: Request-size middleware**

Chỉ áp `/api/v1`: Content-Length >16384 trả 413 trước parse; thiếu Content-Length vẫn đọc qua ASGI limiter tối đa 16384+1, không tin header để bypass.

- [x] **Step 5: Include router, giữ legacy**

`api.py` include v1 router; `/jobs` và `/jobs/by-node` vẫn tồn tại, response có header `Deprecation: true`. MVP không phát `Sunset` khi chưa có ngày loại bỏ được phê duyệt riêng.

- [x] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_api_v1.py
.\.venv\Scripts\python.exe scripts\test_api.py
git -C .. add multiagent/src/review_platform/api multiagent/src/api.py multiagent/scripts/test_api_v1.py
git commit -m "feat: expose site-scoped review API v1"
```

---

### Task 3: Connector protocol, env secrets, revision fetch và result callback client

**Files:**
- Create: `multiagent/src/review_platform/connectors/__init__.py`
- Create: `multiagent/src/review_platform/connectors/base.py`
- Create: `multiagent/src/review_platform/connectors/secrets.py`
- Create: `multiagent/src/review_platform/connectors/drupal.py`
- Create: `multiagent/src/review_platform/connectors/runtime.py`
- Create: `multiagent/scripts/test_drupal_connector.py`

**Interfaces:**
- `ContentDocument(fields: dict[str,str], raw_content: dict, source_url: str | None, external_revision_id: str | None, content_type: str, langcode: str)`.
- `PendingContent(external_content_id, external_revision_id, content_hash, content_type, langcode, source_url)`; feed không mang full fields.
- `ConnectorHealth(ok: bool, status_code: int | None, checked_at: datetime, error_code: str | None)`.
- `WriteBackRequest(run_id, external_content_id, expected_revision_id, content_hash, content_hash_version, status, score, suggestions, report_json)`.
- `WriteBackResult(outcome: Literal["applied", "already_applied", "content_superseded"], applied_revision_id: str | None)`.
- Protocol methods `fetch_content`, `write_back`, `list_pending`, `health`.

- [x] **Step 1: RED secret resolver**

For `secret_ref='DRUPAL'`, read `DRUPAL_USER`, `DRUPAL_PASSWORD`; missing one raises `ConnectorSecretError` listing env name but not value. Reject secret_ref not matching `^[A-Z][A-Z0-9_]{0,63}$` to prevent arbitrary env lookup from compromised DB.

- [x] **Step 2: RED exact revision URL và six fields**

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

- [x] **Step 3: RED error classification và retry một tầng**

401/403 → `ConnectorAuthError`, no retry. 404 revision → `ConnectorRevisionNotFound`, no retry. Result callback 409 code `content_superseded` → typed terminal result, không coi là transport failure. Timeout/429/5xx → `ConnectorTransientError(retry_after_seconds)` sau đúng **một** HTTP call; parse `Retry-After` dạng delta-seconds, clamp 0–600 và bỏ qua date/malformed. Schema response missing/sai keys → `ConnectorPayloadError`, no blind retry. Queue `fail()` ở Foundation mới sở hữu tối đa 3 attempt + jitter, tránh 3×3 nested calls.

- [x] **Step 4: Implement connector**

Không import env tại module load. `DrupalConnector(site, credentials, request_fn=requests.request)` giữ base URL/site context. Mỗi method gọi transport một lần và trả/raise typed result. `write_back` POST `/vf-ai/integration/v1/results` với expected revision/hash/version + `run_id` và đúng bốn field AI; không dùng JSON:API PATCH, không gửi moderation state. Test khóa ba response `applied`, `already_applied`, `content_superseded` và chứng minh retry dùng cùng body/run ID.

`health` gọi capability endpoint và pending feed; nếu feed có item thì fetch exact revision và validate fingerprint metadata. Empty feed vẫn phải có capability `revision_read=true`. Health không gọi result callback và không tạo revision.

- [x] **Step 5: Runtime prepared document**

`runtime.activate(connector, prepared_document)` dùng `ContextVar` token/reset trong `finally`. Compatibility `drupal_client.fetch_content(node_id)` ở Task 5 sẽ đọc prepared doc; nếu không active vẫn dùng legacy client.

- [x] **Step 6: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_drupal_connector.py
git -C .. add multiagent/src/review_platform/connectors multiagent/scripts/test_drupal_connector.py
git commit -m "feat: add revision-aware Drupal connector"
```

---

### Task 4: Fingerprint v2 phủ đủ sáu input, khớp Python/PHP

**Files:**
- Create: `multiagent/src/review_platform/fingerprint.py`
- Create: `multiagent/scripts/test_platform_fingerprint.py`
- Create: `drupal/web/modules/custom/vf_ai_review/src/AiInputFingerprint.php`
- Create: `drupal/scripts/input_fingerprint_v2_fixture.json`
- Create: `drupal/scripts/test_ai_input_fingerprint.php`
- Modify: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`
- Modify: `drupal/scripts/test_ai_report_renderer.php`

**Interfaces:**
- Produces Python `input_fingerprint(fields: Mapping[str, object]) -> str`.
- Produces PHP `AiInputFingerprint::hash(array $fields): string`.
- Exact order: title, body, summary, url_alias, meta_description, image_alt.

- [x] **Step 1: Tạo cross-language fixture literal**

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

- [x] **Step 2: RED Python/PHP**

Canonical bytes là `b"v2\n" + UTF-8(json)` với compact JSON, unescaped Unicode/slashes và insertion order exact. Missing/None field becomes empty string. Thay riêng `url_alias` hoặc `image_alt` phải đổi hash — khóa nợ N2.

- [x] **Step 3: Implement both languages**

Python dùng `json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))`. PHP dùng ordered associative array + `json_encode(JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)`, prefix `"v2\n"`.

Tạo `vf_ai_review_input_fields(NodeInterface $node): array` lấy sáu input từ node: alias qua `path_alias.manager`; ảnh đại diện lấy `field_image.alt`; ảnh body dùng cùng label/order với Python `_extract_image_alt`. Test thẻ alt double/single/unquoted/missing, không nhầm `data-alt`, và test riêng featured image đứng trước body image.

Stale banner phải tương thích lịch sử: report có `content_hash_version=2` dùng `AiInputFingerprint::hash(vf_ai_review_input_fields($node))`; report thiếu version/`version=1` tiếp tục dùng `AiReportRenderer::contentHash(vf_ai_review_hash_fields($node))`. **Không đổi trigger ở Task 4:** nó tiếp tục gửi hash v1 sang endpoint legacy cho tới commit client cutover Task 7; nếu gửi hash v2 sớm, migration default version 1 sẽ làm worker rollback so sai thuật toán.

- [x] **Step 4: GREEN cross-language**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_platform_fingerprint.py
Set-Location ..\drupal
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_ai_report_renderer.php
```

Expected: hai bên cùng literal expected.

- [x] **Step 5: Commit**

```powershell
git -C .. add multiagent/src/review_platform/fingerprint.py multiagent/scripts/test_platform_fingerprint.py drupal/web/modules/custom/vf_ai_review/src/AiInputFingerprint.php drupal/web/modules/custom/vf_ai_review/vf_ai_review.module drupal/scripts/input_fingerprint_v2_fixture.json drupal/scripts/test_ai_input_fingerprint.php drupal/scripts/test_ai_report_renderer.php
git commit -m "fix: fingerprint every field used by review engine"
```

---

### Task 5: Worker prefetch/verify rồi chạy graph qua connector context

**Files:**
- Modify: `multiagent/src/drupal_client.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/job_queue.py`
- Modify: `multiagent/src/audit.py`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Modify: `multiagent/src/review_platform/admin/templates/review_detail.html`
- Modify: `multiagent/scripts/test_worker.py`
- Modify: `multiagent/scripts/test_worker_graph_integration.py`
- Modify: `multiagent/scripts/test_drupal_client_worker.py`
- Modify: `multiagent/scripts/test_admin_dashboard.py`
- Modify: `multiagent/scripts/test_admin_reviews.py`

**Interfaces:**
- Produces: `fail_permanent(conn, job_id, error_code, safe_message)`.
- Produces: `supersede(conn, job_id, reason_code="content_superseded") -> None`, chỉ chuyển chính row `running|queued` sang `superseded` và lưu safe code.
- Produces: connector factory from job site.
- Keeps graph input/output behavior for `cam_nang/vi`.
- `worker.chay_mot_job(..., fixture_run: bool = False)`; production loop không truyền true.

- [x] **Step 1: RED “mismatch before LLM”**

Fake connector returns fields hash khác job. Spy invoke must remain zero calls; job becomes failed code `input_hash_mismatch`; no run_log result. Test exact revision fetch occurs before invoke.

- [x] **Step 2: RED legacy v1 rollback compatibility**

Job từ endpoint legacy có `content_hash_version=1`, `external_revision_id=null` và hash bốn field. Assert worker fetch `rel:working-copy`, lấy revision ID thực từ response, tính bằng `text_utils.content_hash()` và hoàn tất qua callback; fingerprint v2 không được gọi. Job v2 vẫn bắt buộc exact revision và sáu field. Test âm cố tình so v1 bằng v2 phải đỏ với `input_hash_mismatch` để khóa nguyên nhân rollback từng bị hỏng.

- [x] **Step 3: RED prepared document/one fetch và stale-write race**

Success path: connector fetch count 1; graph fetch node reads prepared doc through compatibility wrapper, not second HTTP; invoke receives `node_id`, `content_type`, `langcode`; connector callback count 1 after audit.

Race test: job A revision 10 bắt đầu, job B revision 11 hoàn tất trước, rồi callback A trả `content_superseded`. Assert A không ghi payload, run A `writeback_status='superseded'`, `q.supersede()` đưa job A về terminal `superseded`, B/report hiện hành không đổi và A không retry LLM/callback. Ambiguous-timeout test: callback đã apply nhưng response mất; retry saved payload cùng `run_id` nhận `already_applied`, complete job, không tạo run/usage/revision thứ hai.

- [x] **Step 4: Implement compatibility delegation**

`drupal_client.fetch_content()` first checks active runtime prepared document for matching external ID; returns `{fields, raw_content}`. Không active thì legacy code unchanged. `write_back` compatibility remains for manual graph scripts.

- [x] **Step 5: Implement worker sequence**

1. claim scoped job;
2. gọi `find_reusable_writeback` để lấy saved run/payload/precondition nếu có, chưa gọi network;
3. load site + credentials, build connector;
4. nếu có reusable run, callback bằng đúng public `run_id`/expected revision/hash/version cũ rồi kết thúc, không fetch/LLM/run mới;
5. nếu không reusable: v2 prefetch exact revision; v1 legacy thiếu revision fetch `rel:working-copy` và lấy revision ID thật từ response;
6. chọn fingerprint theo `content_hash_version`: v1 = `text_utils.content_hash()` bốn field, v2 = canonical sáu field; compare trước LLM;
7. activate runtime prepared document;
8. invoke graph without write-back with explicit profile keys;
9. generate `run_public_id=uuid4()`, build payload, replace `report_json.content_hash` with job hash, thêm đúng `content_hash_version` + `platform_run_id`; gọi `ghi_scoped(run_public_id=...)` để DB và payload dùng cùng UUID;
10. connector callback once với run public UUID + expected revision/hash/version: `applied|already_applied` → mark succeeded/complete; `content_superseded` → trong cùng `conn.transaction()` gọi `mark_writeback(status="superseded")` + `q.supersede()` để không có nửa trạng thái; transient failure → mark failed và để chính job retry saved payload.

Không thêm full fields/raw content vào job/run/audit. `source='manual', force=true` sau run succeeded luôn đi qua bước 3–10 để chấm mới; không bị nhánh reuse nuốt mất ý nghĩa “chấm lại”. `fixture_run` được truyền vào `ghi_scoped(is_fixture=...)`; production worker loop luôn default false.

Admin dashboard/cost/decision aggregates thêm `WHERE is_fixture=false`. Review detail vẫn cho xem fixture nhưng hiển thị badge/banner “STAGING FIXTURE — không phải đánh giá AI”; test seed một fixture run để chứng minh metric không tăng.

- [x] **Step 6: Error classification**

Auth/revision/payload/hash mismatch → permanent failed without 3 blind LLM attempts. `content_superseded` → terminal superseded, không retry và không mang payload cũ sang revision mới. Timeout/429/5xx → `q.fail(..., retry_after_seconds=exc.retry_after_seconds)`; queue là tầng duy nhất quyết backoff/max 3. Unexpected programming → internal retry capped bởi cùng queue attempts. Every last_error stored as safe code + short message; raw exception only server log sau redaction Plan 5.

- [x] **Step 7: GREEN regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_worker.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
.\.venv\Scripts\python.exe scripts\test_drupal_client_worker.py
```

Expected: one fetch, one callback, mismatch zero invoke; stale job không ghi; retry timeout không gọi engine/callback apply lần hai; v1 và v2 đều qua đúng hash branch.

- [x] **Step 8: Commit**

```powershell
git -C .. add multiagent/src/drupal_client.py multiagent/src/worker.py multiagent/src/job_queue.py multiagent/src/audit.py multiagent/src/review_platform/admin/queries.py multiagent/src/review_platform/admin/templates/review_detail.html multiagent/scripts/test_worker.py multiagent/scripts/test_worker_graph_integration.py multiagent/scripts/test_drupal_client_worker.py multiagent/scripts/test_admin_dashboard.py multiagent/scripts/test_admin_reviews.py
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

- [x] **Step 1: RED multi-site/pause/dead-letter**

Active site A enqueue; paused B không gọi connector; inactive C bỏ qua. Pending working copy chọn profile explicit, fingerprint v2. Dead-letter đúng scoped key không hồi sinh. Một site connector lỗi không làm bỏ site sau.

- [x] **Step 2: Implement reconciliation**

Load active non-paused sites; page connector `list_pending` đến khi `next_after_revision_id=null`, tối đa 50 item/page. Profile select từng item, đối chiếu `content_type/langcode`, enqueue source reconcile với revision ID + fingerprint v2 do Drupal feed gửi. Legacy item explicit không có revision mới dùng `external_revision_id=null` và worker fetch `rel:working-copy`; feed MVP mới luôn có revision ID.

- [x] **Step 3: Worker pause semantics**

Queue claim đã bỏ paused rows từ Plan 1. Reconcile cũng bỏ pause. In-progress không bị kill. Resume không enqueue hàng loạt trùng vì scoped dedup.

- [x] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_reconcile.py
git -C .. add multiagent/src/reconcile.py multiagent/src/worker.py multiagent/scripts/test_reconcile.py
git commit -m "feat: reconcile pending content per active site"
```

---

### Task 7: Drupal integration endpoints an toàn và client API v1

**Files:**
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/ChamLaiController.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/TrangThaiController.php`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/PendingController.php`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/CapabilitiesController.php`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/ResultController.php`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Service/AiResultWriter.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.info.yml`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.routing.yml`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.permissions.yml`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.services.yml`
- Create: `drupal/scripts/configure_ai_service_role.php`
- Create: `drupal/scripts/test_ai_service_role.php`
- Modify: `drupal/scripts/test_vf_ai_trigger.php`
- Create: `drupal/scripts/test_ai_result_callback.php`

**Interfaces:**
- `guiJob(uuid, revisionId, contentType, langcode, hash, source, force)`.
- Status endpoint `/api/v1/jobs/by-content/{uuid}`.
- Integration endpoints `GET /vf-ai/integration/v1/pending`, `GET /vf-ai/integration/v1/capabilities`, `POST /vf-ai/integration/v1/results` dùng Basic auth + permission riêng.

- [x] **Step 1: RED pending/capability/result callback contract**

`test_ai_result_callback.php` tạo revision 10 rồi 11 và khóa các case:

- request revision 10/hash 10 sau khi 11 tồn tại → 409 `{code:"content_superseded"}`, bốn field AI không đổi;
- request đúng latest revision/hash → 200 `{outcome:"applied", applied_revision_id:"..."}` và chỉ bốn field AI đổi;
- gửi lại cùng `run_id` sau response timeout giả → 200 `{outcome:"already_applied"}`, revision count không tăng;
- unknown/extra key, invalid UUID/revision/hash/version, request >512 KiB, suggestions >64 KiB, report JSON >384 KiB, thiếu permission hoặc non-Basic auth → 4xx, không save;
- payload cố gửi `moderation_state`, title/body hoặc field thứ năm bị từ chối trước entity save.

`test_vf_ai_trigger.php` có một published default + pending non-default và chứng minh feed trả pending revision mới nhất; article đã rời Needs Review không xuất hiện; pagination không lặp revision; capability booleans đổi đúng khi bỏ từng permission.

- [x] **Step 2: Implement metadata feed, capabilities và atomic result writer**

`vf_ai_trigger.info.yml` khai báo dependency `drupal:basic_auth`. Ba route chỉ cho `_auth: ['basic_auth']`, tắt cache theo user và trả `Cache-Control: no-store`; permissions restricted là `access vf ai integration feed`, `access vf ai integration capabilities`, `submit vf ai integration result`.

Pending controller clamp `limit` 1–50, validate `after_revision_id>=0`, query node với `accessCheck(TRUE)`, `latestRevision()`, bundle article, moderation `needs_review`, `vid > after`, sort vid tăng dần, rồi load đúng revision. Mỗi item chỉ có `external_content_id` UUID, `external_revision_id`, `content_type='cam_nang'`, `langcode`, `content_hash`, `content_hash_version=2`, `source_url`; response có `next_after_revision_id` hoặc null. Không serialize field nội dung/AI/secret.

Capabilities controller trả version + booleans `pending_feed`, `result_callback`, `revision_read` theo permission hiện hành, không trả username/role/secret. `AiResultWriter` mở DB transaction, khóa row node bằng `SELECT ... FOR UPDATE`, load lại latest revision trong lock, kiểm expected revision + fingerprint đúng version, rồi mới set đúng bốn AI fields và save new revision. `report_json.platform_run_id` là idempotency key: nếu latest report đã có cùng run ID thì trả `already_applied` trước conflict. Không gọi access-bypass generic từ request và không nhận field tùy ý.

- [x] **Step 3: Cấu hình machine role đủ dùng trước cutover**

`configure_ai_service_role.php` idempotent, tạo role `ai_service` nếu chưa có, mặc định dry-run và chỉ apply với literal `--apply`. Exact allowlist: `access content`, `view any unpublished content`, `view latest version`, `view article revisions`, `access vf ai integration feed`, `access vf ai integration capabilities`, `submit vf ai integration result`; từ chối nếu permission thiếu và gỡ `edit any article content` nếu role cũ có. Không tạo/đổi user/password, không chạm UID 1 hay tự gán role cho tài khoản. Site owner phải gán role này cho đúng user mang tên từ `DRUPAL_USER`; capability test là bằng chứng assignment đúng. `test_ai_service_role.php` fail nếu có edit/delete/publish/workflow/admin permissions. Hardening Task 4 sau đó mở rộng cùng nguyên tắc cho `content_editor`/`site_admin` và kiểm lại trên staging.

- [x] **Step 4: GREEN endpoints và commit ranh giới Drupal trước cutover**

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_result_callback.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev drush php:script scripts/configure_ai_service_role.php -- --apply
ddev exec php scripts/test_ai_service_role.php
ddev drush cr
git -C .. add drupal/web/modules/custom/vf_ai_trigger/src/Controller/PendingController.php drupal/web/modules/custom/vf_ai_trigger/src/Controller/CapabilitiesController.php drupal/web/modules/custom/vf_ai_trigger/src/Controller/ResultController.php drupal/web/modules/custom/vf_ai_trigger/src/Service/AiResultWriter.php drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.info.yml drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.routing.yml drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.permissions.yml drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.services.yml drupal/scripts/configure_ai_service_role.php drupal/scripts/test_ai_service_role.php drupal/scripts/test_ai_result_callback.php drupal/scripts/test_vf_ai_trigger.php
git commit -m "feat: add revision-safe Drupal integration callbacks"
```

Commit này phải được deploy trước client cutover và **không** bị revert khi rollback client về `/jobs` legacy.

- [x] **Step 5: RED API v1 payload contract**

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

- [x] **Step 6: Implement hook/controller mapping**

Article maps `cam_nang`; `$node->language()->getId()`; `$node->getRevisionId()`. Hash fields from shared v2 helper. Trigger chỉ coi đã chấm khi report version 2 và hash v2 khớp; report v1 enqueue một lượt nâng cấp sau cutover. Manual rescore same revision + source manual + force true. Endpoint URL `/api/v1/jobs` and status escaped UUID path. Commit này phải chứa cả thay đổi trigger/hash và ServiceClient để không có trạng thái trung gian “hash v2 gửi vào endpoint legacy version 1”.

- [x] **Step 7: Preserve save failure isolation**

All network error still swallowed/logged; Drupal save never throws. 423 pause logs notice “intake paused”; 409 dead letter behavior giữ. 401/403 warning rõ integration credential, không log token.

- [x] **Step 8: GREEN Drupal client tests**

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev exec php scripts/test_ai_input_fingerprint.php
ddev exec php scripts/test_vf_ai_trigger.php
ddev drush cr
```

- [x] **Step 9: Commit riêng client cutover**

```powershell
git -C .. add drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module drupal/web/modules/custom/vf_ai_trigger/src/Controller/ChamLaiController.php drupal/web/modules/custom/vf_ai_trigger/src/Controller/TrangThaiController.php drupal/scripts/test_vf_ai_trigger.php
git commit -m "feat: send revision-aware jobs to API v1"
```

---

### Task 8: Connection page, test connection và pause/resume

**Files:**
- Create: `multiagent/src/review_platform/admin/templates/connection.html`
- Modify: `multiagent/src/review_platform/admin/router.py`
- Modify: `multiagent/src/review_platform/admin/queries.py`
- Create: `multiagent/scripts/test_admin_connection.py`

**Interfaces:**
- `GET /admin/connection` viewer+.
- `POST /admin/connection/test` operator+.
- `POST /admin/connection/pause`, `/resume` operator+.

- [x] **Step 1: RED RBAC/CSRF/semantics**

Viewer sees status but POST 403. Operator without CSRF 403. Test connection updates `last_health_*`, audit outcome, never returns credential value. A site thiếu một trong `pending_feed|result_callback|revision_read` phải fail dù generic article collection GET trả 200. Empty pending feed vẫn kiểm được capability; feed có item phải fetch exact revision và so metadata/hash mà không ghi Drupal. Pause leaves running job, keeps queued, blocks claim/API/reconcile; resume restores.

- [x] **Step 2: Implement connection service**

Health dùng cùng connector gọi authenticated capabilities + pending feed với timeout 2s; nếu có pending item thì GET exact revision và validate external ID/revision/fingerprint. Không gọi result callback, không PATCH, không LLM. Store code `ok|auth_failed|capability_missing|revision_read_failed|timeout|server_error|payload_error`, checked time và safe message. Admin HTML shows site slug/base URL/secret ref **name only**, active profile/policy, token prefix active list, last result.

- [x] **Step 3: Implement pause transaction/audit**

Lock site row; idempotent pause/resume returns 200/303; reason optional max 300. Do not update queued rows. Dashboard connector health reads saved status.

- [x] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_connection.py
git -C .. add multiagent/src/review_platform/admin multiagent/scripts/test_admin_connection.py
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

- [x] **Step 1: Cấu hình site đúng môi trường và import current token**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\site_config.py set-from-env --site drupal-vn-primary --base-url-env DRUPAL_BASE_URL --secret-ref DRUPAL
.\.venv\Scripts\python.exe scripts\site_config.py show --site drupal-vn-primary
.\.venv\Scripts\python.exe scripts\site_credential.py import-env --site drupal-vn-primary --env VF_SERVICE_TOKEN
```

Expected: `show` phản ánh host nằm trong allowlist chính xác của môi trường; production tuyệt đối không dùng `.ddev.site`, còn local/DDEV rehearsal phải được khai báo rõ là local. Credential chỉ print prefix/id. Xác nhận user `DRUPAL_USER` đã được site owner gán role `ai_service`; capability test sau đó chứng minh quyền thực. Sai/missing URL hoặc user chưa có role dừng cutover trước worker. Smoke POST `/api/v1/jobs` với một fake external ID/hash vào test DB/schema, không production queue.

- [x] **Step 2: Deploy API/worker first**

Deploy callback/capability commit Drupal từ Task 7 trước nhưng chưa đổi ServiceClient enqueue. Restart API/worker, health current, legacy endpoint/hash v1 vẫn hoàn tất end-to-end. Test connection admin success đủ feed/result/revision-read. Không cut client Drupal sang `/api/v1` trước bước này.

- [x] **Step 3: Deploy Drupal module + one-article smoke không gọi LLM**

Tạo `staging_connector_smoke.py` dùng dependency injection hiện có của worker với fake engine output đánh dấu rõ `fixture=true`, `note="STAGING FIXTURE — không phải đánh giá AI"`, đồng thời gọi worker với `fixture_run=true`. Script bắt buộc `--job-id <uuid> --confirm-staging-fixture`, từ chối nếu site base URL không phải `.ddev.site`/allowlist staging và từ chối nếu queue có job queued/running khác. Worker hiện import `ai_core` ở module load, nên test thay `ai_core.get_client` bằng hàm raise và assert không bao giờ được gọi; không dùng API key. `test_staging_connector_smoke.py` khóa các guard này, `run_log.is_fixture=true` và output shape.

Stop worker staging, chọn article không thuộc gold/E1, record UUID/revision/hash, chuyển Needs Review, lấy job ID từ admin/watchdog, rồi chạy script. Verify exactly one scoped job, connector fetch đúng revision, one fixture run, callback outcome `applied`, đúng một AI result revision và editor report hiện banner fixture. Khởi động lại worker sau khi queue sạch. Không trình bày fixture score như kết quả chất lượng.

- [x] **Step 4: Test write-back reuse**

Trong `test_staging_connector_smoke.py` + fake transport, làm callback apply nhưng mất response rồi retry; assert cùng `run_id` nhận `already_applied`, run payload reused, engine invocation vẫn đúng 1, usage không tăng và Drupal revision không tăng lần hai. Thêm race A(rev cũ)/B(rev mới), assert A nhận `content_superseded` và không ghi đè B. Không cố tình làm thất bại trên Drupal staging thật.

- [x] **Step 5: Rollback rehearsal**

Revert riêng commit client `ServiceClient`/hook về endpoint legacy; **giữ nguyên** commit pending/capability/result callback. Verify save enqueue job `content_hash_version=1`, worker fetch working copy, dùng hash bốn field và callback hoàn tất; chỉ nhận HTTP 2xx từ `/jobs` chưa đủ chứng minh rollback. Roll forward lại. Không rollback/drop migration.

- [x] **Step 6: Ghi nhận deprecation nhưng không tự đặt Sunset**

Legacy response tiếp tục chỉ có `Deprecation: true`. Tài liệu ghi endpoint removal là nợ sau MVP; `Sunset` và việc xóa endpoint cần quyết định/plan riêng sau khi production đã qua cửa sổ rollback, không nằm trong commit cutover.

- [x] **Step 7: Evidence + commit**

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

- [x] **Step 1: Focused tests**

Chạy migration, site credential, API v1, fingerprint Python/PHP, connector, worker integration, reconcile, admin connection, legacy API/Drupal tests.

- [x] **Step 2: Full offline suite và score gate**

Chạy toàn `scripts/test_*.py`, Drupal PHP tests, parent `prompt_version`/score-path diff. `text_utils.py`, graph/agents/config phải không đổi.

- [x] **Step 3: Data/privacy assertions**

SQL/HTML/log scan xác nhận không có body/title/Authorization/password/session raw. Assert every new job/run có site/profile/policy/revision/hash version/correlation; một callback apply tối đa một lần, stale result không ghi và retry mơ hồ idempotent.

- [x] **Step 4: Evidence/docs commit**

```powershell
git -C .. add docs/evidence/platform-api-connector-verification.txt docs/technical-debt.md
git commit -m "docs: record API and connector verification"
```
