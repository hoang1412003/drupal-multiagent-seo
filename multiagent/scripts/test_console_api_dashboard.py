r"""Integration test cho endpoint /dashboard cua Console API.

Trong tam: hinh dang JSON va chuyen kieu. Logic tinh metric da co test rieng o
test_admin_dashboard.py, nen o day so ket qua API voi chinh queries.dashboard
thay vi hard-code so lieu.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_dashboard.py
"""
from datetime import date, datetime, timezone
from decimal import Decimal
import json
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
SCHEMA = "vf_test_console_api_dashboard"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("00000000-0000-4000-8000-000000000002")
KNOWN_MODEL = "claude-sonnet-4-5-20250929"
DATE_FROM = date(2026, 8, 1)
DATE_TO = date(2026, 8, 3)


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _insert_job(conn, index: int, status: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_job ("
            "node_id,content_hash,status,attempts,source,created_at,updated_at,"
            "site_id,profile_id,policy_version,external_content_id,"
            "external_revision_id,content_type,langcode,correlation_id"
            ") VALUES (%s,%s,%s,1,'event',%s,%s,%s,%s,'cam-nang-vn-v1',%s,%s,"
            "'cam_nang','vi',%s) RETURNING id",
            (
                f"node-{index}",
                f"hash-{index}",
                status,
                datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
                datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
                SITE_ID,
                PROFILE_ID,
                f"node-{index}",
                f"revision-{index}",
                uuid4(),
            ),
        )
        return cur.fetchone()[0]


def _insert_run(conn, job_id, index: int, *, final_score, duration_ms: int):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO run_log ("
            "job_id,node_id,content_hash,duration_ms,decision,final_score,"
            "agent_results,config_meta,usage,model,payload,site_id,profile_id,"
            "policy_version,external_content_id,external_revision_id,"
            "content_type,langcode,correlation_id,writeback_status,scored_at"
            ") VALUES (%s,%s,%s,%s,'publish',%s,'{}'::jsonb,'{}'::jsonb,"
            "%s::jsonb,%s,'{}'::jsonb,%s,%s,'cam-nang-vn-v1',%s,%s,"
            "'cam_nang','vi',%s,'succeeded',%s)",
            (
                job_id,
                f"node-{index}",
                f"hash-{index}",
                duration_ms,
                final_score,
                json.dumps(
                    [
                        {
                            "model": KNOWN_MODEL,
                            "input_tokens": 1_000_000,
                            "output_tokens": 500_000,
                        }
                    ]
                ),
                KNOWN_MODEL,
                SITE_ID,
                PROFILE_ID,
                f"node-{index}",
                f"revision-{index}",
                uuid4(),
                # Phai nam trong khoang DATE_FROM..DATE_TO, neu khong dashboard
                # loc het va moi metric so deu ra None.
                datetime(2026, 8, 2, 10, tzinfo=timezone.utc),
            ),
        )


def _seed(conn):
    """Du de moi truong so cua DashboardView khac None."""
    for index, status in enumerate(("queued", "running", "failed", "done"), start=1):
        job_id = _insert_job(conn, index, status)
        if status == "done":
            _insert_run(conn, job_id, index, final_score=Decimal("82.5"), duration_ms=1500)
    job_id = _insert_job(conn, 5, "done")
    _insert_run(conn, job_id, 5, final_score=Decimal("91"), duration_ms=4200)


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.91", 50000))


def _login_viewer(conn, username: str = "dash.viewer"):
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


def test_dashboard_returns_all_fields_with_correct_types(conn):
    _reset_schema(conn)
    _seed(conn)
    client = _login_viewer(conn)

    response = client.get(
        f"/api/console/v1/dashboard?from={DATE_FROM}&to={DATE_TO}"
    )
    assert response.status_code == 200, response.text
    body = response.json()

    expected = queries.dashboard(conn, date_from=DATE_FROM, date_to=DATE_TO)
    assert body["total_reviews"] == expected.total_reviews
    assert body["queue_counts"] == expected.queue_counts
    assert body["decision_counts"] == expected.decision_counts
    assert body["writeback_counts"] == expected.writeback_counts
    assert body["date_from"] == DATE_FROM.isoformat()
    assert body["date_to"] == DATE_TO.isoformat()
    assert body["worker_status"] in ("running", "stale", "unavailable")

    thieu = {
        "date_from", "date_to", "queue_counts", "total_reviews", "decision_counts",
        "duration_p50_ms", "duration_p95_ms", "cost_estimate", "writeback_counts",
        "writeback_success_rate", "worker_status", "connector_status",
        "worker_running", "worker_stale", "worker_last_seen_at",
    } - set(body)
    assert not thieu, f"thieu truong: {sorted(thieu)}"
    print("[PASS] dashboard tra du 15 truong va khop voi queries.dashboard")


def test_dashboard_decimal_fields_are_json_numbers(conn):
    _reset_schema(conn)
    _seed(conn)
    client = _login_viewer(conn, "dash.decimal")

    body = client.get(
        f"/api/console/v1/dashboard?from={DATE_FROM}&to={DATE_TO}"
    ).json()

    # Pydantic v2 serialize Decimal thanh CHUOI neu khai bao truong la Decimal.
    # Frontend se nhan "1500.0" thay vi 1500.0 va moi phep so sanh so deu sai.
    for field in ("duration_p50_ms", "duration_p95_ms", "writeback_success_rate"):
        value = body[field]
        assert value is None or isinstance(value, (int, float)), (
            f"{field} la {type(value).__name__} chu khong phai so JSON: {value!r}"
        )
    assert body["duration_p50_ms"] is not None, "seed phai tao it nhat mot run"

    usd = body["cost_estimate"]["estimated_usd"]
    assert usd is None or isinstance(usd, (int, float)), repr(usd)
    assert isinstance(body["cost_estimate"]["input_tokens"], int)
    assert isinstance(body["cost_estimate"]["unknown_models"], list)
    print("[PASS] moi truong Decimal ra so JSON, khong phai chuoi")


def test_dashboard_rejects_invalid_date_range(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "dash.range")

    truong_hop = (
        ("dao nguoc", "?from=2026-08-31&to=2026-08-01"),
        ("thieu mot ve", "?from=2026-08-01"),
        ("sai dinh dang", "?from=2026-13-40&to=2026-08-01"),
    )
    for ten, query in truong_hop:
        response = client.get("/api/console/v1/dashboard" + query)
        assert response.status_code == 422, f"{ten}: {response.status_code}"
        assert set(response.json()["error"]) == {"code", "message", "field"}
        assert response.json()["error"]["code"] == "invalid_filter", ten
    print("[PASS] dashboard tu choi ba dang khoang ngay sai voi 422 dung hinh dang")


def test_dashboard_defaults_to_last_seven_days(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "dash.default")

    body = client.get("/api/console/v1/dashboard").json()
    khoang = date.fromisoformat(body["date_to"]) - date.fromisoformat(body["date_from"])
    assert khoang.days == 6, (
        f"mac dinh phai la 7 ngay nhu admin cu, dang la {khoang.days + 1} ngay"
    )
    print("[PASS] khong truyen ngay thi mac dinh 7 ngay, giong admin cu")


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
            test_dashboard_returns_all_fields_with_correct_types,
            test_dashboard_decimal_fields_are_json_numbers,
            test_dashboard_rejects_invalid_date_range,
            test_dashboard_defaults_to_last_seven_days,
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
