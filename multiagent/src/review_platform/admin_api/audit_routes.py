"""Nhat ky thao tac, CHI DOC va CHI ADMIN.

Hai rang buoc do phai giong het admin Jinja2. Noi long o Console se bien no
thanh duong vong de doc nhat ky he thong.

Tai dung `audit_routes._filters` cua admin cu de hai UI ap cung mot bo quy tac
loc, va `queries.list_audit_events` da lam sach metadata truoc khi tra ve.
"""
from fastapi import APIRouter, Depends, Query, Request

from review_platform.admin import filters as admin_filters
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth.rbac import Role


_QUERY_PARAMS = frozenset({"action", "outcome", "actor", "from", "to",
                           "page", "page_size"})

router = APIRouter()


@router.get("/audit", response_model=models.AuditPage)
def list_audit(
    request: Request,
    action: str | None = Query(None, description="xem GET /filters"),
    outcome: str | None = Query(None, description="success|denied|failed"),
    actor: str | None = Query(None, description="khop mot phan ten dang nhap"),
    date_from: str | None = Query(None, alias="from", description="YYYY-MM-DD"),
    date_to: str | None = Query(None, alias="to", description="phai di cung `from`"),
    page: str | None = Query(None, description="mac dinh 1"),
    page_size: str | None = Query(None, description="mac dinh 25, toi da 100"),
    # CHI ADMIN. Viewer va operator khong duoc doc nhat ky he thong.
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    dependencies.reject_unknown_query_params(request, _QUERY_PARAMS)
    try:
        filters, page_number, page_size_value = admin_filters.audit_filters(request)
        view = queries.list_audit_events(conn, filters, page_number, page_size_value)
    except ValueError as exc:
        raise errors.invalid_filter(str(exc)) from exc
    return models.page_payload(
        view,
        [models.AuditEventModel.from_view(item) for item in view.items],
    )
