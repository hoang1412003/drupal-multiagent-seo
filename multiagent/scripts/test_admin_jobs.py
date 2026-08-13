r"""Integration test cho danh sach/detail/retry job tren Platform Admin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_jobs.py
"""
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from review_platform import migrations, reviews
from review_platform.admin import dependencies, queries, router, sanitization
from review_platform.auth import sessions, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_jobs"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("00000000-0000-4000-8000-000000000002")
SECOND_SITE_ID = UUID("00000000-0000-4000-8000-000000000010")
SECOND_PROFILE_ID = UUID("00000000-0000-4000-8000-000000000011")


def _expect(exc_type, callable_):
    try:
        callable_()
    except exc_type as exc:
        return exc
    raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site (id,slug,name,connector_type,base_url,secret_ref) "
            "VALUES (%s,'drupal-vn-secondary','Drupal VN secondary','drupal',"
            "'https://secondary.example','SECONDARY')",
            (SECOND_SITE_ID,),
        )
        cur.execute(
            "INSERT INTO review_profile ("
            "id,code,market_code,language_code,content_type,status,policy_version,"
            "policy_snapshot) VALUES (%s,'secondary-vn','VN','vi','cam_nang',"
            "'active','secondary-v1','{}'::jsonb)",
            (SECOND_PROFILE_ID,),
        )
        cur.execute(
            "INSERT INTO site_profile_assignment (site_id,profile_id) VALUES (%s,%s)",
            (SECOND_SITE_ID, SECOND_PROFILE_ID),
        )


def _insert_job(
    conn,
    index: int,
    *,
    status: str = "failed",
    site_id: UUID = SITE_ID,
    profile_id: UUID = PROFILE_ID,
    policy_version: str = "cam-nang-vn-v1",
    external_id: str | None = None,
    source: str = "event",
    created_at: datetime | None = None,
    last_error: str | None = None,
):
    external_id = external_id or f"node-{index}"
    created_at = created_at or datetime(2026, 8, index, 12, tzinfo=timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_job ("
            "node_id,content_hash,status,attempts,last_error,source,created_at,updated_at,"
            "site_id,profile_id,policy_version,external_content_id,external_revision_id,"
            "content_type,langcode,correlation_id"
            ") VALUES (%s,%s,%s,3,%s,%s,%s,%s,%s,%s,%s,%s,%s,'cam_nang','vi',%s) "
            "RETURNING id,public_id",
            (
                external_id,
                f"hash-job-{index}",
                status,
                last_error,
                source,
                created_at,
                created_at,
                site_id,
                profile_id,
                policy_version,
                external_id,
                f"revision-{index}",
                uuid4(),
            ),
        )
        job_id, public_id = cur.fetchone()
    return {"id": job_id, "public_id": public_id, "external_id": external_id}


def _insert_run(conn, job, *, writeback_status="failed"):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT site_id,profile_id,policy_version,external_content_id,"
            "external_revision_id,content_type,langcode,correlation_id,content_hash "
            "FROM review_job WHERE id=%s",
            (job["id"],),
        )
        row = cur.fetchone()
        cur.execute(
            "INSERT INTO run_log ("
            "job_id,node_id,content_hash,duration_ms,decision,final_score,agent_results,"
            "config_meta,usage,model,payload,site_id,profile_id,policy_version,"
            "external_content_id,external_revision_id,content_type,langcode,"
            "correlation_id,writeback_status,writeback_error"
            ") VALUES (%s,%s,%s,900,'needs_revision',70,'{}'::jsonb,'{}'::jsonb,"
            "'[]'::jsonb,'model','{}'::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "RETURNING public_id",
            (
                job["id"],
                row[3],
                row[8],
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                writeback_status,
                "Authorization: Bearer run-secret-token",
            ),
        )
        return cur.fetchone()[0]


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.40", 50000))


def _login(client, username: str, password: str):
    page = client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def _session_csrf(conn, client):
    raw = client.cookies.get(router.SESSION_COOKIE)
    token_hash = hashlib.sha256(raw.encode("ascii")).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT csrf_secret FROM admin_session WHERE token_hash=%s",
            (token_hash,),
        )
        return cur.fetchone()[0]


def test_sanitization_che_secret_va_gioi_han_legacy():
    raw = {
        "api-key": "key-should-never-render",
        "nested": {
            "Authorization": "Bearer auth-secret",
            "legacy": "Cookie: sid=cookie-secret; password=hunter2",
        },
        "list": ["token=scalar-secret", {"client_secret": "nested-secret"}],
    }
    safe = sanitization.sanitize_mapping(raw, max_depth=3, max_items=50)
    serialized = json.dumps(safe, ensure_ascii=False)
    for secret in (
        "key-should-never-render",
        "auth-secret",
        "cookie-secret",
        "hunter2",
        "scalar-secret",
        "nested-secret",
    ):
        assert secret not in serialized
    assert "[đã ẩn]" in serialized
    assert len(sanitization.sanitize_text("x" * 1200, max_length=1000)) == 1000
    assert sanitization.sanitize_mapping(123) == 123
    print("[PASS] sanitizer che key/scalar/nested secret va gioi han output")


def test_list_jobs_filter_sort_pagination_va_site(conn):
    _reset_schema(conn)
    older = datetime(2026, 8, 1, 10, tzinfo=timezone.utc)
    same_time = datetime(2026, 8, 2, 10, tzinfo=timezone.utc)
    first = _insert_job(conn, 1, status="failed", created_at=older, source="event")
    second = _insert_job(
        conn,
        2,
        status="failed",
        created_at=same_time,
        source="admin_retry",
        external_id="node_special%",
    )
    third = _insert_job(conn, 3, status="queued", created_at=same_time, source="event")
    other = _insert_job(
        conn,
        4,
        site_id=SECOND_SITE_ID,
        profile_id=SECOND_PROFILE_ID,
        policy_version="secondary-v1",
        source="event",
    )

    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh'")

    page = queries.list_jobs(conn, queries.JobFilters(), page=1, page_size=2)
    assert page.total == 4 and page.total_pages == 2
    assert tuple(item.public_id for item in page.items) == (
        other["public_id"],
        third["public_id"],
    )
    second_page = queries.list_jobs(conn, queries.JobFilters(), page=2, page_size=2)
    assert tuple(item.public_id for item in second_page.items) == (
        second["public_id"],
        first["public_id"],
    )
    assert second_page.items[1].created_at.hour == 10
    assert second_page.items[1].created_at.utcoffset().total_seconds() == 0
    failed = queries.list_jobs(
        conn,
        queries.JobFilters(status="failed"),
        page=1,
        page_size=25,
    )
    assert {item.public_id for item in failed.items} == {
        first["public_id"],
        second["public_id"],
        other["public_id"],
    }
    site_slug = queries.list_jobs(
        conn,
        queries.JobFilters(site="drupal-vn-secondary"),
        page=1,
        page_size=25,
    )
    assert [item.public_id for item in site_slug.items] == [other["public_id"]]
    site_uuid = queries.list_jobs(
        conn,
        queries.JobFilters(site=str(SITE_ID), source="admin_retry"),
        page=1,
        page_size=25,
    )
    assert [item.public_id for item in site_uuid.items] == [second["public_id"]]
    literal = queries.list_jobs(
        conn,
        queries.JobFilters(external_id="special%"),
        page=1,
        page_size=25,
    )
    assert [item.public_id for item in literal.items] == [second["public_id"]]
    dated = queries.list_jobs(
        conn,
        queries.JobFilters(date_from=date(2026, 8, 2), date_to=date(2026, 8, 2)),
        page=1,
        page_size=25,
    )
    assert first["public_id"] not in {item.public_id for item in dated.items}
    print("[PASS] list job filter parameterized, site isolation va sort id DESC")


def test_list_jobs_chan_filter_sai(conn):
    invalid_calls = (
        lambda: queries.list_jobs(
            conn, queries.JobFilters(status="FAILED"), page=1, page_size=25
        ),
        lambda: queries.list_jobs(
            conn, queries.JobFilters(external_id="x" * 101), page=1, page_size=25
        ),
        lambda: queries.list_jobs(conn, queries.JobFilters(), page=0, page_size=25),
        lambda: queries.list_jobs(conn, queries.JobFilters(), page=1, page_size=101),
        lambda: queries.list_jobs(
            conn,
            queries.JobFilters(date_from=date(2026, 8, 1)),
            page=1,
            page_size=25,
        ),
    )
    for call in invalid_calls:
        _expect(ValueError, call)
    print("[PASS] list job chan status/filter/page ngoai contract")


def test_job_detail_sanitize_va_run_link(conn):
    _reset_schema(conn)
    job = _insert_job(
        conn,
        1,
        last_error=(
            "Traceback line\nAuthorization: Bearer job-secret-token\n"
            "Cookie: sid=cookie-secret\npassword=hunter2"
        ),
    )
    run_public_id = _insert_run(conn, job)
    detail = queries.get_job(conn, job["public_id"])
    assert detail.public_id == job["public_id"]
    assert detail.run_public_id == run_public_id
    assert detail.writeback_status == "failed"
    assert detail.saved_result_available is True
    assert "Traceback line" in detail.last_error
    for secret in ("job-secret-token", "cookie-secret", "hunter2"):
        assert secret not in detail.last_error
    print("[PASS] detail co run linkage va last_error da lam sach")


def test_retry_atomic_context_saved_result_va_audit(conn):
    _reset_schema(conn)
    actor = users.create_user(
        conn,
        "retry.operator",
        "Mat-khau-retry-operator",
        Role.OPERATOR,
        must_change_password=False,
    )
    failed = _insert_job(conn, 1, status="failed")
    _insert_run(conn, failed, writeback_status="failed")
    result = reviews.retry_failed(
        conn,
        job_public_id=failed["public_id"],
        actor=actor,
        reason="Authorization: Bearer reason-secret " + ("x" * 700),
    )
    assert result.saved_result_available is True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status,source,supersedes_job_id FROM review_job WHERE public_id=%s",
            (result.new_job_public_id,),
        )
        assert cur.fetchone() == ("queued", "admin_retry", failed["id"])
        cur.execute(
            "SELECT metadata FROM admin_audit_log WHERE action='job_retried'"
        )
        metadata = cur.fetchone()[0]
    assert set(metadata) == {"saved_result_available", "new_job_public_id", "reason"}
    assert metadata["saved_result_available"] is True
    assert metadata["new_job_public_id"] == str(result.new_job_public_id)
    assert "reason-secret" not in metadata["reason"]
    assert len(metadata["reason"]) <= 500

    no_saved = _insert_job(conn, 2, status="failed")
    no_saved_result = reviews.retry_failed(
        conn,
        job_public_id=no_saved["public_id"],
        actor=actor,
        reason=None,
    )
    assert no_saved_result.saved_result_available is False
    with conn.cursor() as cur:
        cur.execute(
            "SELECT metadata->>'saved_result_available' FROM admin_audit_log "
            "WHERE action='job_retried' ORDER BY id DESC LIMIT 1"
        )
        assert cur.fetchone()[0] == "false"

    non_failed = _insert_job(conn, 3, status="running")
    _expect(
        reviews.JobRetryConflict,
        lambda: reviews.retry_failed(
            conn,
            job_public_id=non_failed["public_id"],
            actor=actor,
            reason=None,
        ),
    )
    print("[PASS] retry tao linked queue, saved-result bool va audit allowlist")


def test_retry_audit_fail_rollback_va_context_inactive(conn):
    _reset_schema(conn)
    actor = users.create_user(
        conn,
        "retry.atomic",
        "Mat-khau-retry-atomic",
        Role.OPERATOR,
        must_change_password=False,
    )
    failed = _insert_job(conn, 1, status="failed")
    original_write = reviews.audit_log.write_event

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    reviews.audit_log.write_event = fail_audit
    try:
        _expect(
            RuntimeError,
            lambda: reviews.retry_failed(
                conn,
                job_public_id=failed["public_id"],
                actor=actor,
                reason="atomic",
            ),
        )
    finally:
        reviews.audit_log.write_event = original_write
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM review_job WHERE source='admin_retry'")
        assert cur.fetchone()[0] == 0
        cur.execute("UPDATE site SET active=false WHERE id=%s", (SITE_ID,))
    _expect(
        reviews.JobRetryContextError,
        lambda: reviews.retry_failed(
            conn,
            job_public_id=failed["public_id"],
            actor=actor,
            reason=None,
        ),
    )
    print("[PASS] audit fail rollback job moi va site inactive bi chan")


def test_job_routes_rbac_csrf_confirm_html_va_redirect(conn):
    _reset_schema(conn)
    viewer = users.create_user(
        conn,
        "jobs.viewer",
        "Mat-khau-jobs-viewer",
        Role.VIEWER,
        must_change_password=False,
    )
    operator = users.create_user(
        conn,
        "jobs.operator",
        "Mat-khau-jobs-operator",
        Role.OPERATOR,
        must_change_password=False,
    )
    failed = _insert_job(
        conn,
        1,
        status="failed",
        last_error="Authorization: Bearer route-secret-token",
    )
    _insert_run(conn, failed, writeback_status="failed")
    running = _insert_job(conn, 2, status="running")

    viewer_client = _make_client(conn)
    assert _login(viewer_client, viewer.username, "Mat-khau-jobs-viewer").status_code == 303
    listing = viewer_client.get("/admin/jobs")
    assert listing.status_code == 200
    assert "Jobs" in listing.text and str(failed["public_id"]) in listing.text
    viewer_detail = viewer_client.get(f"/admin/jobs/{failed['public_id']}")
    assert 'action="/admin/jobs/' not in viewer_detail.text
    assert "route-secret-token" not in viewer_detail.text
    assert "[đã ẩn]" in viewer_detail.text
    invalid = viewer_client.get("/admin/jobs?status=FAILED")
    assert invalid.status_code == 422 and invalid.headers["content-type"].startswith(
        "text/html"
    )
    fragment = viewer_client.get("/admin/jobs", headers={"HX-Request": "true"})
    assert fragment.status_code == 200 and "<html" not in fragment.text.lower()
    viewer_csrf = _session_csrf(conn, viewer_client)
    denied = viewer_client.post(
        f"/admin/jobs/{failed['public_id']}/retry",
        data={"csrf_token": viewer_csrf, "confirm_cost": "yes"},
    )
    assert denied.status_code == 403

    operator_client = _make_client(conn)
    assert _login(
        operator_client,
        operator.username,
        "Mat-khau-jobs-operator",
    ).status_code == 303
    no_csrf = operator_client.post(
        f"/admin/jobs/{failed['public_id']}/retry",
        data={"confirm_cost": "yes"},
    )
    assert no_csrf.status_code == 403
    operator_csrf = _session_csrf(conn, operator_client)
    conflict = operator_client.post(
        f"/admin/jobs/{running['public_id']}/retry",
        data={"csrf_token": operator_csrf, "confirm_cost": "yes"},
    )
    assert conflict.status_code == 409
    no_confirm = operator_client.post(
        f"/admin/jobs/{failed['public_id']}/retry",
        data={"csrf_token": operator_csrf},
    )
    assert no_confirm.status_code == 400
    success = operator_client.post(
        f"/admin/jobs/{failed['public_id']}/retry",
        data={
            "csrf_token": operator_csrf,
            "confirm_cost": "yes",
            "reason": "Thử lại sau lỗi connector",
        },
    )
    assert success.status_code == 303
    assert success.headers["location"].startswith("/admin/jobs/")
    assert success.headers["location"] != f"/admin/jobs/{failed['public_id']}"
    new_detail = operator_client.get(success.headers["location"])
    assert new_detail.status_code == 200 and "admin_retry" in new_detail.text
    print("[PASS] jobs route viewer+, retry operator+ CSRF/confirm va redirect 303")


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
            test_sanitization_che_secret_va_gioi_han_legacy,
            test_list_jobs_filter_sort_pagination_va_site,
            test_list_jobs_chan_filter_sai,
            test_job_detail_sanitize_va_run_link,
            test_retry_atomic_context_saved_result_va_audit,
            test_retry_audit_fail_rollback_va_context_inactive,
            test_job_routes_rbac_csrf_confirm_html_va_redirect,
        ):
            try:
                if fn is test_sanitization_che_secret_va_gioi_han_legacy:
                    fn()
                else:
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
