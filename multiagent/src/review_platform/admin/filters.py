"""Doc va kiem tra tham so loc tu query string.

Truoc day cac ham nay nam RAI RAC trong bon file route Jinja2, va `positive_int`
voi `optional_date` bi chep lai o ba cho. Khi xoa admin Jinja2 (2026-08-21),
Console van can chung - nen chung duoc gom vao day thay vi chet theo cac file
route.

Mot bo quy tac duy nhat cho ca hai giao dien la co y: page_size toi da 100,
ngay phai dung YYYY-MM-DD, khoang ngay toi da MAX_RANGE_DAYS. Hai giao dien ap
hai bo quy tac khac nhau se sinh ra hai cach hieu ve cung mot bo loc.
"""
from datetime import date, datetime, timedelta, timezone
import re

from fastapi import Request

from review_platform.admin import queries


_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

PAGE_SIZE_MAC_DINH = 25
PAGE_SIZE_TOI_DA = 100


class DashboardInputError(ValueError):
    """Loi nhap lieu cua bo loc dashboard.

    Tach rieng khoi ValueError de route phan biet duoc "nguoi dung go sai" voi
    "code hong" - hai truong hop can hai ma HTTP khac nhau.
    """


def positive_int(raw: str | None, *, default: int, maximum: int | None = None) -> int:
    if raw is None:
        return default
    # isascii() chan ca chu so Unicode (vi du chu so A Rap - An Do): chung qua
    # duoc isdigit() nhung int() thi doi y nghia.
    if not raw.isascii() or not raw.isdigit():
        raise ValueError("Trang và kích thước trang phải là số nguyên dương.")
    value = int(raw)
    if value < 1 or (maximum is not None and value > maximum):
        raise ValueError("Trang hoặc kích thước trang ngoài giới hạn.")
    return value


def optional_date(raw: str | None) -> date | None:
    if raw is None or raw == "":
        return None
    if _DATE_PATTERN.fullmatch(raw) is None:
        raise ValueError("Ngày phải đúng định dạng YYYY-MM-DD.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Ngày phải đúng định dạng YYYY-MM-DD.") from exc


def _phan_trang(request: Request) -> tuple[int, int]:
    return (
        positive_int(request.query_params.get("page"), default=1),
        positive_int(
            request.query_params.get("page_size"),
            default=PAGE_SIZE_MAC_DINH,
            maximum=PAGE_SIZE_TOI_DA,
        ),
    )


def job_filters(request: Request) -> tuple[queries.JobFilters, int, int]:
    filters = queries.JobFilters(
        status=request.query_params.get("status") or None,
        site=request.query_params.get("site") or None,
        source=request.query_params.get("source") or None,
        external_id=request.query_params.get("external_id") or None,
        date_from=optional_date(request.query_params.get("from")),
        date_to=optional_date(request.query_params.get("to")),
    )
    page, page_size = _phan_trang(request)
    return filters, page, page_size


def review_filters(request: Request) -> tuple[queries.ReviewFilters, int, int]:
    filters = queries.ReviewFilters(
        decision=request.query_params.get("decision") or None,
        site=request.query_params.get("site") or None,
        external_id=request.query_params.get("external_id") or None,
        date_from=optional_date(request.query_params.get("from")),
        date_to=optional_date(request.query_params.get("to")),
    )
    page, page_size = _phan_trang(request)
    return filters, page, page_size


def audit_filters(request: Request) -> tuple[queries.AuditFilters, int, int]:
    filters = queries.AuditFilters(
        action=request.query_params.get("action") or None,
        outcome=request.query_params.get("outcome") or None,
        actor=request.query_params.get("actor") or None,
        date_from=optional_date(request.query_params.get("from")),
        date_to=optional_date(request.query_params.get("to")),
    )
    page, page_size = _phan_trang(request)
    return filters, page, page_size


def _parse_date(raw: str) -> date:
    if _DATE_PATTERN.fullmatch(raw) is None:
        raise DashboardInputError("Ngày phải đúng định dạng YYYY-MM-DD.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise DashboardInputError("Ngày phải đúng định dạng YYYY-MM-DD.") from exc


def date_range(request: Request) -> tuple[date, date, str, str]:
    """Khoang ngay cho dashboard. Khong co tham so thi lay 7 ngay gan nhat.

    Bat buoc co CA HAI `from` va `to`, khong chap nhan mot cai: chi mot ben thi
    ben con lai la gia tri ngam dinh ma nguoi dung khong he thay, va ho se doc
    so lieu cua mot khoang khac voi khoang ho nghi.
    """
    raw_from = request.query_params.get("from")
    raw_to = request.query_params.get("to")
    if raw_from is None and raw_to is None:
        date_to = datetime.now(timezone.utc).date()
        date_from = date_to - timedelta(days=6)
        return date_from, date_to, date_from.isoformat(), date_to.isoformat()
    if raw_from is None or raw_to is None:
        raise DashboardInputError("Phải cung cấp đồng thời cả Từ ngày và Đến ngày.")

    date_from = _parse_date(raw_from)
    date_to = _parse_date(raw_to)
    if date_to < date_from:
        raise DashboardInputError("Đến ngày không được trước Từ ngày.")
    if (date_to - date_from).days + 1 > queries.MAX_RANGE_DAYS:
        raise DashboardInputError(f"Khoảng ngày tối đa {queries.MAX_RANGE_DAYS} ngày.")
    return date_from, date_to, raw_from, raw_to
