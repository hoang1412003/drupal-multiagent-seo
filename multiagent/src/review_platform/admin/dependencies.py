"""Cau hinh xac thuc va ket noi DB dung chung.

Goi `admin` truoc day la giao dien quan tri Jinja2. Giao dien do da bi xoa
(2026-08-21); nhung gi con lai o day la TANG DU LIEU va CAU HINH ma Console
React dung. Ten goi giu nguyen de khoi phai doi hang chuc cho import.

Rieng cac dependency cua FastAPI (kiem phien, kiem role, kiem CSRF) thi KHONG
con o day: ban cua Jinja2 tra ve redirect 303, khong dung cho mot API JSON.
Console co ban rieng trong `admin_api/dependencies.py`.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import hmac
import os

from fastapi import HTTPException, Request

from review_platform import database as platform_database


SESSION_COOKIE = "vf_admin_session"
# Cookie phai gui duoc toi /api/console/v1 va /console, khong chi /admin.
SESSION_COOKIE_PATH = "/"
# Cookie cu con sot tren trinh duyet cua nguoi dang dang nhap luc trien khai.
# Phai xoa o ca hai duong dan: neu khong, trinh duyet giu HAI cookie trung ten
# va Starlette chi tra ve mot cai khong xac dinh.
LEGACY_SESSION_COOKIE_PATH = "/admin"
class AuthConfigError(RuntimeError):
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
