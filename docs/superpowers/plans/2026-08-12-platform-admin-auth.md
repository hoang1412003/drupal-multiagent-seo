# Platform Admin Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cung cấp trang `/admin` có local account, Argon2id, server-side session, CSRF, rate-limit và RBAC `viewer/operator/admin` mà không phụ thuộc tài khoản Drupal.

**Architecture:** Auth được cô lập trong `platform/auth`; database chỉ giữ password hash, session token hash và audit metadata. Admin UI là Jinja2 server-rendered, gắn router vào FastAPI hiện hành; request HTML dùng connection riêng và kiểm quyền ở dependency server-side.

**Tech Stack:** FastAPI, Jinja2, python-multipart, argon2-cffi, psycopg 3, HTML/CSS, TestClient/httpx chỉ cho test.

**Depends on:** `2026-08-12-platform-foundation.md` đã qua checkpoint.

**Quy ước chạy lệnh:** Mỗi code block PowerShell bắt đầu với working directory `D:\drupal-multiagent-seo\multiagent`, trừ khi chính block có `Set-Location` tuyệt đối. Không kế thừa working directory từ block trước.

## Global Constraints

- Argon2id: memory 19 MiB (`19456` KiB), iterations `2`, parallelism `1`, hash length `32`, salt length `16`.
- Password dài 12–128 ký tự; không trim password, không log, không đưa qua CLI argument.
- Session idle 30 phút, absolute 8 giờ; đổi/reset password thu hồi toàn bộ session.
- Cookie name `vf_admin_session`, `HttpOnly`, `SameSite=Lax`, `Path=/admin`; `Secure=true` khi `ADMIN_COOKIE_SECURE=true` ở production.
- CSRF authenticated dùng synchronizer token độc nhất theo session; login dùng signed double-submit pre-auth token. Token không vào URL/log.
- Rate limit: 5 lần thất bại trong 15 phút theo hash `(username_normalized, IP)`; block 15 phút; thông báo login luôn chung chung.
- Không public signup, email reset hoặc “quên mật khẩu” trong MVP.
- Không được khóa/hạ quyền/vô hiệu hóa admin active cuối cùng.
- Mọi audit metadata đi qua allowlist; không chấp nhận dict tùy ý chứa secret.
- Startup từ chối `ADMIN_CSRF_KEY`/`ADMIN_THROTTLE_KEY` ngắn hơn 32 byte hoặc trùng nhau; không dùng default production.
- Throttle lấy IP từ `request.client.host` sau lớp ASGI server; app không tự tin `X-Forwarded-For`. Khi deploy reverse proxy, chỉ bật Uvicorn proxy headers cho đúng IP proxy trong runbook.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/migrations/0002_admin_auth.sql` | User/session/throttle/audit schema |
| `multiagent/src/platform/auth/passwords.py` | Hash/verify/rehash/password policy |
| `multiagent/src/platform/auth/users.py` | User repository + last-admin invariant |
| `multiagent/src/platform/auth/sessions.py` | Issue/resolve/touch/revoke session |
| `multiagent/src/platform/auth/csrf.py` | Session CSRF + signed pre-auth CSRF |
| `multiagent/src/platform/auth/throttle.py` | Login attempt window/block |
| `multiagent/src/platform/auth/rbac.py` | Role enum/rank/authorization |
| `multiagent/src/platform/auth/audit_log.py` | Action enum + sanitized INSERT |
| `multiagent/src/platform/admin/dependencies.py` | Session/RBAC/DB dependencies |
| `multiagent/src/platform/admin/router.py` | Login/logout/change-password/admin home |
| `multiagent/src/platform/admin/templates/` | Base/login/home/change-password/error |
| `multiagent/src/platform/admin/static/admin.css` | UI shell accessible/responsive |
| `multiagent/scripts/admin_user.py` | Bootstrap/reset/lock CLI interactive |

---

### Task 1: Dependency và migration auth

**Files:**
- Modify: `multiagent/requirements.txt`
- Modify: `multiagent/requirements-dev.txt`
- Create: `multiagent/migrations/0002_admin_auth.sql`
- Modify: `multiagent/scripts/test_migrations.py`

**Interfaces:**
- Produces tables: `admin_user`, `admin_session`, `admin_login_throttle`, `admin_audit_log`.

- [ ] **Step 1: Khai báo dependency tường minh**

Thêm runtime:

```text
Jinja2>=3.1,<4
python-multipart>=0.0.9,<1
argon2-cffi>=23.1,<26
```

Sửa mô tả `requirements-dev.txt` vì file không còn chỉ cho chuẩn bị dữ liệu; thêm:

```text
httpx>=0.28,<1
```

- [ ] **Step 2: RED migration test**

Sau apply `0001`, assert `0002` pending; apply rồi assert table/constraint/index tồn tại. Test insert role `owner` bị check constraint từ chối; duplicate normalized username bị unique index chặn.

- [ ] **Step 3: Viết migration 0002 đầy đủ**

```sql
CREATE TABLE admin_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text NOT NULL,
  username_normalized text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('viewer', 'operator', 'admin')),
  active boolean NOT NULL DEFAULT true,
  must_change_password boolean NOT NULL DEFAULT true,
  password_changed_at timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz,
  created_by uuid REFERENCES admin_user(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE admin_session (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES admin_user(id),
  token_hash char(64) NOT NULL UNIQUE,
  csrf_secret text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  idle_expires_at timestamptz NOT NULL,
  absolute_expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  revoke_reason text
);
CREATE INDEX admin_session_lookup ON admin_session (token_hash)
WHERE revoked_at IS NULL;

CREATE TABLE admin_login_throttle (
  subject_hash char(64) PRIMARY KEY,
  failure_count int NOT NULL,
  window_started_at timestamptz NOT NULL,
  blocked_until timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE admin_audit_log (
  id bigserial PRIMARY KEY,
  actor_user_id uuid REFERENCES admin_user(id),
  actor_username text,
  action text NOT NULL,
  target_type text,
  target_id text,
  outcome text NOT NULL CHECK (outcome IN ('success', 'denied', 'failed')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX admin_audit_log_time ON admin_audit_log (created_at DESC);
CREATE INDEX admin_audit_log_actor ON admin_audit_log (actor_user_id, created_at DESC);
```

- [ ] **Step 4: Install và GREEN**

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\test_migrations.py
.\.venv\Scripts\python.exe scripts\migrate.py apply
```

Expected: 0002 apply một lần; status current.

- [ ] **Step 5: Commit**

```powershell
git -C .. add multiagent/requirements.txt multiagent/requirements-dev.txt multiagent/migrations/0002_admin_auth.sql multiagent/scripts/test_migrations.py
git commit -m "feat: add admin authentication schema"
```

---

### Task 2: Password và user repository với last-admin guard

**Files:**
- Create: `multiagent/src/platform/auth/__init__.py`
- Create: `multiagent/src/platform/auth/passwords.py`
- Create: `multiagent/src/platform/auth/users.py`
- Create: `multiagent/src/platform/auth/rbac.py`
- Create: `multiagent/scripts/test_admin_users.py`

**Interfaces:**
- Produces: `Role(str, Enum)` values `viewer`, `operator`, `admin`.
- Produces: `hash_password(password: str) -> str`, `verify_password(hash_value: str, password: str) -> bool`, `needs_rehash(hash_value: str) -> bool`.
- Produces: `create_user`, `authenticate_candidate`, `set_role`, `set_active`, `reset_password`, `change_password`.

- [ ] **Step 1: RED password policy và hash**

```python
def test_argon2id_va_policy():
    with expect(PasswordPolicyError, "12"):
        passwords.hash_password("qua-ngan")
    value = passwords.hash_password("Mat-khau-rat-dai-2026")
    assert value.startswith("$argon2id$")
    assert passwords.verify_password(value, "Mat-khau-rat-dai-2026")
    assert not passwords.verify_password(value, "sai-hoan-toan")
```

Test Unicode password giữ nguyên bytes; chuỗi chỉ khác khoảng trắng đầu/cuối không được tự trim thành giống nhau.

- [ ] **Step 2: Implement Argon2id exact parameters**

```python
HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
```

`verify_password` bắt `VerifyMismatchError`/`InvalidHashError` và trả False; không phân biệt lỗi cho caller.

- [ ] **Step 3: RED repository invariants**

Test username normalize bằng `unicodedata.normalize("NFKC", username).casefold().strip()`. Tạo `Admin` rồi `admin` phải conflict. Test không thể deactivate/hạ role admin active cuối; khi có hai admin thì được phép hạ một.

- [ ] **Step 4: Implement repository transaction**

`set_role` và `set_active` lock toàn bộ active admin row bằng `SELECT ... FOR UPDATE` trong transaction trước khi quyết định. `reset_password` set `must_change_password=true`, update timestamp và revoke session cùng transaction. `change_password` set false và revoke mọi session trừ session hiện tại chỉ khi route sẽ tạo session mới; plan chọn revoke tất cả rồi buộc login lại.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_users.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
git -C .. add multiagent/src/platform/auth multiagent/scripts/test_admin_users.py
git commit -m "feat: add Argon2id admin users and role invariants"
```

---

### Task 3: Session server-side và CSRF

**Files:**
- Create: `multiagent/src/platform/auth/sessions.py`
- Create: `multiagent/src/platform/auth/csrf.py`
- Create: `multiagent/scripts/test_admin_sessions.py`

**Interfaces:**
- Produces: `IssuedSession(raw_token: str, csrf_token: str, absolute_expires_at: datetime)`.
- Produces: `ResolvedSession(session_id: UUID, user: AdminUser, csrf_token: str, must_change_password: bool)`.
- Produces: `issue`, `resolve`, `touch`, `revoke`, `revoke_all_for_user`.
- Produces pre-auth: `issue_login_csrf(signing_key: bytes) -> str`, `verify_login_csrf(cookie_token, form_token, signing_key) -> bool`.

- [ ] **Step 1: RED raw-token rules**

Test `issue()` trả token URL-safe ít nhất 32 random bytes; DB chỉ chứa SHA-256 hex, không chứa raw token. Resolve đúng, token sai/expired/revoked trả None. Touch trượt idle expiry nhưng không vượt absolute expiry.

- [ ] **Step 2: Implement session**

Raw token: `secrets.token_urlsafe(32)`. Hash: `hashlib.sha256(raw.encode("ascii")).hexdigest()`. CSRF: `secrets.token_urlsafe(32)` stored server-side per session and compare bằng `hmac.compare_digest`.

Thời gian luôn timezone-aware UTC; injectable `now_fn` cho test, không monkeypatch `datetime` toàn module.

- [ ] **Step 3: RED/implement login CSRF**

Token format `nonce.signature` với nonce 32 bytes URL-safe, signature `HMAC-SHA256(ADMIN_CSRF_KEY, nonce)`. Verify cookie == form bằng constant-time, rồi verify signature. Không đưa username/IP vào token.

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_sessions.py
git -C .. add multiagent/src/platform/auth/sessions.py multiagent/src/platform/auth/csrf.py multiagent/scripts/test_admin_sessions.py
git commit -m "feat: add server-side admin sessions and CSRF"
```

---

### Task 4: Login throttle và auth audit allowlist

**Files:**
- Create: `multiagent/src/platform/auth/throttle.py`
- Create: `multiagent/src/platform/auth/audit_log.py`
- Create: `multiagent/scripts/test_admin_login_security.py`

**Interfaces:**
- Produces: `LoginThrottle.check/record_failure/record_success`.
- Produces: `AuditAction` enum and `write_event(..., metadata: Mapping) -> int`.

- [ ] **Step 1: RED throttle window**

Test 4 fail chưa block, fail thứ 5 block 15 phút; username khác hoặc IP khác là subject khác; qua block + window reset được thử lại. Subject hash dùng HMAC `ADMIN_THROTTLE_KEY` thay SHA thuần để không dò username/IP từ DB.

- [ ] **Step 2: Implement transaction throttle**

`check()` không tăng counter. `record_failure()` upsert + row lock, reset window sau 15 phút, set blocked_until ở lần 5. `record_success()` xóa row. Route vẫn chạy dummy Argon2 verify khi username không tồn tại để giảm username timing leak.

- [ ] **Step 3: RED audit secret rejection**

Allow metadata keys theo action, ví dụ login chỉ `subject_hash`, `reason`; user change chỉ `old_role/new_role`. Test key chứa `password`, `token`, `authorization`, `cookie`, `secret` raise `AuditMetadataError`; value không được là bytes hoặc mapping lồng không allowlisted.

- [ ] **Step 4: Implement audit action enum**

Tối thiểu: `login_success`, `login_failed`, `logout`, `password_changed`, `user_created`, `user_role_changed`, `user_locked`, `user_unlocked`, `password_reset`, `last_admin_denied`. Outcome exact `success|denied|failed`.

- [ ] **Step 5: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_login_security.py
git -C .. add multiagent/src/platform/auth/throttle.py multiagent/src/platform/auth/audit_log.py multiagent/scripts/test_admin_login_security.py
git commit -m "feat: rate limit and audit admin authentication"
```

---

### Task 5: Admin router login/logout/password và RBAC dependency

**Files:**
- Create: `multiagent/src/platform/admin/__init__.py`
- Create: `multiagent/src/platform/admin/dependencies.py`
- Create: `multiagent/src/platform/admin/router.py`
- Create: `multiagent/src/platform/admin/templates/base.html`
- Create: `multiagent/src/platform/admin/templates/login.html`
- Create: `multiagent/src/platform/admin/templates/home.html`
- Create: `multiagent/src/platform/admin/templates/change_password.html`
- Create: `multiagent/src/platform/admin/templates/403.html`
- Create: `multiagent/src/platform/admin/static/admin.css`
- Modify: `multiagent/src/api.py`
- Create: `multiagent/scripts/test_admin_routes.py`

**Interfaces:**
- Produces routes: `GET/POST /admin/login`, `POST /admin/logout`, `GET /admin`, `GET/POST /admin/change-password`.
- Produces dependencies: `current_user`, `require_role(Role)`, `require_csrf`.

- [ ] **Step 1: RED HTTP behavior bằng TestClient**

Test app riêng include admin router với dependency override DB. Cases:

```python
assert client.get("/admin", follow_redirects=False).headers["location"] == "/admin/login"
assert client.post("/admin/login", data=bad_csrf).status_code == 403
assert client.post("/admin/login", data=valid_wrong_password).status_code == 401
assert login_ok.status_code == 303
assert "vf_admin_session=" in login_ok.headers["set-cookie"]
assert "HttpOnly" in login_ok.headers["set-cookie"]
assert "SameSite=lax" in login_ok.headers["set-cookie"]
```

Test inactive user, throttle, must-change redirect, logout CSRF, session revoke và viewer gọi dependency operator bị 403.

- [ ] **Step 2: Implement dependencies và validate auth config**

`current_user` resolve cookie + active user, touch session tối đa một lần mỗi 5 phút để tránh UPDATE mọi request. `require_role` dùng rank `viewer=10`, `operator=20`, `admin=30`; trả 403 server-side. Nếu `must_change_password`, chỉ cho logout/change-password/static.

Lifespan gọi auth config validator: hai signing key phải tồn tại, mỗi key UTF-8 ít nhất 32 byte và không bằng nhau qua `hmac.compare_digest`. Throttle subject dùng `request.client.host`; không đọc header IP ở application layer.

- [ ] **Step 3: Implement login/logout**

GET login issue signed pre-auth token, set cookie `vf_admin_login_csrf` `HttpOnly=true`, `SameSite=Lax`, `Path=/admin/login`, max-age 600. POST verify token trước credential, throttle trước/after dummy Argon2, issue session, delete preauth cookie, 303 `/admin` hoặc `/admin/change-password`.

Logout POST verify session CSRF, revoke, delete session cookie, 303 login. Không dùng GET cho logout.

- [ ] **Step 4: Implement password change**

Form fields current/new/confirm + CSRF. Generic errors, validate current password, equality confirm, policy. Success revoke all sessions, delete cookie, 303 login với one-time query-free flash cookie hoặc template message; không đưa message nhạy cảm vào URL.

- [ ] **Step 5: Templates/CSS tối thiểu**

Jinja autoescape bật. Base có skip-link, semantic nav/main, visible focus, error summary `role=alert`, không render `|safe` với dữ liệu runtime. Home hiển thị username/role và dòng “Các màn hình vận hành được thêm ở phase tiếp theo”, không tạo metric giả.

- [ ] **Step 6: Gắn router vào app hiện hành**

`api.py` include router và mount static `/admin/static`. Không chuyển/xóa legacy `/jobs`, `/health`. Test cũ API phải giữ nguyên.

- [ ] **Step 7: GREEN + regressions**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_routes.py
.\.venv\Scripts\python.exe scripts\test_api.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

- [ ] **Step 8: Commit**

```powershell
git -C .. add multiagent/src/platform/admin multiagent/src/api.py multiagent/scripts/test_admin_routes.py
git commit -m "feat: add secure admin login and role gate"
```

---

### Task 6: CLI bootstrap/reset không lộ password

**Files:**
- Create: `multiagent/scripts/admin_user.py`
- Create: `multiagent/scripts/test_admin_user_cli.py`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- CLI subcommands: `bootstrap`, `create`, `reset-password`, `lock`, `unlock`, `set-role`.

- [ ] **Step 1: RED parser và no-password-argument**

Test parser từ chối `--password`; inject `getpass_fn` cho test. `bootstrap` chỉ chạy khi không có user; luôn tạo `admin`, `must_change_password=true`. `create` cần actor admin ID hoặc ghi actor `system-cli` rõ trong audit.

- [ ] **Step 2: Implement CLI**

Password nhập hai lần bằng `getpass.getpass`, không echo. `reset-password` sinh bằng `secrets.token_urlsafe(18)`, in đúng một lần sau commit DB, không ghi audit value. Lock/set-role gọi cùng repository nên last-admin guard giữ nguyên.

- [ ] **Step 3: Env và setup**

`.env.example` thêm:

```text
ADMIN_CSRF_KEY=
ADMIN_THROTTLE_KEY=
ADMIN_COOKIE_SECURE=false
```

README hướng dẫn sinh hai key riêng bằng `secrets.token_urlsafe(32)`, production đặt cookie secure true và HTTPS. Bootstrap:

```powershell
.\.venv\Scripts\python.exe scripts\admin_user.py bootstrap --username admin
```

- [ ] **Step 4: GREEN + commit**

```powershell
.\.venv\Scripts\python.exe scripts\test_admin_user_cli.py
git -C .. add multiagent/scripts/admin_user.py multiagent/scripts/test_admin_user_cli.py .env.example README.md
git commit -m "feat: add interactive admin account CLI"
```

---

### Task 7: Auth checkpoint

**Files:**
- Create: `docs/evidence/platform-admin-auth-verification.txt`
- Modify: `docs/technical-debt.md`

**Interfaces:**
- Produces evidence cho Plan 3.

- [ ] **Step 1: Chạy focused suite và full offline suite**

Run mọi `test_admin_*.py`, `test_migrations.py`, `test_api.py`, rồi full `scripts/test_*.py` runner từ parent plan.

- [ ] **Step 2: Security assertions tươi**

Dump schema row mẫu và assert không có raw password/session. Dùng TestClient assert CSRF 403, viewer 403 operator dependency, last-admin denial, cookie flags. Không chép hash/token vào evidence.

- [ ] **Step 3: Score freeze**

Chạy prompt/hash + score-path diff command ở parent plan. Expected unchanged.

- [ ] **Step 4: Evidence/docs + commit**

```powershell
git -C .. add docs/evidence/platform-admin-auth-verification.txt docs/technical-debt.md
git commit -m "docs: record admin authentication verification"
```
