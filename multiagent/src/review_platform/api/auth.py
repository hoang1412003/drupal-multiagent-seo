"""Xac thuc Bearer token cua connector va suy ra site tu chinh credential.

Site KHONG bao gio duoc lay tu body request. Neu client tu khai site_id thi
mot token bi lo se doc/ghi duoc sang site khac; suy site tu credential lam
pham vi truy cap thanh thuoc tinh cua bi mat, khong phai cua payload.

CredentialError mang `reason` de audit doc duoc, nhung lop HTTP phai quy moi
reason ve cung mot 401 chung: phan biet "token sai" voi "site tat" cho client
la chi ro cho tan cong biet no dang o dau.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from uuid import UUID

from review_platform.context import SiteContext


TOKEN_BYTES = 32
PREFIX_LENGTH = 12
TOUCH_INTERVAL = timedelta(minutes=5)


class CredentialError(RuntimeError):
    """Ly do that bai danh cho audit/log noi bo, khong tra ra client."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SitePrincipal:
    site: SiteContext
    credential_id: UUID
    token_prefix: str


def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_prefix(token: str) -> str:
    """12 ky tu dau chi de thu hep danh sach ung vien truoc khi so hash."""
    return token[:PREFIX_LENGTH]


def parse_bearer(authorization: str) -> str:
    """Chi chap nhan dung `Bearer <token>`: mot khoang trang, token khac rong.

    Tach bang split(' ') khong gioi han de "Bearer  x" (hai khoang trang) va
    "Bearer a b" deu thanh malformed thay vi lot qua nho strip ngam.
    """
    if not authorization:
        raise CredentialError("missing_authorization")
    parts = authorization.split(" ")
    if len(parts) != 2:
        raise CredentialError("malformed_authorization")
    scheme, token = parts
    if scheme != "Bearer":
        raise CredentialError("unsupported_scheme")
    if not token:
        raise CredentialError("malformed_authorization")
    return token


def _site_tu_row(row) -> SiteContext:
    return SiteContext(
        id=row[3],
        slug=row[4],
        connector_type=row[5],
        base_url=row[6],
        secret_ref=row[7],
        active=row[8],
        intake_paused=row[9],
    )


def authenticate_bearer(conn, authorization: str, *, now=None) -> SitePrincipal:
    """Doi Bearer token thanh SitePrincipal, hoac nem CredentialError."""
    token = parse_bearer(authorization)
    thoi_diem = datetime.now(timezone.utc) if now is None else now
    ung_vien = hash_token(token)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.id, c.token_hash, c.last_used_at, "
            "s.id, s.slug, s.connector_type, s.base_url, s.secret_ref, "
            "s.active, s.intake_paused "
            "FROM site_api_credential AS c "
            "JOIN site AS s ON s.id = c.site_id "
            "WHERE c.active AND c.token_prefix = %s "
            "ORDER BY c.created_at",
            (token_prefix(token),),
        )
        rows = cur.fetchall()

    khop = None
    for row in rows:
        if hmac.compare_digest(row[1], ung_vien):
            khop = row
            break
    if khop is None:
        raise CredentialError("unknown_token")

    site = _site_tu_row(khop)
    if not site.active:
        raise CredentialError("site_inactive")

    last_used_at = khop[2]
    if last_used_at is None or thoi_diem - last_used_at >= TOUCH_INTERVAL:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE site_api_credential SET last_used_at=%s WHERE id=%s",
                (thoi_diem, khop[0]),
            )

    return SitePrincipal(
        site=site,
        credential_id=khop[0],
        token_prefix=token_prefix(token),
    )
