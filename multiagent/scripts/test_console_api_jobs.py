r"""Integration test cho /jobs va /jobs/{public_id} cua Console API.

Trong tam: hinh dang phan trang chuan, tap truong tra ve, chuyen kieu, va ma
loi cho bo loc sai. Logic loc/sap xep da co test rieng o test_admin_jobs.py.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_jobs.py
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_jobs"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("00000000-0000-4000-8000-000000000002")

LIST_FIELDS = {
    "public_id", "created_at", "site_id", "site_slug", "external_content_id",
    "status", "attempts", "source", "policy_version",
}
DETAIL_FIELDS = {
    "public_id", "created_at", "updated_at", "site_id", "site_slug", "site_name",
    "profile_id", "policy_version", "external_content_id", "external_revision_id",
    "content_type", "langcode", "status", "attempts", "source", "correlation_id",
    "supersedes_job_public_id", "last_error", "run_public_id", "writeback_status",
    "run_scored_at", "saved_result_available",
}


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _insert_job(conn, index: int, *, status: str = "queued", last_error=None):
    created = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_job ("
            "node_id,content_hash,status,attempts,last_error,source,created_at,"
            "updated_at,site_id,profile_id,policy_version,external_content_id,"
            "external_revision_id,content_type,langcode,correlation_id"
            ") VALUES (%s,%s,%s,2,%s,'event',%s,%s,%s,%s,'cam-nang-vn-v1',%s,%s,"
            "'cam_nang','vi',%s) RETURNING public_id",
            (
                f"node-{index}",
                f"hash-{index}",
                status,
                last_error,
                created,
                created,
                SITE_ID,
                PROFILE_ID,
                f"node-{index}",
                f"revision-{index}",
                uuid4(),
            ),
        )
        return cur.fetchone()[0]


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.92", 50000))


def _login_viewer(conn, username: str):
    users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    response = client.post(
        "/api/console/v1/auth/login",
        json={"username": username, "password": f"Mat-khau-{username}-2026"},
    )
    assert response.status_code == 200, response.text
    return client


def test_jobs_pagination_shape(conn):
    _reset_schema(conn)
    for index in range(1, 138):
        _insert_job(conn, index)
    client = _login_viewer(conn, "jobs.page")

    response = client.get("/api/console/v1/jobs?page=1&page_size=50")
    assert response.status_code == 200, response.text
    body = response.json()

    assert set(body) == {"items", "page", "page_size", "total", "total_pages"}
    assert body["total"] == 137 and body["total_pages"] == 3
    assert body["page"] == 1 and body["page_size"] == 50
    assert len(body["items"]) == 50

    first_row = body["items"][0]
    assert set(first_row) == LIST_FIELDS, set(first_row) ^ LIST_FIELDS
    assert first_row["created_at"].endswith("Z"), first_row["created_at"]
    assert isinstance(first_row["attempts"], int)

    trang_cuoi = client.get("/api/console/v1/jobs?page=3&page_size=50").json()
    assert len(trang_cuoi["items"]) == 37
    print("[PASS] jobs dung hinh dang phan trang chuan va dung tap truong")


def test_jobs_invalid_filter_returns_422_error_shape(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "jobs.filter")

    truong_hop = (
        ("status khong hop le", "?status=khong-ton-tai"),
        ("page bang 0", "?page=0"),
        ("page khong phai so", "?page=abc"),
        ("page_size vuot tran", "?page_size=1000"),
        ("chi co mot ve ngay", "?from=2026-08-13"),
        ("ngay sai dinh dang", "?from=2026-13-40&to=2026-08-01"),
    )
    for ten, query in truong_hop:
        response = client.get("/api/console/v1/jobs" + query)
        assert response.status_code == 422, f"{ten}: {response.status_code}"
        loi = response.json()["error"]
        assert set(loi) == {"code", "message", "field"}, ten
        assert loi["code"] == "invalid_filter", ten
    print("[PASS] sau dang bo loc sai deu tra 422 dung hinh dang loi")


def test_jobs_filter_by_status_narrows_result(conn):
    _reset_schema(conn)
    for index in range(1, 4):
        _insert_job(conn, index, status="failed")
    for index in range(4, 10):
        _insert_job(conn, index, status="queued")
    client = _login_viewer(conn, "jobs.status")

    body = client.get("/api/console/v1/jobs?status=failed").json()
    assert body["total"] == 3, body["total"]
    assert {item["status"] for item in body["items"]} == {"failed"}
    print("[PASS] loc theo status thu hep dung ket qua")


def test_job_detail_returns_all_fields(conn):
    _reset_schema(conn)
    public_id = _insert_job(conn, 1, status="failed", last_error="loi gia lap")
    client = _login_viewer(conn, "jobs.detail")

    response = client.get(f"/api/console/v1/jobs/{public_id}")
    assert response.status_code == 200, response.text
    body = response.json()

    assert set(body) == DETAIL_FIELDS, set(body) ^ DETAIL_FIELDS
    assert body["public_id"] == str(public_id)
    assert body["status"] == "failed"
    assert body["last_error"] == "loi gia lap"
    assert body["created_at"].endswith("Z")
    assert body["site_slug"] and body["site_name"]
    # Job chua co run: cac truong lien quan phai la null, khong phai chuoi rong.
    assert body["run_public_id"] is None
    assert body["run_scored_at"] is None
    assert body["saved_result_available"] is False
    print("[PASS] job detail tra du 22 truong, truong thieu la null khong phai rong")


def test_job_detail_missing_returns_404(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "jobs.missing")

    khong_ton_tai = client.get("/api/console/v1/jobs/%s" % uuid4())
    assert khong_ton_tai.status_code == 404, khong_ton_tai.status_code
    assert khong_ton_tai.json()["error"]["code"] == "not_found"

    # ID sai dinh dang cung phai la 404, khong phai 500 hay 422: khong lo ra
    # rang he thong phan biet duoc "sai dinh dang" voi "khong ton tai".
    sai_dinh_dang = client.get("/api/console/v1/jobs/khong-phai-uuid")
    assert sai_dinh_dang.status_code == 404, sai_dinh_dang.status_code
    assert sai_dinh_dang.json()["error"] == khong_ton_tai.json()["error"]
    print("[PASS] job detail tra 404 giong nhau cho id la va id sai dinh dang")


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
            test_jobs_pagination_shape,
            test_jobs_invalid_filter_returns_422_error_shape,
            test_jobs_filter_by_status_narrows_result,
            test_job_detail_returns_all_fields,
            test_job_detail_missing_returns_404,
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
