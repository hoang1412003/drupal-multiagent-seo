"""Read-model SQL dung chung cho cac man hinh Platform Admin."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import re
from collections.abc import Mapping
from urllib.parse import urlsplit
from uuid import UUID

from review_platform.admin import sanitization
from review_platform.admin.sanitization import sanitize_text
from review_platform.auth.rbac import Role
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
class JobFilters:
    status: str | None = None
    site: str | None = None
    source: str | None = None
    external_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True)
class JobListItem:
    public_id: UUID
    created_at: datetime
    site_id: UUID
    site_slug: str
    external_content_id: str
    status: str
    attempts: int
    source: str
    policy_version: str


@dataclass(frozen=True)
class JobDetail:
    public_id: UUID
    created_at: datetime
    updated_at: datetime
    site_id: UUID
    site_slug: str
    site_name: str
    profile_id: UUID
    policy_version: str
    external_content_id: str
    external_revision_id: str | None
    content_type: str
    langcode: str
    status: str
    attempts: int
    source: str
    correlation_id: UUID
    supersedes_job_public_id: UUID | None
    last_error: str | None
    run_public_id: UUID | None
    writeback_status: str | None
    run_scored_at: datetime | None
    saved_result_available: bool


@dataclass(frozen=True)
class ReviewFilters:
    decision: str | None = None
    site: str | None = None
    external_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True)
class ReviewListItem:
    public_id: UUID
    scored_at: datetime
    site_id: UUID
    site_slug: str
    external_content_id: str
    decision: str | None
    final_score: Decimal | None
    profile_code: str
    policy_version: str
    model: str
    is_fixture: bool


@dataclass(frozen=True)
class AgentResultView:
    name: str
    score: object
    criteria: tuple[dict, ...]
    issues: tuple[dict, ...]
    evidence: tuple[dict, ...]


@dataclass(frozen=True)
class ReviewDetail:
    public_id: UUID
    scored_at: datetime
    duration_ms: int | None
    decision: str | None
    final_score: Decimal | None
    missing_agents: tuple[str, ...]
    veto_reason: str | None
    note: str | None
    agents: tuple[AgentResultView, ...]
    config_meta: object
    cost_estimate: CostEstimate
    usage_available: bool
    model: str
    writeback_status: str
    writeback_error: str | None
    site_id: UUID
    site_slug: str
    site_name: str
    profile_id: UUID
    profile_code: str
    policy_version: str
    external_content_id: str
    external_revision_id: str | None
    content_type: str
    langcode: str
    correlation_id: UUID
    is_fixture: bool
    drupal_url: str | None


@dataclass(frozen=True)
class UserListItem:
    id: UUID
    username: str
    role: Role
    active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


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


_AGENT_ORDER = ("content_quality", "seo", "brand", "compliance")
_REVIEW_DECISIONS = ("publish", "needs_revision", "rejected", "unknown")


def _review_value(value):
    return sanitization.sanitize_mapping(
        value,
        max_depth=3,
        max_items=50,
        max_text_length=2000,
    )


def _review_entries(value, *, limit: int = 50) -> tuple[dict, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        raw_items = [
            {"criterion": key, "value": nested}
            for key, nested in list(value.items())[:limit]
        ]
    elif isinstance(value, (list, tuple)):
        raw_items = list(value[:limit])
    else:
        raw_items = [value]

    result = []
    for item in raw_items:
        normalized = _review_value(item)
        result.append(normalized if isinstance(normalized, dict) else {"value": normalized})
    return tuple(result)


def normalize_agent_results(value) -> tuple[AgentResultView, ...]:
    """Normalize JSONB legacy ma khong mutate, gioi han kich thuoc cho UI."""
    if value is None:
        return ()
    if not isinstance(value, Mapping):
        return (
            AgentResultView(
                name="legacy",
                score=None,
                criteria=(),
                issues=_review_entries(value),
                evidence=(),
            ),
        )

    names = [name for name in _AGENT_ORDER if name in value]
    names.extend(sorted(str(name) for name in value if str(name) not in names))
    result = []
    for name in names[:4]:
        raw = value.get(name)
        if isinstance(raw, Mapping):
            score = _review_value(raw.get("score"))
            criteria = _review_entries(raw.get("criteria"))
            combined_issues = []
            for key in ("issues", "flags"):
                current = raw.get(key)
                if isinstance(current, (list, tuple)):
                    combined_issues.extend(current)
                elif current is not None:
                    combined_issues.append(current)
            issues = _review_entries(combined_issues[:50])
            evidence = _review_entries(raw.get("evidence"))
        else:
            score = None
            criteria = ()
            issues = _review_entries(raw)
            evidence = ()
        result.append(
            AgentResultView(
                name=sanitize_text(name, max_length=200),
                score=score,
                criteria=criteria,
                issues=issues,
                evidence=evidence,
            )
        )
    return tuple(result)


def _is_fixture(config_meta) -> bool:
    if not isinstance(config_meta, Mapping):
        return False
    marker = config_meta.get("is_fixture")
    return marker is True or (
        isinstance(marker, str) and marker.casefold() == "true"
    )


def _drupal_node_url(base_url: str, external_id: str) -> str | None:
    if re.fullmatch(r"[0-9]+", external_id) is None:
        return None
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    origin = f"{parsed.scheme}://{host}"
    if port is not None:
        origin += f":{port}"
    return f"{origin}/node/{external_id}"


def _normalize_usage(value) -> tuple[list[dict], bool]:
    if not isinstance(value, list):
        return [], False
    try:
        for row in value:
            if not isinstance(row, dict):
                raise ValueError
            if not isinstance(row.get("model"), str) or not row["model"].strip():
                raise ValueError
            for key in ("input_tokens", "output_tokens"):
                token_count = row.get(key)
                if (
                    isinstance(token_count, bool)
                    or not isinstance(token_count, int)
                    or token_count < 0
                ):
                    raise ValueError
    except (KeyError, ValueError):
        return [], False
    return value, bool(value)


def _validate_optional_text(name: str, value: str | None, max_length: int) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ValueError(f"{name} khong hop le")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _job_where(filters: JobFilters) -> tuple[str, list]:
    if not isinstance(filters, JobFilters):
        raise ValueError("filters phai la JobFilters")
    if filters.status is not None and filters.status not in QUEUE_STATUSES:
        raise ValueError("status job khong hop le")
    _validate_optional_text("site", filters.site, 100)
    _validate_optional_text("source", filters.source, 100)
    _validate_optional_text("external_id", filters.external_id, 100)
    if (filters.date_from is None) != (filters.date_to is None):
        raise ValueError("date_from/date_to phai di cung nhau")

    clauses = []
    params: list = []
    if filters.status is not None:
        clauses.append("j.status=%s")
        params.append(filters.status)
    if filters.site is not None:
        try:
            site_id = UUID(filters.site)
        except ValueError:
            clauses.append("s.slug=%s")
            params.append(filters.site)
        else:
            clauses.append("j.site_id=%s")
            params.append(site_id)
    if filters.source is not None:
        clauses.append("j.source=%s")
        params.append(filters.source)
    if filters.external_id is not None:
        clauses.append("strpos(lower(j.external_content_id), lower(%s)) > 0")
        params.append(filters.external_id)
    if filters.date_from is not None:
        start, end = _bounds(filters.date_from, filters.date_to)
        clauses.extend(("j.created_at >= %s", "j.created_at < %s"))
        params.extend((start, end))
    return (" AND ".join(clauses) if clauses else "TRUE"), params


def list_jobs(
    conn,
    filters: JobFilters,
    page: int,
    page_size: int,
) -> PageView:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("page phai >= 1")
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= 100
    ):
        raise ValueError("page_size phai trong 1..100")
    where_sql, params = _job_where(filters)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM review_job AS j JOIN site AS s ON s.id=j.site_id "
            f"WHERE {where_sql}",
            params,
        )
        total = int(cur.fetchone()[0])
        cur.execute(
            "SELECT j.public_id,j.created_at,j.site_id,s.slug,j.external_content_id,"
            "j.status,j.attempts,j.source,j.policy_version "
            "FROM review_job AS j JOIN site AS s ON s.id=j.site_id "
            f"WHERE {where_sql} ORDER BY j.created_at DESC,j.id DESC "
            "LIMIT %s OFFSET %s",
            (*params, page_size, (page - 1) * page_size),
        )
        items = tuple(
            JobListItem(row[0], _as_utc(row[1]), *row[2:])
            for row in cur.fetchall()
        )
    return PageView(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


def get_job(conn, public_id: UUID) -> JobDetail | None:
    public_id = UUID(str(public_id))
    with conn.cursor() as cur:
        cur.execute(
            "SELECT j.public_id,j.created_at,j.updated_at,j.site_id,s.slug,s.name,"
            "j.profile_id,j.policy_version,j.external_content_id,"
            "j.external_revision_id,j.content_type,j.langcode,j.status,j.attempts,"
            "j.source,j.correlation_id,parent.public_id,j.last_error,latest.public_id,"
            "latest.writeback_status,latest.scored_at,"
            "EXISTS (SELECT 1 FROM run_log AS reusable WHERE reusable.job_id=j.id "
            "AND reusable.writeback_status='failed') "
            "FROM review_job AS j JOIN site AS s ON s.id=j.site_id "
            "LEFT JOIN review_job AS parent ON parent.id=j.supersedes_job_id "
            "LEFT JOIN LATERAL (SELECT run.public_id,run.writeback_status,run.scored_at "
            "FROM run_log AS run WHERE run.job_id=j.id "
            "ORDER BY run.scored_at DESC,run.id DESC LIMIT 1) AS latest ON TRUE "
            "WHERE j.public_id=%s",
            (public_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    last_error = None if row[17] is None else sanitize_text(row[17], max_length=1000)
    normalized = (
        row[0],
        _as_utc(row[1]),
        _as_utc(row[2]),
        *row[3:17],
        last_error,
        row[18],
        row[19],
        _as_utc(row[20]),
        row[21],
    )
    return JobDetail(*normalized)


def _review_where(filters: ReviewFilters) -> tuple[str, list]:
    if not isinstance(filters, ReviewFilters):
        raise ValueError("filters phai la ReviewFilters")
    if filters.decision is not None and filters.decision not in _REVIEW_DECISIONS:
        raise ValueError("decision khong hop le")
    _validate_optional_text("site", filters.site, 100)
    _validate_optional_text("external_id", filters.external_id, 100)
    if (filters.date_from is None) != (filters.date_to is None):
        raise ValueError("date_from/date_to phai di cung nhau")

    clauses = []
    params: list = []
    if filters.decision == "unknown":
        clauses.append(
            "(r.decision IS NULL OR r.decision NOT IN "
            "('publish','needs_revision','rejected'))"
        )
    elif filters.decision is not None:
        clauses.append("r.decision=%s")
        params.append(filters.decision)
    if filters.site is not None:
        try:
            site_id = UUID(filters.site)
        except ValueError:
            clauses.append("s.slug=%s")
            params.append(filters.site)
        else:
            clauses.append("r.site_id=%s")
            params.append(site_id)
    if filters.external_id is not None:
        clauses.append("strpos(lower(r.external_content_id), lower(%s)) > 0")
        params.append(filters.external_id)
    if filters.date_from is not None:
        start, end = _bounds(filters.date_from, filters.date_to)
        clauses.extend(("r.scored_at >= %s", "r.scored_at < %s"))
        params.extend((start, end))
    return (" AND ".join(clauses) if clauses else "TRUE"), params


def list_reviews(
    conn,
    filters: ReviewFilters,
    page: int,
    page_size: int,
) -> PageView:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("page phai >= 1")
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= 100
    ):
        raise ValueError("page_size phai trong 1..100")
    where_sql, params = _review_where(filters)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM run_log AS r JOIN site AS s ON s.id=r.site_id "
            f"JOIN review_profile AS p ON p.id=r.profile_id WHERE {where_sql}",
            params,
        )
        total = int(cur.fetchone()[0])
        cur.execute(
            "SELECT r.public_id,r.scored_at,r.site_id,s.slug,r.external_content_id,"
            "r.decision,r.final_score,p.code,r.policy_version,r.model,"
            "lower(coalesce(r.config_meta->>'is_fixture','false'))='true' "
            "FROM run_log AS r JOIN site AS s ON s.id=r.site_id "
            f"JOIN review_profile AS p ON p.id=r.profile_id WHERE {where_sql} "
            "ORDER BY r.scored_at DESC,r.id DESC LIMIT %s OFFSET %s",
            (*params, page_size, (page - 1) * page_size),
        )
        items = tuple(
            ReviewListItem(row[0], _as_utc(row[1]), *row[2:])
            for row in cur.fetchall()
        )
    return PageView(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


def get_review(conn, public_id: UUID) -> ReviewDetail | None:
    public_id = UUID(str(public_id))
    with conn.cursor() as cur:
        cur.execute(
            "SELECT r.public_id,r.scored_at,r.duration_ms,r.decision,r.final_score,"
            "r.missing_agents,r.veto_reason,r.note,r.agent_results,r.config_meta,"
            "r.usage,r.model,r.writeback_status,r.writeback_error,r.site_id,s.slug,"
            "s.name,s.base_url,r.profile_id,p.code,r.policy_version,"
            "r.external_content_id,r.external_revision_id,r.content_type,r.langcode,"
            "r.correlation_id FROM run_log AS r JOIN site AS s ON s.id=r.site_id "
            "JOIN review_profile AS p ON p.id=r.profile_id WHERE r.public_id=%s",
            (public_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None

    missing_agents = (
        tuple(
            sanitize_text(item, max_length=2000)
            for item in row[5][:20]
            if item is not None
        )
        if isinstance(row[5], list)
        else ()
    )
    usage, usage_available = _normalize_usage(row[10])
    config_meta = sanitization.sanitize_mapping(
        row[9],
        max_depth=3,
        max_items=50,
        max_text_length=2000,
    )
    writeback_status = (
        row[12] if row[12] in WRITEBACK_STATUSES else "unknown"
    )
    return ReviewDetail(
        public_id=row[0],
        scored_at=_as_utc(row[1]),
        duration_ms=row[2],
        decision=row[3],
        final_score=row[4],
        missing_agents=missing_agents,
        veto_reason=(
            None if row[6] is None else sanitize_text(row[6], max_length=2000)
        ),
        note=None if row[7] is None else sanitize_text(row[7], max_length=2000),
        agents=normalize_agent_results(row[8]),
        config_meta=config_meta,
        cost_estimate=estimate_usage(usage, DEFAULT_PRICING_PATH),
        usage_available=usage_available,
        model=sanitize_text(row[11], max_length=200),
        writeback_status=writeback_status,
        writeback_error=(
            None if row[13] is None else sanitize_text(row[13], max_length=1000)
        ),
        site_id=row[14],
        site_slug=row[15],
        site_name=row[16],
        profile_id=row[18],
        profile_code=row[19],
        policy_version=row[20],
        external_content_id=row[21],
        external_revision_id=row[22],
        content_type=row[23],
        langcode=row[24],
        correlation_id=row[25],
        is_fixture=_is_fixture(row[9]),
        drupal_url=_drupal_node_url(row[17], row[21]),
    )


def list_users(conn, *, page: int, page_size: int) -> PageView:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("page phai >= 1")
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= 100
    ):
        raise ValueError("page_size phai trong 1..100")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_user")
        total = int(cur.fetchone()[0])
        cur.execute(
            "SELECT id,username,role,active,must_change_password,last_login_at,"
            "created_at,updated_at FROM admin_user "
            "ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s",
            (page_size, (page - 1) * page_size),
        )
        items = tuple(
            UserListItem(
                id=row[0],
                username=row[1],
                role=Role(row[2]),
                active=row[3],
                must_change_password=row[4],
                last_login_at=_as_utc(row[5]),
                created_at=_as_utc(row[6]),
                updated_at=_as_utc(row[7]),
            )
            for row in cur.fetchall()
        )
    return PageView(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


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
