# Console React Admin — Kế hoạch triển khai giai đoạn 1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng tầng REST API JSON `/api/console/v1` cho sáu màn hình admin lõi, kèm bộ khung React tại `/console`, để Antigravity code giao diện theo hợp đồng OpenAPI mà không đụng vào backend.

**Architecture:** Package mới `src/review_platform/admin_api/` là lớp serialize mỏng trên `admin/queries.py` đã có test. Xác thực dùng lại cookie phiên `vf_admin_session` (same-origin), nhưng có dependency riêng trả 401 JSON thay vì redirect 303. Admin Jinja2 giữ nguyên ở `/admin`, chạy song song.

**Tech Stack:** FastAPI, Pydantic v2, psycopg (Postgres), Vite + React + TypeScript + React Router + TanStack Query + Tailwind, `openapi-typescript`.

**Spec:** `docs/superpowers/specs/2026-08-19-console-react-admin-design.md`

## Global Constraints

- **Không sửa logic** trong `admin/queries.py`, `auth/sessions.py`, `auth/users.py`, `auth/csrf.py`, `auth/rbac.py`, `admin/sanitization.py`.
- **Không sửa** package `src/review_platform/api/` (API key cho connector Drupal).
- Admin Jinja2 giữ nguyên đường dẫn `/admin` và phải còn chạy sau **mọi** task.
- Tiền tố API: `/api/console/v1`. Cookie phiên: `vf_admin_session`. Header CSRF: `X-CSRF-Token`.
- Mọi lỗi trả đúng một hình dạng: `{"error": {"code": ..., "message": ..., "field": ...}}`.
- Mọi danh sách trả đúng một hình dạng: `{"items", "page", "page_size", "total", "total_pages"}`.
- Test là **script Python thuần** theo mẫu `scripts/test_admin_audit_page.py`, **không phải pytest**. In `[PASS]` / `[FAIL]`, `[SKIP]` khi không có Postgres, `sys.exit(1)` khi có lỗi.
- Mọi file `scripts/test_*.py` mới **bắt buộc** khai báo trong `scripts/test_groups.json` nhóm `postgres`, nếu không `run_test_group.py` báo `[LOI MANIFEST]` và chặn toàn bộ.
- Lệnh xác minh chuẩn (chạy từ `multiagent/`): `.venv\Scripts\python.exe scripts\run_test_group.py all-offline` — phải báo `hong: 0` và `co [SKIP]: 0`.
- Commit tiếng Việt **không dấu**, **không** trailer `Co-Authored-By: Claude`.
- Nhánh làm việc: `docs/thiet-ke-console-react-admin` (đã có spec + kế hoạch).

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `src/review_platform/admin_api/__init__.py` | rỗng, đánh dấu package |
| `src/review_platform/admin_api/errors.py` | hình dạng lỗi chuẩn + exception + handler |
| `src/review_platform/admin_api/dependencies.py` | `console_session`, `require_console_role`, `require_console_csrf` |
| `src/review_platform/admin_api/models.py` | Pydantic model cho mọi response |
| `src/review_platform/admin_api/auth_routes.py` | `/auth/login`, `/auth/me`, `/auth/logout`, `/auth/change-password` |
| `src/review_platform/admin_api/dashboard_routes.py` | `/dashboard` |
| `src/review_platform/admin_api/job_routes.py` | `/jobs`, `/jobs/{id}`, `/jobs/{id}/retry` |
| `src/review_platform/admin_api/review_routes.py` | `/reviews`, `/reviews/{id}` |
| `src/review_platform/admin_api/router.py` | gom router con, gắn tiền tố |
| `scripts/export_openapi.py` | ghi `console_ui/openapi.json` |
| `console_ui/` | app React (task 10) |

Tách theo màn hình chứ không theo tầng kỹ thuật: file nào thay đổi cùng nhau thì nằm cùng nhau, khớp với cách `admin/` đang tổ chức.

---

### Task 1: Thống nhất `path` cookie phiên về `/`

Đây là task chặn. Nếu bỏ qua, mọi endpoint ở task sau sẽ trả 401 vì trình duyệt không gửi cookie.

**Files:**
- Modify: `src/review_platform/admin/dependencies.py:14`
- Modify: `src/review_platform/admin/router.py:198-209`, `:232`, `:295`
- Test: `scripts/test_admin_session_cookie_path.py` (tạo mới)
- Modify: `scripts/test_groups.json`

**Interfaces:**
- Consumes: không có.
- Produces: `dependencies.SESSION_COOKIE_PATH: str = "/"` và `dependencies.LEGACY_SESSION_COOKIE_PATH: str = "/admin"` — task 2 và task 3 dùng lại hai hằng số này.

- [ ] **Step 1: Viết test thất bại**

Tạo `scripts/test_admin_session_cookie_path.py`. Phần khung (kết nối DB, reset schema, `_make_client`, `_user`) sao chép nguyên từ `scripts/test_admin_audit_page.py` dòng 1-72, đổi `SCHEMA = "vf_test_admin_cookie_path"`. Phần test:

```python
def test_login_dat_cookie_path_goc_va_xoa_cookie_cu(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.admin", Role.ADMIN)

    client = _make_client(conn)
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    response = client.post(
        "/admin/login",
        data={
            "username": account.username,
            "password": "Mat-khau-cookie.path.admin-2026",
            "csrf_token": token,
        },
    )
    assert response.status_code == 303

    set_cookie_headers = response.headers.get_list("set-cookie")
    phien = [h for h in set_cookie_headers if h.startswith("vf_admin_session=")]
    # Mot header dat cookie moi o path=/, mot header xoa cookie cu o path=/admin.
    assert len(phien) == 2, phien
    dat_moi = [h for h in phien if "Max-Age=0" not in h and 'vf_admin_session=""' not in h]
    xoa_cu = [h for h in phien if "Max-Age=0" in h or 'vf_admin_session=""' in h]
    assert len(dat_moi) == 1 and "Path=/;" in dat_moi[0] + ";", dat_moi
    assert "Path=/admin" in xoa_cu[0], xoa_cu
    assert "HttpOnly" in dat_moi[0] and "SameSite=lax" in dat_moi[0]
    print("[PASS] login dat cookie phien o path=/ va xoa cookie cu o /admin")


def test_cookie_phien_duoc_gui_ngoai_admin(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.viewer", Role.VIEWER)

    client = _make_client(conn)
    _login(client, account.username, "Mat-khau-cookie.path.viewer-2026")
    # httpx chi gui cookie khi path khop. Kiem tra truc tiep tren cookie jar.
    gui_di = client.cookies.get("vf_admin_session", path="/")
    assert gui_di, "cookie phien khong con o path=/ nen /api/console se khong nhan duoc"
    print("[PASS] cookie phien co hieu luc ngoai duong dan /admin")


def test_logout_xoa_cookie_o_ca_hai_path(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.logout", Role.ADMIN)

    client = _make_client(conn)
    _login(client, account.username, "Mat-khau-cookie.path.logout-2026")
    trang = client.get("/admin")
    assert trang.status_code == 200
    csrf_token = router.dependencies.sessions.resolve(
        conn, client.cookies.get("vf_admin_session", path="/")
    ).csrf_token
    response = client.post("/admin/logout", data={"csrf_token": csrf_token})
    assert response.status_code == 303

    duong_dan = {
        h.split("Path=")[1].split(";")[0]
        for h in response.headers.get_list("set-cookie")
        if h.startswith("vf_admin_session=")
    }
    assert duong_dan == {"/", "/admin"}, duong_dan
    print("[PASS] logout xoa cookie phien o ca hai duong dan")
```

Đăng ký vào `scripts/test_groups.json`, thêm `"test_admin_session_cookie_path.py"` vào mảng `nhom.postgres.files`.

- [ ] **Step 2: Chạy để xác nhận thất bại**

```
.venv\Scripts\python.exe scripts\test_admin_session_cookie_path.py
```
Kỳ vọng: `[FAIL] test_login_dat_cookie_path_goc_va_xoa_cookie_cu` — hiện chỉ có 1 header `vf_admin_session`, và `Path=/admin`.

- [ ] **Step 3: Thêm hằng số đường dẫn**

Trong `src/review_platform/admin/dependencies.py`, ngay dưới dòng 14:

```python
SESSION_COOKIE = "vf_admin_session"
# Cookie phai gui duoc toi /api/console/v1 va /console, khong chi /admin.
SESSION_COOKIE_PATH = "/"
# Cookie cu con sot lai tren trinh duyet cua nguoi dang dang nhap luc trien
# khai. Xoa o ca hai duong dan, neu khong trinh duyet giu HAI cookie trung ten
# va Starlette chi tra ve mot cai khong xac dinh.
LEGACY_SESSION_COOKIE_PATH = "/admin"
```

- [ ] **Step 4: Sửa ba vị trí trong `router.py`**

Dòng 199-208, đổi `path="/admin"` thành hằng số và xóa cookie cũ:

```python
    response.set_cookie(
        SESSION_COOKIE,
        issued.raw_token,
        max_age=8 * 60 * 60,
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
        path=dependencies.SESSION_COOKIE_PATH,
    )
    response.delete_cookie(
        SESSION_COOKIE,
        path=dependencies.LEGACY_SESSION_COOKIE_PATH,
    )
    response.delete_cookie(LOGIN_CSRF_COOKIE, path="/admin/login")
```

Dòng 232 và 295 (`delete_cookie(SESSION_COOKIE, path="/admin")`) đổi thành hai lệnh xóa liên tiếp:

```python
    response.delete_cookie(SESSION_COOKIE, path=dependencies.SESSION_COOKIE_PATH)
    response.delete_cookie(SESSION_COOKIE, path=dependencies.LEGACY_SESSION_COOKIE_PATH)
```

- [ ] **Step 5: Chạy lại test mới + toàn bộ nhóm**

```
.venv\Scripts\python.exe scripts\test_admin_session_cookie_path.py
.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```
Kỳ vọng: file mới in 3 dòng `[PASS]`; nhóm báo `hong: 0`, `co [SKIP]: 0`. Các test admin cũ (`test_admin_audit_page.py`, `test_admin_connection.py`, ...) phải vẫn xanh — chúng dùng `TestClient` nên đường dẫn cookie rộng hơn không ảnh hưởng.

- [ ] **Step 6: Commit**

```bash
git add src/review_platform/admin/dependencies.py src/review_platform/admin/router.py scripts/test_admin_session_cookie_path.py scripts/test_groups.json
git commit -m "fix: mo rong path cookie phien ve / de Console dung chung duoc phien"
```

---

### Task 2: Hình dạng lỗi + dependency phiên cho API

**Files:**
- Create: `src/review_platform/admin_api/__init__.py`, `errors.py`, `dependencies.py`
- Test: `scripts/test_console_api_auth.py`
- Modify: `scripts/test_groups.json`

**Interfaces:**
- Consumes: `admin.dependencies.SESSION_COOKIE`, `SESSION_COOKIE_PATH`, `get_db`, `get_auth_config` (task 1).
- Produces:
  - `errors.ConsoleError(status_code: int, code: str, message: str, field: str | None = None)` — exception;
  - `errors.console_error_handler(request, exc) -> JSONResponse`;
  - `dependencies.console_session(request, conn) -> sessions.ResolvedSession`;
  - `dependencies.require_console_role(required: Role) -> Callable`;
  - `dependencies.require_console_csrf(request, resolved) -> None`.

- [ ] **Step 1: Viết test thất bại**

Tạo `scripts/test_console_api_auth.py`. Khung sao chép từ `test_admin_audit_page.py` dòng 1-72, `SCHEMA = "vf_test_console_api_auth"`, và `_make_client` đổi thành:

```python
def _make_client(conn):
    app = FastAPI()
    app.state.auth_config = dependencies.AuthConfig(
        csrf_key=CSRF_KEY, throttle_key=THROTTLE_KEY, cookie_secure=False
    )
    app.add_exception_handler(errors.ConsoleError, errors.console_error_handler)
    app.include_router(console_router.router)
    app.dependency_overrides[dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.85", 50000))
```

Test:

```python
def test_khong_co_phien_tra_401_json_khong_redirect(conn):
    _reset_schema(conn)
    client = _make_client(conn)
    response = client.get("/api/console/v1/auth/me")
    assert response.status_code == 401, response.status_code
    assert response.headers.get("location") is None, "API khong duoc redirect"
    assert response.json() == {
        "error": {"code": "unauthenticated", "message": "Chua dang nhap", "field": None}
    }
    print("[PASS] khong co phien tra 401 JSON, khong redirect 303")


def test_must_change_password_chan_moi_endpoint_tru_auth(conn):
    _reset_schema(conn)
    users.create_user(
        conn, "console.mcp", "Mat-khau-console-mcp-2026", Role.ADMIN,
        must_change_password=True,
    )
    client = _make_client(conn)
    dang_nhap = client.post(
        "/api/console/v1/auth/login",
        json={"username": "console.mcp", "password": "Mat-khau-console-mcp-2026"},
    )
    assert dang_nhap.status_code == 200

    me = client.get("/api/console/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    chan = client.get("/api/console/v1/jobs")
    assert chan.status_code == 403
    assert chan.json()["error"]["code"] == "must_change_password"
    print("[PASS] must_change_password: /auth/me qua duoc, endpoint khac bi chan 403")


def test_sai_role_tra_403_khong_phai_401(conn):
    _reset_schema(conn)
    users.create_user(
        conn, "console.viewer", "Mat-khau-console-viewer-2026", Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    client.post(
        "/api/console/v1/auth/login",
        json={"username": "console.viewer", "password": "Mat-khau-console-viewer-2026"},
    )
    response = client.post("/api/console/v1/jobs/%s/retry" % uuid4())
    assert response.status_code in (403,), response.status_code
    assert response.json()["error"]["code"] in ("forbidden", "csrf_invalid")
    print("[PASS] viewer bi 403 chu khong phai 401")
```

Thêm `"test_console_api_auth.py"` vào `scripts/test_groups.json` nhóm `postgres`.

- [ ] **Step 2: Chạy để xác nhận thất bại**

```
.venv\Scripts\python.exe scripts\test_console_api_auth.py
```
Kỳ vọng: `ModuleNotFoundError: review_platform.admin_api`.

- [ ] **Step 3: Viết `errors.py`**

```python
"""Hinh dang loi duy nhat cho Console API.

Vi sao mot hinh dang: frontend do agent khac viet. Moi endpoint tra loi khac
kieu se sinh ra sau cho xu ly loi khac nhau ben frontend.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class ConsoleError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field


def console_error_handler(request: Request, exc: ConsoleError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
            }
        },
    )


def unauthenticated() -> ConsoleError:
    return ConsoleError(401, "unauthenticated", "Chua dang nhap")


def forbidden(message: str = "Ban khong co quyen thuc hien thao tac nay") -> ConsoleError:
    return ConsoleError(403, "forbidden", message)


def not_found(message: str = "Khong tim thay") -> ConsoleError:
    return ConsoleError(404, "not_found", message)


def invalid_filter(message: str, field: str | None = None) -> ConsoleError:
    return ConsoleError(422, "invalid_filter", message, field)
```

- [ ] **Step 4: Viết `dependencies.py`**

```python
"""Dependency phien rieng cho Console API.

KHONG dung lai admin.dependencies.current_session: ham do raise redirect 303
sang /admin/login. Fetch cua trinh duyet tu di theo redirect, nen SPA se nhan
HTML trang dang nhap voi ma 200 thay vi 401.
"""
from fastapi import Depends, Request

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors
from review_platform.auth import csrf, sessions
from review_platform.auth.rbac import Role, allows


# Endpoint van phuc vu duoc khi tai khoan dang bi buoc doi mat khau.
_MUST_CHANGE_ALLOWED = frozenset({
    "/api/console/v1/auth/me",
    "/api/console/v1/auth/change-password",
    "/api/console/v1/auth/logout",
})


def console_session(
    request: Request,
    conn=Depends(admin_dependencies.get_db),
) -> sessions.ResolvedSession:
    raw_token = request.cookies.get(admin_dependencies.SESSION_COOKIE)
    if not raw_token:
        raise errors.unauthenticated()
    resolved = sessions.resolve(conn, raw_token)
    if resolved is None:
        raise errors.unauthenticated()
    if not resolved.user.active:
        sessions.revoke(conn, raw_token, "user_inactive")
        raise errors.unauthenticated()
    if (
        resolved.must_change_password
        and request.url.path not in _MUST_CHANGE_ALLOWED
    ):
        raise errors.ConsoleError(
            403,
            "must_change_password",
            "Phai doi mat khau truoc khi dung tiep",
        )
    sessions.touch(conn, raw_token)
    request.state.console_session = resolved
    return resolved


def require_console_role(required: Role):
    required = Role(required)

    def dependency(resolved=Depends(console_session)):
        if not allows(resolved.user.role, required):
            raise errors.forbidden()
        return resolved

    return dependency


def require_console_csrf(
    request: Request,
    resolved=Depends(console_session),
) -> None:
    supplied = request.headers.get("X-CSRF-Token")
    if not csrf.verify_session_csrf(resolved.csrf_token, supplied):
        raise errors.ConsoleError(403, "csrf_invalid", "CSRF token khong hop le")
```

- [ ] **Step 5: Chạy test**

```
.venv\Scripts\python.exe scripts\test_console_api_auth.py
```
Kỳ vọng: vẫn `[FAIL]` vì chưa có route `/auth/login`, `/auth/me`, `/jobs`. Đây là kết quả đúng ở bước này — task 3 và task 5 làm cho chúng xanh. Chỉ cần xác nhận lỗi đã đổi từ `ModuleNotFoundError` sang lỗi thiếu route.

- [ ] **Step 6: Commit**

```bash
git add src/review_platform/admin_api/ scripts/test_console_api_auth.py scripts/test_groups.json
git commit -m "feat: hinh dang loi va dependency phien cho Console API"
```

---

### Task 3: Bốn endpoint `/auth/*` + CSRF qua header cho admin cũ

**Files:**
- Create: `src/review_platform/admin_api/models.py`, `auth_routes.py`, `router.py`
- Modify: `src/review_platform/admin/dependencies.py:110-119` (thêm nhánh header)
- Test: `scripts/test_console_api_auth.py` (đã tạo ở task 2, giờ phải xanh)

**Interfaces:**
- Consumes: `errors`, `dependencies.console_session/require_console_csrf` (task 2).
- Produces:
  - `models.MeResponse(username: str, role: str, must_change_password: bool, csrf_token: str)`;
  - `models.PageMeta` — lớp cơ sở cho mọi response phân trang, xem task 5;
  - `router.router: APIRouter` với `prefix="/api/console/v1"`.

- [ ] **Step 1: Viết `models.py` phần auth**

```python
"""Pydantic model cho Console API.

Quy uoc chuyen kieu (giu nhat quan o moi model):
- UUID  -> str
- datetime -> str ISO-8601 UTC (dung `_iso` ben duoi)
- Decimal -> float. KHONG khai bao truong la Decimal: Pydantic v2 serialize
  Decimal thanh CHUOI trong JSON, frontend se nhan "82.5" thay vi 82.5.
- None -> null, khong doi thanh chuoi rong.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


def iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat().replace("+00:00", "Z")


def so(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


class MeResponse(BaseModel):
    username: str
    role: str
    must_change_password: bool
    csrf_token: str


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = ""
    new_password: str = ""
```

- [ ] **Step 2: Viết `auth_routes.py`**

Logic đăng nhập **tái sử dụng nguyên vẹn** trình tự của `admin/router.py:104-209`: kiểm tra throttle, `users.find_by_username(for_update=True)`, so sánh mật khẩu bằng `passwords.verify_password` với `_DUMMY_PASSWORD_HASH` khi không có user (chống dò thời gian), ghi `audit_log`, `sessions.issue`, `users.mark_login_success`. Khác ba điểm:

1. nhận JSON thay vì form;
2. không có CSRF pre-auth (SPA chưa có cookie login-csrf) — chống lạm dụng vẫn dựa trên `throttle.LoginThrottle` như cũ;
3. trả `200` + `MeResponse` thay vì redirect 303.

```python
@router.post("/auth/login", response_model=models.MeResponse)
def login(
    payload: models.LoginRequest,
    request: Request,
    response: Response,
    conn=Depends(admin_dependencies.get_db),
    config=Depends(admin_dependencies.get_auth_config),
):
    ip_address = _client_ip(request)
    limiter = throttle.LoginThrottle(conn, config.throttle_key)
    decision = limiter.check(payload.username, ip_address)
    if decision.blocked:
        _ghi_that_bai(conn, None, decision.subject_hash, "throttled")
        raise errors.ConsoleError(
            429, "throttled", "Tam thoi chua the dang nhap. Vui long thu lai sau."
        )

    with conn.transaction():
        try:
            candidate = users.find_by_username(conn, payload.username, for_update=True)
        except ValueError:
            candidate = None
        candidate_hash = candidate.password_hash if candidate else _DUMMY_PASSWORD_HASH
        credential_ok = (
            len(payload.password) <= passwords.MAX_PASSWORD_LENGTH
            and passwords.verify_password(candidate_hash, payload.password)
        )
        if not credential_ok or candidate is None or not candidate.active:
            failed = limiter.record_failure(payload.username, ip_address)
            _ghi_that_bai(
                conn,
                candidate,
                failed.subject_hash,
                "inactive" if credential_ok and candidate else "invalid_credentials",
            )
            if failed.blocked:
                raise errors.ConsoleError(
                    429, "throttled", "Tam thoi chua the dang nhap. Vui long thu lai sau."
                )
            raise errors.ConsoleError(
                401, "invalid_credentials", "Thong tin dang nhap khong hop le"
            )

        limiter.record_success(payload.username, ip_address)
        issued = sessions.issue(conn, candidate.id)
        users.mark_login_success(conn, candidate.id)
        _ghi_thanh_cong(conn, candidate, decision.subject_hash)

    response.set_cookie(
        admin_dependencies.SESSION_COOKIE,
        issued.raw_token,
        max_age=8 * 60 * 60,
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
        path=admin_dependencies.SESSION_COOKIE_PATH,
    )
    response.delete_cookie(
        admin_dependencies.SESSION_COOKIE,
        path=admin_dependencies.LEGACY_SESSION_COOKIE_PATH,
    )
    return models.MeResponse(
        username=candidate.username,
        role=candidate.role.value,
        must_change_password=candidate.must_change_password,
        csrf_token=issued.csrf_token,
    )


@router.get("/auth/me", response_model=models.MeResponse)
def me(resolved=Depends(dependencies.console_session)):
    return models.MeResponse(
        username=resolved.user.username,
        role=resolved.user.role.value,
        must_change_password=resolved.must_change_password,
        csrf_token=resolved.csrf_token,
    )
```

`/auth/logout` phản chiếu `admin/router.py:212-235`: `require_console_csrf`, `sessions.revoke(conn, raw_token, "logout")`, ghi audit, xóa cookie ở **cả hai** đường dẫn, trả `204`.

`/auth/change-password` phản chiếu `admin/router.py:250` trở đi: `require_console_csrf`, đổi mật khẩu qua `auth/passwords` + `users`, thu hồi các phiên khác bằng `sessions.revoke_all_for_user`, trả `204`.

- [ ] **Step 3: Viết `router.py`**

```python
from fastapi import APIRouter

from review_platform.admin_api import auth_routes

router = APIRouter(prefix="/api/console/v1", tags=["console"])
router.include_router(auth_routes.router)
```

Task 4, 5, 7 sẽ thêm `include_router` cho dashboard, jobs, reviews vào đúng file này.

- [ ] **Step 4: Thêm nhánh header vào `require_csrf` của admin cũ**

`src/review_platform/admin/dependencies.py:110-119` thay bằng:

```python
async def require_csrf(
    request: Request,
    resolved=Depends(current_session),
) -> None:
    # Admin Jinja2 gui csrf_token trong form; Console API gui trong header.
    # Giu ca hai nhanh: bo nhanh form se lam hong toan bo admin cu.
    supplied = request.headers.get("X-CSRF-Token")
    if supplied is None:
        form = await request.form()
        supplied = form.get("csrf_token")
    if not csrf.verify_session_csrf(resolved.csrf_token, supplied):
        raise HTTPException(403, "CSRF token không hợp lệ")
```

- [ ] **Step 5: Chạy test**

```
.venv\Scripts\python.exe scripts\test_console_api_auth.py
```
Kỳ vọng: `test_khong_co_phien_tra_401_json_khong_redirect` và `test_must_change_password_chan_moi_endpoint_tru_auth` in `[PASS]`. `test_sai_role_tra_403_khong_phai_401` vẫn `[FAIL]` cho tới task 6 (chưa có route retry).

- [ ] **Step 6: Commit**

```bash
git add src/review_platform/admin_api/ src/review_platform/admin/dependencies.py
git commit -m "feat: bon endpoint /auth cho Console API va CSRF qua header"
```

---

### Task 4: `GET /dashboard`

**Files:**
- Create: `src/review_platform/admin_api/dashboard_routes.py`
- Modify: `src/review_platform/admin_api/models.py`, `router.py`
- Test: `scripts/test_console_api_dashboard.py`
- Modify: `scripts/test_groups.json`

**Interfaces:**
- Consumes: `dependencies.require_console_role`, `models.iso`, `models.so`.
- Produces: `models.DashboardResponse`, `models.CostEstimateModel` — task 7 dùng lại `CostEstimateModel`.

- [ ] **Step 1: Viết test thất bại**

`scripts/test_console_api_dashboard.py`, khung như task 2. Trước khi so sánh, gọi thẳng `queries.dashboard(conn, ...)` để lấy giá trị mong đợi — test so API với hàm truy vấn, không hard-code số:

```python
def test_dashboard_tra_du_truong_va_dung_kieu(conn):
    _reset_schema(conn)
    _seed_jobs_va_reviews(conn)          # sao chep tu scripts/test_admin_dashboard*.py
    client = _dang_nhap_viewer(conn)

    response = client.get("/api/console/v1/dashboard?from=2026-08-01&to=2026-08-31")
    assert response.status_code == 200
    body = response.json()

    mong_doi = queries.dashboard(conn, date(2026, 8, 1), date(2026, 8, 31))
    assert body["total_reviews"] == mong_doi.total_reviews
    assert body["queue_counts"] == mong_doi.queue_counts
    assert body["decision_counts"] == mong_doi.decision_counts
    assert body["worker_status"] in ("running", "stale", "unavailable")
    # Decimal phai la so JSON, khong phai chuoi.
    assert body["duration_p95_ms"] is None or isinstance(body["duration_p95_ms"], (int, float))
    assert body["cost_estimate"]["estimated_usd"] is None or isinstance(
        body["cost_estimate"]["estimated_usd"], (int, float)
    )
    assert body["date_from"] == "2026-08-01"
    print("[PASS] dashboard tra du truong, Decimal la so JSON")


def test_dashboard_tu_choi_khoang_ngay_sai(conn):
    _reset_schema(conn)
    client = _dang_nhap_viewer(conn)
    response = client.get("/api/console/v1/dashboard?from=2026-08-31&to=2026-08-01")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_filter"
    print("[PASS] dashboard tu choi khoang ngay dao nguoc")
```

- [ ] **Step 2: Chạy để xác nhận thất bại** — kỳ vọng 404 vì chưa có route.

- [ ] **Step 3: Thêm model**

```python
class CostEstimateModel(BaseModel):
    input_tokens: int
    output_tokens: int
    estimated_usd: float | None
    pricing_version: int
    effective_at: str
    currency: str
    source: str
    unknown_models: list[str]

    @classmethod
    def tu_dataclass(cls, value) -> "CostEstimateModel":
        return cls(
            input_tokens=value.input_tokens,
            output_tokens=value.output_tokens,
            estimated_usd=so(value.estimated_usd),
            pricing_version=value.pricing_version,
            effective_at=value.effective_at.isoformat(),
            currency=value.currency,
            source=value.source,
            unknown_models=list(value.unknown_models),
        )


class DashboardResponse(BaseModel):
    date_from: str
    date_to: str
    queue_counts: dict[str, int]
    total_reviews: int
    decision_counts: dict[str, int]
    duration_p50_ms: float | None
    duration_p95_ms: float | None
    cost_estimate: CostEstimateModel
    writeback_counts: dict[str, int]
    writeback_success_rate: float | None
    worker_status: str
    connector_status: str
    worker_running: int
    worker_stale: int
    worker_last_seen_at: str | None
```

- [ ] **Step 4: Viết route**

```python
@router.get("/dashboard", response_model=models.DashboardResponse)
def dashboard(
    request: Request,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    date_from, date_to = _khoang_ngay(request)   # parse ?from=&to=, mac dinh 30 ngay
    try:
        view = queries.dashboard(conn, date_from, date_to)
    except ValueError as exc:
        raise errors.invalid_filter(str(exc)) from exc
    return models.DashboardResponse(
        date_from=view.date_from.isoformat(),
        date_to=view.date_to.isoformat(),
        queue_counts=view.queue_counts,
        total_reviews=view.total_reviews,
        decision_counts=view.decision_counts,
        duration_p50_ms=models.so(view.duration_p50_ms),
        duration_p95_ms=models.so(view.duration_p95_ms),
        cost_estimate=models.CostEstimateModel.tu_dataclass(view.cost_estimate),
        writeback_counts=view.writeback_counts,
        writeback_success_rate=models.so(view.writeback_success_rate),
        worker_status=view.worker_status,
        connector_status=view.connector_status,
        worker_running=view.worker_running,
        worker_stale=view.worker_stale,
        worker_last_seen_at=models.iso(view.worker_last_seen_at),
    )
```

`_khoang_ngay` đọc `?from=`/`?to=` dạng `YYYY-MM-DD`, raise `errors.invalid_filter` khi sai định dạng hoặc `from > to`, mặc định 30 ngày gần nhất khi thiếu.

- [ ] **Step 5: Chạy test + đăng ký manifest + chạy cả nhóm** — kỳ vọng `[PASS]` cả hai, `all-offline` báo `hong: 0`, `co [SKIP]: 0`.

- [ ] **Step 6: Commit**

```bash
git add src/review_platform/admin_api/ scripts/test_console_api_dashboard.py scripts/test_groups.json
git commit -m "feat: endpoint dashboard cho Console API"
```

---

### Task 5: `GET /jobs` và `GET /jobs/{public_id}`

**Files:**
- Create: `src/review_platform/admin_api/job_routes.py`
- Modify: `models.py`, `router.py`
- Test: `scripts/test_console_api_jobs.py`
- Modify: `scripts/test_groups.json`

**Interfaces:**
- Consumes: `queries.JobFilters`, `queries.list_jobs`, `queries.get_job`.
- Produces: `models.JobListItemModel`, `models.JobDetailModel`, `models.JobPage`, và **`models.trang(...)`** — helper phân trang dùng lại ở task 7.

- [ ] **Step 1: Viết test thất bại**

```python
def test_jobs_phan_trang_dung_hinh_dang(conn):
    _reset_schema(conn)
    _seed_jobs(conn, so_luong=137)
    client = _dang_nhap_viewer(conn)

    response = client.get("/api/console/v1/jobs?page=1&page_size=50")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total", "total_pages"}
    assert body["total"] == 137 and body["total_pages"] == 3
    assert len(body["items"]) == 50

    dau = body["items"][0]
    assert set(dau) == {
        "public_id", "created_at", "site_id", "site_slug",
        "external_content_id", "status", "attempts", "source", "policy_version",
    }
    assert dau["created_at"].endswith("Z"), dau["created_at"]
    print("[PASS] jobs phan trang dung hinh dang chuan")


def test_jobs_loc_sai_tra_422_dung_hinh_dang_loi(conn):
    _reset_schema(conn)
    client = _dang_nhap_viewer(conn)
    for duong_dan in ("/api/console/v1/jobs?status=khong-ton-tai",
                      "/api/console/v1/jobs?page=0",
                      "/api/console/v1/jobs?from=2026-08-13"):
        response = client.get(duong_dan)
        assert response.status_code == 422, duong_dan
        assert set(response.json()["error"]) == {"code", "message", "field"}
    print("[PASS] jobs loc sai tra 422 dung hinh dang loi")


def test_job_detail_khong_ton_tai_tra_404(conn):
    _reset_schema(conn)
    client = _dang_nhap_viewer(conn)
    assert client.get("/api/console/v1/jobs/%s" % uuid4()).status_code == 404
    assert client.get("/api/console/v1/jobs/khong-phai-uuid").status_code == 404
    print("[PASS] job detail tra 404 cho id la va id sai dinh dang")
```

- [ ] **Step 2: Chạy để xác nhận thất bại** — kỳ vọng 404 vì chưa có route.

- [ ] **Step 3: Thêm helper phân trang + model**

```python
class PageResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


def trang(view, items: list) -> dict:
    """Trai PageView thanh dict chuan. Dung cho MOI endpoint danh sach."""
    return {
        "items": items,
        "page": view.page,
        "page_size": view.page_size,
        "total": view.total,
        "total_pages": view.total_pages,
    }


class JobListItemModel(BaseModel):
    public_id: str
    created_at: str
    site_id: str
    site_slug: str
    external_content_id: str
    status: str
    attempts: int
    source: str
    policy_version: str


class JobPage(PageResponse):
    items: list[JobListItemModel]
```

`JobDetailModel` khai báo đủ 22 trường của `queries.JobDetail`, giữ nguyên tên, áp quy ước chuyển kiểu: `public_id`/`site_id`/`profile_id`/`correlation_id`/`supersedes_job_public_id`/`run_public_id` → `str | None`; `created_at`/`updated_at`/`run_scored_at` → `str | None` qua `iso`; `saved_result_available` → `bool`.

- [ ] **Step 4: Viết route**

```python
@router.get("/jobs", response_model=models.JobPage)
def list_jobs(
    request: Request,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    try:
        filters, page_number, page_size = _bo_loc(request)
        view = queries.list_jobs(conn, filters, page_number, page_size)
    except ValueError as exc:
        raise errors.invalid_filter(str(exc)) from exc
    return models.trang(view, [_job_item(item) for item in view.items])


@router.get("/jobs/{public_id}", response_model=models.JobDetailModel)
def get_job(
    public_id: str,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    try:
        parsed = UUID(public_id)
    except ValueError as exc:
        raise errors.not_found("Job khong ton tai") from exc
    job = queries.get_job(conn, parsed)
    if job is None:
        raise errors.not_found("Job khong ton tai")
    return _job_detail(job)
```

`_bo_loc` chuyển query params thành `queries.JobFilters` + `page`/`page_size`, tái dùng đúng quy tắc của `admin/job_routes.py:_filters` (bao gồm `page >= 1`, `page_size` trong khoảng cho phép, `from` và `to` phải đi cùng nhau).

- [ ] **Step 5: Chạy test + đăng ký manifest + chạy cả nhóm** — kỳ vọng 3 `[PASS]`, `all-offline` sạch.

- [ ] **Step 6: Commit**

```bash
git add src/review_platform/admin_api/ scripts/test_console_api_jobs.py scripts/test_groups.json
git commit -m "feat: endpoint danh sach va chi tiet job cho Console API"
```

---

### Task 6: `POST /jobs/{public_id}/retry` (yêu cầu operator)

**Files:**
- Modify: `src/review_platform/admin_api/job_routes.py`
- Test: `scripts/test_console_api_jobs.py` (bổ sung), `scripts/test_console_api_auth.py` (test role giờ phải xanh)

**Interfaces:**
- Consumes: `reviews.retry_failed(conn, *, job_public_id, actor, reason) -> RetryResult` (`src/review_platform/reviews.py:74`); ngoại lệ `reviews.JobRetryNotFound`, `reviews.JobRetryConflict`, `reviews.JobRetryContextError`. Dùng lại **nguyên hàm đó**, không viết lại logic retry.
- Produces: `models.RetryRequest(confirm_cost: bool, reason: str | None)`.

**Cổng an toàn bắt buộc giữ:** retry kích hoạt lại pipeline, tức là **gọi API trả phí**. `admin/job_routes.py:216` chặn khi `confirm_cost != "yes"` và trả 400. Console API phải giữ cổng này dưới dạng `confirm_cost: bool` trong thân JSON. Bỏ nó đi nghĩa là một cú bấm nhầm trong React tiêu tiền thật.

**Lưu ý về giá trị trả về:** `retry_failed` tạo ra **job mới** và trả `RetryResult.new_job_public_id`, không phải job cũ. Response trả chi tiết của job mới.

- [ ] **Step 1: Viết test thất bại**

```python
def test_retry_yeu_cau_operator_va_job_phai_failed(conn):
    _reset_schema(conn)
    job_failed = _seed_job(conn, status="failed")
    job_running = _seed_job(conn, status="running")

    xac_nhan = {"confirm_cost": True, "reason": "test"}

    viewer = _dang_nhap(conn, "retry.viewer", Role.VIEWER)
    r = viewer.post(
        "/api/console/v1/jobs/%s/retry" % job_failed,
        json=xac_nhan,
        headers={"X-CSRF-Token": _csrf(viewer, conn)},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"

    operator = _dang_nhap(conn, "retry.operator", Role.OPERATOR)
    ok = operator.post(
        "/api/console/v1/jobs/%s/retry" % job_failed,
        json=xac_nhan,
        headers={"X-CSRF-Token": _csrf(operator, conn)},
    )
    assert ok.status_code == 200, ok.text
    # retry tao JOB MOI, khong tra lai job cu.
    assert ok.json()["public_id"] != str(job_failed)

    xung_dot = operator.post(
        "/api/console/v1/jobs/%s/retry" % job_running,
        json=xac_nhan,
        headers={"X-CSRF-Token": _csrf(operator, conn)},
    )
    assert xung_dot.status_code == 409
    assert xung_dot.json()["error"]["code"] == "conflict"
    print("[PASS] retry: viewer 403, operator 200 tao job moi, job dang chay 409")


def test_retry_khong_xac_nhan_chi_phi_bi_chan(conn):
    _reset_schema(conn)
    job_failed = _seed_job(conn, status="failed")
    operator = _dang_nhap(conn, "retry.chiphi", Role.OPERATOR)
    r = operator.post(
        "/api/console/v1/jobs/%s/retry" % job_failed,
        json={"confirm_cost": False, "reason": None},
        headers={"X-CSRF-Token": _csrf(operator, conn)},
    )
    assert r.status_code == 400, r.status_code
    assert r.json()["error"]["code"] == "cost_not_confirmed"
    print("[PASS] retry khong xac nhan chi phi bi chan truoc khi goi API tra phi")


def test_retry_thieu_csrf_header_bi_tu_choi(conn):
    _reset_schema(conn)
    job_failed = _seed_job(conn, status="failed")
    operator = _dang_nhap(conn, "retry.nocsrf", Role.OPERATOR)
    r = operator.post("/api/console/v1/jobs/%s/retry" % job_failed)
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_invalid"
    print("[PASS] retry thieu header X-CSRF-Token bi tu choi")
```

- [ ] **Step 2: Chạy để xác nhận thất bại** — kỳ vọng 404/405 vì chưa có route.

- [ ] **Step 3: Viết route**

Thêm vào `models.py`:

```python
class RetryRequest(BaseModel):
    confirm_cost: bool = False
    reason: str | None = None
```

Route trong `job_routes.py`:

```python
@router.post(
    "/jobs/{public_id}/retry",
    response_model=models.JobDetailModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def retry_job(
    public_id: str,
    payload: models.RetryRequest,
    resolved=Depends(dependencies.require_console_role(Role.OPERATOR)),
    conn=Depends(admin_dependencies.get_db),
):
    try:
        parsed = UUID(public_id)
    except ValueError as exc:
        raise errors.not_found("Job khong ton tai") from exc
    if queries.get_job(conn, parsed) is None:
        raise errors.not_found("Job khong ton tai")
    # Cong an toan: retry kich hoat lai pipeline goi API TRA PHI.
    if not payload.confirm_cost:
        raise errors.ConsoleError(
            400,
            "cost_not_confirmed",
            "Phai xac nhan kha nang phat sinh chi phi truoc khi retry",
            "confirm_cost",
        )
    try:
        result = reviews.retry_failed(
            conn,
            job_public_id=parsed,
            actor=resolved.user,
            reason=payload.reason,
        )
    except reviews.JobRetryNotFound as exc:
        raise errors.not_found("Job khong ton tai") from exc
    except (reviews.JobRetryConflict, reviews.JobRetryContextError) as exc:
        raise errors.ConsoleError(409, "conflict", str(exc)) from exc
    job_moi = queries.get_job(conn, result.new_job_public_id)
    return _job_detail(job_moi)
```

Thứ tự ba lần kiểm tra là cố ý và phải giữ đúng: **404 trước, rồi cổng chi phí, rồi mới retry**. Đảo lại thì một job không tồn tại vẫn trả 400 "chưa xác nhận chi phí", làm lộ ra rằng lỗi nằm ở chỗ khác và gây nhiễu khi truy sự cố.

- [ ] **Step 4: Chạy test** — kỳ vọng 3 `[PASS]` mới (role, cổng chi phí, thiếu CSRF), và `test_sai_role_tra_403_khong_phai_401` trong `test_console_api_auth.py` giờ cũng `[PASS]`.

- [ ] **Step 5: Commit**

```bash
git add src/review_platform/admin_api/job_routes.py scripts/test_console_api_jobs.py
git commit -m "feat: endpoint retry job cho Console API, yeu cau operator"
```

---

### Task 7: `GET /reviews` và `GET /reviews/{public_id}`

Đây là task serialize phức tạp nhất và là task **có rủi ro bảo mật**: `ReviewDetail` chứa dữ liệu bắt nguồn từ output của model.

**Files:**
- Create: `src/review_platform/admin_api/review_routes.py`
- Modify: `models.py`, `router.py`
- Test: `scripts/test_console_api_reviews.py`
- Modify: `scripts/test_groups.json`

**Interfaces:**
- Consumes: `queries.list_reviews`, `queries.get_review`, `models.trang`, `models.CostEstimateModel`.
- Produces: không có gì cho task sau.

- [ ] **Step 1: Viết test thất bại**

Test quan trọng nhất là test làm sạch dữ liệu — nó phải chứng minh API **không** trả ra dữ liệu thô:

```python
def test_review_detail_van_lam_sach_du_lieu_agent(conn):
    _reset_schema(conn)
    # Gieo mot run_log co payload doc hai trong criteria/issues/evidence.
    review_id = _seed_review_doc_hai(
        conn,
        marker_script="<script>alert('XSS-MARKER')</script>",
        marker_password="RAW-PASSWORD-MARKER",
    )
    client = _dang_nhap_viewer(conn)

    response = client.get("/api/console/v1/reviews/%s" % review_id)
    assert response.status_code == 200
    raw = response.text
    assert "XSS-MARKER" not in raw, "payload tho lot ra JSON, thieu buoc sanitization"
    assert "RAW-PASSWORD-MARKER" not in raw

    # So sanh voi chinh queries.get_review: API khong duoc lam sach it hon.
    mong_doi = queries.get_review(conn, review_id)
    assert len(response.json()["agents"]) == len(mong_doi.agents)
    print("[PASS] review detail giu nguyen buoc lam sach cua queries")


def test_reviews_final_score_la_so_khong_phai_chuoi(conn):
    _reset_schema(conn)
    _seed_reviews(conn, so_luong=3)
    client = _dang_nhap_viewer(conn)
    body = client.get("/api/console/v1/reviews").json()
    diem = [i["final_score"] for i in body["items"] if i["final_score"] is not None]
    assert diem, "can it nhat mot review co diem de kiem tra kieu"
    assert all(isinstance(d, (int, float)) and not isinstance(d, bool) for d in diem)
    print("[PASS] final_score la so JSON, khong phai chuoi")
```

- [ ] **Step 2: Chạy để xác nhận thất bại** — kỳ vọng 404 vì chưa có route.

- [ ] **Step 3: Thêm model**

```python
class AgentResultModel(BaseModel):
    name: str
    score: float | int | str | None
    criteria: list[dict]
    issues: list[dict]
    evidence: list[dict]


class ReviewListItemModel(BaseModel):
    public_id: str
    scored_at: str
    site_id: str
    site_slug: str
    external_content_id: str
    decision: str | None
    final_score: float | None
    profile_code: str
    policy_version: str
    model: str
    is_fixture: bool


class ReviewPage(PageResponse):
    items: list[ReviewListItemModel]
```

`ReviewDetailModel` khai báo đủ 26 trường của `queries.ReviewDetail`, giữ nguyên tên. `agents: list[AgentResultModel]`, `cost_estimate: CostEstimateModel`, `config_meta: dict | list | str | int | float | bool | None`.

- [ ] **Step 4: Viết route**

Route chỉ gọi `queries.list_reviews` / `queries.get_review` rồi map sang model. **Không thêm và không bỏ bước xử lý dữ liệu nào** — `queries.get_review` đã chạy `sanitization` cho `criteria`/`issues`/`evidence`, và đó chính là lý do test bước 1 xanh. Nếu test bước 1 đỏ, nguyên nhân là route đã đọc dữ liệu thô từ chỗ khác chứ không phải thiếu bước làm sạch mới.

- [ ] **Step 5: Chạy test + đăng ký manifest + chạy cả nhóm** — kỳ vọng 2 `[PASS]`, `all-offline` sạch.

- [ ] **Step 6: Commit**

```bash
git add src/review_platform/admin_api/ scripts/test_console_api_reviews.py scripts/test_groups.json
git commit -m "feat: endpoint danh sach va chi tiet review cho Console API"
```

---

### Task 8: Mount vào app + xuất `openapi.json` + sinh `api-types.ts`

**Files:**
- Modify: `src/api.py:44` trở đi
- Create: `scripts/export_openapi.py`
- Create: `console_ui/openapi.json` (sinh ra, commit vào repo)
- Test: `scripts/test_console_api_mount.py`
- Modify: `scripts/test_groups.json`

**Interfaces:**
- Consumes: `admin_api.router.router`, `admin_api.errors.console_error_handler`.
- Produces: `console_ui/openapi.json` — task 9 (brief Stitch) và task 10 (types) đều đọc file này.

- [ ] **Step 1: Viết test thất bại**

```python
def test_app_that_co_du_route_console(conn):
    import api as app_module
    duong_dan = {r.path for r in app_module.app.routes}
    can_co = {
        "/api/console/v1/auth/login",
        "/api/console/v1/auth/me",
        "/api/console/v1/auth/logout",
        "/api/console/v1/auth/change-password",
        "/api/console/v1/dashboard",
        "/api/console/v1/jobs",
        "/api/console/v1/jobs/{public_id}",
        "/api/console/v1/jobs/{public_id}/retry",
        "/api/console/v1/reviews",
        "/api/console/v1/reviews/{public_id}",
    }
    thieu = can_co - duong_dan
    assert not thieu, f"thieu route: {sorted(thieu)}"
    print("[PASS] app that mount du 10 route Console")


def test_openapi_sinh_duoc_va_khong_co_route_admin_cu(conn):
    import api as app_module
    schema = app_module.app.openapi()
    duong_dan = set(schema["paths"])
    assert "/api/console/v1/auth/me" in duong_dan
    # Trang Jinja2 dat include_in_schema=False hoac khong nam trong openapi:
    # hop dong giao cho Antigravity chi duoc chua API JSON.
    assert not [p for p in duong_dan if p.startswith("/admin")], sorted(duong_dan)
    print("[PASS] openapi chi chua API JSON, khong lan route admin cu")
```

- [ ] **Step 2: Chạy để xác nhận thất bại** — kỳ vọng `thieu route: [...]` liệt kê cả 10.

- [ ] **Step 3: Mount trong `src/api.py`**

Sau dòng `app = FastAPI(...)`:

```python
from review_platform.admin_api import errors as console_errors
from review_platform.admin_api import router as console_router

app.add_exception_handler(console_errors.ConsoleError, console_errors.console_error_handler)
app.include_router(console_router.router)
```

Mount thư mục build React (đặt **sau** mọi `include_router`, nếu không catch-all sẽ nuốt các route API):

```python
CONSOLE_DIST = Path(__file__).resolve().parent.parent / "console_ui" / "dist"
if CONSOLE_DIST.is_dir():
    # html=True tra index.html cho duong dan con, de React Router khong 404 khi F5.
    app.mount("/console", StaticFiles(directory=CONSOLE_DIST, html=True), name="console")
```

Bọc trong `if` để app vẫn khởi động được khi chưa build frontend — quan trọng vì task 1-8 chạy trước khi `console_ui/` tồn tại.

Nếu các route admin Jinja2 hiện lên trong `openapi.json`, thêm `include_in_schema=False` cho router admin lúc `include_router`, **không** sửa từng decorator.

- [ ] **Step 4: Viết `scripts/export_openapi.py`**

```python
"""Ghi hop dong API ra console_ui/openapi.json.

Chay lai sau MOI lan doi model hoac route Console:
    .venv\\Scripts\\python.exe scripts\\export_openapi.py
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import api as app_module

DICH = Path(__file__).resolve().parents[1] / "console_ui" / "openapi.json"


def main() -> int:
    schema = app_module.app.openapi()
    paths = {p: v for p, v in schema["paths"].items() if p.startswith("/api/console/")}
    schema["paths"] = paths
    DICH.parent.mkdir(parents=True, exist_ok=True)
    DICH.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] ghi {len(paths)} duong dan vao {DICH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Tên file bắt đầu bằng `export_`, không phải `test_`, nên `kiem_manifest` bỏ qua — đúng ý đồ.

- [ ] **Step 5: Sinh file và chạy test**

```
.venv\Scripts\python.exe scripts\export_openapi.py
.venv\Scripts\python.exe scripts\test_console_api_mount.py
.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```
Kỳ vọng: in `[OK] ghi 10 duong dan`, 2 `[PASS]`, nhóm sạch.

- [ ] **Step 6: Commit**

```bash
git add src/api.py scripts/export_openapi.py scripts/test_console_api_mount.py scripts/test_groups.json console_ui/openapi.json
git commit -m "feat: mount Console API vao app that va xuat openapi.json"
```

---

### Task 9: Sáu brief Stitch

**Files:**
- Create: `docs/console-ui/stitch-briefs.md`, `docs/console-ui/integration.md`

**Interfaces:**
- Consumes: `console_ui/openapi.json` (task 8).
- Produces: tài liệu cho người, không có interface code.

- [ ] **Step 1: Đọc `openapi.json` lấy danh sách trường thật**

```
.venv\Scripts\python.exe -c "import json;s=json.load(open('console_ui/openapi.json',encoding='utf-8'));[print(k, sorted(v.get('properties',{}))) for k,v in s['components']['schemas'].items()]"
```

Mọi trường xuất hiện trong brief **phải** có mặt trong đầu ra này. Đây là bước kiểm chứng, không phải bước tham khảo.

- [ ] **Step 2: Viết `stitch-briefs.md`**

Sáu prompt: Login, Dashboard, Jobs, Job detail, Reviews, Review detail. Mỗi prompt bốn khối `CONTEXT` / `DATA` / `STATES` / `STYLE`. Khối `STYLE` **giống hệt nhau ở cả sáu prompt** — chép lại đầy đủ trong từng prompt, không viết "như prompt trên", vì người dùng sẽ copy từng khối riêng lẻ vào Stitch:

```
STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

Prompt Jobs dùng nguyên khối `DATA` sau (tên trường lấy từ `JobListItemModel`):

```
DATA — the table must show EXACTLY these columns, no others, no invented ones:
- Ma job        (public_id, UUID, shortened, monospace)      e.g. "a3f2…9c41"
- Thoi gian tao (created_at, ISO datetime UTC)                e.g. "19/08/2026 14:32"
- Site          (site_slug, short string)                     e.g. "vinfast-vn"
- ID noi dung   (external_content_id, string)                 e.g. "node/1842"
- Trang thai    (status, badge, exactly 4 values): queued / running / succeeded / failed
- So lan thu    (attempts, integer, right-aligned)            e.g. 2
- Thao tac: a "Thu lai" button, ONLY on rows with status = failed,
  and ONLY visible to roles operator and admin.

CONTROLS: filter by Trang thai (dropdown) and Site (dropdown); pagination showing
"Trang 1 / 3 · 137 ket qua" with previous/next. No search box, no export button.
```

Năm brief còn lại theo đúng khuôn đó, khối `DATA` lấy từ `DashboardResponse`, `JobDetailModel`, `ReviewListItemModel`, `ReviewDetailModel`, và `MeResponse` (Login chỉ có username + password + thông báo lỗi).

Brief **Job detail** phải mô tả thêm một hộp thoại xác nhận cho nút "Thử lại", vì API bắt buộc `confirm_cost` (task 6):

```
The "Thu lai" action opens a confirmation dialog before it fires. The dialog
states that retrying re-runs the paid AI pipeline and may incur cost, has an
optional "Ly do" text field, and requires an explicit confirm click. Design
both the dialog and its loading state. The action is hidden entirely for the
viewer role.
```

- [ ] **Step 3: Viết `integration.md`**

Ba mục, đúng những thứ OpenAPI diễn đạt kém: (1) vòng đời phiên — `/auth/me` khi khởi động, 401 thì về login; (2) CSRF — lấy token từ `/auth/me`, gửi header `X-CSRF-Token` cho mọi POST; (3) bảng mã lỗi 401/403/404/409/422 kèm hành vi UI mong đợi, sao chép từ spec mục 4.2.

- [ ] **Step 4: Kiểm chứng**

Với mỗi tên trường xuất hiện trong `stitch-briefs.md`, xác nhận nó có trong đầu ra bước 1. Ghi kết quả kiểm chứng vào cuối `stitch-briefs.md` dưới dạng một dòng: `Đối chiếu với console_ui/openapi.json ngày <ngày>: N trường, 0 lệch.`

- [ ] **Step 5: Commit**

```bash
git add docs/console-ui/
git commit -m "docs: sau brief Stitch va tai lieu tich hop cho Console UI"
```

---

### Task 10: Bộ khung React

**Files:**
- Create: `console_ui/package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `index.html`
- Create: `console_ui/src/api/client.ts`, `src/api/api-types.ts` (sinh tự động), `src/auth/AuthProvider.tsx`, `src/auth/RequireAuth.tsx`, `src/auth/RequireRole.tsx`, `src/layout/AppShell.tsx`, `src/router.tsx`, `src/main.tsx`
- Create: `console_ui/src/pages/` — 7 file skeleton
- Create: `console_ui/README.md` — hướng dẫn cho Antigravity

**Interfaces:**
- Consumes: `console_ui/openapi.json` (task 8).
- Produces: hợp đồng frontend mà Antigravity phải dùng —
  - `client.get<T>(path: string): Promise<T>` và `client.post<T>(path: string, body?: unknown): Promise<T>` (tự gắn `X-CSRF-Token`, tự ném `ConsoleApiError` khi lỗi);
  - `useAuth(): { user: MeResponse | null; login(u, p): Promise<void>; logout(): Promise<void> }`;
  - `<RequireRole role="operator">` bọc phần UI chỉ operator thấy.

- [ ] **Step 1: Khởi tạo dự án**

```bash
cd console_ui
npm create vite@latest . -- --template react-ts
npm install react-router-dom @tanstack/react-query
npm install -D tailwindcss postcss autoprefixer openapi-typescript
npx tailwindcss init -p
```

- [ ] **Step 2: Cấu hình proxy và token thương hiệu**

`vite.config.ts` — proxy giữ same-origin khi dev, nhờ đó cookie phiên hoạt động y như production:

```ts
export default defineConfig({
  plugins: [react()],
  base: "/console/",
  server: {
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: false } },
  },
});
```

`base: "/console/"` là bắt buộc: thiếu nó, các đường dẫn asset trong `dist/index.html` trỏ về `/` và trang trắng khi FastAPI serve.

`tailwind.config.js` — token lấy từ `drupal/web/themes/custom/vinfast_theme/css/`:

```js
theme: {
  extend: {
    colors: {
      vf: { DEFAULT: "#00237a", hover: "#001f68" },
      surface: "#f9f9f9",
      ink: "#1a1c1c",
    },
    fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
  },
},
```

- [ ] **Step 3: Sinh kiểu từ hợp đồng**

```bash
npx openapi-typescript openapi.json -o src/api/api-types.ts
```

Thêm script vào `package.json`: `"types": "openapi-typescript openapi.json -o src/api/api-types.ts"`. Chạy lại mỗi khi backend đổi.

- [ ] **Step 4: Viết `src/api/client.ts`**

```ts
export class ConsoleApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly field: string | null = null,
  ) {
    super(message);
  }
}

const BASE = "/api/console/v1";
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.method && init.method !== "GET") {
    headers.set("Content-Type", "application/json");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }
  // credentials: "same-origin" la mac dinh, nhung ghi ro de khong ai doi nham
  // thanh "omit" - cookie phien la thu duy nhat xac thuc request nay.
  const response = await fetch(BASE + path, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const e = body?.error ?? {};
    throw new ConsoleApiError(
      response.status,
      e.code ?? "unknown",
      e.message ?? "Đã xảy ra lỗi",
      e.field ?? null,
    );
  }
  return body as T;
}

export const client = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};
```

- [ ] **Step 5: Viết `AuthProvider` + `RequireAuth` + `RequireRole`**

`AuthProvider` gọi `client.get<MeResponse>("/auth/me")` một lần khi mount; thành công thì `setCsrfToken(me.csrf_token)` và lưu `user`; `ConsoleApiError` mã 401 thì đặt `user = null`. `RequireAuth` chuyển hướng sang `/console/login` khi `user === null` và render spinner khi còn đang tải. `RequireRole` so `user.role` với thứ tự `viewer < operator < admin` — chép đúng thứ tự từ `auth/rbac.py`.

- [ ] **Step 6: Viết 7 trang skeleton**

Mỗi trang chỉ chứa hook gọi API và bốn nhánh trạng thái, **không có CSS trang trí** — phần đó là việc của Antigravity theo design Stitch:

```tsx
export function JobsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => client.get<JobPage>("/jobs"),
  });
  if (isLoading) return <div>Đang tải…</div>;
  if (error) return <div>{(error as ConsoleApiError).message}</div>;
  if (!data?.items.length) return <div>Chưa có job nào khớp bộ lọc</div>;
  // TODO(Antigravity): dựng bảng theo design Stitch "Jobs".
  // Dữ liệu đã có trong `data.items`; KHÔNG gọi fetch trực tiếp.
  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}
```

- [ ] **Step 7: Viết `console_ui/README.md` cho Antigravity**

Năm quy tắc, mỗi quy tắc một câu lý do: (1) không sửa `src/api/api-types.ts` — file sinh tự động; (2) không gọi `fetch`/`axios` trực tiếp, dùng `client`; (3) không lưu token vào `localStorage`/`sessionStorage` — phiên nằm trong cookie `HttpOnly`; (4) mỗi màn hình phải có đủ bốn trạng thái; (5) chạy `npx tsc --noEmit` trước khi báo xong.

- [ ] **Step 8: Kiểm chứng chạy thật**

```bash
npx tsc --noEmit
npm run build
```
Rồi khởi động FastAPI và mở `http://localhost:8000/console`, đăng nhập bằng tài khoản thật. Tiêu chí đạt: đăng nhập vào được, `/auth/me` trả 200, trang Jobs hiện JSON thật. **Chụp màn hình gửi vào `img-for-ai-see/`** — dự án không có JS test harness nên đây là bằng chứng duy nhất, và không được tuyên bố "đã kiểm thử giao diện" nếu chưa có ảnh.

- [ ] **Step 9: Commit**

```bash
git add console_ui/
git commit -m "feat: bo khung React cho Console, san sang cho Antigravity dap giao dien"
```

---

## Kiểm tra sau khi xong toàn bộ

```
.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```
Phải báo `hong: 0` và `co [SKIP]: 0`.

Và xác nhận bằng tay rằng admin cũ chưa hỏng: mở `/admin`, đăng nhập, vào trang jobs, bấm đăng xuất. Bốn thao tác này chạm đúng những chỗ task 1 và task 3 đã sửa.
