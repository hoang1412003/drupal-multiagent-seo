"""Hinh dang loi duy nhat cho Console API.

Vi sao chi mot hinh dang: frontend do mot agent khac viet dua tren openapi.json.
Moi endpoint tra loi theo kieu rieng se sinh ra bay nhieu cho xu ly loi khac
nhau ben frontend, va agent do khong co cach nao biet truoc co bao nhieu kieu.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


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
