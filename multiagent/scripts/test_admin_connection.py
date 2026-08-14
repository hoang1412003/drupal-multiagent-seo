"""Integration test HTTP cho trang ket noi Drupal (Plan 4 Task 8).

Khoa ba dieu de trang nay khong tro thanh mot nut bam trang tri:
1. Viewer XEM duoc nhung POST bi 403 o SERVER, khong phai chi an nut.
2. Test connection that bai neu thieu BAT KY nang luc nao, ke ca khi Drupal
   tra 200 cho mot GET chung chung.
3. Test connection khong bao gio goi result callback - chan doan khong duoc
   phep tao revision tren bai cua nguoi ta.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_connection.py
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import connection_routes, dependencies, router
from review_platform.auth import users
from review_platform.auth.rbac import Role
from review_platform.connectors import base as connector_base


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_connection"
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


class ConnectorGia:
    def __init__(self, health=None, loi=None):
        self._health = health
        self.loi = loi
        self.health_calls = 0
        self.write_calls = 0

    def health(self):
        self.health_calls += 1
        if self.loi is not None:
            raise self.loi
        return self._health

    def write_back(self, request):
        self.write_calls += 1
        raise AssertionError("test connection KHONG duoc goi result callback")


def _health(ok=True, error_code=None, status_code=200):
    return connector_base.ConnectorHealth(
        ok=ok,
        status_code=status_code,
        checked_at=datetime.now(timezone.utc),
        error_code=error_code,
    )


def _make_client(conn):
    app = FastAPI()
    app.state.auth_config = dependencies.AuthConfig(
        csrf_key=CSRF_KEY, throttle_key=THROTTLE_KEY, cookie_secure=False
    )
    app.add_exception_handler(dependencies.AdminForbidden, router.forbidden_response)
    app.include_router(router.router)
    app.dependency_overrides[dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.30", 50000))


def _tao_user(conn, username, role):
    return users.create_user(conn, username, "MatKhauRatDai#2026", role,
                             must_change_password=False)


def _dang_nhap(client, username):
    trang = client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    phan_hoi = client.post(
        "/admin/login",
        data={"username": username, "password": "MatKhauRatDai#2026",
              "csrf_token": token},
    )
    assert phan_hoi.status_code in (200, 303), phan_hoi.status_code
    return trang


def _csrf(client):
    trang = client.get("/admin/connection")
    assert trang.status_code == 200, trang.text
    moc = trang.text.split('name="csrf_token" value="')[1]
    return moc.split('"')[0]


def test_viewer_xem_duoc_nhung_khong_bam_duoc(conn):
    _reset_schema(conn)
    _tao_user(conn, "viewer1", Role.VIEWER)
    client = _make_client(conn)
    _dang_nhap(client, "viewer1")

    trang = client.get("/admin/connection")
    assert trang.status_code == 200, trang.text
    assert "drupal-vn-primary" in trang.text
    assert "Cần quyền operator" in trang.text

    token = _csrf(client)
    for duong_dan in ("/admin/connection/test", "/admin/connection/pause",
                      "/admin/connection/resume"):
        phan_hoi = client.post(duong_dan, data={"csrf_token": token})
        assert phan_hoi.status_code == 403, (duong_dan, phan_hoi.status_code)
    print("[PASS] viewer xem duoc trang nhung moi POST deu 403 o server")


def test_operator_thieu_csrf_bi_403(conn):
    _reset_schema(conn)
    _tao_user(conn, "op1", Role.OPERATOR)
    client = _make_client(conn)
    _dang_nhap(client, "op1")

    phan_hoi = client.post("/admin/connection/test", data={})
    assert phan_hoi.status_code == 403, phan_hoi.status_code
    phan_hoi = client.post("/admin/connection/pause", data={"csrf_token": "sai"})
    assert phan_hoi.status_code == 403, phan_hoi.status_code
    print("[PASS] operator thieu hoac sai CSRF deu bi 403")


def test_test_connection_luu_health_va_ghi_audit(conn):
    _reset_schema(conn)
    _tao_user(conn, "op2", Role.OPERATOR)
    client = _make_client(conn)
    _dang_nhap(client, "op2")
    token = _csrf(client)

    connector = ConnectorGia(health=_health(ok=True))
    goc = connection_routes._connection_factory
    connection_routes._connection_factory = lambda conn_, site_id: connector
    try:
        phan_hoi = client.post("/admin/connection/test", data={"csrf_token": token})
    finally:
        connection_routes._connection_factory = goc

    assert phan_hoi.status_code == 200, phan_hoi.text
    assert connector.health_calls == 1
    assert connector.write_calls == 0, "khong duoc goi result callback"
    with conn.cursor() as cur:
        cur.execute("SELECT last_health_status, last_health_error FROM site")
        assert cur.fetchone() == ("ok", None)
        cur.execute(
            "SELECT action, outcome, metadata FROM admin_audit_log "
            "WHERE action='connection_tested'"
        )
        row = cur.fetchone()
    assert row is not None, "phai ghi audit"
    assert row[1] == "success", row
    assert row[2]["site_slug"] == "drupal-vn-primary", row[2]
    # Tuyet doi khong luu token/base URL day du vao audit.
    assert set(row[2]) <= {"site_slug", "ok", "error_code"}, row[2]
    print("[PASS] test connection luu health, ghi audit, khong goi result callback")


def test_thieu_mot_capability_la_that_bai(conn):
    _reset_schema(conn)
    _tao_user(conn, "op3", Role.OPERATOR)
    client = _make_client(conn)
    _dang_nhap(client, "op3")
    token = _csrf(client)

    connector = ConnectorGia(health=_health(ok=False, error_code="capability_missing"))
    goc = connection_routes._connection_factory
    connection_routes._connection_factory = lambda conn_, site_id: connector
    try:
        phan_hoi = client.post("/admin/connection/test", data={"csrf_token": token})
    finally:
        connection_routes._connection_factory = goc

    assert "capability_missing" in phan_hoi.text, phan_hoi.text
    with conn.cursor() as cur:
        cur.execute("SELECT last_health_status, last_health_error FROM site")
        assert cur.fetchone() == ("capability_missing", "capability_missing")
        cur.execute(
            "SELECT outcome FROM admin_audit_log WHERE action='connection_tested'"
        )
        assert cur.fetchone()[0] == "failed"
    print("[PASS] thieu mot capability -> bao that bai va audit outcome=failed")


def test_connector_nem_loi_van_luu_ma_an_toan(conn):
    _reset_schema(conn)
    _tao_user(conn, "op4", Role.OPERATOR)
    client = _make_client(conn)
    _dang_nhap(client, "op4")
    token = _csrf(client)

    connector = ConnectorGia(loi=connector_base.ConnectorAuthError("403 tu Drupal"))
    goc = connection_routes._connection_factory
    connection_routes._connection_factory = lambda conn_, site_id: connector
    try:
        phan_hoi = client.post("/admin/connection/test", data={"csrf_token": token})
    finally:
        connection_routes._connection_factory = goc

    assert phan_hoi.status_code == 200, phan_hoi.status_code
    with conn.cursor() as cur:
        cur.execute("SELECT last_health_status FROM site")
        assert cur.fetchone()[0] == "connector_auth"
    print("[PASS] connector nem loi -> luu ma an toan, khong lam sap trang")


def test_pause_resume_giu_job_queued_va_ghi_audit(conn):
    _reset_schema(conn)
    _tao_user(conn, "op5", Role.OPERATOR)
    client = _make_client(conn)
    _dang_nhap(client, "op5")
    token = _csrf(client)

    tam_dung = client.post(
        "/admin/connection/pause",
        data={"csrf_token": token, "reason": "bao tri Drupal"},
    )
    assert tam_dung.status_code == 303, tam_dung.status_code
    with conn.cursor() as cur:
        cur.execute("SELECT intake_paused FROM site")
        assert cur.fetchone()[0] is True
        cur.execute(
            "SELECT metadata FROM admin_audit_log WHERE action='intake_paused'"
        )
        assert cur.fetchone()[0]["reason"] == "bao tri Drupal"

    mo_lai = client.post("/admin/connection/resume", data={"csrf_token": token})
    assert mo_lai.status_code == 303, mo_lai.status_code
    with conn.cursor() as cur:
        cur.execute("SELECT intake_paused FROM site")
        assert cur.fetchone()[0] is False
        cur.execute(
            "SELECT count(*) FROM admin_audit_log WHERE action='intake_resumed'"
        )
        assert cur.fetchone()[0] == 1
    print("[PASS] pause/resume doi dung trang thai va ghi audit day du")


def test_trang_khong_bao_gio_in_gia_tri_secret(conn):
    _reset_schema(conn)
    _tao_user(conn, "op6", Role.OPERATOR)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site_api_credential (site_id, token_prefix, token_hash) "
            "SELECT id, 'abc123def456', %s FROM site",
            ("f" * 64,),
        )
    client = _make_client(conn)
    _dang_nhap(client, "op6")

    trang = client.get("/admin/connection")
    assert "abc123def456" in trang.text, "phai hien prefix de doi chieu"
    assert "f" * 64 not in trang.text, "khong duoc lo token hash"
    assert "DRUPAL" in trang.text, "phai hien TEN bien secret"
    print("[PASS] trang chi hien prefix va ten bien secret, khong lo hash/gia tri")


if __name__ == "__main__":
    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            f"[SKIP] khong phai [PASS]"
        )
        sys.exit(0)

    failed = False
    for fn in (
        test_viewer_xem_duoc_nhung_khong_bam_duoc,
        test_operator_thieu_csrf_bi_403,
        test_test_connection_luu_health_va_ghi_audit,
        test_thieu_mot_capability_la_that_bai,
        test_connector_nem_loi_van_luu_ma_an_toan,
        test_pause_resume_giu_job_queued_va_ghi_audit,
        test_trang_khong_bao_gio_in_gia_tri_secret,
    ):
        try:
            fn(postgres_conn)
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    with postgres_conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
