"""Integration test HTTP cho Platform Admin routes.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_routes.py
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from review_platform import migrations
from review_platform.admin import dependencies, router
from review_platform.auth import sessions, throttle, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_routes"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _make_client(conn, *, cookie_secure=False):
    app = FastAPI()
    app.state.auth_config = dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=cookie_secure,
    )
    app.add_exception_handler(
        dependencies.AdminForbidden,
        router.forbidden_response,
    )
    app.include_router(router.router)
    app.mount(
        "/admin/static",
        StaticFiles(directory=router.STATIC_DIR),
        name="admin-static",
    )
    app.dependency_overrides[dependencies.get_db] = lambda: conn

    @app.get("/admin/operator-test")
    def operator_test(
        user=Depends(dependencies.require_role(Role.OPERATOR)),
    ):
        return {"username": user.username}

    return TestClient(
        app,
        follow_redirects=False,
        client=("198.51.100.20", 50000),
    )


def _login_csrf(client) -> str:
    response = client.get("/admin/login")
    assert response.status_code == 200, response.text
    return client.cookies.get(router.LOGIN_CSRF_COOKIE)


def _login(client, username, password):
    token = _login_csrf(client)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def _session_csrf(conn, client) -> str:
    raw_token = client.cookies.get(router.SESSION_COOKIE)
    token_hash = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT csrf_secret FROM admin_session WHERE token_hash=%s",
            (token_hash,),
        )
        return cur.fetchone()[0]


def test_auth_config_fail_fast_key_thieu_ngan_trung_va_bool_sai(conn):
    valid = {
        "ADMIN_CSRF_KEY": "c" * 32,
        "ADMIN_THROTTLE_KEY": "t" * 32,
        "ADMIN_COOKIE_SECURE": "true",
    }
    loaded = dependencies.load_auth_config(valid)
    assert loaded.cookie_secure is True
    for changed, message in (
        ({"ADMIN_CSRF_KEY": ""}, "ADMIN_CSRF_KEY"),
        ({"ADMIN_THROTTLE_KEY": "short"}, "ADMIN_THROTTLE_KEY"),
        ({"ADMIN_THROTTLE_KEY": "c" * 32}, "khác nhau"),
        ({"ADMIN_COOKIE_SECURE": "sometimes"}, "true hoặc false"),
    ):
        with expect(dependencies.AuthConfigError, message):
            dependencies.load_auth_config({**valid, **changed})
    print("[PASS] auth config fail-fast voi key thieu/ngan/trung va bool sai")


def test_redirect_login_csrf_truoc_credential_va_wrong_password(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "route-user",
        "Mat-khau-route-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    unauthenticated = client.get("/admin")
    assert unauthenticated.status_code == 303
    assert unauthenticated.headers["location"] == "/admin/login"

    page = client.get("/admin/login")
    assert page.status_code == 200
    assert "Đăng nhập quản trị" in page.text
    assert "HttpOnly" in page.headers["set-cookie"]
    bad_csrf = client.post(
        "/admin/login",
        data={"username": "route-user", "password": "sai", "csrf_token": "sai"},
    )
    assert bad_csrf.status_code == 403
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_login_throttle")
        assert cur.fetchone()[0] == 0

    token = _login_csrf(client)
    wrong = client.post(
        "/admin/login",
        data={
            "username": "route-user",
            "password": "Mat-khau-sai-2026",
            "csrf_token": token,
        },
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert wrong.status_code == 401
    limiter = throttle.LoginThrottle(conn, THROTTLE_KEY)
    with conn.cursor() as cur:
        cur.execute("SELECT subject_hash FROM admin_login_throttle")
        assert cur.fetchone()[0] == limiter.subject_hash(
            "route-user",
            "198.51.100.20",
        )
    print("[PASS] redirect, login CSRF truoc credential va bo qua X-Forwarded-For")


def test_login_ok_cookie_flags_home_va_static(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "operator.user",
        "Mat-khau-operator-2026",
        Role.OPERATOR,
        must_change_password=False,
    )
    client = _make_client(conn)
    response = _login(client, "operator.user", "Mat-khau-operator-2026")
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    cookie = response.headers["set-cookie"]
    assert f"{router.SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/admin" in cookie

    home = client.get("/admin")
    assert home.status_code == 200
    assert "operator.user" in home.text and "operator" in home.text
    assert "Các màn hình vận hành được thêm ở phase tiếp theo" in home.text
    static = client.get("/admin/static/admin.css")
    assert static.status_code == 200
    assert "focus-visible" in static.text
    print("[PASS] login cookie flags, home that va static CSS")


def test_inactive_throttle_va_must_change_redirect(conn):
    _reset_schema(conn)
    inactive = users.create_user(
        conn,
        "inactive",
        "Mat-khau-inactive-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    users.set_active(conn, inactive.id, False)
    client = _make_client(conn)
    assert _login(client, "inactive", "Mat-khau-inactive-2026").status_code == 401

    forced = users.create_user(
        conn,
        "forced-change",
        "Mat-khau-forced-2026",
        Role.VIEWER,
        must_change_password=True,
    )
    login = _login(client, forced.username, "Mat-khau-forced-2026")
    assert login.status_code == 303
    assert login.headers["location"] == "/admin/change-password"
    blocked_home = client.get("/admin")
    assert blocked_home.status_code == 303
    assert blocked_home.headers["location"] == "/admin/change-password"

    client = _make_client(conn)
    for attempt in range(1, 6):
        response = _login(client, "khong-ton-tai", "Mat-khau-sai-2026")
        assert response.status_code == (429 if attempt == 5 else 401)
    print("[PASS] inactive bi tu choi, must-change bi ep route va fail thu 5 bi throttle")


def test_logout_csrf_revoke_va_viewer_bi_operator_gate(conn):
    _reset_schema(conn)
    user = users.create_user(
        conn,
        "viewer.user",
        "Mat-khau-viewer-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    assert _login(client, user.username, "Mat-khau-viewer-2026").status_code == 303
    forbidden = client.get("/admin/operator-test")
    assert forbidden.status_code == 403
    assert "<h1>Không có quyền truy cập</h1>" in forbidden.text
    assert client.post("/admin/logout", data={"csrf_token": "sai"}).status_code == 403

    csrf_token = _session_csrf(conn, client)
    logout = client.post("/admin/logout", data={"csrf_token": csrf_token})
    assert logout.status_code == 303
    assert logout.headers["location"] == "/admin/login"
    assert client.get("/admin").status_code == 303
    with conn.cursor() as cur:
        cur.execute(
            "SELECT revoked_at IS NOT NULL, revoke_reason FROM admin_session "
            "WHERE user_id=%s",
            (user.id,),
        )
        assert cur.fetchone() == (True, "logout")
    print("[PASS] logout bat CSRF/revoke va viewer bi operator gate 403")


def test_change_password_generic_error_revoke_va_bat_login_lai(conn):
    _reset_schema(conn)
    user = users.create_user(
        conn,
        "change.user",
        "Mat-khau-cu-2026",
        Role.VIEWER,
        must_change_password=True,
    )
    client = _make_client(conn)
    assert _login(client, user.username, "Mat-khau-cu-2026").status_code == 303
    csrf_token = _session_csrf(conn, client)
    mismatch = client.post(
        "/admin/change-password",
        data={
            "current_password": "Mat-khau-cu-2026",
            "new_password": "Mat-khau-moi-2026",
            "confirm_password": "khong-trung-2026",
            "csrf_token": csrf_token,
        },
    )
    assert mismatch.status_code == 400
    assert "Không thể đổi mật khẩu" in mismatch.text

    changed = client.post(
        "/admin/change-password",
        data={
            "current_password": "Mat-khau-cu-2026",
            "new_password": "Mat-khau-moi-2026",
            "confirm_password": "Mat-khau-moi-2026",
            "csrf_token": csrf_token,
        },
    )
    assert changed.status_code == 303
    assert changed.headers["location"] == "/admin/login"
    assert users.authenticate_candidate(conn, user.username, "Mat-khau-moi-2026")
    assert sessions.resolve(
        conn,
        client.cookies.get(router.SESSION_COOKIE, "missing"),
    ) is None
    login_page = client.get("/admin/login")
    assert "Đổi mật khẩu thành công" in login_page.text
    print("[PASS] change password dung generic error, revoke va bat login lai")


if __name__ == "__main__":
    try:
        connection = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            "[SKIP] khong phai [PASS]"
        )
        sys.exit(0)

    failed = False
    try:
        for fn in (
            test_auth_config_fail_fast_key_thieu_ngan_trung_va_bool_sai,
            test_redirect_login_csrf_truoc_credential_va_wrong_password,
            test_login_ok_cookie_flags_home_va_static,
            test_inactive_throttle_va_must_change_redirect,
            test_logout_csrf_revoke_va_viewer_bi_operator_gate,
            test_change_password_generic_error_revoke_va_bat_login_lai,
        ):
            try:
                fn(connection)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
    finally:
        with connection.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        connection.close()

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
