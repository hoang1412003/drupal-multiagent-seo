r"""Integration/security test cho /reviews va /reviews/{public_id}.

Trong tam bao mat: agent_results bat nguon tu output cua model, nen du lieu
tho khong duoc ra thang JSON. queries.get_review da chay sanitization; test o
day chung minh route KHONG di duong vong qua no.

Luu y ve XSS: sanitization che bi mat chu khong escape HTML, va dung ra khong
nen escape. Voi API JSON, chong XSS la viec cua React (escape mac dinh, cam
dangerouslySetInnerHTML) chu khong phai cua backend.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_reviews.py
"""
from datetime import datetime, timezone
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
SCHEMA = "vf_test_console_api_reviews"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("00000000-0000-4000-8000-000000000002")
KNOWN_MODEL = "claude-sonnet-4-5-20250929"

SECRET_MARKERS = (
    "RAW-PASSWORD-MARKER",
    "RAW-BEARER-MARKER",
    "RAW-API-KEY-MARKER",
    "RAW-COOKIE-MARKER",
)

LIST_FIELDS = {
    "public_id", "scored_at", "site_id", "site_slug", "external_content_id",
    "decision", "final_score", "profile_code", "policy_version", "model",
    "is_fixture",
}
DETAIL_FIELDS = {
    "public_id", "scored_at", "duration_ms", "decision", "final_score",
    "missing_agents", "veto_reason", "note", "agents", "config_meta",
    "cost_estimate", "usage_available", "model", "writeback_status",
    "writeback_error", "site_id", "site_slug", "site_name", "profile_id",
    "profile_code", "policy_version", "external_content_id",
    "external_revision_id", "content_type", "langcode", "correlation_id",
    "is_fixture", "drupal_url",
}


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _insert_job(conn, index: int):
    created = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_job ("
            "node_id,content_hash,status,attempts,source,created_at,updated_at,"
            "site_id,profile_id,policy_version,external_content_id,"
            "external_revision_id,content_type,langcode,correlation_id"
            ") VALUES (%s,%s,'done',1,'event',%s,%s,%s,%s,'cam-nang-vn-v1',%s,%s,"
            "'cam_nang','vi',%s) RETURNING id",
            (
                f"node-{index}",
                f"hash-{index}",
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


def _insert_run(conn, index: int, *, agent_results=None, final_score=Decimal("82.5")):
    job_id = _insert_job(conn, index)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO run_log ("
            "job_id,node_id,content_hash,duration_ms,decision,final_score,"
            "agent_results,config_meta,usage,model,payload,site_id,profile_id,"
            "policy_version,external_content_id,external_revision_id,"
            "content_type,langcode,correlation_id,writeback_status,scored_at"
            ") VALUES (%s,%s,%s,1200,'needs_revision',%s,%s::jsonb,'{}'::jsonb,"
            "%s::jsonb,%s,'{}'::jsonb,%s,%s,'cam-nang-vn-v1',%s,%s,"
            "'cam_nang','vi',%s,'succeeded',%s) RETURNING public_id",
            (
                job_id,
                f"node-{index}",
                f"hash-{index}",
                final_score,
                json.dumps(agent_results or {}),
                json.dumps(
                    [
                        {
                            "model": KNOWN_MODEL,
                            "input_tokens": 1_000_000,
                            "output_tokens": 200_000,
                        }
                    ]
                ),
                KNOWN_MODEL,
                SITE_ID,
                PROFILE_ID,
                f"node-{index}",
                f"revision-{index}",
                uuid4(),
                datetime(2026, 8, 2, 10, tzinfo=timezone.utc),
            ),
        )
        return cur.fetchone()[0]


def _malicious_agent_results():
    """Sau agent, moi agent nhet bi mat vao ca criteria, issues va evidence."""
    mau = {
        "score": 70,
        "criteria": {"api-key": "RAW-API-KEY-MARKER"},
        "issues": ["Authorization: Bearer RAW-BEARER-MARKER"],
        "evidence": [{"password": "RAW-PASSWORD-MARKER"}],
        "note": "Cookie: sid=RAW-COOKIE-MARKER",
    }
    return {
        ten: dict(mau)
        for ten in (
            "content_quality", "seo", "brand", "compliance",
            "agent_thu_nam", "agent_thu_sau",
        )
    }


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.93", 50000))


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


def test_reviews_pagination_shape(conn):
    _reset_schema(conn)
    for index in range(1, 61):
        _insert_run(conn, index)
    client = _login_viewer(conn, "rev.page")

    response = client.get("/api/console/v1/reviews?page=1&page_size=25")
    assert response.status_code == 200, response.text
    body = response.json()

    assert set(body) == {"items", "page", "page_size", "total", "total_pages"}
    assert body["total"] == 60 and body["total_pages"] == 3
    assert len(body["items"]) == 25

    first_row = body["items"][0]
    assert set(first_row) == LIST_FIELDS, set(first_row) ^ LIST_FIELDS
    assert first_row["scored_at"].endswith("Z")
    assert isinstance(first_row["is_fixture"], bool)
    print("[PASS] reviews dung hinh dang phan trang chuan va dung tap truong")


def test_reviews_final_score_is_number_not_string(conn):
    _reset_schema(conn)
    _insert_run(conn, 1, final_score=Decimal("82.5"))
    _insert_run(conn, 2, final_score=None)
    client = _login_viewer(conn, "rev.score")

    items = client.get("/api/console/v1/reviews").json()["items"]
    scores = [item["final_score"] for item in items]
    assert None in scores, "can mot review khong co diem de kiem tra null"

    co_diem = [s for s in scores if s is not None]
    assert co_diem, "can mot review co diem de kiem tra kieu"
    for value in co_diem:
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"final_score la {type(value).__name__}: {value!r}. Pydantic v2 "
            "serialize Decimal thanh chuoi neu khai bao truong la Decimal."
        )
    print("[PASS] final_score la so JSON, thieu diem thi null khong phai chuoi rong")


def test_review_detail_redacts_secrets_from_agent_data(conn):
    _reset_schema(conn)
    public_id = _insert_run(conn, 1, agent_results=_malicious_agent_results())
    client = _login_viewer(conn, "rev.secret")

    response = client.get(f"/api/console/v1/reviews/{public_id}")
    assert response.status_code == 200, response.text
    raw = response.text

    for marker in SECRET_MARKERS:
        assert marker not in raw, (
            f"{marker} lot ra JSON. Route dang doc du lieu tho thay vi di qua "
            "queries.get_review."
        )
    assert "[đã ẩn]" in raw, "khong thay dau hieu da che bi mat nao"
    print("[PASS] review detail che het bi mat trong criteria/issues/evidence")


def test_review_detail_keeps_size_limits_of_queries(conn):
    _reset_schema(conn)
    public_id = _insert_run(conn, 1, agent_results=_malicious_agent_results())
    client = _login_viewer(conn, "rev.limit")

    body = client.get(f"/api/console/v1/reviews/{public_id}").json()
    expected = queries.get_review(conn, public_id)

    # queries cat con 4 agent du dau vao co 6. Route khong duoc noi lai.
    assert len(body["agents"]) == len(expected.agents) == 4, len(body["agents"])
    assert [a["name"] for a in body["agents"]] == [a.name for a in expected.agents]
    for agent in body["agents"]:
        assert set(agent) == {"name", "score", "criteria", "issues", "evidence"}
        assert isinstance(agent["criteria"], list)
    print("[PASS] review detail giu nguyen gioi han kich thuoc cua queries")


def test_review_detail_returns_all_fields(conn):
    _reset_schema(conn)
    public_id = _insert_run(conn, 1)
    client = _login_viewer(conn, "rev.detail")

    body = client.get(f"/api/console/v1/reviews/{public_id}").json()
    assert set(body) == DETAIL_FIELDS, set(body) ^ DETAIL_FIELDS
    assert body["public_id"] == str(public_id)
    assert body["scored_at"].endswith("Z")
    assert isinstance(body["duration_ms"], int)
    assert isinstance(body["missing_agents"], list)
    assert isinstance(body["usage_available"], bool)
    assert body["cost_estimate"]["estimated_usd"] is None or isinstance(
        body["cost_estimate"]["estimated_usd"], (int, float)
    )
    print("[PASS] review detail tra du 28 truong voi dung kieu")


def test_review_detail_missing_returns_404(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "rev.missing")

    khong_ton_tai = client.get("/api/console/v1/reviews/%s" % uuid4())
    assert khong_ton_tai.status_code == 404
    sai_dinh_dang = client.get("/api/console/v1/reviews/khong-phai-uuid")
    assert sai_dinh_dang.status_code == 404
    assert sai_dinh_dang.json()["error"] == khong_ton_tai.json()["error"]
    print("[PASS] review detail tra 404 giong nhau cho id la va id sai dinh dang")


def test_dict_shaped_criteria_still_redacts_secrets(conn):
    """Chan hoi quy cho lo hong da vá trong queries._review_entries.

    Khi `criteria` la dict, ham do tung tai cau truc thanh
    {"criterion": <khoa>, "value": <gia tri>} TRUOC khi lam sach, nen ten khoa
    chuyen sang vi tri gia tri va bo loc theo ten khoa khong con khop.
    """
    from review_platform.admin import queries as q

    for shape, payload in (
        ("dict", {"api-key": "RAW-API-KEY-MARKER"}),
        ("list dict", [{"api-key": "RAW-API-KEY-MARKER"}]),
        ("dict long", {"nested": {"client_secret": "RAW-API-KEY-MARKER"}}),
    ):
        entries = q._review_entries(payload)
        rendered = repr(entries)
        assert "RAW-API-KEY-MARKER" not in rendered, f"{shape}: {rendered}"
    print("[PASS] _review_entries che bi mat o ca hinh dang dict lan list")


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
            test_reviews_pagination_shape,
            test_reviews_final_score_is_number_not_string,
            test_review_detail_redacts_secrets_from_agent_data,
            test_review_detail_keeps_size_limits_of_queries,
            test_review_detail_returns_all_fields,
            test_review_detail_missing_returns_404,
            test_dict_shaped_criteria_still_redacts_secrets,
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
