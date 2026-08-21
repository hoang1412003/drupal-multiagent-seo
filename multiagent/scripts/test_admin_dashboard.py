r"""Regression cho pricing va dashboard read-model cua Platform Admin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_dashboard.py
"""
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import migrations
from review_platform.admin import queries
from review_platform.pricing import estimate_usage


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
PRICING_PATH = Path(__file__).resolve().parents[1] / "config" / "model_pricing.yaml"
SCHEMA = "vf_test_admin_dashboard"
SITE_ID = "00000000-0000-4000-8000-000000000001"
PROFILE_ID = "00000000-0000-4000-8000-000000000002"
KNOWN_MODEL = "claude-haiku-4-5-20251001"


def _expect_value_error(callable_):
    try:
        callable_()
    except ValueError:
        return
    raise AssertionError("khong nem ValueError")


def test_pricing_config_co_nguon_va_moc_hieu_luc():
    raw = yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["currency"] == "USD"
    assert raw["effective_at"] == "2025-10-15"
    assert raw["source"].startswith("https://www.anthropic.com/")
    assert raw["models"][KNOWN_MODEL]["input_usd_per_million"] == 1.0
    assert raw["models"][KNOWN_MODEL]["output_usd_per_million"] == 5.0
    print("[PASS] pricing config khoa version, ngay hieu luc va nguon HTTPS")


def test_pricing_decimal_sum_unknown_va_validation():
    estimate = estimate_usage(
        [
            {"model": KNOWN_MODEL, "input_tokens": 400_000, "output_tokens": 250_000},
            {"model": KNOWN_MODEL, "input_tokens": 600_000, "output_tokens": 750_000},
        ],
        PRICING_PATH,
    )
    assert estimate.input_tokens == 1_000_000
    assert estimate.output_tokens == 1_000_000
    assert estimate.estimated_usd == Decimal("6")
    assert estimate.pricing_version == 1
    assert estimate.effective_at == date(2025, 10, 15)
    assert estimate.currency == "USD"
    assert estimate.unknown_models == ()

    unknown = estimate_usage(
        [{"model": "model-chua-co-gia", "input_tokens": 10, "output_tokens": 20}],
        PRICING_PATH,
    )
    assert unknown.input_tokens == 10 and unknown.output_tokens == 20
    assert unknown.estimated_usd is None
    assert unknown.unknown_models == ("model-chua-co-gia",)

    invalid_rows = (
        {"model": KNOWN_MODEL, "input_tokens": -1, "output_tokens": 0},
        {"model": KNOWN_MODEL, "input_tokens": 0},
        {"model": KNOWN_MODEL, "input_tokens": True, "output_tokens": 0},
    )
    for row in invalid_rows:
        _expect_value_error(lambda row=row: estimate_usage([row], PRICING_PATH))
    print("[PASS] cost dung Decimal; unknown khong thanh $0; token sai bi chan")


def test_page_view_contract():
    page = queries.PageView(items=("a", "b"), page=2, page_size=2, total=5, total_pages=3)
    assert page.items == ("a", "b")
    assert (page.page, page.page_size, page.total, page.total_pages) == (2, 2, 5, 3)
    print("[PASS] PageView co contract pagination dung chung")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _insert_job(cur, index: int, status: str):
    cur.execute(
        "INSERT INTO review_job ("
        "node_id, content_hash, status, source, site_id, profile_id, policy_version, "
        "external_content_id, content_type, langcode"
        ") VALUES (%s,%s,%s,'admin-dashboard-test',%s,%s,'cam-nang-vn-v1',%s,'cam_nang','vi')",
        (f"job-{index}", f"hash-job-{index}", status, SITE_ID, PROFILE_ID, f"job-{index}"),
    )


def _insert_run(
    cur,
    index: int,
    *,
    scored_at: datetime,
    duration_ms: int | None,
    decision: str,
    final_score: Decimal | None,
    usage: list[dict],
    writeback_status: str,
    config_meta: dict | None = None,
):
    cur.execute(
        "INSERT INTO run_log ("
        "node_id, content_hash, scored_at, duration_ms, decision, final_score, "
        "agent_results, config_meta, usage, model, payload, site_id, profile_id, "
        "policy_version, external_content_id, content_type, langcode, correlation_id, "
        "writeback_status"
        ") VALUES ("
        "%s,%s,%s,%s,%s,%s,'{}'::jsonb,%s::jsonb,%s::jsonb,%s,'{}'::jsonb,"
        "%s,%s,'cam-nang-vn-v1',%s,'cam_nang','vi',%s,%s"
        ")",
        (
            f"run-{index}",
            f"hash-run-{index}",
            scored_at,
            duration_ms,
            decision,
            final_score,
            json.dumps(config_meta or {}),
            json.dumps(usage),
            usage[0]["model"] if usage else KNOWN_MODEL,
            SITE_ID,
            PROFILE_ID,
            f"run-{index}",
            uuid4(),
            writeback_status,
        ),
    )


def _seed_dashboard(conn):
    with conn.cursor() as cur:
        for index, status in enumerate(
            ("queued", "queued", "running", "failed", "done", "superseded"),
            start=1,
        ):
            _insert_job(cur, index, status)

        rows = (
            dict(
                index=1,
                scored_at=datetime(2026, 8, 1, 1, tzinfo=timezone.utc),
                duration_ms=1000,
                decision="publish",
                final_score=Decimal("90"),
                usage=[{"model": KNOWN_MODEL, "input_tokens": 1_000_000, "output_tokens": 0}],
                writeback_status="succeeded",
            ),
            dict(
                index=2,
                scored_at=datetime(2026, 8, 2, 23, 59, 59, tzinfo=timezone.utc),
                duration_ms=3000,
                decision="needs_revision",
                final_score=None,
                usage=[{"model": KNOWN_MODEL, "input_tokens": 0, "output_tokens": 1_000_000}],
                writeback_status="failed",
            ),
            dict(
                index=3,
                scored_at=datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
                duration_ms=2000,
                decision="rejected",
                final_score=Decimal("20"),
                usage=[{"model": "model-chua-co-gia", "input_tokens": 10, "output_tokens": 20}],
                writeback_status="superseded",
            ),
            dict(
                index=4,
                scored_at=datetime(2026, 8, 2, 13, tzinfo=timezone.utc),
                duration_ms=4000,
                decision="publish",
                final_score=Decimal("80"),
                usage=[],
                writeback_status="pending",
                config_meta={"is_fixture": "definitely"},
            ),
            dict(
                index=5,
                scored_at=datetime(2026, 8, 2, 14, tzinfo=timezone.utc),
                duration_ms=7000,
                decision="publish",
                final_score=Decimal("99"),
                usage=[{"model": KNOWN_MODEL, "input_tokens": 2_000_000, "output_tokens": 0}],
                writeback_status="succeeded",
                config_meta={"is_fixture": True},
            ),
            dict(
                index=6,
                scored_at=datetime(2026, 8, 3, 0, tzinfo=timezone.utc),
                duration_ms=9000,
                decision="publish",
                final_score=Decimal("95"),
                usage=[
                    {
                        "model": KNOWN_MODEL,
                        "input_tokens": 9_000_000,
                        "output_tokens": 9_000_000,
                    }
                ],
                writeback_status="succeeded",
            ),
            dict(
                index=7,
                scored_at=datetime(2026, 8, 2, 15, tzinfo=timezone.utc),
                duration_ms=None,
                decision="needs_revision",
                final_score=None,
                usage=[],
                writeback_status="unknown",
            ),
        )
        for row in rows:
            _insert_run(cur, **row)


def test_dashboard_range_fixture_usage_va_writeback(conn):
    view = queries.dashboard(
        conn,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 2),
    )
    assert view.queue_counts == {
        "queued": 2,
        "running": 1,
        "failed": 1,
        "done": 1,
        "superseded": 1,
    }
    assert view.total_reviews == 5
    assert view.decision_counts == {
        "publish": 2,
        "needs_revision": 2,
        "rejected": 1,
        "unknown": 0,
    }
    assert view.duration_p50_ms == Decimal("2500")
    assert view.duration_p95_ms == Decimal("3850")
    assert view.cost_estimate.input_tokens == 1_000_010
    assert view.cost_estimate.output_tokens == 1_000_020
    assert view.cost_estimate.estimated_usd is None
    assert view.cost_estimate.unknown_models == ("model-chua-co-gia",)
    assert view.writeback_counts == {
        "succeeded": 1,
        "failed": 1,
        "superseded": 1,
        "pending": 1,
        "unknown": 1,
    }
    assert view.writeback_success_rate == Decimal("0.5")
    # Chua co heartbeat va chua ai bam test connection -> phai la "chua biet",
    # tuyet doi khong duoc mac dinh thanh khoe.
    assert view.worker_status == "unavailable", view.worker_status
    assert view.connector_status == "unknown", view.connector_status
    assert view.worker_running == 0 and view.worker_stale == 0
    print("[PASS] dashboard dung UTC range, percentile, usage va writeback semantics")


def test_dashboard_include_fixture_noi_bo(conn):
    view = queries.dashboard(
        conn,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 2),
        include_fixtures=True,
    )
    assert view.total_reviews == 6
    assert view.decision_counts["publish"] == 3
    assert view.duration_p50_ms == Decimal("3000")
    assert view.duration_p95_ms == Decimal("6400")
    assert view.cost_estimate.input_tokens == 3_000_010
    assert view.writeback_counts["succeeded"] == 2
    assert view.writeback_counts["unknown"] == 1
    assert view.writeback_success_rate == Decimal(2) / Decimal(3)
    print("[PASS] include_fixtures=True chi mo lai fixture trong read-model noi bo")


# `test_template_dashboard_hien_dung_trang_thai_connector_da_luu` da bi xoa
# cung admin Jinja2 (2026-08-21). Tinh chat no khoa - ba trang thai worker
# phai NHIN KHAC NHAU - nay do console_ui/src/lib/status.test.ts giu:
# "khong co hai gia tri nao trong giong het nhau".


def test_dashboard_chan_date_range_sai_truoc_khi_query():
    start, end = queries._bounds(date(2026, 1, 1), date(2026, 4, 3))
    assert (end - start).days == 93
    _expect_value_error(
        lambda: queries.dashboard(
            object(), date_from=date(2026, 8, 2), date_to=date(2026, 8, 1)
        )
    )
    _expect_value_error(
        lambda: queries.dashboard(
            object(), date_from=date(2026, 1, 1), date_to=date(2026, 4, 4)
        )
    )
    print("[PASS] dashboard chan range dao va qua 93 ngay truoc SQL")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_pricing_config_co_nguon_va_moc_hieu_luc,
        test_pricing_decimal_sum_unknown_va_validation,
        test_page_view_contract,
        test_dashboard_chan_date_range_sai_truoc_khi_query,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    try:
        connection = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] dashboard SQL khong ket noi duoc Postgres "
            f"({exc.__class__.__name__}); [SKIP] khong phai [PASS]"
        )
        print("OK" if not failed else "CO TEST DO")
        sys.exit(1 if failed else 0)

    try:
        _reset_schema(connection)
        _seed_dashboard(connection)
        for fn in (
            test_dashboard_range_fixture_usage_va_writeback,
            test_dashboard_include_fixture_noi_bo,
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
