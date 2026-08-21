"""Gia tri hop le cho cac bo loc, de frontend khong hard-code gi ca.

Vi sao can: enum trang thai khong nam trong openapi.json (`status` khai la
`str`), nen mot frontend hard-code danh sach sai se khong bi bat boi bat ky
phep kiem nao. Lay tu day thi khong the lech.
"""
from fastapi import APIRouter, Depends

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin_api import dependencies, models
from review_platform.auth.rbac import Role


router = APIRouter()


@router.get("/filters", response_model=models.FiltersResponse)
def filters(
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    options = queries.filter_options(conn)
    return models.FiltersResponse(
        sites=[
            models.SiteOptionModel(slug=s.slug, name=s.name, active=s.active)
            for s in options.sites
        ],
        job_sources=list(options.job_sources),
        # Ba danh sach duoi day la hang so trong code, khong phai du lieu.
        job_statuses=list(queries.QUEUE_STATUSES),
        review_decisions=list(queries._REVIEW_DECISIONS),
        writeback_statuses=list(queries.WRITEBACK_STATUSES),
        audit_actions=list(queries.AUDIT_ACTIONS),
        audit_outcomes=list(queries.AUDIT_OUTCOMES),
        # Lay THANG tu enum Role. Man Nguoi dung can danh sach nay de dung
        # bang chon quyen; go tay o frontend la dung lai loi enum trang thai
        # job (brief ghi `succeeded` trong khi that su la `done`).
        roles=[role.value for role in Role],
    )
