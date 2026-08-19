"""Pydantic model cho Console API.

Quy uoc chuyen kieu, ap dung nhat quan o moi model:
- UUID     -> str
- datetime -> chuoi ISO-8601 UTC ket thuc bang "Z" (dung `iso`)
- date     -> chuoi "YYYY-MM-DD"
- Decimal  -> so JSON (dung `to_number`). KHONG khai bao truong la Decimal:
  Pydantic v2 serialize Decimal thanh CHUOI, frontend se nhan "82.5" thay vi
  82.5 va moi phep so sanh so ben React deu sai am tham.
- None     -> null, khong doi thanh chuoi rong.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def to_number(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


class MeResponse(BaseModel):
    username: str
    role: str
    must_change_password: bool
    csrf_token: str


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = ""
    new_password: str = ""


class PageResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


def page_payload(view, items: list) -> dict:
    """Trai PageView thanh dict chuan. Dung cho MOI endpoint danh sach."""
    return {
        "items": items,
        "page": view.page,
        "page_size": view.page_size,
        "total": view.total,
        "total_pages": view.total_pages,
    }


class CostEstimateModel(BaseModel):
    input_tokens: int
    output_tokens: int
    estimated_usd: float | None
    pricing_version: int
    effective_at: str
    currency: str
    source: str
    unknown_models: list[str]

    @classmethod
    def from_dataclass(cls, value) -> "CostEstimateModel":
        return cls(
            input_tokens=value.input_tokens,
            output_tokens=value.output_tokens,
            estimated_usd=to_number(value.estimated_usd),
            pricing_version=value.pricing_version,
            effective_at=value.effective_at.isoformat(),
            currency=value.currency,
            source=value.source,
            unknown_models=list(value.unknown_models),
        )


class DashboardResponse(BaseModel):
    date_from: str
    date_to: str
    queue_counts: dict[str, int]
    total_reviews: int
    decision_counts: dict[str, int]
    duration_p50_ms: float | None
    duration_p95_ms: float | None
    cost_estimate: CostEstimateModel
    writeback_counts: dict[str, int]
    writeback_success_rate: float | None
    worker_status: str
    connector_status: str
    worker_running: int
    worker_stale: int
    worker_last_seen_at: str | None

    @classmethod
    def from_view(cls, view) -> "DashboardResponse":
        return cls(
            date_from=view.date_from.isoformat(),
            date_to=view.date_to.isoformat(),
            queue_counts=view.queue_counts,
            total_reviews=view.total_reviews,
            decision_counts=view.decision_counts,
            duration_p50_ms=to_number(view.duration_p50_ms),
            duration_p95_ms=to_number(view.duration_p95_ms),
            cost_estimate=CostEstimateModel.from_dataclass(view.cost_estimate),
            writeback_counts=view.writeback_counts,
            writeback_success_rate=to_number(view.writeback_success_rate),
            worker_status=view.worker_status,
            connector_status=view.connector_status,
            worker_running=view.worker_running,
            worker_stale=view.worker_stale,
            worker_last_seen_at=iso(view.worker_last_seen_at),
        )


class JobListItemModel(BaseModel):
    public_id: str
    created_at: str
    site_id: str
    site_slug: str
    external_content_id: str
    status: str
    attempts: int
    source: str
    policy_version: str

    @classmethod
    def from_view(cls, item) -> "JobListItemModel":
        return cls(
            public_id=str(item.public_id),
            created_at=iso(item.created_at),
            site_id=str(item.site_id),
            site_slug=item.site_slug,
            external_content_id=item.external_content_id,
            status=item.status,
            attempts=item.attempts,
            source=item.source,
            policy_version=item.policy_version,
        )


class JobPage(PageResponse):
    items: list[JobListItemModel]


class JobDetailModel(BaseModel):
    public_id: str
    created_at: str
    updated_at: str
    site_id: str
    site_slug: str
    site_name: str
    profile_id: str
    policy_version: str
    external_content_id: str
    external_revision_id: str | None
    content_type: str
    langcode: str
    status: str
    attempts: int
    source: str
    correlation_id: str
    supersedes_job_public_id: str | None
    last_error: str | None
    run_public_id: str | None
    writeback_status: str | None
    run_scored_at: str | None
    saved_result_available: bool

    @classmethod
    def from_view(cls, job) -> "JobDetailModel":
        return cls(
            public_id=str(job.public_id),
            created_at=iso(job.created_at),
            updated_at=iso(job.updated_at),
            site_id=str(job.site_id),
            site_slug=job.site_slug,
            site_name=job.site_name,
            profile_id=str(job.profile_id),
            policy_version=job.policy_version,
            external_content_id=job.external_content_id,
            external_revision_id=job.external_revision_id,
            content_type=job.content_type,
            langcode=job.langcode,
            status=job.status,
            attempts=job.attempts,
            source=job.source,
            correlation_id=str(job.correlation_id),
            supersedes_job_public_id=(
                None
                if job.supersedes_job_public_id is None
                else str(job.supersedes_job_public_id)
            ),
            last_error=job.last_error,
            run_public_id=(
                None if job.run_public_id is None else str(job.run_public_id)
            ),
            writeback_status=job.writeback_status,
            run_scored_at=iso(job.run_scored_at),
            saved_result_available=job.saved_result_available,
        )
