r"""Integration test cho man Nguoi dung cua Console API.

Man rui ro cao nhat cua Console: no tao tai khoan, doi quyen, va khoa nguoi.
Nam diem can khoa:

1. CHI admin. Viewer va operator deu bi 403 o server, ke ca khi goi thang.
2. Mat khau tam KHONG duoc lot vao bo nho dem. Response phai co
   Cache-Control: no-store - neu khong, proxy hay trinh duyet co the giu lai
   mot mat khau con dung duoc.
3. Bam bam mat khau (password_hash) khong duoc xuat hien trong BAT KY response
   nao. Day la thu de lot nhat vi no nam ngay canh cac truong khac cua user.
4. Admin active CUOI CUNG khong the bi ha quyen hay khoa. Mat no la mat quyen
   quan tri vinh vien - khong ai vao sua duoc nua.
5. Dat lai mat khau phai thu hoi moi phien dang mo cua nguoi do. Neu khong,
   ke dang dung phien cu van tiep tuc duoc dung sau khi bi doi mat khau.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_users.py
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform import security as platform_security
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_users"
CSRF_KEY = b"csrf-key-rieng-cho-users-2026!!!!!!!"
THROTTLE_KEY = b"throttle-key-rieng-cho-users-2026!!"


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
    app.add_exception_handler(
        RequestValidationError, errors.validation_error_handler
    )
    app.include_router(console_router.router)
    # Boc DUNG middleware bao mat cua app that. Khong boc thi phep kiem
    # Cache-Control: no-store o duoi la vo nghia - no chi chung minh route dat
    # header, khong chung minh header do song sot qua tang middleware.
    app.add_middleware(platform_security.SecurityMiddleware)
    app.dependency_overrides[admin_dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.98", 50000))


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


def _tat_ca_thao_tac(uid: str):
    """Sau endpoint cua man nay, dung chung cho cac phep kiem phan quyen."""
    return (
        ("get", "/api/console/v1/users", None),
        ("post", "/api/console/v1/users", {"username": "x", "role": "viewer"}),
        ("post", f"/api/console/v1/users/{uid}/role", {"role": "viewer"}),
        ("post", f"/api/console/v1/users/{uid}/lock", {}),
        ("post", f"/api/console/v1/users/{uid}/unlock", {}),
        ("post", f"/api/console/v1/users/{uid}/reset-password", {}),
    )


UUID_GIA = "00000000-0000-4000-8000-000000000009"


def test_chi_admin_vao_duoc(conn):
    """Viewer va operator deu bi chan o SERVER, khong phai chi an nut."""
    _reset_schema(conn)
    for ten, role in (("u.viewer", Role.VIEWER), ("u.operator", Role.OPERATOR)):
        client = _login(conn, ten, role)
        for method, path, body in _tat_ca_thao_tac(UUID_GIA):
            r = getattr(client, method)(path, json=body) if body is not None \
                else getattr(client, method)(path)
            assert r.status_code == 403, f"{role.value} {method} {path}: {r.status_code}"
            assert r.json()["error"]["code"] == "forbidden", r.json()
    print("[PASS] viewer va operator deu bi 403 o ca sau endpoint")


def test_thieu_csrf_bi_tu_choi(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.csrf", Role.ADMIN)
    del client.headers["X-CSRF-Token"]
    for method, path, body in _tat_ca_thao_tac(UUID_GIA):
        if method == "get":
            continue
        r = getattr(client, method)(path, json=body)
        assert r.status_code == 403, f"{method} {path}: {r.status_code}"
    print("[PASS] thieu CSRF -> 403 cho ca nam thao tac ghi")


def test_danh_sach_khong_lo_bam_mat_khau(conn):
    """password_hash nam ngay canh cac truong khac - de lot nhat."""
    _reset_schema(conn)
    client = _login(conn, "u.admin.list", Role.ADMIN)

    r = client.get("/api/console/v1/users")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"items", "page", "page_size", "total"}, set(body)
    assert body["items"], "phai co it nhat tai khoan vua tao"

    truong = set(body["items"][0])
    assert truong == {
        "id", "username", "role", "active", "must_change_password",
        "last_login_at", "created_at", "updated_at",
    }, truong

    tho = r.text.lower()
    for cam in ("password_hash", "$argon2", "$2b$", "bcrypt"):
        assert cam not in tho, f"response lo {cam}"
    print("[PASS] danh sach khong lo bam mat khau")


def test_tao_nguoi_dung_tra_mat_khau_tam_va_khong_cho_luu_dem(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.create", Role.ADMIN)

    r = client.post(
        "/api/console/v1/users",
        json={"username": "nguoi.moi", "role": "operator"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"user", "temporary_password"}, set(body)
    assert body["user"]["username"] == "nguoi.moi"
    assert body["user"]["role"] == "operator"
    # Bat buoc doi mat khau: mat khau tam do NGUOI KHAC biet.
    assert body["user"]["must_change_password"] is True
    assert len(body["temporary_password"]) >= 16

    # Khong cho luu dem: mot mat khau con dung duoc ma nam trong bo nho dem
    # cua proxy hay trinh duyet la mot ban sao khong ai kiem soat.
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    print("[PASS] tao nguoi dung tra mat khau tam kem Cache-Control: no-store")


def test_username_trung_va_role_sai(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.loi", Role.ADMIN)
    client.post("/api/console/v1/users", json={"username": "trung.ten", "role": "viewer"})

    r = client.post(
        "/api/console/v1/users", json={"username": "trung.ten", "role": "viewer"}
    )
    assert r.status_code == 409, r.status_code
    assert r.json()["error"]["field"] == "username", r.json()

    r = client.post(
        "/api/console/v1/users", json={"username": "ten.khac", "role": "sieu.nhan"}
    )
    assert r.status_code == 400, r.status_code
    assert r.json()["error"]["field"] == "role", r.json()
    print("[PASS] username trung -> 409 field=username, role sai -> 400 field=role")


def _id_cua(conn, username: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM admin_user WHERE username_normalized=%s",
            (users.normalize_username(username),),
        )
        return str(cur.fetchone()[0])


def test_admin_active_cuoi_cung_khong_bi_ha_quyen_hay_khoa(conn):
    """Mat admin cuoi cung la mat quyen quan tri VINH VIEN."""
    _reset_schema(conn)
    client = _login(conn, "u.admin.duy.nhat", Role.ADMIN)
    minh = _id_cua(conn, "u.admin.duy.nhat")

    r = client.post(f"/api/console/v1/users/{minh}/role", json={"role": "viewer"})
    assert r.status_code == 409, r.status_code
    assert r.json()["error"]["code"] == "last_active_admin", r.json()

    r = client.post(f"/api/console/v1/users/{minh}/lock", json={})
    assert r.status_code == 409, r.status_code
    assert r.json()["error"]["code"] == "last_active_admin", r.json()

    # Va ca hai lan tu choi deu phai duoc ghi so kiem toan.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM admin_audit_log "
            "WHERE action='last_admin_denied' AND outcome='denied'"
        )
        assert cur.fetchone()[0] == 2, "hai lan tu choi phai co hai dong kiem toan"
    print("[PASS] admin active cuoi cung khong bi ha quyen/khoa, co ghi kiem toan")


def test_co_admin_thu_hai_thi_khoa_va_mo_duoc(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.mot", Role.ADMIN)
    client.post("/api/console/v1/users", json={"username": "u.admin.hai", "role": "admin"})
    hai = _id_cua(conn, "u.admin.hai")

    r = client.post(f"/api/console/v1/users/{hai}/lock", json={})
    assert r.status_code == 200, r.text
    assert r.json()["active"] is False

    r = client.post(f"/api/console/v1/users/{hai}/unlock", json={})
    assert r.status_code == 200, r.text
    assert r.json()["active"] is True

    r = client.post(f"/api/console/v1/users/{hai}/role", json={"role": "viewer"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "viewer"
    print("[PASS] co admin thu hai thi khoa/mo/ha quyen deu duoc")


def test_dat_lai_mat_khau_thu_hoi_moi_phien(conn):
    """Khong thu hoi thi ke dang dung phien cu van tiep tuc duoc."""
    _reset_schema(conn)
    admin = _login(conn, "u.admin.reset", Role.ADMIN)
    admin.post("/api/console/v1/users", json={"username": "u.nan.nhan", "role": "viewer"})
    nan_nhan_id = _id_cua(conn, "u.nan.nhan")

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_user SET must_change_password=false WHERE id=%s",
            (nan_nhan_id,),
        )
        cur.execute(
            "SELECT count(*) FROM admin_session WHERE user_id=%s AND revoked_at IS NULL",
            (nan_nhan_id,),
        )

    r = admin.post(f"/api/console/v1/users/{nan_nhan_id}/reset-password", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"user", "temporary_password"}, set(body)
    assert body["user"]["must_change_password"] is True
    assert "no-store" in r.headers.get("cache-control", ""), r.headers

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM admin_session "
            "WHERE user_id=%s AND revoked_at IS NULL",
            (nan_nhan_id,),
        )
        con_song = cur.fetchone()[0]
    assert con_song == 0, f"con {con_song} phien chua bi thu hoi"
    print("[PASS] dat lai mat khau thu hoi moi phien dang mo")


def test_khong_tim_thay_nguoi_dung_tra_404(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.404", Role.ADMIN)
    for duong_dan in ("role", "lock", "unlock", "reset-password"):
        body = {"role": "viewer"} if duong_dan == "role" else {}
        r = client.post(f"/api/console/v1/users/{UUID_GIA}/{duong_dan}", json=body)
        assert r.status_code == 404, f"{duong_dan}: {r.status_code}"
        assert r.json()["error"]["code"] == "not_found"
    # ID sai dinh dang cung phai 404, khong duoc 422: khong lo ra rang he thong
    # phan biet duoc "sai dinh dang" voi "khong ton tai".
    r = client.post("/api/console/v1/users/khong-phai-uuid/lock", json={})
    assert r.status_code == 404, r.status_code
    print("[PASS] khong tim thay va ID sai dinh dang deu tra 404 giong nhau")


def test_moi_thao_tac_deu_ghi_so_kiem_toan(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.audit", Role.ADMIN)
    client.post("/api/console/v1/users", json={"username": "u.bi.sua", "role": "viewer"})
    uid = _id_cua(conn, "u.bi.sua")
    client.post(f"/api/console/v1/users/{uid}/role", json={"role": "operator"})
    client.post(f"/api/console/v1/users/{uid}/lock", json={})
    client.post(f"/api/console/v1/users/{uid}/unlock", json={})
    client.post(f"/api/console/v1/users/{uid}/reset-password", json={})

    with conn.cursor() as cur:
        cur.execute(
            "SELECT action FROM admin_audit_log WHERE actor_username='u.admin.audit'"
        )
        da_ghi = {r[0] for r in cur.fetchall()}
    for can in (
        "user_created", "user_role_changed", "user_locked", "user_unlocked",
        "password_reset",
    ):
        assert can in da_ghi, f"thieu {can} trong so kiem toan; da co {da_ghi}"
    print("[PASS] ca nam thao tac deu ghi so kiem toan")


def test_mat_khau_tam_khong_bao_gio_lap_lai(conn):
    _reset_schema(conn)
    client = _login(conn, "u.admin.random", Role.ADMIN)
    thu = set()
    for i in range(5):
        r = client.post(
            "/api/console/v1/users", json={"username": f"u.ngau.{i}", "role": "viewer"}
        )
        thu.add(r.json()["temporary_password"])
    assert len(thu) == 5, "mat khau tam bi lap - khong duoc sinh tu nguon doan duoc"
    print("[PASS] mat khau tam khac nhau qua nam lan tao")


def test_filters_co_danh_sach_role(conn):
    """De frontend khong hard-code ['viewer','operator','admin']."""
    _reset_schema(conn)
    client = _login(conn, "u.admin.filters", Role.ADMIN)
    body = client.get("/api/console/v1/filters").json()
    assert "roles" in body, set(body)
    assert body["roles"] == [role.value for role in Role], body["roles"]
    print("[PASS] /filters co danh sach role lay thang tu Role")


def test_me_co_id_de_nhan_ra_chinh_minh(conn):
    """Khoa hay ha quyen CHINH MINH thi bi dang xuat ngay sau do.

    Frontend can canh bao truoc, ma muon canh bao thi phai nhan ra "day la
    minh". So sanh bang username cung chay duoc nhung so sanh danh tinh thi
    phai dung dinh danh.

    Kiem ca hai cho tra MeResponse: login va /auth/me. Chung la hai doan code
    khac nhau nen them truong vao mot cho la du de lech.
    """
    _reset_schema(conn)
    users.create_user(
        conn, "u.me", "Mat-khau-u.me-2026", Role.ADMIN, must_change_password=False
    )
    client = _make_client(conn)
    khi_login = client.post(
        "/api/console/v1/auth/login",
        json={"username": "u.me", "password": "Mat-khau-u.me-2026"},
    ).json()
    khi_goi_me = client.get("/api/console/v1/auth/me").json()

    assert "id" in khi_login, khi_login
    assert "id" in khi_goi_me, khi_goi_me
    assert khi_login["id"] == khi_goi_me["id"], "hai cho tra id khac nhau"
    assert khi_login["id"] == _id_cua(conn, "u.me")

    # Va id do phai khop voi dong tuong ung trong danh sach nguoi dung.
    client.headers["X-CSRF-Token"] = khi_login["csrf_token"]
    danh_sach = client.get("/api/console/v1/users").json()["items"]
    minh = [u for u in danh_sach if u["username"] == "u.me"]
    assert minh and minh[0]["id"] == khi_login["id"], "id khong khop danh sach"
    print("[PASS] /auth/me va login deu tra id, khop voi danh sach nguoi dung")


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
            test_chi_admin_vao_duoc,
            test_thieu_csrf_bi_tu_choi,
            test_danh_sach_khong_lo_bam_mat_khau,
            test_tao_nguoi_dung_tra_mat_khau_tam_va_khong_cho_luu_dem,
            test_username_trung_va_role_sai,
            test_admin_active_cuoi_cung_khong_bi_ha_quyen_hay_khoa,
            test_co_admin_thu_hai_thi_khoa_va_mo_duoc,
            test_dat_lai_mat_khau_thu_hoi_moi_phien,
            test_khong_tim_thay_nguoi_dung_tra_404,
            test_moi_thao_tac_deu_ghi_so_kiem_toan,
            test_mat_khau_tam_khong_bao_gio_lap_lai,
            test_filters_co_danh_sach_role,
            test_me_co_id_de_nhan_ra_chinh_minh,
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
