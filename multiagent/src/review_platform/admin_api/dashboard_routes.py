"""Endpoint tong quan van hanh cho Console API.

Tai dung nguyen `dashboard_routes._date_range` cua admin Jinja2 thay vi viet
lai luat kiem tra khoang ngay. Viet lai se de hai UI trinh bay hai bo quy tac
khac nhau tren cung mot du lieu, va sai lech kieu do rat kho phat hien.
"""
from fastapi import APIRouter, Depends, Request

from review_platform.admin import dashboard_routes as legacy_dashboard
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth.rbac import Role


router = APIRouter()


@router.get("/dashboard", response_model=models.DashboardResponse)
def dashboard(
    request: Request,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    try:
        date_from, date_to, _, _ = legacy_dashboard._date_range(request)
    except legacy_dashboard.DashboardInputError as exc:
        raise errors.invalid_filter(str(exc)) from exc

    view = queries.dashboard(conn, date_from=date_from, date_to=date_to)
    return models.DashboardResponse.from_view(view)
