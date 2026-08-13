"""Login/logout/home/change-password routes cho Platform Admin MVP."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from review_platform.admin import dashboard_routes, dependencies, rendering
from review_platform.auth import audit_log, csrf, passwords, sessions, throttle, users


SESSION_COOKIE = dependencies.SESSION_COOKIE
LOGIN_CSRF_COOKIE = "vf_admin_login_csrf"
FLASH_COOKIE = "vf_admin_flash"
TEMPLATE_DIR = rendering.TEMPLATE_DIR
STATIC_DIR = rendering.STATIC_DIR

router = APIRouter(prefix="/admin", tags=["admin"])
templates = rendering.templates

_DUMMY_PASSWORD_HASH = passwords.hash_password("Dummy-password-not-a-user-2026")


def _template(request: Request, name: str, *, status_code=200, **context):
    return rendering.render_template(
        request,
        name,
        status_code=status_code,
        **context,
    )


def _set_login_csrf(response, token: str, config: dependencies.AuthConfig) -> None:
    response.set_cookie(
        LOGIN_CSRF_COOKIE,
        token,
        max_age=600,
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/admin/login",
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _login_error(request: Request, status_code: int, message: str):
    return _template(
        request,
        "login.html",
        status_code=status_code,
        csrf_token=request.cookies.get(LOGIN_CSRF_COOKIE, ""),
        error=message,
        flash=None,
    )


def forbidden_response(request: Request, exc: dependencies.AdminForbidden):
    resolved = getattr(request.state, "admin_session", None)
    return _template(
        request,
        "403.html",
        status_code=403,
        user=resolved.user if resolved else None,
        csrf_token=resolved.csrf_token if resolved else "",
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    config=Depends(dependencies.get_auth_config),
):
    flash = (
        "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."
        if request.cookies.get(FLASH_COOKIE) == "password_changed"
        else None
    )
    token = csrf.issue_login_csrf(config.csrf_key)
    response = _template(
        request,
        "login.html",
        csrf_token=token,
        error=None,
        flash=flash,
    )
    _set_login_csrf(response, token, config)
    if flash:
        response.delete_cookie(FLASH_COOKIE, path="/admin/login")
    return response


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(default=""),
    password: str = Form(default=""),
    csrf_token: str = Form(default=""),
    conn=Depends(dependencies.get_db),
    config=Depends(dependencies.get_auth_config),
):
    if not csrf.verify_login_csrf(
        request.cookies.get(LOGIN_CSRF_COOKIE),
        csrf_token,
        config.csrf_key,
    ):
        return _login_error(request, 403, "Yêu cầu không hợp lệ. Vui lòng thử lại.")

    ip_address = _client_ip(request)
    limiter = throttle.LoginThrottle(conn, config.throttle_key)
    decision = limiter.check(username, ip_address)
    if decision.blocked:
        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.LOGIN_FAILED,
            actor_user_id=None,
            actor_username="anonymous",
            target_type="admin_user",
            target_id=None,
            outcome="denied",
            metadata={"subject_hash": decision.subject_hash, "reason": "throttled"},
        )
        return _login_error(
            request,
            429,
            "Tạm thời chưa thể đăng nhập. Vui lòng thử lại sau.",
        )

    with conn.transaction():
        try:
            candidate = users.find_by_username(conn, username, for_update=True)
        except ValueError:
            candidate = None
        candidate_hash = candidate.password_hash if candidate else _DUMMY_PASSWORD_HASH
        credential_ok = (
            len(password) <= passwords.MAX_PASSWORD_LENGTH
            and passwords.verify_password(candidate_hash, password)
        )
        active_ok = candidate is not None and candidate.active
        if not credential_ok or not active_ok:
            failed = limiter.record_failure(username, ip_address)
            reason = (
                "inactive"
                if credential_ok and candidate is not None
                else "invalid_credentials"
            )
            audit_log.write_event(
                conn,
                action=audit_log.AuditAction.LOGIN_FAILED,
                actor_user_id=None,
                actor_username="anonymous",
                target_type="admin_user",
                target_id=str(candidate.id) if candidate else None,
                outcome="denied",
                metadata={"subject_hash": failed.subject_hash, "reason": reason},
            )
            if failed.blocked:
                return _login_error(
                    request,
                    429,
                    "Tạm thời chưa thể đăng nhập. Vui lòng thử lại sau.",
                )
            return _login_error(
                request,
                401,
                "Thông tin đăng nhập không hợp lệ. Vui lòng thử lại.",
            )

        limiter.record_success(username, ip_address)
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
        destination = (
            "/admin/change-password"
            if candidate.must_change_password
            else "/admin"
        )
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        issued.raw_token,
        max_age=8 * 60 * 60,
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/admin",
    )
    response.delete_cookie(LOGIN_CSRF_COOKIE, path="/admin/login")
    return response


@router.post("/logout", dependencies=[Depends(dependencies.require_csrf)])
def logout(
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    raw_token = request.cookies.get(SESSION_COOKIE, "")
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
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/admin")
    return response


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
):
    return _template(
        request,
        "change_password.html",
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        error=None,
    )


@router.post(
    "/change-password",
    response_class=HTMLResponse,
    dependencies=[Depends(dependencies.require_csrf)],
)
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
    config=Depends(dependencies.get_auth_config),
):
    try:
        with conn.transaction():
            if new_password != confirm_password:
                raise passwords.PasswordPolicyError("password confirmation mismatch")
            users.change_password(
                conn,
                resolved.user.id,
                current_password,
                new_password,
            )
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
    except (passwords.PasswordPolicyError, users.InvalidCurrentPasswordError):
        return _template(
            request,
            "change_password.html",
            status_code=400,
            user=resolved.user,
            csrf_token=resolved.csrf_token,
            error="Không thể đổi mật khẩu. Vui lòng kiểm tra thông tin và thử lại.",
        )

    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/admin")
    response.set_cookie(
        FLASH_COOKIE,
        "password_changed",
        max_age=60,
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/admin/login",
    )
    return response


router.add_api_route(
    "",
    dashboard_routes.dashboard_page,
    methods=["GET"],
    response_class=HTMLResponse,
)
router.include_router(dashboard_routes.router)
