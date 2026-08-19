"""Pydantic model cho Console API.

Quy uoc chuyen kieu, ap dung nhat quan o moi model:
- UUID     -> str
- datetime -> chuoi ISO-8601 UTC ket thuc bang "Z" (dung `iso`)
- date     -> chuoi "YYYY-MM-DD"
- Decimal  -> so JSON (dung `to_number`). KHONG khai bao truong la Decimal:
  Pydantic v2 serialize Decimal thanh CHUOI, frontend se nhan "82.5" thay vi
  82.5 va moi phep so sanh so ben React deu sai am tham.
- None     -> null, khong doi thanh chuoi rong.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def to_number(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


class MeResponse(BaseModel):
    username: str
    role: str
    must_change_password: bool
    csrf_token: str


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = ""
    new_password: str = ""
