r"""Test duong dan cookie phien admin.

Vi sao can: cookie phien truoc day dat o path=/admin, nen trinh duyet KHONG gui
no toi /api/console/v1 hay /console. Console React dung chung phien voi admin
Jinja2, nen cookie phai co hieu luc o toan bo origin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_session_cookie_path.py
"""
import hashlib
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies, router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_cookie_path"
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
    app.state.auth_config = dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=False,
    )
    app.add_exception_handler(dependencies.AdminForbidden, router.forbidden_response)
    app.include_router(router.router)
    app.mount(
        "/admin/static",
        StaticFiles(directory=router.STATIC_DIR),
        name="admin-static",
    )

    # Dai dien cho /api/console/v1: mot duong dan NGOAI /admin. Neu cookie con
    # bi gioi han o path=/admin thi route nay khong nhan duoc cookie nao.
    @app.get("/probe-outside-admin")
    def probe(request: Request):
        return {"has_cookie": dependencies.SESSION_COOKIE in request.cookies}

    app.dependency_overrides[dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.85", 50000))


def _user(conn, username: str, role: Role):
    return users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        role,
        must_change_password=False,
    )


def _login(client, username: str):
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={
            "username": username,
            "password": f"Mat-khau-{username}-2026",
            "csrf_token": token,
        },
    )


def _session_csrf(conn, client):
    raw = client.cookies.get(dependencies.SESSION_COOKIE)
    token_hash = hashlib.sha256(raw.encode("ascii")).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT csrf_secret FROM admin_session WHERE token_hash=%s",
            (token_hash,),
        )
        return cur.fetchone()[0]


def _session_cookie_headers(response):
    return [
        header
        for header in response.headers.get_list("set-cookie")
        if header.startswith(dependencies.SESSION_COOKIE + "=")
    ]


def _cookie_path(header: str) -> str:
    for part in header.split(";"):
        part = part.strip()
        if part.lower().startswith("path="):
            return part[5:]
    return ""


def test_login_sets_cookie_at_root_path(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.admin", Role.ADMIN)

    client = _make_client(conn)
    response = _login(client, account.username)
    assert response.status_code == 303, response.status_code

    headers = _session_cookie_headers(response)
    assert headers, "login khong dat cookie phien nao"
    issued = [h for h in headers if "Max-Age=0" not in h]
    assert len(issued) == 1, issued
    assert _cookie_path(issued[0]) == "/", issued[0]
    assert "HttpOnly" in issued[0] and "samesite=lax" in issued[0].lower()
    print("[PASS] login dat cookie phien o path=/ voi HttpOnly va SameSite=lax")


def test_login_clears_legacy_admin_cookie(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.legacy", Role.ADMIN)

    client = _make_client(conn)
    response = _login(client, account.username)

    cleared = [h for h in _session_cookie_headers(response) if "Max-Age=0" in h]
    assert cleared, (
        "login khong xoa cookie cu o /admin. Trinh duyet cua nguoi dang dang "
        "nhap se giu HAI cookie trung ten o hai path khac nhau."
    )
    assert _cookie_path(cleared[0]) == "/admin", cleared[0]
    print("[PASS] login xoa cookie phien cu con sot o /admin")


def test_cookie_reaches_paths_outside_admin(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.viewer", Role.VIEWER)

    client = _make_client(conn)
    _login(client, account.username)

    probe = client.get("/probe-outside-admin")
    assert probe.status_code == 200, probe.status_code
    assert probe.json()["has_cookie"] is True, (
        "cookie phien khong den duoc duong dan ngoai /admin, nen "
        "/api/console/v1 se luon tra 401"
    )
    print("[PASS] cookie phien den duoc duong dan ngoai /admin")


def test_logout_clears_cookie_on_both_paths(conn):
    _reset_schema(conn)
    account = _user(conn, "cookie.path.logout", Role.ADMIN)

    client = _make_client(conn)
    _login(client, account.username)
    csrf_token = _session_csrf(conn, client)

    response = client.post("/admin/logout", data={"csrf_token": csrf_token})
    assert response.status_code == 303, response.status_code

    paths = {_cookie_path(h) for h in _session_cookie_headers(response)}
    assert paths == {"/", "/admin"}, paths
    print("[PASS] logout xoa cookie phien o ca hai duong dan")


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
            test_login_sets_cookie_at_root_path,
            test_login_clears_legacy_admin_cookie,
            test_cookie_reaches_paths_outside_admin,
            test_logout_clears_cookie_on_both_paths,
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
