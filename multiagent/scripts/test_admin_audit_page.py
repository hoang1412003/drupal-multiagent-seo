r"""Integration/security test trang audit Platform Admin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_audit_page.py
"""
import json
import os
from pathlib import Path
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies, queries, router
from review_platform.auth import audit_log, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_audit_page"
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
    app.dependency_overrides[dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.85", 50000))


def _login(client, username: str, password: str):
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def _user(conn, username: str, role: Role):
    return users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        role,
        must_change_password=False,
    )


def _seed_audit(conn, actor):
    with conn.cursor() as cur:
        for index in range(30):
            cur.execute(
                "INSERT INTO admin_audit_log "
                "(actor_user_id,actor_username,action,target_type,target_id,"
                "outcome,metadata,created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s) RETURNING id",
                (
                    actor.id,
                    actor.username,
                    "login_success" if index % 2 == 0 else "logout",
                    "admin_user",
                    str(actor.id),
                    "success",
                    json.dumps({"index": index}),
                    "2026-08-13 08:00:00+00",
                ),
            )
        cur.execute(
            "INSERT INTO admin_audit_log "
            "(actor_user_id,actor_username,action,target_type,target_id,"
            "outcome,metadata,created_at) "
            "VALUES (%s,%s,'login_failed','admin_user',%s,'denied',%s::jsonb,"
            "'2026-08-13 09:00:00+00') RETURNING id",
            (
                actor.id,
                actor.username,
                str(actor.id),
                json.dumps(
                    {
                        "password": "RAW-PASSWORD-MARKER",
                        "note": "Authorization: Bearer RAW-BEARER-MARKER",
                        "nested": {"api_key": "RAW-API-KEY-MARKER"},
                    }
                ),
            ),
        )
        malicious_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO admin_audit_log "
            "(actor_user_id,actor_username,action,target_type,target_id,"
            "outcome,metadata,created_at) "
            "VALUES (%s,%s,'logout','admin_session',NULL,'success',"
            "%s::jsonb,'2026-08-13 10:00:00+00') RETURNING id",
            (actor.id, actor.username, json.dumps("legacy malformed metadata")),
        )
        malformed_id = cur.fetchone()[0]
        cur.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh'")
    return malicious_id, malformed_id


def test_audit_query_filter_pagination_utc_va_redaction(conn):
    _reset_schema(conn)
    admin = _user(conn, "audit.query.admin", Role.ADMIN)
    malicious_id, malformed_id = _seed_audit(conn, admin)

    page = queries.list_audit_events(
        conn,
        queries.AuditFilters(actor="QUERY.ADMIN"),
        page=1,
        page_size=25,
    )
    assert page.total == 32 and page.total_pages == 2
    assert page.items[0].id == malformed_id
    assert page.items[1].id == malicious_id
    assert page.items[0].created_at.utcoffset().total_seconds() == 0
    assert page.items[0].metadata_text == "[đã ẩn]"
    malicious = page.items[1].metadata_text
    assert "RAW-PASSWORD-MARKER" not in malicious
    assert "RAW-BEARER-MARKER" not in malicious
    assert "RAW-API-KEY-MARKER" not in malicious
    assert malicious.count("[đã ẩn]") >= 3
    second = queries.list_audit_events(
        conn,
        queries.AuditFilters(actor="query.admin"),
        page=2,
        page_size=25,
    )
    assert len(second.items) == 7

    filtered = queries.list_audit_events(
        conn,
        queries.AuditFilters(
            action=audit_log.AuditAction.LOGIN_FAILED.value,
            outcome="denied",
            actor="audit.query",
            date_from=date(2026, 8, 13),
            date_to=date(2026, 8, 13),
        ),
        page=1,
        page_size=25,
    )
    assert filtered.total == 1 and filtered.items[0].id == malicious_id

    invalid = (
        queries.AuditFilters(action="unknown"),
        queries.AuditFilters(outcome="unknown"),
        queries.AuditFilters(actor="x" * 101),
        queries.AuditFilters(date_from=date(2026, 8, 13)),
    )
    for filters in invalid:
        try:
            queries.list_audit_events(conn, filters, page=1, page_size=25)
        except ValueError:
            pass
        else:
            raise AssertionError(f"audit query chap nhan filter sai: {filters}")
    print("[PASS] audit query loc/phan trang/UTC va redact metadata legacy")


def test_audit_route_admin_only_invalid_html_va_no_mutation(conn):
    _reset_schema(conn)
    viewer = _user(conn, "audit.route.viewer", Role.VIEWER)
    operator = _user(conn, "audit.route.operator", Role.OPERATOR)
    admin = _user(conn, "audit.route.admin", Role.ADMIN)
    _seed_audit(conn, admin)

    for account in (viewer, operator):
        client = _make_client(conn)
        assert _login(
            client,
            account.username,
            f"Mat-khau-{account.username}-2026",
        ).status_code == 303
        assert client.get("/admin/audit").status_code == 403

    client = _make_client(conn)
    assert _login(client, admin.username, "Mat-khau-audit.route.admin-2026").status_code == 303
    page = client.get("/admin/audit")
    assert page.status_code == 200
    assert "Nhật ký" in page.text
    assert "RAW-PASSWORD-MARKER" not in page.text
    assert "RAW-BEARER-MARKER" not in page.text
    assert "RAW-API-KEY-MARKER" not in page.text
    assert "[đã ẩn]" in page.text
    assert "Trang sau" in page.text

    assert client.get("/admin/audit?action=unknown").status_code == 422
    assert client.get("/admin/audit?outcome=unknown").status_code == 422
    assert client.get("/admin/audit?actor=" + "x" * 101).status_code == 422
    assert client.get("/admin/audit?from=2026-08-13").status_code == 422
    assert client.get("/admin/audit?from=2026-13-40&to=2026-08-13").status_code == 422
    assert client.get("/admin/audit?page=0").status_code == 422
    assert client.post("/admin/audit").status_code == 405
    print("[PASS] audit route admin-only, filter loi HTML va khong co mutation")


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
            test_audit_query_filter_pagination_utc_va_redaction,
            test_audit_route_admin_only_invalid_html_va_no_mutation,
        ):
            try:
                fn(connection)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
    finally:
        with connection.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC'")
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        connection.close()

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
