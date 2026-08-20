r"""Integration/security test cho /audit cua Console API.

Trong tam: audit la man CHI ADMIN, va metadata da duoc lam sach truoc khi ra
UI. Hai dieu do phai dung o Console y het admin Jinja2 - neu Console noi long
hon thi no tro thanh duong vong de doc nhat ky he thong.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_audit.py
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_audit"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"

FIELDS = {
    "id", "actor_user_id", "actor_username", "action", "target_type",
    "target_id", "outcome", "metadata_text", "created_at",
}


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
    app.dependency_overrides[admin_dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.95", 50000))


def _login_as(conn, username: str, role: Role):
    users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        role,
        must_change_password=False,
    )
    client = _make_client(conn)
    response = client.post(
        "/api/console/v1/auth/login",
        json={"username": username, "password": f"Mat-khau-{username}-2026"},
    )
    assert response.status_code == 200, response.text
    return client


def _seed_audit(conn, actor_username: str, *, so_dong: int = 30):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM admin_user WHERE username=%s", (actor_username,))
        actor_id = cur.fetchone()[0]
        for index in range(so_dong):
            cur.execute(
                "INSERT INTO admin_audit_log "
                "(actor_user_id,actor_username,action,target_type,target_id,"
                "outcome,metadata,created_at) "
                "VALUES (%s,%s,%s,'admin_user',%s,%s,%s::jsonb,'2026-08-13 08:00:00+00')",
                (
                    actor_id,
                    actor_username,
                    "login_success" if index % 2 == 0 else "logout",
                    str(actor_id),
                    "success",
                    json.dumps({"index": index}),
                ),
            )
        # Mot dong chua bi mat, de kiem lop lam sach.
        cur.execute(
            "INSERT INTO admin_audit_log "
            "(actor_user_id,actor_username,action,target_type,target_id,"
            "outcome,metadata,created_at) "
            "VALUES (%s,%s,'login_failed','admin_user',%s,'denied',%s::jsonb,"
            "'2026-08-13 09:00:00+00')",
            (
                actor_id,
                actor_username,
                str(actor_id),
                json.dumps(
                    {
                        "password": "RAW-PASSWORD-MARKER",
                        "note": "Authorization: Bearer RAW-BEARER-MARKER",
                        "nested": {"api_key": "RAW-API-KEY-MARKER"},
                    }
                ),
            ),
        )


def test_audit_chi_admin_moi_xem_duoc(conn):
    """Viewer va operator KHONG duoc doc nhat ky he thong."""
    _reset_schema(conn)
    for role in (Role.VIEWER, Role.OPERATOR):
        client = _login_as(conn, f"audit.{role.value}", role)
        response = client.get("/api/console/v1/audit")
        assert response.status_code == 403, f"{role.value}: {response.status_code}"
        assert response.json()["error"]["code"] == "forbidden"

    client = _login_as(conn, "audit.admin", Role.ADMIN)
    assert client.get("/api/console/v1/audit").status_code == 200
    print("[PASS] audit chi admin xem duoc, viewer va operator bi 403")


def test_audit_hinh_dang_phan_trang_va_tap_truong(conn):
    _reset_schema(conn)
    client = _login_as(conn, "audit.page", Role.ADMIN)
    _seed_audit(conn, "audit.page", so_dong=30)

    body = client.get("/api/console/v1/audit?page=1&page_size=25").json()
    assert set(body) == {"items", "page", "page_size", "total", "total_pages"}
    # 30 dong seed + 1 dong co bi mat + cac dong login_success cua chinh
    # phien dang nhap -> chi kiem cau truc, khong chot con so tuyet doi.
    assert body["total"] >= 31, body["total"]
    assert len(body["items"]) == 25

    first_row = body["items"][0]
    assert set(first_row) == FIELDS, set(first_row) ^ FIELDS
    assert first_row["created_at"].endswith("Z"), first_row["created_at"]
    assert isinstance(first_row["id"], int)
    print("[PASS] audit dung hinh dang phan trang chuan va dung tap truong")


def test_audit_khong_lo_bi_mat_trong_metadata(conn):
    """Day la ly do endpoint nay ton tai duoi dang chi doc va chi admin."""
    _reset_schema(conn)
    client = _login_as(conn, "audit.secret", Role.ADMIN)
    _seed_audit(conn, "audit.secret", so_dong=0)

    raw = client.get("/api/console/v1/audit").text
    for marker in ("RAW-PASSWORD-MARKER", "RAW-BEARER-MARKER", "RAW-API-KEY-MARKER"):
        assert marker not in raw, (
            f"{marker} lot ra JSON. Route dang doc metadata tho thay vi di qua "
            "queries.list_audit_events."
        )
    assert "[đã ẩn]" in raw, "khong thay dau hieu da che bi mat nao"
    print("[PASS] audit che het bi mat trong metadata")


def test_audit_bo_loc_va_tham_so_la(conn):
    _reset_schema(conn)
    client = _login_as(conn, "audit.filter", Role.ADMIN)
    _seed_audit(conn, "audit.filter", so_dong=10)

    # Moi tham so trong hop dong phai that su loc.
    chi_login_failed = client.get(
        "/api/console/v1/audit?action=login_failed&outcome=denied"
    ).json()
    assert chi_login_failed["total"] == 1, chi_login_failed["total"]

    # Bo loc sai -> 422 dung hinh dang.
    for query in ("?action=khong-ton-tai", "?outcome=khong-ton-tai",
                  "?from=2026-08-13", "?page=0"):
        r = client.get("/api/console/v1/audit" + query)
        assert r.status_code == 422, f"{query}: {r.status_code}"
        assert set(r.json()["error"]) == {"code", "message", "field"}

    # Ten tham so la phai bi TU CHOI, khong duoc bo qua im lang.
    la = client.get("/api/console/v1/audit?actor_name=abc")
    assert la.status_code == 422, la.status_code
    print("[PASS] audit loc dung, bo loc sai 422, tham so la bi tu choi")


def test_audit_khong_co_endpoint_ghi(conn):
    """Nhat ky he thong phai KHONG sua duoc tu giao dien."""
    _reset_schema(conn)
    client = _login_as(conn, "audit.readonly", Role.ADMIN)
    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/api/console/v1/audit")
        assert response.status_code == 405, f"{method}: {response.status_code}"
    print("[PASS] audit khong co endpoint ghi nao")


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
            test_audit_chi_admin_moi_xem_duoc,
            test_audit_hinh_dang_phan_trang_va_tap_truong,
            test_audit_khong_lo_bi_mat_trong_metadata,
            test_audit_bo_loc_va_tham_so_la,
            test_audit_khong_co_endpoint_ghi,
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
