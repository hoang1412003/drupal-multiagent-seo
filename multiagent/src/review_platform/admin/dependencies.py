"""FastAPI dependencies va startup config cho Platform Admin."""
from collections.abc import Mapping
from dataclasses import dataclass
import hmac
import os

from fastapi import Depends, HTTPException, Request

from review_platform import database as platform_database
from review_platform.auth import csrf, sessions
from review_platform.auth.rbac import Role, allows


SESSION_COOKIE = "vf_admin_session"
_MUST_CHANGE_ALLOWED = frozenset({
    "/admin/change-password",
    "/admin/logout",
})


class AuthConfigError(RuntimeError):
    pass


class AdminForbidden(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthConfig:
    csrf_key: bytes
    throttle_key: bytes
    cookie_secure: bool


def _load_key(environ: Mapping[str, str], name: str) -> bytes:
    raw = environ.get(name, "")
    value = raw.encode("utf-8")
    if len(value) < 32:
        raise AuthConfigError(f"{name} phải có ít nhất 32 byte UTF-8")
    return value


def load_auth_config(environ: Mapping[str, str] | None = None) -> AuthConfig:
    environ = os.environ if environ is None else environ
    csrf_key = _load_key(environ, "ADMIN_CSRF_KEY")
    throttle_key = _load_key(environ, "ADMIN_THROTTLE_KEY")
    if hmac.compare_digest(csrf_key, throttle_key):
        raise AuthConfigError("ADMIN_CSRF_KEY và ADMIN_THROTTLE_KEY phải khác nhau")
    secure_raw = environ.get("ADMIN_COOKIE_SECURE", "false").casefold()
    if secure_raw not in {"true", "false"}:
        raise AuthConfigError("ADMIN_COOKIE_SECURE phải là true hoặc false")
    return AuthConfig(csrf_key, throttle_key, secure_raw == "true")


def get_db():
    with platform_database.open_connection() as conn:
        yield conn


def get_auth_config(request: Request) -> AuthConfig:
    try:
        return request.app.state.auth_config
    except AttributeError as exc:
        raise HTTPException(500, "admin auth config chưa được khởi tạo") from exc


def _login_redirect() -> HTTPException:
    return HTTPException(303, headers={"Location": "/admin/login"})


def current_session(request: Request, conn=Depends(get_db)) -> sessions.ResolvedSession:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise _login_redirect()
    resolved = sessions.resolve(conn, raw_token)
    if resolved is None:
        raise _login_redirect()
    if not resolved.user.active:
        sessions.revoke(conn, raw_token, "user_inactive")
        raise _login_redirect()
    if (
        resolved.must_change_password
        and request.url.path not in _MUST_CHANGE_ALLOWED
    ):
        raise HTTPException(
            303,
            headers={"Location": "/admin/change-password"},
        )
    sessions.touch(conn, raw_token)
    request.state.admin_session = resolved
    return resolved


def current_user(resolved=Depends(current_session)):
    return resolved.user


def require_role(required: Role):
    required = Role(required)

    def dependency(user=Depends(current_user)):
        if not allows(user.role, required):
            raise AdminForbidden("Bạn không có quyền thực hiện thao tác này")
        return user

    return dependency


async def require_csrf(
    request: Request,
    resolved=Depends(current_session),
) -> None:
    form = await request.form()
    if not csrf.verify_session_csrf(
        resolved.csrf_token,
        form.get("csrf_token"),
    ):
        raise HTTPException(403, "CSRF token không hợp lệ")
