r"""Integration/security test cho tang xac thuc cua Console API.

Vi sao rieng khoi admin Jinja2: admin cu tra redirect 303 sang trang dang nhap
khi khong co phien. Voi API JSON dieu do sai - fetch cua trinh duyet tu di theo
redirect nen SPA se nhan HTML voi ma 200 thay vi 401.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_auth.py
"""
import os
from pathlib import Path
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import dependencies as console_dependencies
from review_platform.admin_api import auth_routes, errors, router as console_router
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
            "message": "Chưa đăng nhập",
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


def _dang_nhap_dua_voi(conn, doi_mat_khau, ten_thao_tac: str):
    """Ep mot lan dang nhap gap dung mot lan doi mat khau dang chay.

    Cach lam: chan `verify_password` lai NGAY SAU khi no xac nhan mat khau
    dung, roi cho thao tac doi mat khau chay xen vao. Neu khong co khoa row,
    hai ben se di qua nhau va phien vua cap se song sot - tuc la ke biet mat
    khau cu van giu duoc quyen truy cap sau khi mat khau da bi doi.
    """
    mat_khau_cu = f"Mat-khau-{ten_thao_tac}-cu-2026"
    nguoi_dung = users.create_user(
        conn, f"race.{ten_thao_tac}", mat_khau_cu, Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)

    # Ket noi RIENG cho luong doi mat khau: dung chung connection thi hai luong
    # noi tiep nhau va tranh chap khong bao gio xay ra.
    conn_khac = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn_khac.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")

    da_xac_thuc = threading.Event()
    cho_di_tiep = threading.Event()
    doi_xong = threading.Event()
    ket_qua_login: dict = {}
    ket_qua_doi: dict = {}
    goc = auth_routes.passwords.verify_password

    def chan_lai(hash_value, password):
        ket_qua = goc(hash_value, password)
        if password == mat_khau_cu and ket_qua:
            da_xac_thuc.set()
            if not cho_di_tiep.wait(5):
                raise AssertionError("test qua gio khi cho login di tiep")
        return ket_qua

    def chay_login():
        try:
            ket_qua_login["response"] = client.post(
                "/api/console/v1/auth/login",
                json={"username": nguoi_dung.username, "password": mat_khau_cu},
            )
        except Exception as exc:
            ket_qua_login["error"] = exc

    def chay_doi():
        try:
            doi_mat_khau(conn_khac, nguoi_dung.id)
        except Exception as exc:
            ket_qua_doi["error"] = exc
        finally:
            doi_xong.set()

    auth_routes.passwords.verify_password = chan_lai
    luong_login = threading.Thread(target=chay_login)
    luong_doi = threading.Thread(target=chay_doi)
    bi_chan = False
    try:
        luong_login.start()
        assert da_xac_thuc.wait(5), "login khong toi duoc diem xac thuc"
        luong_doi.start()
        # Neu co khoa row, luong doi mat khau phai BI CHAN o day.
        bi_chan = not doi_xong.wait(0.25)
    finally:
        cho_di_tiep.set()
        luong_login.join(5)
        if luong_doi.ident is not None:
            luong_doi.join(5)
        auth_routes.passwords.verify_password = goc
        conn_khac.close()

    assert not luong_login.is_alive() and not luong_doi.is_alive(), "co luong bi treo"
    assert "error" not in ket_qua_login, ket_qua_login
    assert "error" not in ket_qua_doi, ket_qua_doi
    assert bi_chan, f"{ten_thao_tac} khong cho khoa row cua login"
    assert ket_qua_login["response"].status_code == 200

    # Phien vua cap PHAI da bi thu hoi.
    raw_token = client.cookies.get(admin_dependencies.SESSION_COOKIE)
    assert raw_token is not None
    assert sessions.resolve(conn, raw_token) is None, (
        "phien cap cho ke dung mat khau cu van con song sau khi doi mat khau"
    )


def test_dat_lai_mat_khau_thu_hoi_ca_phien_dang_dang_nhap(conn):
    """Chuyen tu test_admin_routes.py (2026-08-21)."""
    _reset_schema(conn)
    _dang_nhap_dua_voi(
        conn,
        lambda c, uid: users.reset_password(c, uid, "Mat-khau-race-moi-2026"),
        "reset",
    )
    print("[PASS] dat lai mat khau thu hoi ca phien vua duoc cap trong luc do")


def test_doi_mat_khau_thu_hoi_ca_phien_dang_dang_nhap(conn):
    """Chuyen tu test_admin_routes.py (2026-08-21)."""
    _reset_schema(conn)
    _dang_nhap_dua_voi(
        conn,
        lambda c, uid: users.change_password(
            c, uid, "Mat-khau-change-cu-2026", "Mat-khau-race-moi-2026"
        ),
        "change",
    )
    print("[PASS] doi mat khau thu hoi ca phien vua duoc cap trong luc do")


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
        test_dat_lai_mat_khau_thu_hoi_ca_phien_dang_dang_nhap,
        test_doi_mat_khau_thu_hoi_ca_phien_dang_dang_nhap,
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
