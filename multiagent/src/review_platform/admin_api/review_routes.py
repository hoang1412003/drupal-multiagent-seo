"""Endpoint doc ket qua review cho Console API.

Bao mat: agent_results bat nguon tu output cua model. `queries.get_review` da
chay sanitization (che bi mat, gioi han do sau/so phan tu/do dai) va cat con 4
agent. Route nay CHI anh xa sang Pydantic - khong duoc doc lai du lieu tho tu
run_log, va khong duoc noi lai gioi han.

Escape HTML khong phai viec o day: React escape mac dinh. Quy tac tuong ung
ben frontend la cam dangerouslySetInnerHTML.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin import review_routes as legacy_reviews
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth.rbac import Role


router = APIRouter()


def _parsed_review_id(public_id: str) -> UUID:
    try:
        return UUID(public_id)
    except ValueError as exc:
        raise errors.not_found("Review khong ton tai") from exc


@router.get("/reviews", response_model=models.ReviewPage)
def list_reviews(
    request: Request,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
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
        raise errors.not_found("Review khong ton tai")
    return models.ReviewDetailModel.from_view(review)
