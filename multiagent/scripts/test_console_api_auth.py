r"""Integration/security test cho tang xac thuc cua Console API.

Vi sao rieng khoi admin Jinja2: admin cu tra redirect 303 sang trang dang nhap
khi khong co phien. Voi API JSON dieu do sai - fetch cua trinh duyet tu di theo
redirect nen SPA se nhan HTML voi ma 200 thay vi 401.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_auth.py
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import dependencies as console_dependencies
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import sessions, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_auth"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _make_client(conn):
    app = FastAPI()
    app.state.auth_config = admin_dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=False,
    )
    app.add_exception_handler(errors.ConsoleError, errors.console_error_handler)
    app.include_router(console_router.router)

    # Hai route tham do dai dien cho endpoint nghiep vu. Dung chung dependency
    # voi route that, nhung khong phu thuoc vao task /jobs va /reviews.
    @app.get("/api/console/v1/probe")
    def probe(resolved=Depends(console_dependencies.console_session)):
        return {"username": resolved.user.username}

    @app.post("/api/console/v1/probe-operator")
    def probe_operator(
        resolved=Depends(console_dependencies.require_console_role(Role.OPERATOR)),
    ):
        return {"username": resolved.user.username}

    app.dependency_overrides[admin_dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.90", 50000))


def _user(conn, username: str, role: Role, *, must_change_password: bool = False):
    return users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        role,
        must_change_password=must_change_password,
    )


def _login(client, username: str, password: str | None = None):
    return client.post(
        "/api/console/v1/auth/login",
        json={
            "username": username,
            "password": password or f"Mat-khau-{username}-2026",
        },
    )


def test_no_session_returns_401_json_not_redirect(conn):
    _reset_schema(conn)
    client = _make_client(conn)

    response = client.get("/api/console/v1/probe")
    assert response.status_code == 401, response.status_code
    assert response.headers.get("location") is None, (
        "API tra redirect. Fetch cua trinh duyet se di theo redirect va SPA "
        "nhan HTML voi ma 200 thay vi 401."
    )
    assert response.json() == {
        "error": {
            "code": "unauthenticated",
            "message": "Chua dang nhap",
            "field": None,
        }
    }
    print("[PASS] khong co phien tra 401 JSON, khong redirect 303")


def test_login_returns_identity_and_csrf_token(conn):
    _reset_schema(conn)
    account = _user(conn, "console.login", Role.OPERATOR)

    client = _make_client(conn)
    response = _login(client, account.username)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["username"] == account.username
    assert body["role"] == "operator"
    assert body["must_change_password"] is False
    assert body["csrf_token"], "SPA khong lay duoc csrf_token thi khong POST duoc"

    # Phien dung duoc ngay sau login.
    assert client.get("/api/console/v1/probe").status_code == 200
    print("[PASS] login tra danh tinh va csrf_token, phien dung duoc ngay")


def test_login_invalid_credentials_returns_401_error_shape(conn):
    _reset_schema(conn)
    _user(conn, "console.wrongpass", Role.VIEWER)

    client = _make_client(conn)
    response = _login(client, "console.wrongpass", password="Sai-mat-khau-2026")
    assert response.status_code == 401, response.status_code
    assert response.json()["error"]["code"] == "invalid_credentials"
    # Khong duoc lo ra la tai khoan co ton tai hay khong.
    khong_ton_tai = _login(client, "console.khongtontai", password="Bat-ky-2026")
    assert khong_ton_tai.status_code == 401
    assert khong_ton_tai.json()["error"] == response.json()["error"]
    print("[PASS] sai thong tin dang nhap tra 401 va khong lo su ton tai tai khoan")


def test_must_change_password_blocks_all_but_auth(conn):
    _reset_schema(conn)
    account = _user(conn, "console.mcp", Role.ADMIN, must_change_password=True)

    client = _make_client(conn)
    assert _login(client, account.username).status_code == 200

    me = client.get("/api/console/v1/auth/me")
    assert me.status_code == 200, (
        "/auth/me phai qua duoc, day la cach SPA biet can hien form doi mat khau"
    )
    assert me.json()["must_change_password"] is True

    blocked = client.get("/api/console/v1/probe")
    assert blocked.status_code == 403, blocked.status_code
    assert blocked.json()["error"]["code"] == "must_change_password"
    print("[PASS] must_change_password: /auth/me qua duoc, endpoint khac bi chan")


def test_wrong_role_returns_403_not_401(conn):
    _reset_schema(conn)
    viewer = _user(conn, "console.viewer", Role.VIEWER)

    client = _make_client(conn)
    csrf_token = _login(client, viewer.username).json()["csrf_token"]

    response = client.post(
        "/api/console/v1/probe-operator",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 403, response.status_code
    assert response.json()["error"]["code"] == "forbidden"
    print("[PASS] viewer bi 403 chu khong phai 401")


def test_logout_requires_csrf_header_and_revokes_session(conn):
    _reset_schema(conn)
    account = _user(conn, "console.logout", Role.ADMIN)

    client = _make_client(conn)
    csrf_token = _login(client, account.username).json()["csrf_token"]
    raw_token = client.cookies.get(admin_dependencies.SESSION_COOKIE)

    thieu_csrf = client.post("/api/console/v1/auth/logout")
    assert thieu_csrf.status_code == 403, thieu_csrf.status_code
    assert thieu_csrf.json()["error"]["code"] == "csrf_invalid"
    assert sessions.resolve(conn, raw_token) is not None, (
        "logout that bai CSRF ma van huy phien"
    )

    ok = client.post(
        "/api/console/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert ok.status_code == 204, ok.status_code
    assert sessions.resolve(conn, raw_token) is None, "logout khong huy phien"

    # Phai xoa cookie o CA HAI duong dan. dict(headers) se gop nhieu header
    # set-cookie thanh mot va lam mat mot lenh xoa - test nay bat dung loi do.
    paths = {
        part.strip()[5:]
        for header in ok.headers.get_list("set-cookie")
        if header.startswith(admin_dependencies.SESSION_COOKIE + "=")
        for part in header.split(";")
        if part.strip().lower().startswith("path=")
    }
    assert paths == {"/", "/admin"}, paths
    print("[PASS] logout bat buoc header CSRF, huy phien va xoa cookie ca hai path")


def test_change_password_requires_csrf_and_clears_must_change(conn):
    _reset_schema(conn)
    account = _user(conn, "console.chpw", Role.VIEWER, must_change_password=True)
    mat_khau_cu = f"Mat-khau-{account.username}-2026"
    mat_khau_moi = "Mat-khau-hoan-toan-moi-2026"

    client = _make_client(conn)
    csrf_token = _login(client, account.username).json()["csrf_token"]

    thieu_csrf = client.post(
        "/api/console/v1/auth/change-password",
        json={"current_password": mat_khau_cu, "new_password": mat_khau_moi},
    )
    assert thieu_csrf.status_code == 403
    assert thieu_csrf.json()["error"]["code"] == "csrf_invalid"

    sai_mat_khau = client.post(
        "/api/console/v1/auth/change-password",
        json={"current_password": "Sai-mat-khau-cu-2026", "new_password": mat_khau_moi},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert sai_mat_khau.status_code == 400, sai_mat_khau.status_code
    assert sai_mat_khau.json()["error"]["code"] == "password_rejected"

    ok = client.post(
        "/api/console/v1/auth/change-password",
        json={"current_password": mat_khau_cu, "new_password": mat_khau_moi},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert ok.status_code == 204, ok.text

    # Dang nhap lai bang mat khau moi thi khong con bi buoc doi nua.
    client_moi = _make_client(conn)
    lai = _login(client_moi, account.username, password=mat_khau_moi)
    assert lai.status_code == 200, lai.text
    assert lai.json()["must_change_password"] is False
    assert client_moi.get("/api/console/v1/probe").status_code == 200
    print("[PASS] doi mat khau bat buoc CSRF, tu choi mat khau cu sai, go co buoc doi")


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
            test_no_session_returns_401_json_not_redirect,
            test_login_returns_identity_and_csrf_token,
            test_login_invalid_credentials_returns_401_error_shape,
            test_must_change_password_blocks_all_but_auth,
            test_wrong_role_returns_403_not_401,
            test_logout_requires_csrf_header_and_revokes_session,
            test_change_password_requires_csrf_and_clears_must_change,
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
