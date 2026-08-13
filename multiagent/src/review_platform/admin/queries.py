"""Read-model SQL dung chung cho cac man hinh Platform Admin."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from review_platform.pricing import CostEstimate, estimate_usage


DEFAULT_PRICING_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "model_pricing.yaml"
)
MAX_RANGE_DAYS = 93
PERCENTILE_MS_PRECISION = Decimal("0.01")
QUEUE_STATUSES = ("queued", "running", "failed", "done", "superseded")
WRITEBACK_STATUSES = ("succeeded", "failed", "superseded", "pending", "unknown")


@dataclass(frozen=True)
class PageView:
    items: tuple
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class DashboardView:
    date_from: date
    date_to: date
    queue_counts: dict[str, int]
    total_reviews: int
    decision_counts: dict[str, int]
    duration_p50_ms: Decimal | None
    duration_p95_ms: Decimal | None
    cost_estimate: CostEstimate
    writeback_counts: dict[str, int]
    writeback_success_rate: Decimal | None
    worker_status: str = "unknown"
    connector_status: str = "unknown"


def _bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if not isinstance(date_from, date) or not isinstance(date_to, date):
        raise ValueError("date_from/date_to phai la date")
    if date_to < date_from:
        raise ValueError("date_to khong duoc truoc date_from")
    if (date_to - date_from).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(f"khoang ngay toi da {MAX_RANGE_DAYS} ngay")
    return (
        datetime.combine(date_from, time.min, tzinfo=timezone.utc),
        datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def _fixture_clause(include_fixtures: bool) -> str:
    if include_fixtures:
        return ""
    return " AND lower(coalesce(config_meta->>'is_fixture','false')) <> 'true'"


def _duration_percentile(value) -> Decimal | None:
    if value is None:
        return None
    # PostgreSQL percentile_cont tren cot integer tra float8. Chuan hoa ve
    # 0,01 ms de loai nhieu IEEE-754 (vi du 3849.9999999999995) khoi UI/API.
    return Decimal(str(value)).quantize(PERCENTILE_MS_PRECISION)


def dashboard(
    conn,
    *,
    date_from: date,
    date_to: date,
    include_fixtures: bool = False,
) -> DashboardView:
    """Doc metric that trong [from 00:00 UTC, to+1 day 00:00 UTC)."""
    start, end = _bounds(date_from, date_to)
    fixture_sql = _fixture_clause(include_fixtures)

    with conn.cursor() as cur:
        cur.execute("SELECT status, count(*) FROM review_job GROUP BY status")
        raw_queue = dict(cur.fetchall())

        cur.execute(
            "SELECT count(*), "
            "count(*) FILTER (WHERE decision='publish'), "
            "count(*) FILTER (WHERE decision='needs_revision'), "
            "count(*) FILTER (WHERE decision='rejected'), "
            "count(*) FILTER (WHERE decision IS NULL OR decision NOT IN "
            "('publish','needs_revision','rejected')), "
            "percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) "
            "FILTER (WHERE duration_ms IS NOT NULL), "
            "percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) "
            "FILTER (WHERE duration_ms IS NOT NULL), "
            "count(*) FILTER (WHERE writeback_status='succeeded'), "
            "count(*) FILTER (WHERE writeback_status='failed'), "
            "count(*) FILTER (WHERE writeback_status='superseded'), "
            "count(*) FILTER (WHERE writeback_status='pending'), "
            "count(*) FILTER (WHERE writeback_status='unknown' OR "
            "writeback_status NOT IN ('succeeded','failed','superseded','pending')) "
            "FROM run_log WHERE scored_at >= %s AND scored_at < %s"
            + fixture_sql,
            (start, end),
        )
        metrics = cur.fetchone()

        cur.execute(
            "SELECT item FROM run_log "
            "CROSS JOIN LATERAL jsonb_array_elements("
            "CASE WHEN jsonb_typeof(usage)='array' THEN usage ELSE '[]'::jsonb END"
            ") AS item "
            "WHERE scored_at >= %s AND scored_at < %s"
            + fixture_sql,
            (start, end),
        )
        usage = [row[0] for row in cur.fetchall()]

    queue_counts = {status: int(raw_queue.get(status, 0)) for status in QUEUE_STATUSES}
    decision_counts = {
        "publish": int(metrics[1]),
        "needs_revision": int(metrics[2]),
        "rejected": int(metrics[3]),
        "unknown": int(metrics[4]),
    }
    writeback_counts = {
        status: int(metrics[index])
        for index, status in enumerate(WRITEBACK_STATUSES, start=7)
    }
    completed_writebacks = writeback_counts["succeeded"] + writeback_counts["failed"]
    success_rate = (
        None
        if completed_writebacks == 0
        else Decimal(writeback_counts["succeeded"]) / Decimal(completed_writebacks)
    )

    return DashboardView(
        date_from=date_from,
        date_to=date_to,
        queue_counts=queue_counts,
        total_reviews=int(metrics[0]),
        decision_counts=decision_counts,
        duration_p50_ms=_duration_percentile(metrics[5]),
        duration_p95_ms=_duration_percentile(metrics[6]),
        cost_estimate=estimate_usage(usage, DEFAULT_PRICING_PATH),
        writeback_counts=writeback_counts,
        writeback_success_rate=success_rate,
    )
