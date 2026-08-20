"""Endpoint doc ket qua review cho Console API.

Bao mat: agent_results bat nguon tu output cua model. `queries.get_review` da
chay sanitization (che bi mat, gioi han do sau/so phan tu/do dai) va cat con 4
agent. Route nay CHI anh xa sang Pydantic - khong duoc doc lai du lieu tho tu
run_log, va khong duoc noi lai gioi han.

Escape HTML khong phai viec o day: React escape mac dinh. Quy tac tuong ung
ben frontend la cam dangerouslySetInnerHTML.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin import review_routes as legacy_reviews
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth.rbac import Role


_QUERY_PARAMS = frozenset({
    "decision", "site", "external_id", "from", "to", "page", "page_size",
})

router = APIRouter()


def _parsed_review_id(public_id: str) -> UUID:
    try:
        return UUID(public_id)
    except ValueError as exc:
        raise errors.not_found("Không tìm thấy review") from exc


@router.get("/reviews", response_model=models.ReviewPage)
def list_reviews(
    request: Request,
    # Xem ghi chu o job_routes.list_jobs: khai bao de openapi.json ghi dung
    # ten tham so, khong rang buoc kieu de giu hinh dang loi cua Console.
    decision: str | None = Query(None, description="publish|needs_revision|rejected|unknown"),
    site: str | None = Query(None, description="slug cua site, khop chinh xac"),
    external_id: str | None = Query(None, description="khop mot phan chuoi"),
    date_from: str | None = Query(None, alias="from", description="YYYY-MM-DD"),
    date_to: str | None = Query(None, alias="to", description="phai di cung `from`"),
    page: str | None = Query(None, description="mac dinh 1"),
    page_size: str | None = Query(None, description="mac dinh 25, toi da 100"),
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    dependencies.reject_unknown_query_params(request, _QUERY_PARAMS)
    try:
        filters, page_number, page_size = legacy_reviews._filters(request)
        view = queries.list_reviews(conn, filters, page_number, page_size)
    except ValueError as exc:
        raise errors.invalid_filter(str(exc)) from exc
    return models.page_payload(
        view,
        [models.ReviewListItemModel.from_view(item) for item in view.items],
    )


@router.get("/reviews/{public_id}", response_model=models.ReviewDetailModel)
def get_review(
    public_id: str,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    review = queries.get_review(conn, _parsed_review_id(public_id))
    if review is None:
        raise errors.not_found("Không tìm thấy review")
    return models.ReviewDetailModel.from_view(review)
