r"""Integration test cho man Ket noi cua Console API.

Man nay khac han sau man truoc: day la man DAU TIEN cua Console co thao tac
GHI ngoai retry. Diem can khoa:

- Viewer XEM duoc nhung khong BAM duoc. An nut khong phai la phan quyen -
  server phai tra 403 ke ca khi client goi thang.
- Ba thao tac deu can CSRF. Thieu header -> 403, khong phai 500.
- Test connection KHONG duoc goi result callback: mot lan bam nut chan doan
  khong duoc phep tao revision moi tren bai cua nguoi ta.
- `secret_ref` la TEN bien moi truong, khong phai gia tri. Neu mot ngay nao do
  co nguoi doi no thanh gia tri that thi test cuoi cung o day se do.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_connection.py
"""
import os
from pathlib import Path
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform.auth.rbac import Role
from review_platform.connectors import base as connector_base


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_connection"
CSRF_KEY = b"csrf-key-rieng-cho-connection-2026!!"
THROTTLE_KEY = b"throttle-key-rieng-cho-connection-26"


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _seed_site(conn):
    """Migration 0001 da gieo san mot site; chi can them credential."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM site ORDER BY slug LIMIT 1")
        site_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO site_api_credential (site_id, token_prefix, token_hash, active) "
            "VALUES (%s, 'vfp_abc123', %s, true)",
            (site_id, "f" * 64),
        )
    return site_id


class ConnectorGia:
    """write_back() tu no la mot cai bay: chan doan ma goi toi day la sai."""

    def __init__(self, health=None, loi=None):
        self._health = health
        self.loi = loi
        self.health_calls = 0

    def health(self):
        self.health_calls += 1
        if self.loi is not None:
            raise self.loi
        return self._health

    def write_back(self, request):
        raise AssertionError("test connection KHONG duoc goi result callback")


def _make_client(conn):
    app = FastAPI()
    app.state.auth_config = admin_dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=False,
    )
    app.add_exception_handler(errors.ConsoleError, errors.console_error_handler)
    app.add_exception_handler(
        RequestValidationError, errors.validation_error_handler
    )
    app.include_router(console_router.router)
    app.dependency_overrides[admin_dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.97", 50000))


def _login(conn, username: str, role: Role):
    users.create_user(
        conn, username, f"Mat-khau-{username}-2026", role, must_change_password=False
    )
    client = _make_client(conn)
    response = client.post(
        "/api/console/v1/auth/login",
        json={"username": username, "password": f"Mat-khau-{username}-2026"},
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


@contextmanager
def _connector(module, gia):
    """Thay factory o cap MODULE, khong phai tham so cua route.

    De lam tham so thi FastAPI coi no la query param va client tu chon duoc
    connector - admin cu da ghi ro bay nay trong connection_routes.py.
    """
    goc = module._connection_factory
    module._connection_factory = lambda conn, site_id: gia
    try:
        yield gia
    finally:
        module._connection_factory = goc


def _health(ok: bool, error_code=None):
    from datetime import datetime, timezone

    return connector_base.ConnectorHealth(
        ok=ok,
        status_code=200 if ok else 502,
        checked_at=datetime.now(timezone.utc),
        error_code=error_code,
    )


def test_viewer_xem_duoc_trang_thai_ket_noi(conn):
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.viewer", Role.VIEWER)

    response = client.get("/api/console/v1/connection")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "slug", "name", "base_url", "secret_ref", "active", "intake_paused",
        "profile_code", "policy_version", "token_prefixes",
        "last_health_status", "last_health_checked_at", "last_health_error",
    }, set(body)
    assert body["slug"] == "drupal-vn-primary"
    assert body["token_prefixes"] == ["vfp_abc123"]
    assert body["intake_paused"] is False
    print("[PASS] viewer xem duoc trang thai ket noi")


def test_chua_cau_hinh_site_tra_404(conn):
    _reset_schema(conn)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM site_profile_assignment")
        cur.execute("DELETE FROM site")
    client = _login(conn, "cn.trong", Role.VIEWER)

    response = client.get("/api/console/v1/connection")
    assert response.status_code == 404, response.status_code
    assert response.json()["error"]["code"] == "not_found"
    print("[PASS] chua cau hinh site -> 404 dung hinh dang loi")


def test_viewer_khong_bam_duoc_ba_nut(conn):
    """An nut o frontend khong phai la phan quyen."""
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.viewer2", Role.VIEWER)

    for path in ("test", "pause", "resume"):
        r = client.post(f"/api/console/v1/connection/{path}", json={})
        assert r.status_code == 403, f"{path}: {r.status_code}"
        assert r.json()["error"]["code"] == "forbidden"
    print("[PASS] viewer goi thang ca ba thao tac deu bi 403")


def test_thieu_csrf_bi_tu_choi(conn):
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.operator", Role.OPERATOR)
    del client.headers["X-CSRF-Token"]

    for path in ("test", "pause", "resume"):
        r = client.post(f"/api/console/v1/connection/{path}", json={})
        assert r.status_code == 403, f"{path}: {r.status_code}"
    print("[PASS] thieu CSRF -> 403 cho ca ba thao tac")


def test_tam_dung_va_mo_lai_intake(conn):
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.op2", Role.OPERATOR)

    r = client.post(
        "/api/console/v1/connection/pause", json={"reason": "Bao tri Drupal"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["intake_paused"] is True

    r = client.post("/api/console/v1/connection/resume", json={})
    assert r.status_code == 200, r.text
    assert r.json()["intake_paused"] is False
    print("[PASS] tam dung va mo lai intake, tra ve trang thai moi")


def test_ly_do_qua_dai_bi_tu_choi_thay_vi_cat_cut(conn):
    """Cat cut im lang lam mat chu cua nguoi van hanh trong so kiem toan."""
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.op3", Role.OPERATOR)

    r = client.post(
        "/api/console/v1/connection/pause", json={"reason": "x" * 301}
    )
    assert r.status_code == 422, r.status_code
    assert r.json()["error"]["field"] == "reason", r.json()

    # Dung 300 thi phai qua.
    r = client.post("/api/console/v1/connection/pause", json={"reason": "x" * 300})
    assert r.status_code == 200, r.text
    print("[PASS] ly do >300 ky tu bi tu choi, dung 300 thi qua")


def test_body_sai_kieu_van_giu_hinh_dang_loi(conn):
    """FastAPI mac dinh tra {"detail": [...]} - hinh dang KHAC hop dong.

    Frontend do agent khac viet chi biet mot hinh dang loi. Ro ri hinh dang thu
    hai la ro ri im lang: UI se hien "loi khong xac dinh" ma khong ai biet vi sao.
    """
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.op4", Role.OPERATOR)

    r = client.post("/api/console/v1/connection/pause", json={"reason": 123})
    assert r.status_code == 422, r.status_code
    assert "error" in r.json(), r.json()
    assert set(r.json()["error"]) == {"code", "message", "field"}, r.json()
    print("[PASS] body sai kieu van tra dung hinh dang {error: {...}}")


def test_test_connection_dat_va_khong_dat(conn):
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.op5", Role.OPERATOR)

    from review_platform.admin_api import connection_routes

    with _connector(connection_routes, ConnectorGia(_health(True))):
        r = client.post("/api/console/v1/connection/test", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"ok", "error_code", "connection"}, set(body)
    assert body["ok"] is True
    assert body["connection"]["last_health_status"] == "ok"

    with _connector(connection_routes, ConnectorGia(_health(False, "auth_failed"))):
        r = client.post("/api/console/v1/connection/test", json={})
    # Ket noi hong KHONG phai la loi cua request: thao tac chan doan da chay
    # xong. Tra 4xx o day se khien UI hien "thao tac that bai" thay vi
    # "ket noi chua dat".
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is False
    assert r.json()["error_code"] == "auth_failed"
    assert r.json()["connection"]["last_health_error"] == "auth_failed"
    print("[PASS] test connection: dat va khong dat deu 200, co co `ok` ro rang")


def test_test_connection_khong_goi_result_callback(conn):
    """Bam nut chan doan khong duoc tao revision moi tren bai cua nguoi ta."""
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.op6", Role.OPERATOR)

    from review_platform.admin_api import connection_routes

    gia = ConnectorGia(_health(True))
    with _connector(connection_routes, gia):
        r = client.post("/api/console/v1/connection/test", json={})

    assert r.status_code == 200, r.text
    assert gia.health_calls == 1, gia.health_calls
    # write_back() cua ConnectorGia nem AssertionError; neu route co goi thi
    # test da do o tren truoc khi toi day.
    print("[PASS] test connection chi goi health(), khong dung toi write-back")


def test_ba_thao_tac_deu_ghi_so_kiem_toan(conn):
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.op7", Role.OPERATOR)

    from review_platform.admin_api import connection_routes

    with _connector(connection_routes, ConnectorGia(_health(True))):
        client.post("/api/console/v1/connection/test", json={})
    client.post("/api/console/v1/connection/pause", json={"reason": "vi sao do"})
    client.post("/api/console/v1/connection/resume", json={})

    with conn.cursor() as cur:
        cur.execute(
            "SELECT action, outcome FROM admin_audit_log "
            "WHERE actor_username='cn.op7' ORDER BY created_at"
        )
        rows = cur.fetchall()
    actions = [r[0] for r in rows]
    assert "connection_tested" in actions, actions
    assert "intake_paused" in actions, actions
    assert "intake_resumed" in actions, actions
    print("[PASS] ca ba thao tac deu ghi so kiem toan")


def test_secret_ref_la_ten_bien_khong_phai_gia_tri(conn):
    """Hang rao: neu co nguoi doi secret_ref thanh gia tri that, test nay do."""
    _reset_schema(conn)
    site_id = _seed_site(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT secret_ref FROM site WHERE id=%s", (site_id,))
        luu_trong_db = cur.fetchone()[0]

    client = _login(conn, "cn.viewer3", Role.VIEWER)
    phoi_ra = client.get("/api/console/v1/connection").json()["secret_ref"]

    assert phoi_ra == luu_trong_db
    # Ten bien moi truong: chi chu HOA, so va gach duoi.
    assert phoi_ra.replace("_", "").isalnum() and phoi_ra.isupper(), (
        f"secret_ref {phoi_ra!r} khong giong ten bien moi truong - "
        "neu no da thanh gia tri that thi endpoint nay dang lam ro ri secret"
    )
    print("[PASS] secret_ref van la ten bien moi truong, khong phai gia tri")


def test_thieu_mot_capability_la_that_bai(conn):
    """Chan doan phai doi DU nang luc, khong chi doi Drupal tra 200.

    Chuyen tu test_admin_connection.py (2026-08-21). Mot GET chung chung thanh
    cong khong chung minh duoc rang feed, result callback va doc revision deu
    dung - va do moi la thu pipeline can.
    """
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.capability", Role.OPERATOR)

    from review_platform.admin_api import connection_routes

    with _connector(connection_routes, ConnectorGia(_health(False, "capability_missing"))):
        r = client.post("/api/console/v1/connection/test", json={})

    assert r.status_code == 200, r.text
    assert r.json()["ok"] is False
    assert r.json()["error_code"] == "capability_missing"

    with conn.cursor() as cur:
        cur.execute("SELECT last_health_status, last_health_error FROM site")
        assert cur.fetchone() == ("capability_missing", "capability_missing")
        cur.execute(
            "SELECT outcome FROM admin_audit_log WHERE action='connection_tested'"
        )
        assert cur.fetchone()[0] == "failed", "chan doan hong phai ghi outcome=failed"
    print("[PASS] thieu mot capability -> bao that bai va audit outcome=failed")


def test_connector_nem_loi_van_luu_ma_an_toan(conn):
    """Connector nem exception thi van phai luu mot MA, khong lam sap endpoint.

    Chuyen tu test_admin_connection.py (2026-08-21). Ma luu phai la ma da biet
    (`connector_auth`), khong phai chuoi loi tho - thong bao loi tho tu Drupal
    co the chua duong dan hay token.
    """
    _reset_schema(conn)
    _seed_site(conn)
    client = _login(conn, "cn.exception", Role.OPERATOR)

    from review_platform.admin_api import connection_routes

    gia = ConnectorGia(loi=connector_base.ConnectorAuthError("403 tu Drupal"))
    with _connector(connection_routes, gia):
        r = client.post("/api/console/v1/connection/test", json={})

    assert r.status_code == 200, r.status_code
    assert r.json()["ok"] is False
    with conn.cursor() as cur:
        cur.execute("SELECT last_health_status FROM site")
        luu = cur.fetchone()[0]
    assert luu == "connector_auth", luu
    # Thong bao loi tho khong duoc lot ra ngoai.
    assert "403 tu Drupal" not in r.text
    print("[PASS] connector nem loi -> luu ma an toan, khong lo thong bao tho")


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
            test_viewer_xem_duoc_trang_thai_ket_noi,
            test_chua_cau_hinh_site_tra_404,
            test_viewer_khong_bam_duoc_ba_nut,
            test_thieu_csrf_bi_tu_choi,
            test_tam_dung_va_mo_lai_intake,
            test_ly_do_qua_dai_bi_tu_choi_thay_vi_cat_cut,
            test_body_sai_kieu_van_giu_hinh_dang_loi,
            test_test_connection_dat_va_khong_dat,
            test_test_connection_khong_goi_result_callback,
            test_ba_thao_tac_deu_ghi_so_kiem_toan,
            test_secret_ref_la_ten_bien_khong_phai_gia_tri,
            test_thieu_mot_capability_la_that_bai,
            test_connector_nem_loi_van_luu_ma_an_toan,
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
