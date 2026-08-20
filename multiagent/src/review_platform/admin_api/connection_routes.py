"""Man Ket noi cho Console API: xem trang thai, chan doan, tam dung/mo intake.

Dung lai `_view` va `_doi_intake` cua admin Jinja2 de hai UI khong bao gio noi
hai chuyen khac nhau ve cung mot site.

Ba diem giu nguyen tu admin cu, khong duoc noi long:
- Viewer XEM duoc nhung khong BAM duoc, kiem o server chu khong phai an nut.
- Test connection KHONG goi result callback: mot lan bam nut chan doan khong
  duoc phep tao revision moi tren bai cua nguoi ta.
- Moi thao tac deu ghi so kiem toan.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from review_platform import sites
from review_platform.admin import connection_routes as legacy_connection
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth import audit_log
from review_platform.auth.rbac import Role
from review_platform.connectors import base as connector_base


router = APIRouter()


def _connection_factory(conn, site_id):
    # Bien cap MODULE de test thay duoc. KHONG dat lam tham so cua route: khi
    # do FastAPI coi no la query param va client tu chon duoc connector factory.
    from review_platform.connectors.factory import connector_cho_site

    return connector_cho_site(conn, site_id)


def _view_or_404(conn):
    view = legacy_connection._view(conn)
    if view is None:
        raise errors.not_found("Chưa cấu hình site nào")
    return view


def _reason(payload: models.ReasonRequest) -> str | None:
    """Tu choi ly do qua dai thay vi cat cut im lang.

    Admin cu cat o 300 ky tu khi ghi so kiem toan. Cat im lang nghia la nguoi
    van hanh viet mot doan giai thich roi so kiem toan chi giu duoc nua dau -
    dung luc can tra lai "vi sao dung intake" thi phan quan trong da mat.
    """
    reason = payload.reason
    if reason is not None and len(reason) > models.MAX_REASON:
        raise errors.ConsoleError(
            422,
            "invalid_payload",
            f"Lý do không được dài quá {models.MAX_REASON} ký tự",
            "reason",
        )
    return reason


@router.get("/connection", response_model=models.ConnectionModel)
def get_connection(
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    return models.ConnectionModel.from_view(_view_or_404(conn))


@router.post(
    "/connection/test",
    response_model=models.TestConnectionResponse,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def test_connection(
    resolved=Depends(dependencies.require_console_role(Role.OPERATOR)),
    conn=Depends(admin_dependencies.get_db),
):
    view = _view_or_404(conn)
    site_id, slug = legacy_connection._site_row(conn)

    try:
        health = _connection_factory(conn, site_id).health()
    except (connector_base.ConnectorError, sites.ContextSelectionError) as exc:
        health = connector_base.ConnectorHealth(
            ok=False,
            status_code=None,
            checked_at=datetime.now(timezone.utc),
            error_code=getattr(exc, "ma", "internal"),
        )

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE site SET last_health_status=%s, last_health_checked_at=%s, "
                "last_health_error=%s WHERE id=%s",
                (
                    "ok" if health.ok else (health.error_code or "internal"),
                    health.checked_at,
                    None if health.ok else (health.error_code or "internal"),
                    site_id,
                ),
            )
        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.CONNECTION_TESTED,
            actor_user_id=resolved.user.id,
            actor_username=resolved.user.username,
            target_type="site",
            target_id=str(site_id),
            outcome="success" if health.ok else "failed",
            metadata={
                "site_slug": slug,
                "ok": health.ok,
                "error_code": health.error_code,
            },
        )

    # 200 ke ca khi ket noi hong: thao tac chan doan DA chay xong. Tra 4xx o
    # day se khien UI hien "thao tac that bai" thay vi "ket noi chua dat" -
    # hai chuyen khac han nhau khi truy su co.
    return models.TestConnectionResponse(
        ok=health.ok,
        error_code=health.error_code,
        connection=models.ConnectionModel.from_view(legacy_connection._view(conn)),
    )


def _doi_intake(conn, resolved, payload, *, tam_dung: bool):
    _view_or_404(conn)
    reason = _reason(payload)
    legacy_connection._doi_intake(
        conn, resolved.user, tam_dung=tam_dung, reason=reason
    )
    return models.ConnectionModel.from_view(legacy_connection._view(conn))


@router.post(
    "/connection/pause",
    response_model=models.ConnectionModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def pause_intake(
    payload: models.ReasonRequest,
    resolved=Depends(dependencies.require_console_role(Role.OPERATOR)),
    conn=Depends(admin_dependencies.get_db),
):
    return _doi_intake(conn, resolved, payload, tam_dung=True)


@router.post(
    "/connection/resume",
    response_model=models.ConnectionModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def resume_intake(
    payload: models.ReasonRequest,
    resolved=Depends(dependencies.require_console_role(Role.OPERATOR)),
    conn=Depends(admin_dependencies.get_db),
):
    return _doi_intake(conn, resolved, payload, tam_dung=False)
