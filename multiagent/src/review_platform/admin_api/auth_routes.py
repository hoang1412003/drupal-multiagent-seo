"""Endpoint dang nhap/dang xuat/doi mat khau cho Console API.

Trinh tu xac thuc sao lai dung admin/router.py: throttle -> tim user ->
so sanh mat khau voi hash gia khi khong co user (chong do thoi gian) -> ghi
audit -> cap phien. Khac ba diem: nhan JSON, khong co CSRF pre-auth (SPA chua
co cookie login-csrf; chan lam dung van dua tren throttle nhu cu), va tra 200
kem danh tinh thay vi redirect 303.
"""
from fastapi import APIRouter, Depends, Request, Response

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth import audit_log, passwords, sessions, throttle, users


router = APIRouter()

_DUMMY_PASSWORD_HASH = passwords.hash_password("Dummy-password-not-a-user-2026")
_SESSION_MAX_AGE = 8 * 60 * 60


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _write_login_failure(conn, candidate, subject_hash: str, reason: str) -> None:
    audit_log.write_event(
        conn,
        action=audit_log.AuditAction.LOGIN_FAILED,
        actor_user_id=None,
        actor_username="anonymous",
        target_type="admin_user",
        target_id=str(candidate.id) if candidate else None,
        outcome="denied",
        metadata={"subject_hash": subject_hash, "reason": reason},
    )


def _set_session_cookie(response: Response, raw_token: str, config) -> None:
    response.set_cookie(
        admin_dependencies.SESSION_COOKIE,
        raw_token,
        max_age=_SESSION_MAX_AGE,
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
        path=admin_dependencies.SESSION_COOKIE_PATH,
    )
    response.delete_cookie(
        admin_dependencies.SESSION_COOKIE,
        path=admin_dependencies.LEGACY_SESSION_COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        admin_dependencies.SESSION_COOKIE,
        path=admin_dependencies.SESSION_COOKIE_PATH,
    )
    response.delete_cookie(
        admin_dependencies.SESSION_COOKIE,
        path=admin_dependencies.LEGACY_SESSION_COOKIE_PATH,
    )


def _throttled() -> errors.ConsoleError:
    return errors.ConsoleError(
        429,
        "throttled",
        "Tạm thời chưa thể đăng nhập. Vui lòng thử lại sau.",
    )


@router.post("/auth/login", response_model=models.MeResponse)
def login(
    payload: models.LoginRequest,
    request: Request,
    response: Response,
    conn=Depends(admin_dependencies.get_db),
    config=Depends(admin_dependencies.get_auth_config),
):
    ip_address = _client_ip(request)
    limiter = throttle.LoginThrottle(conn, config.throttle_key)
    decision = limiter.check(payload.username, ip_address)
    if decision.blocked:
        _write_login_failure(conn, None, decision.subject_hash, "throttled")
        raise _throttled()

    with conn.transaction():
        try:
            candidate = users.find_by_username(conn, payload.username, for_update=True)
        except ValueError:
            candidate = None
        candidate_hash = candidate.password_hash if candidate else _DUMMY_PASSWORD_HASH
        credential_ok = (
            len(payload.password) <= passwords.MAX_PASSWORD_LENGTH
            and passwords.verify_password(candidate_hash, payload.password)
        )
        active_ok = candidate is not None and candidate.active
        if not credential_ok or not active_ok:
            failed = limiter.record_failure(payload.username, ip_address)
            reason = (
                "inactive"
                if credential_ok and candidate is not None
                else "invalid_credentials"
            )
            _write_login_failure(conn, candidate, failed.subject_hash, reason)
            if failed.blocked:
                raise _throttled()
            # Mot thong bao duy nhat cho moi truong hop: khong lo ra tai khoan
            # co ton tai hay khong.
            raise errors.ConsoleError(
                401,
                "invalid_credentials",
                "Thông tin đăng nhập không hợp lệ",
            )

        limiter.record_success(payload.username, ip_address)
        issued = sessions.issue(conn, candidate.id)
        users.mark_login_success(conn, candidate.id)
        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.LOGIN_SUCCESS,
            actor_user_id=candidate.id,
            actor_username=candidate.username,
            target_type="admin_user",
            target_id=str(candidate.id),
            outcome="success",
            metadata={"subject_hash": decision.subject_hash},
        )

    _set_session_cookie(response, issued.raw_token, config)
    return models.MeResponse(
        username=candidate.username,
        role=candidate.role.value,
        must_change_password=candidate.must_change_password,
        csrf_token=issued.csrf_token,
    )


@router.get("/auth/me", response_model=models.MeResponse)
def me(resolved=Depends(dependencies.console_session)):
    return models.MeResponse(
        username=resolved.user.username,
        role=resolved.user.role.value,
        must_change_password=resolved.must_change_password,
        csrf_token=resolved.csrf_token,
    )


@router.post(
    "/auth/logout",
    status_code=204,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def logout(
    request: Request,
    response: Response,
    resolved=Depends(dependencies.console_session),
    conn=Depends(admin_dependencies.get_db),
):
    raw_token = request.cookies.get(admin_dependencies.SESSION_COOKIE, "")
    with conn.transaction():
        sessions.revoke(conn, raw_token, "logout")
        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.LOGOUT,
            actor_user_id=resolved.user.id,
            actor_username=resolved.user.username,
            target_type="admin_session",
            target_id=str(resolved.session_id),
            outcome="success",
            metadata={"session_id": str(resolved.session_id)},
        )
    # Dat cookie tren `response` da tiem vao roi tra None: FastAPI se gop
    # raw_headers cua no vao response cuoi. KHONG duoc tu tao Response va copy
    # bang dict(response.headers) - dict gop nhieu header set-cookie thanh mot
    # nen chi mot trong hai lenh xoa song sot.
    _clear_session_cookie(response)
    return None


@router.post(
    "/auth/change-password",
    status_code=204,
    dependencies=[Depends(dependencies.require_console_csrf)],
)
def change_password(
    payload: models.ChangePasswordRequest,
    response: Response,
    resolved=Depends(dependencies.console_session),
    conn=Depends(admin_dependencies.get_db),
):
    try:
        users.change_password(
            conn,
            resolved.user.id,
            payload.current_password,
            payload.new_password,
        )
    except (passwords.PasswordPolicyError, users.InvalidCurrentPasswordError) as exc:
        # Mot ma loi duy nhat: khong noi ro la mat khau cu sai hay mat khau moi
        # yeu, de khong bien endpoint nay thanh cong cu do mat khau.
        raise errors.ConsoleError(
            400,
            "password_rejected",
            "Không thể đổi mật khẩu. Kiểm tra lại mật khẩu hiện tại, và mật khẩu mới phải có ít nhất 12 ký tự.",
        ) from exc

    with conn.transaction():
        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.PASSWORD_CHANGED,
            actor_user_id=resolved.user.id,
            actor_username=resolved.user.username,
            target_type="admin_user",
            target_id=str(resolved.user.id),
            outcome="success",
            metadata={},
        )
        # Doi mat khau huy MOI phien, ke ca phien hien tai: neu mat khau cu da
        # lo thi phien mo bang no khong duoc song tiep.
        sessions.revoke_all_for_user(conn, resolved.user.id, "password_changed")

    _clear_session_cookie(response)
    return None
