"""Trang ket noi Drupal: xem trang thai, test connection, tam dung/mo intake.

Nguyen tac o day: viewer XEM duoc nhung khong BAM duoc. An nut khong phai la
phan quyen - moi thao tac deu kiem role o server, co CSRF va co audit.

Test connection KHONG goi result callback: mot lan bam nut chan doan khong
duoc phep tao revision moi tren bai cua nguoi ta.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from review_platform import sites
from review_platform.admin import dependencies, rendering
from review_platform.auth import audit_log
from review_platform.auth.rbac import Role, allows
from review_platform.connectors import base as connector_base


router = APIRouter()

MAX_REASON = 300


@dataclass(frozen=True)
class ConnectionView:
    slug: str
    name: str
    base_url: str
    secret_ref: str
    active: bool
    intake_paused: bool
    profile_code: str | None
    policy_version: str | None
    token_prefixes: tuple
    last_health_status: str | None
    last_health_checked_at: datetime | None
    last_health_error: str | None


def _connection_factory(conn, site_id):
    from review_platform.connectors.factory import connector_cho_site

    return connector_cho_site(conn, site_id)


def _view(conn) -> ConnectionView | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.slug, s.name, s.base_url, s.secret_ref, s.active, "
            "s.intake_paused, s.last_health_status, s.last_health_checked_at, "
            "s.last_health_error, p.code, p.policy_version "
            "FROM site AS s "
            "LEFT JOIN site_profile_assignment AS a "
            "  ON a.site_id=s.id AND a.active "
            "LEFT JOIN review_profile AS p "
            "  ON p.id=a.profile_id AND p.status='active' "
            "ORDER BY s.slug LIMIT 1"
        )
        row = cur.fetchone()
    if row is None:
        return None

    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.token_prefix FROM site_api_credential AS c "
            "JOIN site AS s ON s.id=c.site_id "
            "WHERE s.slug=%s AND c.active ORDER BY c.created_at",
            (row[0],),
        )
        prefixes = tuple(item[0] for item in cur.fetchall())

    return ConnectionView(
        slug=row[0],
        name=row[1],
        base_url=row[2],
        secret_ref=row[3],
        active=row[4],
        intake_paused=row[5],
        last_health_status=row[6],
        last_health_checked_at=row[7],
        last_health_error=row[8],
        profile_code=row[9],
        policy_version=row[10],
        token_prefixes=prefixes,
    )


def _render(request, resolved, view, *, error=None, notice=None, status_code=200):
    return rendering.render_template(
        request,
        "connection.html",
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        connection=view,
        can_operate=allows(resolved.user.role, Role.OPERATOR),
        error=error,
        notice=notice,
    )


@router.get("/connection", response_class=HTMLResponse)
def connection_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    return _render(request, resolved, _view(conn))


def _site_row(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, slug FROM site ORDER BY slug LIMIT 1")
        return cur.fetchone()


@router.post(
    "/connection/test",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def test_connection(
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.OPERATOR)),
    conn=Depends(dependencies.get_db),
):
    row = _site_row(conn)
    if row is None:
        return _render(request, resolved, None, error="Chưa cấu hình site nào.",
                       status_code=404)
    site_id, slug = row

    # Goi qua bien module de test thay duoc; KHONG dat lam tham so cua route,
    # neu khong FastAPI se coi no la query param va client tu chon duoc
    # connector factory.
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
            actor_user_id=actor.id,
            actor_username=actor.username,
            target_type="site",
            target_id=str(site_id),
            outcome="success" if health.ok else "failed",
            metadata={
                "site_slug": slug,
                "ok": health.ok,
                "error_code": health.error_code,
            },
        )

    view = _view(conn)
    if health.ok:
        return _render(request, resolved, view,
                       notice="Kết nối đạt: đủ feed, result callback và đọc đúng revision.")
    return _render(
        request,
        resolved,
        view,
        error=f"Kết nối chưa đạt (mã: {health.error_code}).",
        status_code=200,
    )


def _doi_intake(conn, actor, *, tam_dung: bool, reason: str | None):
    row = _site_row(conn)
    if row is None:
        return None
    site_id, slug = row
    with conn.transaction():
        with conn.cursor() as cur:
            # Khoa row de hai lan bam song song khong ghi de nhau.
            cur.execute("SELECT id FROM site WHERE id=%s FOR UPDATE", (site_id,))
            cur.execute(
                "UPDATE site SET intake_paused=%s, updated_at=now() WHERE id=%s",
                (tam_dung, site_id),
            )
        audit_log.write_event(
            conn,
            action=(
                audit_log.AuditAction.INTAKE_PAUSED if tam_dung
                else audit_log.AuditAction.INTAKE_RESUMED
            ),
            actor_user_id=actor.id,
            actor_username=actor.username,
            target_type="site",
            target_id=str(site_id),
            outcome="success",
            metadata={"site_slug": slug, "reason": (reason or "")[:MAX_REASON] or None},
        )
    return slug


@router.post(
    "/connection/pause",
    dependencies=[Depends(dependencies.require_csrf)],
)
def pause_intake(
    reason: str | None = Form(default=None),
    actor=Depends(dependencies.require_role(Role.OPERATOR)),
    conn=Depends(dependencies.get_db),
):
    _doi_intake(conn, actor, tam_dung=True, reason=reason)
    return RedirectResponse("/admin/connection", status_code=303)


@router.post(
    "/connection/resume",
    dependencies=[Depends(dependencies.require_csrf)],
)
def resume_intake(
    reason: str | None = Form(default=None),
    actor=Depends(dependencies.require_role(Role.OPERATOR)),
    conn=Depends(dependencies.get_db),
):
    _doi_intake(conn, actor, tam_dung=False, reason=reason)
    return RedirectResponse("/admin/connection", status_code=303)
