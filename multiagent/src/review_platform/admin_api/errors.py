"""Hinh dang loi duy nhat cho Console API.

Vi sao chi mot hinh dang: frontend do mot agent khac viet dua tren openapi.json.
Moi endpoint tra loi theo kieu rieng se sinh ra bay nhieu cho xu ly loi khac
nhau ben frontend, va agent do khong co cach nao biet truoc co bao nhieu kieu.
"""
from fastapi import Request
from fastapi.exception_handlers import (
    request_validation_exception_handler as _fastapi_default,
)
from fastapi.responses import JSONResponse


CONSOLE_PREFIX = "/api/console"


class ConsoleError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field


def console_error_handler(request: Request, exc: ConsoleError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
            }
        },
    )


async def validation_error_handler(request: Request, exc):
    """Doi 422 mac dinh cua FastAPI ve dung mot hinh dang loi.

    FastAPI tra {"detail": [{...}]} - hinh dang THU HAI ma frontend khong he
    biet toi, vi openapi.json khong mo ta no. UI se roi vao nhanh "loi khong
    xac dinh" ma khong hien duoc truong nao sai.

    `loc` cua FastAPI co dang ("body", "reason"); lay phan tu cuoi lam `field`
    de UI to do dung o nhap lieu.

    CHI ap dung cho /api/console. `/api/v1` la hop dong voi module Drupal dang
    chay that - doi hinh dang loi cua no la thay doi pha vo, va khong ai yeu
    cau. Duong dan khac deu tra ve xu ly mac dinh cua FastAPI.
    """
    if not request.url.path.startswith(CONSOLE_PREFIX):
        return await _fastapi_default(request, exc)

    loi = (exc.errors() or [{}])[0]
    loc = [p for p in loi.get("loc", ()) if p not in ("body", "query", "path")]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "invalid_payload",
                "message": "Dữ liệu gửi lên không hợp lệ",
                "field": str(loc[-1]) if loc else None,
            }
        },
    )


def unauthenticated() -> ConsoleError:
    return ConsoleError(401, "unauthenticated", "Chưa đăng nhập")


def forbidden(
    message: str = "Bạn không có quyền thực hiện thao tác này",
) -> ConsoleError:
    return ConsoleError(403, "forbidden", message)


def not_found(message: str = "Không tìm thấy") -> ConsoleError:
    return ConsoleError(404, "not_found", message)


def invalid_filter(message: str, field: str | None = None) -> ConsoleError:
    return ConsoleError(422, "invalid_filter", message, field)
