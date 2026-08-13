"""Admin-only routes quan ly tai khoan Platform Admin."""
import secrets
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from review_platform.admin import dependencies, queries, rendering
from review_platform.auth import audit_log, users
from review_platform.auth.rbac import Role


router = APIRouter()


def _generate_temporary_password() -> str:
    return secrets.token_urlsafe(18)


def _admin_context(
    request: Request,
    resolved,
    *,
    status_code: int = 200,
    **context,
):
    return rendering.render_template(
        request,
        context.pop("template"),
        status_code=status_code,
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        **context,
    )


def _parse_uuid(raw: str) -> UUID | None:
    try:
        return UUID(raw)
    except (ValueError, TypeError, AttributeError):
        return None


def _target(conn, raw_id: str):
    user_id = _parse_uuid(raw_id)
    if user_id is None:
        return None
    try:
        return users.get_user(conn, user_id)
    except users.UserNotFoundError:
        return None


def _list_url(page: int, page_size: int) -> str:
    return f"/admin/users?{urlencode({'page': page, 'page_size': page_size})}"


@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    del actor
    try:
        raw_page = request.query_params.get("page", "1")
        raw_size = request.query_params.get("page_size", "25")
        if not raw_page.isascii() or not raw_page.isdigit():
            raise ValueError("page khong hop le")
        if not raw_size.isascii() or not raw_size.isdigit():
            raise ValueError("page_size khong hop le")
        page = queries.list_users(
            conn,
            page=int(raw_page),
            page_size=int(raw_size),
        )
    except ValueError as exc:
        return _admin_context(
            request,
            resolved,
            template="users.html",
            status_code=422,
            page=None,
            error=f"Phân trang không hợp lệ. {exc}",
            previous_url=None,
            next_url=None,
        )
    return _admin_context(
        request,
        resolved,
        template="users.html",
        page=page,
        error=None,
        previous_url=(
            None if page.page <= 1 else _list_url(page.page - 1, page.page_size)
        ),
        next_url=(
            None
            if page.page >= page.total_pages
            else _list_url(page.page + 1, page.page_size)
        ),
    )


@router.get("/users/new", response_class=HTMLResponse)
def new_user_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
):
    del actor
    return _admin_context(
        request,
        resolved,
        template="user_form.html",
        error=None,
        roles=tuple(role.value for role in Role),
    )


def _temporary_password_response(
    request: Request,
    resolved,
    *,
    target,
    temporary_password: str,
    status_code: int,
):
    response = _admin_context(
        request,
        resolved,
        template="user_temporary_password.html",
        status_code=status_code,
        target=target,
        temporary_password=temporary_password,
    )
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    return response


@router.post(
    "/users",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def create_user(
    request: Request,
    username: str = Form(default=""),
    role: str = Form(default=""),
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    try:
        parsed_role = Role(role)
        temporary_password = _generate_temporary_password()
        with conn.transaction():
            created = users.create_user(
                conn,
                username,
                temporary_password,
                parsed_role,
                created_by=actor.id,
                must_change_password=True,
            )
            audit_log.write_event(
                conn,
                action=audit_log.AuditAction.USER_CREATED,
                actor_user_id=actor.id,
                actor_username=actor.username,
                target_type="admin_user",
                target_id=str(created.id),
                outcome="success",
                metadata={"role": created.role.value},
            )
    except (ValueError, users.UsernameConflictError) as exc:
        return _admin_context(
            request,
            resolved,
            template="user_form.html",
            status_code=400,
            error=f"Không thể tạo người dùng. {exc}",
            roles=tuple(role.value for role in Role),
        )
    return _temporary_password_response(
        request,
        resolved,
        target=created,
        temporary_password=temporary_password,
        status_code=201,
    )


def _write_success_audit(conn, *, action, actor, target, metadata=None):
    audit_log.write_event(
        conn,
        action=action,
        actor_user_id=actor.id,
        actor_username=actor.username,
        target_type="admin_user",
        target_id=str(target.id),
        outcome="success",
        metadata={} if metadata is None else metadata,
    )


def _last_admin_denied(conn, *, actor, target, operation: str):
    with conn.transaction():
        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.LAST_ADMIN_DENIED,
            actor_user_id=actor.id,
            actor_username=actor.username,
            target_type="admin_user",
            target_id=str(target.id),
            outcome="denied",
            metadata={"operation": operation},
        )


def _not_found(request: Request, resolved):
    return _admin_context(
        request,
        resolved,
        template="user_form.html",
        status_code=404,
        error="Không tìm thấy người dùng.",
        roles=tuple(role.value for role in Role),
    )


def _mutation_error(request: Request, resolved, message: str, status_code: int):
    return _admin_context(
        request,
        resolved,
        template="user_form.html",
        status_code=status_code,
        error=message,
        roles=tuple(role.value for role in Role),
    )


@router.post(
    "/users/{user_id}/role",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def change_role(
    user_id: str,
    request: Request,
    role: str = Form(default=""),
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    target = _target(conn, user_id)
    if target is None:
        return _not_found(request, resolved)
    try:
        parsed_role = Role(role)
    except ValueError:
        return _mutation_error(request, resolved, "Role không hợp lệ.", 400)
    try:
        with conn.transaction():
            updated = users.set_role(conn, target.id, parsed_role)
            _write_success_audit(
                conn,
                action=audit_log.AuditAction.USER_ROLE_CHANGED,
                actor=actor,
                target=updated,
                metadata={
                    "old_role": target.role.value,
                    "new_role": updated.role.value,
                },
            )
    except users.LastActiveAdminError:
        _last_admin_denied(conn, actor=actor, target=target, operation="set-role")
        return _mutation_error(
            request,
            resolved,
            "Không thể hạ quyền admin active cuối cùng.",
            409,
        )
    return RedirectResponse("/admin/users", status_code=303)


def _set_active(
    user_id: str,
    request: Request,
    resolved,
    actor,
    conn,
    *,
    active: bool,
):
    target = _target(conn, user_id)
    if target is None:
        return _not_found(request, resolved)
    operation = "unlock" if active else "lock"
    action = (
        audit_log.AuditAction.USER_UNLOCKED
        if active
        else audit_log.AuditAction.USER_LOCKED
    )
    try:
        with conn.transaction():
            updated = users.set_active(conn, target.id, active)
            _write_success_audit(
                conn,
                action=action,
                actor=actor,
                target=updated,
            )
    except users.LastActiveAdminError:
        _last_admin_denied(conn, actor=actor, target=target, operation=operation)
        return _mutation_error(
            request,
            resolved,
            "Không thể khóa admin active cuối cùng.",
            409,
        )
    return RedirectResponse("/admin/users", status_code=303)


@router.post(
    "/users/{user_id}/lock",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def lock_user(
    user_id: str,
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    return _set_active(
        user_id,
        request,
        resolved,
        actor,
        conn,
        active=False,
    )


@router.post(
    "/users/{user_id}/unlock",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def unlock_user(
    user_id: str,
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    return _set_active(
        user_id,
        request,
        resolved,
        actor,
        conn,
        active=True,
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def reset_password(
    user_id: str,
    request: Request,
    resolved=Depends(dependencies.current_session),
    actor=Depends(dependencies.require_role(Role.ADMIN)),
    conn=Depends(dependencies.get_db),
):
    target = _target(conn, user_id)
    if target is None:
        return _not_found(request, resolved)
    temporary_password = _generate_temporary_password()
    with conn.transaction():
        updated = users.reset_password(conn, target.id, temporary_password)
        _write_success_audit(
            conn,
            action=audit_log.AuditAction.PASSWORD_RESET,
            actor=actor,
            target=updated,
        )
    return _temporary_password_response(
        request,
        resolved,
        target=updated,
        temporary_password=temporary_password,
        status_code=200,
    )
