"""Route doc job va retry co audit cho Platform Admin."""
from datetime import date
import re
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from review_platform import reviews
from review_platform.admin import dependencies, queries, rendering
from review_platform.auth.rbac import Role, allows


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


def _filters(request: Request) -> tuple[queries.JobFilters, int, int]:
    date_from = _optional_date(request.query_params.get("from"))
    date_to = _optional_date(request.query_params.get("to"))
    filters = queries.JobFilters(
        status=request.query_params.get("status") or None,
        site=request.query_params.get("site") or None,
        source=request.query_params.get("source") or None,
        external_id=request.query_params.get("external_id") or None,
        date_from=date_from,
        date_to=date_to,
    )
    page = _positive_int(request.query_params.get("page"), default=1)
    page_size = _positive_int(
        request.query_params.get("page_size"),
        default=25,
        maximum=100,
    )
    return filters, page, page_size


def _page_url(request: Request, page: int) -> str:
    params = list(request.query_params.multi_items())
    params = [(key, value) for key, value in params if key != "page"]
    params.append(("page", str(page)))
    return f"/admin/jobs?{urlencode(params)}"


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
            "partials/jobs_table.html",
            status_code=status_code,
            **context,
        )
    return rendering.render_template(
        request,
        "jobs.html",
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        filter_values=dict(request.query_params),
        **context,
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    try:
        filters, page_number, page_size = _filters(request)
        page = queries.list_jobs(conn, filters, page_number, page_size)
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


def _detail_response(
    request: Request,
    *,
    resolved,
    job,
    error: str | None = None,
    status_code: int = 200,
):
    can_retry = (
        job is not None
        and job.status == "failed"
        and allows(resolved.user.role, Role.OPERATOR)
    )
    return rendering.render_template(
        request,
        "job_detail.html",
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        job=job,
        can_retry=can_retry,
        error=error,
    )


def _job_or_error(conn, public_id: str):
    try:
        parsed = UUID(public_id)
    except ValueError as exc:
        raise reviews.JobRetryNotFound("job khong ton tai") from exc
    job = queries.get_job(conn, parsed)
    if job is None:
        raise reviews.JobRetryNotFound("job khong ton tai")
    return job


@router.get("/jobs/{public_id}", response_class=HTMLResponse)
def job_detail_page(
    public_id: str,
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    try:
        job = _job_or_error(conn, public_id)
    except reviews.JobRetryNotFound:
        return _detail_response(
            request,
            resolved=resolved,
            job=None,
            error="Không tìm thấy job.",
            status_code=404,
        )
    return _detail_response(request, resolved=resolved, job=job)


@router.post(
    "/jobs/{public_id}/retry",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def retry_job(
    public_id: str,
    request: Request,
    confirm_cost: str = Form(default=""),
    reason: str | None = Form(default=None),
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.OPERATOR)),
    conn=Depends(dependencies.get_db),
):
    try:
        job = _job_or_error(conn, public_id)
    except reviews.JobRetryNotFound:
        return _detail_response(
            request,
            resolved=resolved,
            job=None,
            error="Không tìm thấy job.",
            status_code=404,
        )
    if confirm_cost != "yes":
        return _detail_response(
            request,
            resolved=resolved,
            job=job,
            error="Bạn phải xác nhận khả năng phát sinh chi phí trước khi retry.",
            status_code=400,
        )
    try:
        result = reviews.retry_failed(
            conn,
            job_public_id=job.public_id,
            actor=actor,
            reason=reason,
        )
    except reviews.JobRetryNotFound:
        return _detail_response(
            request,
            resolved=resolved,
            job=None,
            error="Không tìm thấy job.",
            status_code=404,
        )
    except (reviews.JobRetryConflict, reviews.JobRetryContextError) as exc:
        return _detail_response(
            request,
            resolved=resolved,
            job=queries.get_job(conn, job.public_id),
            error=f"Không thể retry job. {exc}",
            status_code=409,
        )
    return RedirectResponse(
        f"/admin/jobs/{result.new_job_public_id}",
        status_code=303,
    )
