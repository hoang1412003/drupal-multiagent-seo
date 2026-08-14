"""Doi `secret_ref` trong database thanh credential lay tu bien moi truong.

Database chi giu TEN bien, khong giu gia tri. Nho vay mot ban dump database
lot ra ngoai khong kem theo mat khau Drupal.

Doi lai, `secret_ref` tro thanh du lieu dieu khien viec tra os.environ - nen
no phai duoc kiem dinh dang TRUOC khi dung. Khong kiem thi mot row bi sua co
the doc bien moi truong bat ky cua tien trinh (vi du ANTHROPIC_API_KEY).
"""
from dataclasses import dataclass
import os
import re

from review_platform.connectors.base import ConnectorSecretError


SECRET_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


@dataclass(frozen=True)
class ConnectorCredentials:
    username: str
    password: str


def resolve(secret_ref: str, *, environ=None) -> ConnectorCredentials:
    moi_truong = os.environ if environ is None else environ
    if not SECRET_REF_PATTERN.fullmatch(secret_ref or ""):
        raise ConnectorSecretError(
            f"secret_ref sai dinh dang: '{secret_ref}'"
        )

    ten_user = f"{secret_ref}_USER"
    ten_password = f"{secret_ref}_PASSWORD"
    thieu = [ten for ten in (ten_user, ten_password) if not moi_truong.get(ten)]
    if thieu:
        # Chi neu TEN bien, khong bao gio neu gia tri cua bien con lai.
        raise ConnectorSecretError(
            f"thieu bien moi truong: {', '.join(thieu)}"
        )

    return ConnectorCredentials(
        username=moi_truong[ten_user],
        password=moi_truong[ten_password],
    )
