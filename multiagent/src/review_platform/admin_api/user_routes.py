"""Man Nguoi dung cho Console API - man rui ro cao nhat cua Console.

No tao tai khoan, doi quyen, va khoa nguoi. Nam dieu khong duoc noi long:

1. CHI admin. Viewer va operator bi chan o server, khong phai chi an nut.
2. Mat khau tam tra ve kem Cache-Control: no-store. Mot mat khau con dung
   duoc ma nam trong bo nho dem cua proxy hay trinh duyet la ban sao khong ai
   kiem soat.
3. Khong truong nao lien quan toi mat khau duoc ra khoi day - xem UserModel.
4. Admin active CUOI CUNG khong the bi ha quyen hay khoa. `users.set_role` va
   `users.set_active` tu kiem (co khoa row), o day chi dich loi sang 409 va
   ghi so kiem toan.
5. Dat lai mat khau thu hoi moi phien dang mo cua nguoi do - `users` lo do.
"""
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import queries
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth import audit_log, users
from review_platform.auth.rbac import Role


_QUERY_PARAMS = frozenset({"page", "page_size"})

router = APIRouter()


def _temporary_password() -> str:
    # token_urlsafe(18) = 144 bit tu nguon ngau nhien an toan.
    return secrets.token_urlsafe(18)


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"


def _target(conn, raw_id: str):
    """ID sai dinh dang va ID khong ton tai tra 404 GIONG NHAU.

    Phan biet hai truong hop la lo ra rang ID nao dung dinh dang - du de do
    dan mot danh sach tai khoan.
    """
    try:
        user_id = UUID(raw_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise errors.not_found("Không tìm thấy người dùng") from exc
    try:
        return users.get_user(conn, user_id)
    except users.UserNotFoundError as exc:
        raise errors.not_found("Không tìm thấy người dùng") from exc


def _parsed_role(raw: str) -> Role:
    try:
        return Role(raw)
    except ValueError as exc:
        raise errors.ConsoleError(
            400, "invalid_role", "Quyền không hợp lệ", "role"
        ) from exc


def _audit(conn, *, action, actor, target, metadata=None):
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


def _last_admin(conn, *, actor, target, operation: str) -> errors.ConsoleError:
    """Ghi lai lan tu choi roi tra loi de route nem.

    Ghi ca lan bi TU CHOI, khong chi lan thanh cong: mot chuoi nhieu lan thu
    ha quyen admin cuoi cung la thu can nhin thay khi truy su co.
    """
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
    return errors.ConsoleError(
        409,
        "last_active_admin",
        "Không thể hạ quyền hoặc khoá admin đang hoạt động cuối cùng",
    )


@router.get("/users", response_model=models.UserPage)
def list_users(
    request: Request,
    page: str | None = Query(None, description="mac dinh 1"),
    page_size: str | None = Query(None, description="mac dinh 25, toi da 100"),
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    dependencies.reject_unknown_query_params(request, _QUERY_PARAMS)
    try:
        view = queries.list_users(
            conn,
            page=int(page) if page is not None else 1,
            page_size=int(page_size) if page_size is not None else 25,
        )
    except ValueError as exc:
        raise errors.invalid_filter(f"Phân trang không hợp lệ. {exc}") from exc
    return models.page_payload(
        view, [models.UserModel.from_view(item) for item in view.items]
    )


@router.post(
    "/users",
    response_model=models.TemporaryPasswordResponse,
    status_code=201,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def create_user(
    payload: models.CreateUserRequest,
    response: Response,
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    role = _parsed_role(payload.role)
    mat_khau = _temporary_password()
    actor = resolved.user
    try:
        with conn.transaction():
            created = users.create_user(
                conn,
                payload.username,
                mat_khau,
                role,
                created_by=actor.id,
                # Mat khau tam do NGUOI KHAC biet, nen no chi duoc dung mot
                # lan de vao va doi ngay.
                must_change_password=True,
            )
            _audit(
                conn,
                action=audit_log.AuditAction.USER_CREATED,
                actor=actor,
                target=created,
                metadata={"role": created.role.value},
            )
    except users.UsernameConflictError as exc:
        raise errors.ConsoleError(
            409, "conflict", "Tên đăng nhập đã tồn tại", "username"
        ) from exc
    except ValueError as exc:
        raise errors.ConsoleError(
            400, "invalid_payload", f"Không thể tạo người dùng. {exc}", "username"
        ) from exc

    _no_store(response)
    return models.TemporaryPasswordResponse(
        user=models.UserModel.from_view(created), temporary_password=mat_khau
    )


@router.post(
    "/users/{user_id}/role",
    response_model=models.UserModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def change_role(
    user_id: str,
    payload: models.ChangeRoleRequest,
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    target = _target(conn, user_id)
    role = _parsed_role(payload.role)
    actor = resolved.user
    try:
        with conn.transaction():
            updated = users.set_role(conn, target.id, role)
            _audit(
                conn,
                action=audit_log.AuditAction.USER_ROLE_CHANGED,
                actor=actor,
                target=updated,
                metadata={
                    "old_role": target.role.value,
                    "new_role": updated.role.value,
                },
            )
    except users.LastActiveAdminError as exc:
        raise _last_admin(
            conn, actor=actor, target=target, operation="set-role"
        ) from exc
    return models.UserModel.from_view(updated)


def _set_active(conn, resolved, user_id: str, *, active: bool):
    target = _target(conn, user_id)
    actor = resolved.user
    try:
        with conn.transaction():
            updated = users.set_active(conn, target.id, active)
            _audit(
                conn,
                action=(
                    audit_log.AuditAction.USER_UNLOCKED
                    if active
                    else audit_log.AuditAction.USER_LOCKED
                ),
                actor=actor,
                target=updated,
            )
    except users.LastActiveAdminError as exc:
        raise _last_admin(
            conn,
            actor=actor,
            target=target,
            operation="unlock" if active else "lock",
        ) from exc
    return models.UserModel.from_view(updated)


@router.post(
    "/users/{user_id}/lock",
    response_model=models.UserModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def lock_user(
    user_id: str,
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    return _set_active(conn, resolved, user_id, active=False)


@router.post(
    "/users/{user_id}/unlock",
    response_model=models.UserModel,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def unlock_user(
    user_id: str,
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    return _set_active(conn, resolved, user_id, active=True)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=models.TemporaryPasswordResponse,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def reset_password(
    user_id: str,
    response: Response,
    resolved=Depends(dependencies.require_console_role(Role.ADMIN)),
    conn=Depends(admin_dependencies.get_db),
):
    target = _target(conn, user_id)
    mat_khau = _temporary_password()
    with conn.transaction():
        # users.reset_password tu thu hoi moi phien dang mo cua nguoi do.
        updated = users.reset_password(conn, target.id, mat_khau)
        _audit(
            conn,
            action=audit_log.AuditAction.PASSWORD_RESET,
            actor=resolved.user,
            target=updated,
        )
    _no_store(response)
    return models.TemporaryPasswordResponse(
        user=models.UserModel.from_view(updated), temporary_password=mat_khau
    )
