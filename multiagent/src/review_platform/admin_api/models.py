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
