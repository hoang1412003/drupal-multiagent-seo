r"""Integration test lich su cham va review detail cua Platform Admin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_reviews.py
"""
from datetime import date, datetime, timezone
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
from review_platform import migrations
from review_platform.admin import dependencies, queries, router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_reviews"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("00000000-0000-4000-8000-000000000002")
SECOND_SITE_ID = UUID("00000000-0000-4000-8000-000000000020")
SECOND_PROFILE_ID = UUID("00000000-0000-4000-8000-000000000021")
KNOWN_MODEL = "claude-haiku-4-5-20251001"


def _expect_value_error(callable_):
    try:
        callable_()
    except ValueError:
        return
    raise AssertionError("khong nem ValueError")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site (id,slug,name,connector_type,base_url,secret_ref) "
            "VALUES (%s,'secondary-site','Secondary','drupal',"
            "'https://secondary.example/base?ignored=1','SECONDARY')",
            (SECOND_SITE_ID,),
        )
        cur.execute(
            "INSERT INTO review_profile ("
            "id,code,market_code,language_code,content_type,status,policy_version,"
            "policy_snapshot) VALUES (%s,'secondary-profile','VN','vi','cam_nang',"
            "'active','secondary-v1','{}'::jsonb)",
            (SECOND_PROFILE_ID,),
        )
        cur.execute(
            "INSERT INTO site_profile_assignment (site_id,profile_id) VALUES (%s,%s)",
            (SECOND_SITE_ID, SECOND_PROFILE_ID),
        )


def _insert_run(
    conn,
    index: int,
    *,
    site_id: UUID = SITE_ID,
    profile_id: UUID = PROFILE_ID,
    policy_version: str = "cam-nang-vn-v1",
    profile_code: str = "cam-nang-vn",
    external_id: str | None = None,
    scored_at: datetime | None = None,
    decision: str | None = "needs_revision",
    final_score=70,
    agent_results=None,
    config_meta=None,
    usage=None,
    model: str = KNOWN_MODEL,
    writeback_status: str = "unknown",
    missing_agents=None,
    veto_reason: str | None = None,
    note: str | None = None,
):
    del profile_code
    external_id = external_id or str(100 + index)
    scored_at = scored_at or datetime(2026, 8, index, 12, tzinfo=timezone.utc)
    agent_results = {} if agent_results is None else agent_results
    config_meta = {} if config_meta is None else config_meta
    usage = [] if usage is None else usage
    missing_agents = [] if missing_agents is None else missing_agents
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO run_log ("
            "node_id,content_hash,scored_at,duration_ms,decision,final_score,"
            "missing_agents,veto_reason,note,agent_results,config_meta,usage,model,payload,"
            "site_id,profile_id,policy_version,external_content_id,external_revision_id,"
            "content_type,langcode,correlation_id,writeback_status,writeback_error"
            ") VALUES ("
            "%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,"
            "'{}'::jsonb,%s,%s,%s,%s,%s,'cam_nang','vi',%s,%s,%s"
            ") RETURNING id,public_id",
            (
                external_id,
                f"hash-review-{index}",
                scored_at,
                1000 * index,
                decision,
                final_score,
                json.dumps(missing_agents),
                veto_reason,
                note,
                json.dumps(agent_results, ensure_ascii=False),
                json.dumps(config_meta, ensure_ascii=False),
                json.dumps(usage),
                model,
                site_id,
                profile_id,
                policy_version,
                external_id,
                f"revision-{index}",
                uuid4(),
                writeback_status,
                "Authorization: Bearer writeback-secret" if writeback_status == "failed" else None,
            ),
        )
        row_id, public_id = cur.fetchone()
    return {"id": row_id, "public_id": public_id, "external_id": external_id}


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.60", 50000))


def _login(client, username: str, password: str):
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def test_normalize_agent_results_gioi_han_va_khong_mutate():
    raw = {
        "seo": {
            "score": 75,
            "criteria": [
                {"name": f"SEO-{index}", "evidence": "<b>evidence</b> " + "x" * 2500}
                for index in range(55)
            ],
            "issues": [
                {"type": f"issue-{index}", "suggestion": "token=agent-secret"}
                for index in range(55)
            ],
        },
        "content_quality": {"score": None, "issues": "legacy issue"},
        "brand": "legacy scalar",
        "compliance": {"score": 85, "flags": [{"excerpt": "<script>x</script>"}]},
        "fifth_agent": {"score": 100},
    }
    before = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    normalized = queries.normalize_agent_results(raw)
    assert len(normalized) == 4
    seo = next(agent for agent in normalized if agent.name == "seo")
    assert len(seo.criteria) == 50 and len(seo.issues) == 50
    assert len(seo.criteria[0]["evidence"]) == 2000
    assert "agent-secret" not in json.dumps(seo.issues, ensure_ascii=False)
    compliance = next(agent for agent in normalized if agent.name == "compliance")
    assert compliance.issues[0]["excerpt"] == "<script>x</script>"
    assert json.dumps(raw, ensure_ascii=False, sort_keys=True) == before
    assert queries.normalize_agent_results(None) == ()
    assert len(queries.normalize_agent_results([1, 2, 3])) == 1
    print("[PASS] normalize agents gioi han 4/50/2000, redact va khong mutate")


def test_list_reviews_filter_sort_pagination(conn):
    _reset_schema(conn)
    same_time = datetime(2026, 8, 2, 12, tzinfo=timezone.utc)
    first = _insert_run(
        conn,
        1,
        scored_at=datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
        decision="publish",
        external_id="101",
    )
    second = _insert_run(
        conn,
        2,
        scored_at=same_time,
        decision="rejected",
        external_id="node_special%",
    )
    third = _insert_run(conn, 3, scored_at=same_time, decision=None, external_id="103")
    other = _insert_run(
        conn,
        4,
        site_id=SECOND_SITE_ID,
        profile_id=SECOND_PROFILE_ID,
        policy_version="secondary-v1",
        decision="rejected",
        scored_at=same_time,
        external_id="104",
    )
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh'")

    page = queries.list_reviews(conn, queries.ReviewFilters(), page=1, page_size=2)
    assert page.total == 4 and page.total_pages == 2
    assert tuple(item.public_id for item in page.items) == (
        other["public_id"],
        third["public_id"],
    )
    page_two = queries.list_reviews(conn, queries.ReviewFilters(), page=2, page_size=2)
    assert tuple(item.public_id for item in page_two.items) == (
        second["public_id"],
        first["public_id"],
    )
    assert page_two.items[1].scored_at.hour == 12
    assert page_two.items[1].scored_at.utcoffset().total_seconds() == 0

    rejected = queries.list_reviews(
        conn,
        queries.ReviewFilters(decision="rejected"),
        page=1,
        page_size=25,
    )
    assert {item.public_id for item in rejected.items} == {
        second["public_id"],
        other["public_id"],
    }
    by_slug = queries.list_reviews(
        conn,
        queries.ReviewFilters(site="secondary-site"),
        page=1,
        page_size=25,
    )
    assert [item.public_id for item in by_slug.items] == [other["public_id"]]
    literal = queries.list_reviews(
        conn,
        queries.ReviewFilters(external_id="special%"),
        page=1,
        page_size=25,
    )
    assert [item.public_id for item in literal.items] == [second["public_id"]]
    dated = queries.list_reviews(
        conn,
        queries.ReviewFilters(
            date_from=date(2026, 8, 2),
            date_to=date(2026, 8, 2),
        ),
        page=1,
        page_size=25,
    )
    assert first["public_id"] not in {item.public_id for item in dated.items}

    invalid = (
        lambda: queries.list_reviews(
            conn,
            queries.ReviewFilters(decision="APPROVED"),
            page=1,
            page_size=25,
        ),
        lambda: queries.list_reviews(
            conn,
            queries.ReviewFilters(external_id="x" * 101),
            page=1,
            page_size=25,
        ),
        lambda: queries.list_reviews(conn, queries.ReviewFilters(), page=0, page_size=25),
        lambda: queries.list_reviews(conn, queries.ReviewFilters(), page=1, page_size=101),
    )
    for call in invalid:
        _expect_value_error(call)
    print("[PASS] review list filter/site/date, stable pagination va UTC")


def test_review_detail_day_du_fixture_unknown_cost_link_va_legacy(conn):
    _reset_schema(conn)
    issues = [
        {
            "field": "body",
            "type": "Claim",
            "suggestion": "Cookie: sid=issue-secret",
            "evidence": "<img src=x onerror=alert(1)>",
        }
    ]
    run = _insert_run(
        conn,
        1,
        site_id=SECOND_SITE_ID,
        profile_id=SECOND_PROFILE_ID,
        policy_version="secondary-v1",
        external_id="123",
        final_score=None,
        agent_results={
            "seo": {
                "score": 72,
                "criteria": [{"name": "SEO1", "score": 1, "evidence": "e"}],
                "issues": issues,
            }
        },
        config_meta={
            "is_fixture": True,
            "prompt_version": "p1",
            "api-token": "config-secret",
        },
        usage=[{"model": "unknown-model", "input_tokens": 10, "output_tokens": 20}],
        model="unknown-model",
        writeback_status="unknown",
        missing_agents=["brand"],
        veto_reason="Veto <strong>raw</strong>",
        note="Authorization: Bearer note-secret",
    )
    detail = queries.get_review(conn, run["public_id"])
    assert detail.public_id == run["public_id"]
    assert detail.final_score is None
    assert detail.is_fixture is True
    assert detail.missing_agents == ("brand",)
    assert detail.agents[0].score == 72
    assert detail.cost_estimate.estimated_usd is None
    assert detail.cost_estimate.unknown_models == ("unknown-model",)
    assert detail.writeback_status == "unknown"
    assert detail.drupal_url == "https://secondary.example/node/123"
    serialized_meta = json.dumps(detail.config_meta, ensure_ascii=False)
    assert "config-secret" not in serialized_meta and "[đã ẩn]" in serialized_meta
    assert "note-secret" not in detail.note
    assert "issue-secret" not in json.dumps(detail.agents[0].issues, ensure_ascii=False)

    uuid_external = _insert_run(conn, 2, external_id="uuid-content-value")
    assert queries.get_review(conn, uuid_external["public_id"]).drupal_url is None
    assert queries._drupal_node_url("javascript:alert(1)", "123") is None
    assert queries._drupal_node_url("https://user:pass@example.test", "123") is None
    legacy = _insert_run(
        conn,
        3,
        agent_results=["legacy", None, 1],
        config_meta="legacy-meta",
        usage={"legacy": "not-a-list"},
        decision=None,
        final_score=None,
    )
    legacy_detail = queries.get_review(conn, legacy["public_id"])
    assert legacy_detail.agents and legacy_detail.config_meta == "legacy-meta"
    assert legacy_detail.usage_available is False
    print("[PASS] review detail day du, fixture, legacy, unknown cost va Drupal URL an toan")


def test_review_routes_viewer_html_htmx_fixture_va_escape(conn):
    _reset_schema(conn)
    viewer = users.create_user(
        conn,
        "reviews.viewer",
        "Mat-khau-reviews-viewer",
        Role.VIEWER,
        must_change_password=False,
    )
    run = _insert_run(
        conn,
        1,
        external_id="123",
        agent_results={
            "seo": {
                "score": 72,
                "criteria": [{"name": "SEO1", "evidence": "<b>không raw</b>"}],
                "issues": [{"suggestion": "<script>alert(1)</script>"}],
            }
        },
        config_meta={"is_fixture": True, "prompt_version": "p1"},
        usage=[{"model": KNOWN_MODEL, "input_tokens": 1_000_000, "output_tokens": 0}],
        writeback_status="unknown",
        missing_agents=["brand"],
    )
    client = _make_client(conn)
    assert _login(client, viewer.username, "Mat-khau-reviews-viewer").status_code == 303

    listing = client.get("/admin/reviews")
    assert listing.status_code == 200
    assert "Lịch sử chấm" in listing.text and str(run["public_id"]) in listing.text
    invalid = client.get("/admin/reviews?decision=APPROVED")
    assert invalid.status_code == 422
    assert invalid.headers["content-type"].startswith("text/html")
    fragment = client.get("/admin/reviews", headers={"HX-Request": "true"})
    assert fragment.status_code == 200 and "<html" not in fragment.text.lower()
    assert 'id="reviews-table"' in fragment.text

    detail = client.get(f"/admin/reviews/{run['public_id']}")
    assert detail.status_code == 200
    assert "Dữ liệu fixture — không phải kết quả AI thật" in detail.text
    assert "Không có dữ liệu" in detail.text
    assert "unknown" in detail.text
    assert "status-done" not in detail.text
    assert "Chi phí ước tính" in detail.text
    assert "Phiên bản giá 1" in detail.text and "15/10/2025" in detail.text
    assert "1,000,000" in detail.text
    assert "<details" in detail.text
    assert "&lt;b&gt;không raw&lt;/b&gt;" in detail.text
    assert "<script>alert(1)</script>" not in detail.text
    assert "http://drupal.ddev.site/node/123" in detail.text
    print("[PASS] review routes viewer+, HTML/HTMX, fixture warning va escape evidence")


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
            test_normalize_agent_results_gioi_han_va_khong_mutate,
            test_list_reviews_filter_sort_pagination,
            test_review_detail_day_du_fixture_unknown_cost_link_va_legacy,
            test_review_routes_viewer_html_htmx_fixture_va_escape,
        ):
            try:
                if fn is test_normalize_agent_results_gioi_han_va_khong_mutate:
                    fn()
                else:
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
