r"""Integration test cho /filters cua Console API.

Endpoint nay ton tai de frontend khong phai hard-code danh sach nao ca. Do la
diem chinh: dot truoc mot brief hard-code trang thai job sai (`succeeded` thay
vi `done`) va khong phep kiem nao bat duoc, vi gia tri hop le chua bao gio nam
trong hop dong. Gio thi co.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_filters.py
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
from review_platform.admin import queries
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_filters"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("00000000-0000-4000-8000-000000000002")
SITE_TAT = UUID("00000000-0000-4000-8000-0000000000ff")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _insert_site_tat(conn):
    """Site da tat: van phai xuat hien de loc duoc du lieu lich su cua no."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site (id,slug,name,connector_type,base_url,secret_ref,active) "
            "VALUES (%s,'site-da-tat','Site da tat','drupal','https://tat.example',"
            "'TAT',false)",
            (SITE_TAT,),
        )


def _insert_job(conn, index: int, *, source: str):
    created = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_job ("
            "node_id,content_hash,status,attempts,source,created_at,updated_at,"
            "site_id,profile_id,policy_version,external_content_id,"
            "external_revision_id,content_type,langcode,correlation_id"
            ") VALUES (%s,%s,'done',1,%s,%s,%s,%s,%s,'cam-nang-vn-v1',%s,%s,"
            "'cam_nang','vi',%s)",
            (
                f"node-{index}",
                f"hash-{index}",
                source,
                created,
                created,
                SITE_ID,
                PROFILE_ID,
                f"node-{index}",
                f"revision-{index}",
                uuid4(),
            ),
        )


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.94", 50000))


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


def test_filters_requires_session(conn):
    _reset_schema(conn)
    client = _make_client(conn)
    response = client.get("/api/console/v1/filters")
    assert response.status_code == 401, response.status_code
    assert response.json()["error"]["code"] == "unauthenticated"
    print("[PASS] /filters yeu cau dang nhap")


def test_filters_enums_match_code_exactly(conn):
    """Day la ly do endpoint nay ton tai: frontend khong hard-code enum nua."""
    _reset_schema(conn)
    client = _login_viewer(conn, "filters.enum")

    body = client.get("/api/console/v1/filters").json()

    assert body["job_statuses"] == list(queries.QUEUE_STATUSES), body["job_statuses"]
    assert body["review_decisions"] == list(queries._REVIEW_DECISIONS)
    assert body["writeback_statuses"] == list(queries.WRITEBACK_STATUSES)
    assert body["audit_actions"] == list(queries.AUDIT_ACTIONS)
    assert body["audit_outcomes"] == list(queries.AUDIT_OUTCOMES)

    # Chot lai gia tri that de doi enum ma quen endpoint nay se lam do test.
    assert body["job_statuses"] == [
        "queued", "running", "failed", "done", "superseded",
    ], "trang thai job doi ma /filters khong theo"
    print("[PASS] /filters tra dung enum trong code, khong hard-code lech")


def test_filters_lists_sites_including_inactive(conn):
    _reset_schema(conn)
    _insert_site_tat(conn)
    client = _login_viewer(conn, "filters.site")

    sites = client.get("/api/console/v1/filters").json()["sites"]
    slugs = [s["slug"] for s in sites]

    assert "drupal-vn-primary" in slugs, slugs
    # Site da tat VAN phai co: du lieu lich su cua no van nam trong danh sach
    # job/review, nen bo di thi khong con cach nao loc ra.
    assert "site-da-tat" in slugs, slugs
    assert slugs == sorted(slugs), "sites phai sap xep on dinh"
    for site in sites:
        assert set(site) == {"slug", "name", "active"}, set(site)
        assert isinstance(site["active"], bool)
    print("[PASS] /filters liet ke site ke ca site da tat, co co active")


def test_filters_lists_actual_job_sources(conn):
    _reset_schema(conn)
    for index, source in enumerate(
        ("event", "reconcile", "event", "manual-test-b7", "admin_retry"), start=1
    ):
        _insert_job(conn, index, source=source)
    client = _login_viewer(conn, "filters.source")

    sources = client.get("/api/console/v1/filters").json()["job_sources"]
    assert sources == ["admin_retry", "event", "manual-test-b7", "reconcile"], sources
    print("[PASS] /filters tra dung tap source co that, khong trung, da sap xep")


def test_filters_empty_database_still_valid(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "filters.empty")

    body = client.get("/api/console/v1/filters").json()
    assert body["job_sources"] == [], body["job_sources"]
    # Enum la hang so nen van phai day du du chua co du lieu nao.
    assert len(body["job_statuses"]) == 5
    print("[PASS] database rong: job_sources rong nhung enum van day du")


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
            test_filters_requires_session,
            test_filters_enums_match_code_exactly,
            test_filters_lists_sites_including_inactive,
            test_filters_lists_actual_job_sources,
            test_filters_empty_database_still_valid,
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
