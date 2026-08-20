"""Dependency phien rieng cho Console API.

KHONG dung lai admin.dependencies.current_session: ham do raise redirect 303
sang /admin/login. Fetch cua trinh duyet tu di theo redirect, nen SPA se nhan
HTML trang dang nhap voi ma 200 thay vi 401 va khong biet minh da mat phien.
"""
from fastapi import Depends, Request

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors
from review_platform.auth import csrf, sessions
from review_platform.auth.rbac import Role, allows


# Endpoint van phuc vu duoc khi tai khoan dang bi buoc doi mat khau.
# /auth/me PHAI nam trong day: do la cach SPA biet can hien form doi mat khau.
_MUST_CHANGE_ALLOWED = frozenset({
    "/api/console/v1/auth/me",
    "/api/console/v1/auth/change-password",
    "/api/console/v1/auth/logout",
})


def console_session(
    request: Request,
    conn=Depends(admin_dependencies.get_db),
) -> sessions.ResolvedSession:
    raw_token = request.cookies.get(admin_dependencies.SESSION_COOKIE)
    if not raw_token:
        raise errors.unauthenticated()
    resolved = sessions.resolve(conn, raw_token)
    if resolved is None:
        raise errors.unauthenticated()
    if not resolved.user.active:
        sessions.revoke(conn, raw_token, "user_inactive")
        raise errors.unauthenticated()
    if (
        resolved.must_change_password
        and request.url.path not in _MUST_CHANGE_ALLOWED
    ):
        raise errors.ConsoleError(
            403,
            "must_change_password",
            "Bạn phải đổi mật khẩu trước khi sử dụng hệ thống",
        )
    sessions.touch(conn, raw_token)
    request.state.console_session = resolved
    return resolved


def require_console_role(required: Role):
    required = Role(required)

    def dependency(resolved=Depends(console_session)):
        if not allows(resolved.user.role, required):
            raise errors.forbidden()
        return resolved

    return dependency


def require_console_csrf(
    request: Request,
    resolved=Depends(console_session),
) -> None:
    supplied = request.headers.get("X-CSRF-Token")
    if not csrf.verify_session_csrf(resolved.csrf_token, supplied):
        raise errors.ConsoleError(403, "csrf_invalid", "Yêu cầu không hợp lệ. Vui lòng tải lại trang.")


def reject_unknown_query_params(request: Request, allowed: frozenset[str]) -> None:
    """Tu choi tham so truy van khong co trong hop dong.

    Mac dinh cua FastAPI la BO QUA tham so la. Voi mot API ma frontend do agent
    khac viet, bo qua im lang la bay: go sai ten thi bo loc "chay" ma khong loc
    gi ca, va khong co dau hieu nao. Da xay ra 2026-08-20 voi
    `external_content_id` (dung: `external_id`) va `date_from` (dung: `from`).
    """
    unknown = sorted(set(request.query_params) - allowed)
    if unknown:
        raise errors.invalid_filter(
            "Tham số lọc không hợp lệ: " + ", ".join(unknown),
            unknown[0],
        )
