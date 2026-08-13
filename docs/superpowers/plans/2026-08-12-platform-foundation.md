# Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa database hiện hành sang migration có version và làm mọi job/run mang site, profile, policy, external revision cùng correlation ID mà không làm gãy API/worker cũ.

**Architecture:** Một migration runner SQL thuần khớp phong cách psycopg hiện tại, có checksum để cấm sửa migration đã apply. Schema seed đúng một site/profile; các hàm scoped mới được thêm cạnh compatibility wrapper cũ để cutover từng bước, không big-bang.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL 17 + pgvector, SQL migration files, các test script assert hiện có.

**Parent plan:** `docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md`.

**Quy ước chạy lệnh:** Mỗi code block PowerShell bắt đầu với working directory `D:\drupal-multiagent-seo\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

## Global Constraints

- Không sửa score path hoặc gọi LLM.
- Default IDs cố định: site `00000000-0000-4000-8000-000000000001`, profile `00000000-0000-4000-8000-000000000002`.
- Default codes: site `drupal-vn-primary`, profile `cam-nang-vn`, policy `cam-nang-vn-v1`.
- Migration đã apply không được sửa; mismatch checksum phải chặn startup.
- Migration từ schema hiện hành phải backfill trước khi thêm `NOT NULL`/FK/index.
- Không lưu trường nội dung đầy đủ trong cột mới.
- Compatibility wrapper `/jobs` và worker hiện tại phải tiếp tục chạy tới Plan API/connector.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/src/platform/__init__.py` | Đánh dấu package mới, không side effect |
| `multiagent/src/platform/migrations.py` | Discover/checksum/status/apply/require migration |
| `multiagent/src/platform/database.py` | Kết nối mới theo context, không dùng shared connection cho request |
| `multiagent/src/platform/context.py` | Dataclass `SiteContext`, `ReviewProfileContext`, `ReviewContext` |
| `multiagent/src/platform/sites.py` | Query site/profile assignment chính xác một kết quả |
| `multiagent/migrations/0001_platform_foundation.sql` | Baseline + backfill site/profile/job/run/KB |
| `multiagent/scripts/migrate.py` | CLI `status`/`apply` |
| `multiagent/scripts/test_migrations.py` | Unit discovery/checksum + integration upgrade |
| `multiagent/scripts/test_platform_context.py` | Profile selection/no fallback |
| `multiagent/src/job_queue.py` | Thêm API scoped, claim tôn trọng pause |
| `multiagent/src/audit.py` | Ghi/tra run scoped theo site/policy |
| `multiagent/src/worker.py` | Truyền metadata job vào audit, chưa đổi engine/connector |

---

### Task 1: Migration runner có checksum

**Files:**
- Create: `multiagent/src/platform/__init__.py`
- Create: `multiagent/src/platform/migrations.py`
- Create: `multiagent/src/platform/database.py`
- Create: `multiagent/scripts/migrate.py`
- Create: `multiagent/scripts/test_migrations.py`

**Interfaces:**
- Produces: `discover(migrations_dir: Path) -> list[Migration]`.
- Produces: `status(conn, migrations_dir: Path) -> MigrationStatus`.
- Produces: `apply_pending(conn, migrations_dir: Path) -> list[int]`.
- Produces: `require_current(conn, migrations_dir: Path) -> None`.
- Produces: `open_connection(dsn_str: str | None = None)` context manager.

- [ ] **Step 1: Viết test RED cho discovery và checksum**

Test dùng `tempfile.TemporaryDirectory()` tạo `0001_first.sql`, `0002_second.sql`; assert version tăng dần, SHA-256 ổn định, file sai tên và version trùng bị `MigrationError`:

```python
def test_discover_sap_xep_va_chan_version_trung():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "0002_second.sql").write_text("SELECT 2;", encoding="utf-8")
        (root / "0001_first.sql").write_text("SELECT 1;", encoding="utf-8")
        found = migrations.discover(root)
        assert [m.version for m in found] == [1, 2]
        assert found[0].checksum == hashlib.sha256(b"SELECT 1;").hexdigest()
        (root / "0001_duplicate.sql").write_text("SELECT 3;", encoding="utf-8")
        with expect(migrations.MigrationError, "trung version 0001"):
            migrations.discover(root)
```

`expect()` là context manager nhỏ định nghĩa ngay trong test, bắt đúng exception và substring; không thêm test framework.

- [ ] **Step 2: Chạy để thấy RED**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\test_migrations.py
```

Expected: FAIL vì chưa có `platform.migrations`.

- [ ] **Step 3: Cài migration types và discovery**

Trong `platform/migrations.py` định nghĩa chính xác:

```python
@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str

@dataclass(frozen=True)
class MigrationStatus:
    applied: tuple[int, ...]
    pending: tuple[int, ...]

class MigrationError(RuntimeError):
    pass
```

Regex filename là `r"^(\d{4})_([a-z0-9_]+)\.sql$"`. `discover()` chỉ đọc file `.sql`, từ chối filename sai, version trùng, khoảng trống trong chuỗi version và danh sách không tăng sau sort. Checksum băm đúng bytes trên disk, không normalize newline.

- [ ] **Step 4: Thêm bảng lịch sử và transaction apply**

`_ensure_history_table(conn)` tạo:

```sql
CREATE TABLE IF NOT EXISTS schema_migration (
  version integer PRIMARY KEY,
  name text NOT NULL,
  checksum char(64) NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
)
```

`status()` so từng version đã apply với checksum file; thiếu file hoặc mismatch đều raise. `apply_pending()` chạy mỗi file trong `with conn.transaction():`, execute toàn file rồi INSERT history cùng transaction. `require_current()` raise message liệt kê pending và lệnh `python scripts/migrate.py apply`.

- [ ] **Step 5: Thêm CLI và connection context**

`platform/database.py`:

```python
@contextmanager
def open_connection(dsn_str: str | None = None):
    conn = psycopg.connect(dsn_str or db.dsn(), autocommit=True)
    try:
        yield conn
    finally:
        conn.close()
```

`scripts/migrate.py` chỉ nhận `status|apply`, mặc định `status`; resolve `multiagent/migrations` từ vị trí script, in version đã apply/pending; exit 2 khi `MigrationError`.

- [ ] **Step 6: GREEN và meta-test**

```powershell
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: discovery/checksum tests PASS; phần Postgres in `[SKIP]` nếu DB tắt, không được in PASS giả.

- [ ] **Step 7: Commit**

```powershell
git -C .. add multiagent/src/platform multiagent/scripts/migrate.py multiagent/scripts/test_migrations.py
git commit -m "feat: add versioned SQL migration runner"
```

---

### Task 2: Migration 0001 nâng schema hiện hành không mất dữ liệu

**Files:**
- Create: `multiagent/migrations/0001_platform_foundation.sql`
- Modify: `multiagent/scripts/test_migrations.py`

**Interfaces:**
- Produces: tables `site`, `review_profile`, `site_profile_assignment`.
- Upgrades: `review_job`, `run_log`; keeps legacy `node_id` during transition.
- Seeds: one default site/profile/assignment.

- [ ] **Step 1: Viết integration test RED từ schema legacy**

Trong schema test riêng `vf_test_migration`, tự tạo đúng bản rút gọn của `review_job`, `run_log`, `kb_chunk`; insert một queued job và một run payload. Chạy `apply_pending()`, rồi assert:

```python
assert scalar(conn, "SELECT count(*) FROM review_job") == 1
assert scalar(conn, "SELECT count(*) FROM run_log") == 1
assert scalar(conn, "SELECT site_id::text FROM review_job") == DEFAULT_SITE_ID
assert scalar(conn, "SELECT profile_id::text FROM run_log") == DEFAULT_PROFILE_ID
assert scalar(conn, "SELECT external_content_id FROM review_job") == "legacy-node"
assert scalar(conn, "SELECT payload->>'status' FROM run_log") == "needs_revision"
assert migrations.apply_pending(conn, MIGRATIONS_DIR) == []
```

Test thêm trường hợp fresh schema không có table nào và trường hợp sửa bytes file migration sau apply bị checksum guard từ chối.

- [ ] **Step 2: Chạy RED với PostgreSQL đang bật**

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe scripts\test_migrations.py
```

Expected: FAIL vì chưa có `0001_platform_foundation.sql`.

- [ ] **Step 3: Viết phần baseline SQL**

Migration bắt đầu bằng:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS review_job (
  id bigserial PRIMARY KEY,
  node_id text NOT NULL,
  content_hash text NOT NULL,
  status text NOT NULL,
  attempts int NOT NULL DEFAULT 0,
  run_after timestamptz NOT NULL DEFAULT now(),
  claimed_at timestamptz,
  claimed_by text,
  last_error text,
  source text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS run_log (
  id bigserial PRIMARY KEY,
  job_id bigint,
  node_id text NOT NULL,
  content_hash text NOT NULL,
  scored_at timestamptz NOT NULL DEFAULT now(),
  duration_ms int,
  decision text,
  final_score numeric,
  missing_agents jsonb NOT NULL DEFAULT '[]'::jsonb,
  veto_reason text,
  note text,
  agent_results jsonb NOT NULL,
  config_meta jsonb NOT NULL,
  usage jsonb NOT NULL,
  model text NOT NULL,
  payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_chunk (
  collection text NOT NULL,
  chunk_id text NOT NULL,
  document text NOT NULL,
  embedding vector(1024) NOT NULL,
  content_type text NOT NULL,
  langcode text NOT NULL,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (collection, chunk_id)
);
```

Không drop table/index/data.

- [ ] **Step 4: Tạo site/profile/assignment và seed cố định**

SQL phải có đầy đủ check constraint:

```sql
CREATE TABLE site (
  id uuid PRIMARY KEY,
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  connector_type text NOT NULL CHECK (connector_type IN ('drupal')),
  base_url text NOT NULL,
  secret_ref text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  intake_paused boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE review_profile (
  id uuid PRIMARY KEY,
  code text NOT NULL UNIQUE,
  market_code char(2) NOT NULL,
  language_code text NOT NULL,
  content_type text NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'inactive')),
  policy_version text NOT NULL,
  policy_snapshot jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE site_profile_assignment (
  site_id uuid NOT NULL REFERENCES site(id),
  profile_id uuid NOT NULL REFERENCES review_profile(id),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (site_id, profile_id)
);
```

Ngay trong migration tạo constraint trigger `site_profile_assignment_scope_guard` cho INSERT/UPDATE active assignment: lock row `site` tương ứng bằng `FOR UPDATE`, join `review_profile` và từ chối (`unique_violation`) nếu site đã có assignment active khác cùng `(content_type, language_code)`. Trigger thứ hai trên UPDATE `review_profile.content_type/language_code/status` chạy cùng phép kiểm để không tạo trùng bằng cách sửa profile sau khi assign. Migration test tạo profile thứ hai cùng `cam_nang/vi` và phải thấy DB từ chối assignment active, không chỉ chờ application phát hiện.

Seed dùng `INSERT ... ON CONFLICT DO NOTHING`; `policy_snapshot` là literal bất biến sau (hash lowercase, tính từ snapshot `04f10e1`):

```json
{
  "release": "cam-nang-vn-v1",
  "score_path_snapshot": "04f10e1",
  "prompt_version": "020738e209017213",
  "rubric_version": "v1",
  "model": "claude-haiku-4-5-20251001",
  "scoring_key": "cam_nang:vi",
  "scoring_sha256": "d9eeec581888a112fa20faaea545199e698a067209229eac9de0f0193adb90a3",
  "compliance_rules_sha256": "c57be948ed14e1b500b270d4a3676c86c741b6ef555312c60eff9765bda55f4e",
  "brand_rules_sha256": "6f89233c3ed371a62a64d5ae65a4cb3345e086c1bd957de0085dd0c01dbf82a5",
  "factcheck_kb_specs_sha256": "fe2185e06d64dcb237b8b49b683d42d4d3487f2bc7d1187de81e3b6ab05e6d61",
  "brand_guideline_sha256": "9ecc02fde085e4109eff5e5a8f0582ac206afff5a7333bfe1f72293fd1376af2",
  "brand_corpus_index_sha256": "b5fdbe4bf2095c7529b1ab3693896c10ac8dc8da6101268ccec49a1bf81f823b",
  "embedding_model": "BAAI/bge-m3",
  "embedding_dimension": 1024
}
```

Migration test tính lại từng hash từ file nguồn và so literal để chống tài liệu/migration chép sai. `base_url='http://drupal.ddev.site'`, `secret_ref='DRUPAL'` chỉ để giữ tương thích môi trường local hiện tại. Giá trị này không phải cấu hình staging/production; API/Connector Task 1 phải cung cấp CLI cấu hình site và cutover bắt buộc chạy CLI trước worker mới.

- [ ] **Step 5: ALTER/backfill job và run**

Thêm vào `review_job`: `public_id`, `site_id`, `profile_id`, `policy_version`, `external_content_id`, `external_revision_id`, `content_type`, `langcode`, `correlation_id`, `supersedes_job_id`. Thêm vào `run_log`: `public_id`, `site_id`, `profile_id`, `policy_version`, `external_content_id`, `external_revision_id`, `content_type`, `langcode`, `correlation_id`, `writeback_status`, `writeback_error`.

Quy tắc backfill chính xác:

```sql
UPDATE review_job SET
  public_id = COALESCE(public_id, gen_random_uuid()),
  site_id = COALESCE(site_id, '00000000-0000-4000-8000-000000000001'),
  profile_id = COALESCE(profile_id, '00000000-0000-4000-8000-000000000002'),
  policy_version = COALESCE(policy_version, 'cam-nang-vn-v1'),
  external_content_id = COALESCE(external_content_id, node_id),
  content_type = COALESCE(content_type, 'cam_nang'),
  langcode = COALESCE(langcode, 'vi'),
  correlation_id = COALESCE(correlation_id, gen_random_uuid());
```

`run_log` backfill tương tự, gồm `public_id=gen_random_uuid()` cho row cũ và `writeback_status='unknown'`. Code cũ ghi run trước PATCH nên không có dữ liệu để suy thành công hay thất bại; CHECK exact là `writeback_status IN ('unknown','pending','succeeded','failed','superseded')`, không được đổi `unknown` thành `succeeded`. Migration test assert row legacy là `unknown`; dashboard loại nó khỏi cả tử số và mẫu số tỷ lệ write-back, review detail hiển thị `Không có dữ liệu`. Sau khi assert không còn NULL, mới `SET NOT NULL` và thêm FK/check/unique cho `public_id` của cả hai bảng.

Drop index legacy `review_job_dedup`, tạo partial unique:

```sql
CREATE UNIQUE INDEX review_job_scoped_dedup
ON review_job (site_id, external_content_id, content_hash, policy_version)
WHERE status IN ('queued', 'running', 'done');
```

Tạo index claim `(status, run_after, site_id)`, lookup run `(site_id, external_content_id, content_hash, policy_version, scored_at DESC)`, unique `public_id` và FK bằng `DO $$ BEGIN ... END $$` kiểm `pg_constraint` trước khi add.

- [ ] **Step 6: GREEN và xác minh bảo toàn**

```powershell
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\migrate.py status
```

Expected: legacy/fresh/idempotent/checksum tests PASS; DB thật báo pending `0001` nhưng chưa tự apply vào DB dev ở bước test.

- [ ] **Step 7: Apply dev sau backup logic**

```powershell
docker compose exec -T db pg_dump -U vf_agent -d vf_agent -Fc -f /tmp/pre_platform_0001.dump
.\.venv\Scripts\python.exe scripts\migrate.py apply
.\.venv\Scripts\python.exe scripts\migrate.py status
```

Expected: apply version 1; status không còn pending. Không xóa `/tmp` trong task này; evidence/rehearsal xử lý ở Plan 5.

- [ ] **Step 8: Commit**

```powershell
git -C .. add multiagent/migrations/0001_platform_foundation.sql multiagent/scripts/test_migrations.py
git commit -m "feat: migrate existing data to site and profile schema"
```

---

### Task 3: Site/profile context không fallback im lặng

**Files:**
- Create: `multiagent/src/platform/context.py`
- Create: `multiagent/src/platform/sites.py`
- Create: `multiagent/scripts/test_platform_context.py`

**Interfaces:**
- Produces: `SiteContext(id: UUID, slug: str, connector_type: str, base_url: str, secret_ref: str, active: bool, intake_paused: bool)`.
- Produces: `ReviewProfileContext(id: UUID, code: str, market_code: str, language_code: str, content_type: str, policy_version: str, policy_snapshot: dict)`.
- Produces: `ReviewContext(site: SiteContext, profile: ReviewProfileContext)`.
- Produces: `load_site_by_slug(conn, slug: str) -> SiteContext`.
- Produces: `select_review_context(conn, site_id: UUID, content_type: str, langcode: str) -> ReviewContext`.

- [ ] **Step 1: Test RED**

Test trên schema đã migrate: đúng assignment trả `cam-nang-vn`; không match hoặc hai assignment active cùng scope đều raise `ContextSelectionError`, không rơi `default`.

```python
ctx = sites.select_review_context(conn, DEFAULT_SITE_ID, "cam_nang", "vi")
assert ctx.site.slug == "drupal-vn-primary"
assert ctx.profile.policy_version == "cam-nang-vn-v1"
with expect(sites.ContextSelectionError, "khong co profile active"):
    sites.select_review_context(conn, DEFAULT_SITE_ID, "landing_page", "vi")
```

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_platform_context.py
```

Expected: import/module missing.

- [ ] **Step 3: Implement dataclass và query**

Query profile phải join `site_profile_assignment`, `site`, `review_profile`, lọc cả site/profile/assignment active và đúng `content_type/language_code`. Fetch tối đa 2 row để phân biệt 0/1/>1; không dùng `LIMIT 1` che cấu hình trùng.

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_platform_context.py
git -C .. add multiagent/src/platform/context.py multiagent/src/platform/sites.py multiagent/scripts/test_platform_context.py
git commit -m "feat: resolve explicit site and review profile context"
```

---

### Task 4: Queue scoped và pause không claim queued job

**Files:**
- Modify: `multiagent/src/job_queue.py`
- Modify: `multiagent/scripts/test_job_queue.py`
- Modify: `multiagent/scripts/test_api.py`

**Interfaces:**
- Produces: `enqueue_scoped(conn, context: ReviewContext, external_content_id: str, content_hash: str, source: str, *, external_revision_id: str | None = None, force: bool = False, correlation_id: UUID | None = None, supersedes_job_id: int | None = None) -> dict`.
- Keeps temporarily: `enqueue(conn, node_id, content_hash, source, force=False)` wrapping default context.
- `claim()` returns new keys plus legacy alias `node_id=external_content_id` until Plan 4.
- `fail(conn, job_id, error, *, retry_after_seconds: float | None = None, rng=random.random)` keeps maximum 3 claims total.

- [ ] **Step 1: Viết RED cases**

Thêm test:

```python
def test_cung_external_id_khac_site_khong_dedup(conn): ...
def test_cung_site_hash_policy_tra_duplicate(conn): ...
def test_force_lien_ket_supersedes_job_id(conn): ...
def test_pause_giu_queued_va_claim_bo_qua(conn): ...
def test_resume_claim_lai_job_cu(conn): ...
def test_transient_retry_co_jitter_va_toi_da_ba_claim(conn): ...
```

Pause test update `site.intake_paused=true`, assert row vẫn `queued`, `claim()` trả `None`; resume rồi claim đúng row.

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_job_queue.py
```

Expected: scoped API missing/pause test fail.

- [ ] **Step 3: Implement scoped enqueue**

Validate `external_content_id`, `content_hash`, `source` non-empty; insert mọi snapshot từ `ReviewContext`. Force không có target explicit thì transaction update đúng `done` scoped row sang `superseded`, insert row mới và link tới row cũ. Khi caller truyền `supersedes_job_id`, target explicit được ưu tiên: lock row đó và chỉ chấp nhận row cùng site/external/profile/policy ở trạng thái `failed|done|superseded`; không tự đổi/xóa row `failed`. Dead-letter lookup và duplicate lookup phải có đủ site/external/hash/policy.

- [ ] **Step 4: Sửa claim**

Subquery claim join `site s ON s.id=j.site_id`, lọc `s.active=true AND s.intake_paused=false`. `RETURNING` gồm `public_id`, site/profile/policy/external/revision/content_type/langcode/correlation. Không xóa field legacy trong return trước Plan 4.

Chuẩn hóa backoff ở `fail`: sau claim thất bại lần 1, delay `60 + rng()*6` giây; lần 2, `300 + rng()*30` giây; lần 3 chuyển terminal `failed`. Nếu connector có `Retry-After`, dùng `max(calculated_delay, min(retry_after_seconds, 600))`. Test inject `rng=lambda: 0.5`; không `sleep` trong queue test. Đây là retry ở **một tầng duy nhất**; connector mới ở Plan 4 không tự lặp HTTP bên trong một job attempt.

- [ ] **Step 5: Compatibility regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_job_queue.py
.\.venv\Scripts\python.exe scripts\test_api.py
.\.venv\Scripts\python.exe scripts\test_reconcile.py
```

Expected: scoped tests và toàn bộ legacy tests PASS.

- [ ] **Step 6: Commit**

```powershell
git -C .. add multiagent/src/job_queue.py multiagent/scripts/test_job_queue.py multiagent/scripts/test_api.py
git commit -m "feat: scope review queue by site and policy"
```

---

### Task 5: Audit scoped và worker truyền đúng metadata

**Files:**
- Modify: `multiagent/src/audit.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/scripts/test_audit.py`
- Modify: `multiagent/scripts/test_worker.py`
- Modify: `multiagent/scripts/test_worker_graph_integration.py`

**Interfaces:**
- Produces: `ghi_scoped(conn, *, run_public_id: UUID, job: dict, content_hash: str, duration_ms: int, report: dict, config_meta: dict, usage: list, model: str, payload: dict) -> int`.
- Produces: `da_cham_scoped(conn, *, site_id: UUID, external_content_id: str, content_hash: str, policy_version: str) -> dict | None`.
- Produces: `find_reusable_writeback(conn, *, job: dict) -> dict | None`.
- Keeps compatibility wrappers `ghi()` and `da_cham()` until worker test migration is complete.

- [ ] **Step 1: RED audit isolation**

Test hai site cùng external/hash/policy có payload khác; `da_cham_scoped` chỉ trả đúng site. Assert row có site/profile/policy/correlation/external revision và không có key nội dung `title/body/summary` trong payload.

`find_reusable_writeback` chỉ trả run có payload khi: (a) run thuộc chính job hiện tại và `writeback_status IN ('pending','failed')`, hoặc (b) job có `source='admin_retry'`, `supersedes_job_id` trỏ đúng failed job cùng scope và run của target có `writeback_status='failed'`. Nhánh `pending` cùng job xử lý crash/reclaim sau audit nhưng trước hoặc trong callback; phải retry saved payload/idempotency thay vì trả tiền LLM lại. Kết quả gồm `run_id` public UUID, payload, external revision, content hash/version để Plan 4 retry callback bằng đúng idempotency/precondition cũ. Manual `force` sau một run `succeeded` phải trả None và thực sự chấm lại; run `unknown|superseded|succeeded` không reusable; không reuse rộng chỉ vì cùng content hash.

- [ ] **Step 2: RED worker metadata**

Fake job trong `test_worker.py` phải có scoped fields; spy `audit.ghi_scoped` assert nguyên job snapshot và application-generated `run_public_id` được truyền. Test reusable write-back dùng đủ scope, trả lại đúng public run ID/precondition và phân biệt `admin_retry` với `manual force`.

- [ ] **Step 3: Implement audit scoped**

Caller tạo UUID trước khi dựng payload; INSERT dùng UUID đó, giữ append-only và set `writeback_status='pending'`. Unique constraint bảo vệ trùng public ID. Thêm:

```python
def mark_writeback(
    conn,
    run_id: int,
    *,
    status: Literal["succeeded", "failed", "superseded"],
    error: str | None = None,
) -> None:
    ...
```

Đây là UPDATE duy nhất được phép trên run: chỉ đổi trạng thái transport, không sửa decision/agent result/payload. Cho phép `pending → succeeded|failed|superseded` và `failed → succeeded|failed|superseded` để saved-result callback retry có thể chốt lại chính run cũ; `succeeded|superseded|unknown` là terminal và không được mở lại. Error được cắt tối đa 1000 ký tự và redaction ở Plan 5; `superseded` dành cho callback từ chối kết quả revision cũ ở Plan 4.

- [ ] **Step 4: Worker dùng run ID để mark write-back**

Worker flow ở giai đoạn compatibility: trước graph gọi `find_reusable_writeback`. Có reusable run `pending|failed` của chính job (hoặc failed run được admin link rõ) thì ghi payload đã lưu, mark chính run đó rồi complete/fail mà không tạo run/usage mới. Không có thì `run_id=ghi_scoped(...)` → write-back → `mark_writeback(status="succeeded")` → complete; write-back fail → `mark_writeback(status="failed", error="write-back that bai")` → q.fail. API/Connector Plan 4 thay transport bằng callback CAS và dùng thêm terminal `superseded`. Tuyệt đối không reuse run succeeded cho manual force.

- [ ] **Step 5: GREEN regression**

```powershell
.\.venv\Scripts\python.exe scripts\test_audit.py
.\.venv\Scripts\python.exe scripts\test_worker.py
.\.venv\Scripts\python.exe scripts\test_worker_graph_integration.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: PASS; integration spy vẫn đúng một PATCH.

- [ ] **Step 6: Commit**

```powershell
git -C .. add multiagent/src/audit.py multiagent/src/worker.py multiagent/scripts/test_audit.py multiagent/scripts/test_worker.py multiagent/scripts/test_worker_graph_integration.py
git commit -m "feat: persist scoped review audit metadata"
```

---

### Task 6: Startup yêu cầu schema current và connection theo request

**Files:**
- Modify: `multiagent/src/api.py`
- Modify: `multiagent/src/worker.py`
- Modify: `multiagent/src/job_queue.py`
- Modify: `multiagent/src/audit.py`
- Modify: `multiagent/src/db.py`
- Modify: `multiagent/scripts/test_api.py`
- Modify: `README.md`

**Interfaces:**
- API lifespan: `migrations.require_current()` một lần, không auto-apply.
- FastAPI dependency: mỗi request mở/đóng connection riêng.
- Worker: một dedicated connection, require current trước preload model.

- [ ] **Step 1: RED cho request connection isolation**

Thay fake `open_connection()` ghi open/close; gọi handler hai lần, assert hai connection khác nhau và đều close. Test lifespan với pending migration phải fail trước khi route phục vụ.

- [ ] **Step 2: Implement dependency yield**

Trong `api.py`:

```python
def _conn():
    with platform_database.open_connection() as conn:
        yield conn
```

Route dùng `conn=Depends(_conn)`, không gọi `_conn()` trực tiếp. Lifespan mở connection ngắn, `require_current`, đóng rồi yield. Worker dùng `open_connection()` bao toàn vòng lặp.

- [ ] **Step 3: Loại DDL runtime**

`job_queue.dam_bao_bang()` và `audit.dam_bao_bang()` được giữ làm compatibility guard nhưng chỉ gọi `migrations.require_current()`; chúng không còn chạy DDL. Mọi startup/test schema mới dùng migration runner. `db.dam_bao_bang()` chỉ validate dimension + index cho KB build; README bắt buộc chạy migration trước build KB.

- [ ] **Step 4: Docs setup**

Thêm setup:

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
docker compose up -d db
.\.venv\Scripts\python.exe scripts\migrate.py apply
.\.venv\Scripts\python.exe src\kb\build_kb.py
```

Migration directory luôn resolve từ `Path(__file__).parents[2] / "migrations"`; MVP không thêm biến môi trường cho một path nội bộ cố định.

- [ ] **Step 5: Regression và score gate**

```powershell
.\.venv\Scripts\python.exe scripts\test_api.py
.\.venv\Scripts\python.exe scripts\test_job_queue.py
.\.venv\Scripts\python.exe scripts\test_audit.py
.\.venv\Scripts\python.exe scripts\test_worker.py
.\.venv\Scripts\python.exe scripts\test_reconcile.py
.\.venv\Scripts\python.exe -c "import sys; sys.path[:0]=['scripts','src']; import eval_calibration as e; assert e.prompt_version() == '020738e209017213'"
git -C .. diff --exit-code 04f10e1 -- multiagent/src/agents multiagent/src/ai_core.py multiagent/src/graph.py multiagent/src/scoring.py multiagent/src/retrieval.py multiagent/src/kb multiagent/config/scoring.yaml
```

Expected: PASS; Postgres tests chạy thật; score diff rỗng.

- [ ] **Step 6: Commit**

```powershell
git -C .. add multiagent/src/api.py multiagent/src/worker.py multiagent/src/job_queue.py multiagent/src/audit.py multiagent/src/db.py multiagent/scripts/test_api.py README.md
git commit -m "refactor: require migrated schema at service startup"
```

---

### Task 7: Foundation checkpoint

**Files:**
- Modify: `docs/technical-debt.md`
- Create: `docs/evidence/platform-foundation-verification.txt`

**Interfaces:**
- Produces: evidence bảo toàn migration và score freeze trước Plan 2.

- [ ] **Step 1: Chạy full offline suite**

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$failed = @()
Get-ChildItem scripts\test_*.py | Sort-Object Name | ForEach-Object {
  & $python $_.FullName
  if ($LASTEXITCODE -ne 0) { $failed += $_.Name }
}
if ($failed.Count) { throw "Test failures: $($failed -join ', ')" }
```

Expected: exit 0; ghi riêng script nào `[SKIP]`, không gọi chúng PASS.

- [ ] **Step 2: Kiểm data count trước/sau và schema**

Query count `review_job`, `run_log`, `kb_chunk`; assert mọi job/run có site/profile/policy/external/correlation; assert đúng một assignment active cho default scope.

- [ ] **Step 3: Ghi evidence thật**

Evidence có commit, timestamp, migration status, row counts, test pass/skip/fail, prompt version và output `git diff --exit-code` score path. Không ghi DSN/password.

- [ ] **Step 4: Cập nhật nợ kỹ thuật**

Đánh dấu P1 foundation đã triển khai chỉ khi evidence đạt; H3 ghi phần migration đã đóng, connection pool vẫn là quyết định riêng nếu chưa dùng pool.

- [ ] **Step 5: Commit checkpoint**

```powershell
git -C .. add docs/evidence/platform-foundation-verification.txt docs/technical-debt.md
git commit -m "docs: record platform foundation verification"
```
