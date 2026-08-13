"""Trang audit log chi doc, chi role admin."""
from datetime import date
import re
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from review_platform.admin import dependencies, queries, rendering
from review_platform.auth.rbac import Role


router = APIRouter()
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def _positive_int(raw: str | None, *, default: int, maximum: int | None = None) -> int:
    if raw is None:
        return default
    if not raw.isascii() or not raw.isdigit():
        raise ValueError("Trang và kích thước trang phải là số nguyên dương.")
    value = int(raw)
    if value < 1 or (maximum is not None and value > maximum):
        raise ValueError("Trang hoặc kích thước trang ngoài giới hạn.")
    return value


def _optional_date(raw: str | None) -> date | None:
    if raw is None or raw == "":
        return None
    if _DATE_PATTERN.fullmatch(raw) is None:
        raise ValueError("Ngày phải đúng định dạng YYYY-MM-DD.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Ngày phải đúng định dạng YYYY-MM-DD.") from exc


def _filters(request: Request):
    filters = queries.AuditFilters(
        action=request.query_params.get("action") or None,
        outcome=request.query_params.get("outcome") or None,
        actor=request.query_params.get("actor") or None,
        date_from=_optional_date(request.query_params.get("from")),
        date_to=_optional_date(request.query_params.get("to")),
    )
    return (
        filters,
        _positive_int(request.query_params.get("page"), default=1),
        _positive_int(request.query_params.get("page_size"), default=25, maximum=100),
    )


def _page_url(request: Request, page: int) -> str:
    params = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key != "page"
    ]
    params.append(("page", str(page)))
    return f"/admin/audit?{urlencode(params)}"


def _response(
    request: Request,
    *,
    resolved,
    page,
    error: str | None,
    status_code: int,
):
    previous_url = None if page is None or page.page <= 1 else _page_url(
        request, page.page - 1
    )
    next_url = (
        None
        if page is None or page.page >= page.total_pages
        else _page_url(request, page.page + 1)
    )
    return rendering.render_template(
        request,
        "audit.html",
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        page=page,
        error=error,
        filter_values=dict(request.query_params),
        action_options=queries.AUDIT_ACTIONS,
        outcome_options=queries.AUDIT_OUTCOMES,
        previous_url=previous_url,
        next_url=next_url,
    )


@router.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    del actor
    try:
        filters, page_number, page_size = _filters(request)
        page = queries.list_audit_events(conn, filters, page_number, page_size)
    except ValueError as exc:
        return _response(
            request,
            resolved=resolved,
            page=None,
            error=f"Bộ lọc không hợp lệ. {exc}",
            status_code=422,
        )
    return _response(
        request,
        resolved=resolved,
        page=page,
        error=None,
        status_code=200,
    )
