"""Bien HTTP: correlation ID tin cay, security header va exception an toan.

Ba nguyen tac o day:

1. **Correlation ID do SERVER sinh.** Client gui `X-Request-ID` thi bo qua
   hoan toan. Tin ID cua client nghia la ke tan cong tu chon ID de trung voi
   ID cua request khac, lam nhat ky truy vet khong con truy vet duoc gi.

2. **Exception khong bao gio ra ngoai nguyen ban.** Traceback chua duong dan,
   ten bien, doi khi ca doan SQL. Client chi nhan mot ma chung + correlation
   ID de doi chieu voi log ben trong.

3. **Header bat theo moi truong.** `Strict-Transport-Security` CHI bat khi
   VF_HTTPS_ONLY=1: bat no tren HTTP local la noi doi voi trinh duyet, va se
   khoa chinh may dev vao HTTPS trong 6 thang.
"""
import json
import os
import uuid
from contextvars import ContextVar


CORRELATION_HEADER = "X-Correlation-ID"

_correlation: ContextVar[str | None] = ContextVar("correlation_id", default=None)

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; "
    "form-action 'self'"
)

HEADER_BAO_MAT = {
    "Content-Security-Policy": CSP,
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

MAX_ADMIN_BODY = 65536


def correlation_hien_tai() -> str | None:
    return _correlation.get()


def https_only(environ=None) -> bool:
    return (environ or os.environ).get("VF_HTTPS_ONLY") == "1"


def header_cho_response(*, path: str, environ=None) -> dict:
    """Header bao mat. Trang admin them no-store; HSTS chi khi that su HTTPS."""
    headers = dict(HEADER_BAO_MAT)
    if path.startswith("/admin"):
        headers["Cache-Control"] = "no-store"
    if https_only(environ):
        headers["Strict-Transport-Security"] = "max-age=15768000; includeSubDomains"
    return headers


class SecurityMiddleware:
    """ASGI middleware: correlation ID + header + exception an toan.

    Viet o tang ASGI thay vi BaseHTTPMiddleware de khong buffer toan bo
    response - dashboard va trang danh sach co the tra vai tram KB HTML.
    """

    def __init__(self, app, *, environ=None):
        self.app = app
        self.environ = environ or os.environ

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        # BO QUA X-Request-ID cua client. ID phai do server sinh moi tin duoc.
        correlation = str(uuid.uuid4())
        token = _correlation.set(correlation)
        headers = header_cho_response(path=path, environ=self.environ)
        da_bat_dau = False

        async def send_them_header(message):
            nonlocal da_bat_dau
            if message["type"] == "http.response.start":
                da_bat_dau = True
                raw = list(message.get("headers") or [])
                san_co = {ten.lower() for ten, _ in raw}
                for ten, gia_tri in headers.items():
                    if ten.lower().encode() not in san_co:
                        raw.append((ten.encode(), gia_tri.encode()))
                raw.append((CORRELATION_HEADER.encode(), correlation.encode()))
                message = {**message, "headers": raw}
            await send(message)

        try:
            await self.app(scope, receive, send_them_header)
        except Exception:
            if da_bat_dau:
                # Response da bat dau gui - khong the thay bang 500 nua.
                raise
            await self._tra_500(send, correlation, path)
        finally:
            _correlation.reset(token)

    async def _tra_500(self, send, correlation: str, path: str) -> None:
        if path.startswith("/admin"):
            body = (
                "<!doctype html><meta charset=\"utf-8\">"
                "<title>Lỗi hệ thống</title>"
                "<h1>Đã xảy ra lỗi</h1>"
                "<p>Mã đối chiếu: <code>" + correlation + "</code></p>"
            ).encode("utf-8")
            content_type = b"text/html; charset=utf-8"
        else:
            body = json.dumps(
                {"code": "internal_error", "correlation_id": correlation}
            ).encode("utf-8")
            content_type = b"application/json"

        raw = [
            (b"content-type", content_type),
            (b"content-length", str(len(body)).encode("ascii")),
            (CORRELATION_HEADER.encode(), correlation.encode()),
        ]
        for ten, gia_tri in HEADER_BAO_MAT.items():
            raw.append((ten.encode(), gia_tri.encode()))
        await send({"type": "http.response.start", "status": 500, "headers": raw})
        await send({"type": "http.response.body", "body": body})
