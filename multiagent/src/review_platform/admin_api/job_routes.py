"""Endpoint doc job cho Console API.

Tai dung `job_routes._filters` cua admin Jinja2 de hai UI ap dung dung mot bo
quy tac loc va phan trang (page_size toi da 100, mac dinh 25).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from review_platform import reviews
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import job_routes as legacy_jobs
from review_platform.admin import queries
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth.rbac import Role


router = APIRouter()


def _parsed_job_id(public_id: str) -> UUID:
    # ID sai dinh dang va ID khong ton tai deu tra 404 giong nhau: khong lo ra
    # rang he thong phan biet duoc hai truong hop.
    try:
        return UUID(public_id)
    except ValueError as exc:
        raise errors.not_found("Job khong ton tai") from exc


@router.get("/jobs", response_model=models.JobPage)
def list_jobs(
    request: Request,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    try:
        filters, page_number, page_size = legacy_jobs._filters(request)
        view = queries.list_jobs(conn, filters, page_number, page_size)
    except ValueError as exc:
        raise errors.invalid_filter(str(exc)) from exc
    return models.page_payload(
        view,
        [models.JobListItemModel.from_view(item) for item in view.items],
    )


@router.get("/jobs/{public_id}", response_model=models.JobDetailModel)
def get_job(
    public_id: str,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    job = queries.get_job(conn, _parsed_job_id(public_id))
    if job is None:
        raise errors.not_found("Job khong ton tai")
    return models.JobDetailModel.from_view(job)


@router.post(
    "/jobs/{public_id}/retry",
    response_model=models.JobDetailModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def retry_job(
    public_id: str,
    payload: models.RetryRequest,
    resolved=Depends(dependencies.require_console_role(Role.OPERATOR)),
    conn=Depends(admin_dependencies.get_db),
):
    # Thu tu ba buoc kiem tra la co y: 404 truoc, roi cong chi phi, roi moi
    # retry. Dao lai thi mot job khong ton tai van tra 400 "chua xac nhan chi
    # phi", lam nguoi dung tuong job co that va gay nhieu khi truy su co.
    parsed = _parsed_job_id(public_id)
    if queries.get_job(conn, parsed) is None:
        raise errors.not_found("Job khong ton tai")

    if not payload.confirm_cost:
        raise errors.ConsoleError(
            400,
            "cost_not_confirmed",
            "Phai xac nhan kha nang phat sinh chi phi truoc khi retry",
            "confirm_cost",
        )

    try:
        result = reviews.retry_failed(
            conn,
            job_public_id=parsed,
            actor=resolved.user,
            reason=payload.reason,
        )
    except reviews.JobRetryNotFound as exc:
        raise errors.not_found("Job khong ton tai") from exc
    except (reviews.JobRetryConflict, reviews.JobRetryContextError) as exc:
        raise errors.ConsoleError(409, "conflict", str(exc)) from exc
    except PermissionError as exc:
        # Lop chan thu hai ben trong reviews.retry_failed. Neu toi day nghia la
        # require_console_role da bi qua mat, nen khong duoc de lot thanh 500.
        raise errors.forbidden() from exc

    new_job = queries.get_job(conn, result.new_job_public_id)
    return models.JobDetailModel.from_view(new_job)
