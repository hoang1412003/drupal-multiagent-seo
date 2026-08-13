"""Route tong quan van hanh cua Platform Admin."""
from datetime import date, datetime, timedelta, timezone
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from review_platform.admin import dependencies, queries, rendering


router = APIRouter()
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class DashboardInputError(ValueError):
    pass


def _parse_date(raw: str) -> date:
    if _DATE_PATTERN.fullmatch(raw) is None:
        raise DashboardInputError("Ngày phải đúng định dạng YYYY-MM-DD.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise DashboardInputError("Ngày phải đúng định dạng YYYY-MM-DD.") from exc


def _date_range(request: Request) -> tuple[date, date, str, str]:
    raw_from = request.query_params.get("from")
    raw_to = request.query_params.get("to")
    if raw_from is None and raw_to is None:
        date_to = datetime.now(timezone.utc).date()
        date_from = date_to - timedelta(days=6)
        return date_from, date_to, date_from.isoformat(), date_to.isoformat()
    if raw_from is None or raw_to is None:
        raise DashboardInputError(
            "Phải cung cấp đồng thời cả Từ ngày và Đến ngày."
        )

    date_from = _parse_date(raw_from)
    date_to = _parse_date(raw_to)
    if date_to < date_from:
        raise DashboardInputError("Đến ngày không được trước Từ ngày.")
    if (date_to - date_from).days + 1 > queries.MAX_RANGE_DAYS:
        raise DashboardInputError(
            f"Khoảng ngày tối đa {queries.MAX_RANGE_DAYS} ngày."
        )
    return date_from, date_to, raw_from, raw_to


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").casefold() == "true"


def _response(
    request: Request,
    *,
    resolved,
    view,
    filter_from: str,
    filter_to: str,
    error: str | None,
    status_code: int = 200,
):
    if _is_htmx(request):
        return rendering.render_template(
            request,
            "partials/dashboard_metrics.html",
            status_code=status_code,
            view=view,
            error=error,
        )
    return rendering.render_template(
        request,
        "home.html",
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        view=view,
        filter_from=filter_from,
        filter_to=filter_to,
        error=error,
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    try:
        date_from, date_to, filter_from, filter_to = _date_range(request)
    except DashboardInputError as exc:
        return _response(
            request,
            resolved=resolved,
            view=None,
            filter_from=request.query_params.get("from", ""),
            filter_to=request.query_params.get("to", ""),
            error=str(exc),
            status_code=422,
        )

    view = queries.dashboard(conn, date_from=date_from, date_to=date_to)
    return _response(
        request,
        resolved=resolved,
        view=view,
        filter_from=filter_from,
        filter_to=filter_to,
        error=None,
    )
