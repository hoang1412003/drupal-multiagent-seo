"""Route lich su cham read-only cua Platform Admin."""
from datetime import date
import re
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from review_platform.admin import dependencies, queries, rendering


router = APIRouter()
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").casefold() == "true"


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


def _filters(request: Request) -> tuple[queries.ReviewFilters, int, int]:
    filters = queries.ReviewFilters(
        decision=request.query_params.get("decision") or None,
        site=request.query_params.get("site") or None,
        external_id=request.query_params.get("external_id") or None,
        date_from=_optional_date(request.query_params.get("from")),
        date_to=_optional_date(request.query_params.get("to")),
    )
    return (
        filters,
        _positive_int(request.query_params.get("page"), default=1),
        _positive_int(
            request.query_params.get("page_size"),
            default=25,
            maximum=100,
        ),
    )


def _page_url(request: Request, page: int) -> str:
    params = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key != "page"
    ]
    params.append(("page", str(page)))
    return f"/admin/reviews?{urlencode(params)}"


def _list_response(
    request: Request,
    *,
    resolved,
    page,
    error: str | None,
    status_code: int,
):
    previous_url = None if page is None or page.page <= 1 else _page_url(
        request,
        page.page - 1,
    )
    next_url = (
        None
        if page is None or page.page >= page.total_pages
        else _page_url(request, page.page + 1)
    )
    context = {
        "page": page,
        "error": error,
        "previous_url": previous_url,
        "next_url": next_url,
    }
    if _is_htmx(request):
        return rendering.render_template(
            request,
            "partials/reviews_table.html",
            status_code=status_code,
            **context,
        )
    return rendering.render_template(
        request,
        "reviews.html",
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        filter_values=dict(request.query_params),
        **context,
    )


@router.get("/reviews", response_class=HTMLResponse)
def reviews_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    try:
        filters, page_number, page_size = _filters(request)
        page = queries.list_reviews(conn, filters, page_number, page_size)
    except ValueError as exc:
        return _list_response(
            request,
            resolved=resolved,
            page=None,
            error=f"Bộ lọc không hợp lệ. {exc}",
            status_code=422,
        )
    return _list_response(
        request,
        resolved=resolved,
        page=page,
        error=None,
        status_code=200,
    )


@router.get("/reviews/{public_id}", response_class=HTMLResponse)
def review_detail_page(
    public_id: str,
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    try:
        parsed = UUID(public_id)
    except ValueError:
        parsed = None
    review = None if parsed is None else queries.get_review(conn, parsed)
    if review is None:
        return rendering.render_template(
            request,
            "review_detail.html",
            status_code=404,
            user=resolved.user,
            csrf_token=resolved.csrf_token,
            review=None,
            error="Không tìm thấy lượt chấm.",
        )
    return rendering.render_template(
        request,
        "review_detail.html",
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        review=review,
        error=None,
    )
