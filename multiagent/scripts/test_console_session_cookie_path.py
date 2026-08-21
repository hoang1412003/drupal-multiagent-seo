r"""Test duong dan cua cookie phien Console.

Viet lai tu `test_admin_session_cookie_path.py` (2026-08-21) khi xoa admin
Jinja2: ban cu dang nhap qua form HTML cua /admin, ban nay dang nhap qua
Console API.

Vi sao van can sau khi /admin bien mat:

- Cookie phai dat o `path=/`. Neu no quay ve `/admin` thi trinh duyet khong
  gui no toi `/api/console/v1` nua va Console luon tra 401 - dung loi da xay
  ra that ngay 2026-08-19, va no im lang: server khong he thay request nao.
- Dang nhap phai XOA cookie cu con sot o `/admin`. Nguoi tung dung admin cu
  van con cookie do trong trinh duyet; hai cookie trung ten o hai path khac
  nhau se duoc gui kem nhau va server doc phai cai sai.
- Dang xuat phai xoa o CA HAI duong dan, vi ly do tren.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_session_cookie_path.py
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_cookie_path"
CSRF_KEY = b"csrf-key-rieng-cho-cookie-path-2026!"
THROTTLE_KEY = b"throttle-key-rieng-cho-cookie-2026!!"


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

    # Duong dan NGOAI /api/console: dung de chung minh cookie den duoc moi noi
    # trong origin, khong bi gioi han o mot tien to nao.
    @app.get("/probe-outside-console")
    def probe(request: Request):
        return {
            "has_cookie": admin_dependencies.SESSION_COOKIE in request.cookies,
        }

    app.dependency_overrides[admin_dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.99", 50000))


def _user(conn, username: str, role: Role):
    return users.create_user(
        conn, username, f"Mat-khau-{username}-2026", role, must_change_password=False
    )


def _login(client, username: str):
    return client.post(
        "/api/console/v1/auth/login",
        json={"username": username, "password": f"Mat-khau-{username}-2026"},
    )


def _session_cookie_headers(response) -> list[str]:
    """Moi header set-cookie cua cookie phien.

    Dung raw headers chu KHONG dung dict(response.headers): dict gop nhieu
    header cung ten lai lam mot va lam mat cac header con lai - dung loi da
    lam mot trong hai lenh xoa cookie bien mat khong dau vet.
    """
    return [
        gia_tri.decode("latin-1")
        for ten, gia_tri in response.headers.raw
        if ten.decode("latin-1").lower() == "set-cookie"
        and gia_tri.decode("latin-1").startswith(admin_dependencies.SESSION_COOKIE + "=")
    ]


def _cookie_path(header: str) -> str:
    for phan in header.split(";"):
        phan = phan.strip()
        if phan.lower().startswith("path="):
            return phan[5:]
    return ""


def test_login_dat_cookie_o_path_goc(conn):
    _reset_schema(conn)
    _user(conn, "cookie.path.admin", Role.ADMIN)

    client = _make_client(conn)
    response = _login(client, "cookie.path.admin")
    assert response.status_code == 200, response.text

    headers = _session_cookie_headers(response)
    assert headers, "login khong dat cookie phien nao"
    cap = [h for h in headers if "Max-Age=0" not in h]
    assert len(cap) == 1, cap
    assert _cookie_path(cap[0]) == "/", cap[0]
    assert "HttpOnly" in cap[0], cap[0]
    assert "samesite=lax" in cap[0].lower(), cap[0]
    print("[PASS] login dat cookie o path=/ voi HttpOnly va SameSite=lax")


def test_login_xoa_cookie_cu_con_sot_o_admin(conn):
    _reset_schema(conn)
    _user(conn, "cookie.path.legacy", Role.ADMIN)

    client = _make_client(conn)
    response = _login(client, "cookie.path.legacy")

    xoa = [h for h in _session_cookie_headers(response) if "Max-Age=0" in h]
    assert xoa, (
        "login khong xoa cookie cu o /admin. Trinh duyet cua nguoi tung dung "
        "admin cu se giu HAI cookie trung ten o hai path khac nhau."
    )
    assert _cookie_path(xoa[0]) == "/admin", xoa[0]
    print("[PASS] login xoa cookie phien cu con sot o /admin")


def test_cookie_den_duoc_duong_dan_ngoai_console(conn):
    _reset_schema(conn)
    _user(conn, "cookie.path.viewer", Role.VIEWER)

    client = _make_client(conn)
    _login(client, "cookie.path.viewer")

    probe = client.get("/probe-outside-console")
    assert probe.status_code == 200, probe.status_code
    assert probe.json()["has_cookie"] is True, (
        "cookie phien khong den duoc duong dan ngoai /api/console"
    )
    print("[PASS] cookie phien den duoc moi duong dan trong origin")


def test_logout_xoa_cookie_o_ca_hai_duong_dan(conn):
    _reset_schema(conn)
    _user(conn, "cookie.path.logout", Role.ADMIN)

    client = _make_client(conn)
    dang_nhap = _login(client, "cookie.path.logout")
    client.headers["X-CSRF-Token"] = dang_nhap.json()["csrf_token"]

    response = client.post("/api/console/v1/auth/logout")
    assert response.status_code in (200, 204), response.status_code

    duong_dan = {_cookie_path(h) for h in _session_cookie_headers(response)}
    assert duong_dan == {"/", "/admin"}, duong_dan
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
            test_login_dat_cookie_o_path_goc,
            test_login_xoa_cookie_cu_con_sot_o_admin,
            test_cookie_den_duoc_duong_dan_ngoai_console,
            test_logout_xoa_cookie_o_ca_hai_duong_dan,
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
