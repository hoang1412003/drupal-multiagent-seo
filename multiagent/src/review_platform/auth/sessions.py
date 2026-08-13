"""Opaque server-side sessions cho Platform Admin."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Callable
from uuid import UUID

from review_platform.auth.users import AdminUser, get_user


IDLE_TIMEOUT = timedelta(minutes=30)
ABSOLUTE_TIMEOUT = timedelta(hours=8)
TOUCH_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True)
class IssuedSession:
    raw_token: str
    csrf_token: str
    absolute_expires_at: datetime


@dataclass(frozen=True)
class ResolvedSession:
    session_id: UUID
    user: AdminUser
    csrf_token: str
    must_change_password: bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware_now(now_fn: Callable[[], datetime]) -> datetime:
    value = now_fn()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("session time phải là timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _token_hash(raw_token: str) -> str | None:
    try:
        return hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    except (AttributeError, UnicodeEncodeError):
        return None


def issue(
    conn,
    user_id: UUID,
    *,
    now_fn: Callable[[], datetime] = utc_now,
) -> IssuedSession:
    now = _aware_now(now_fn)
    get_user(conn, user_id)
    raw_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    absolute_expires_at = now + ABSOLUTE_TIMEOUT
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admin_session "
            "(user_id, token_hash, csrf_secret, created_at, last_seen_at, "
            "idle_expires_at, absolute_expires_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                user_id,
                _token_hash(raw_token),
                csrf_token,
                now,
                now,
                now + IDLE_TIMEOUT,
                absolute_expires_at,
            ),
        )
    return IssuedSession(raw_token, csrf_token, absolute_expires_at)


def resolve(
    conn,
    raw_token: str,
    *,
    now_fn: Callable[[], datetime] = utc_now,
) -> ResolvedSession | None:
    now = _aware_now(now_fn)
    token_hash = _token_hash(raw_token)
    if token_hash is None:
        return None
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, user_id, csrf_secret FROM admin_session "
            "WHERE token_hash=%s AND revoked_at IS NULL "
            "AND idle_expires_at>%s AND absolute_expires_at>%s",
            (token_hash, now, now),
        )
        row = cur.fetchone()
    if row is None:
        return None
    user = get_user(conn, row[1])
    return ResolvedSession(
        session_id=row[0],
        user=user,
        csrf_token=row[2],
        must_change_password=user.must_change_password,
    )


def touch(
    conn,
    raw_token: str,
    *,
    now_fn: Callable[[], datetime] = utc_now,
) -> bool:
    now = _aware_now(now_fn)
    token_hash = _token_hash(raw_token)
    if token_hash is None:
        return False
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_session SET last_seen_at=%s, "
            "idle_expires_at=LEAST(%s, absolute_expires_at) "
            "WHERE token_hash=%s AND revoked_at IS NULL "
            "AND idle_expires_at>%s AND absolute_expires_at>%s "
            "AND last_seen_at<=%s",
            (
                now,
                now + IDLE_TIMEOUT,
                token_hash,
                now,
                now,
                now - TOUCH_INTERVAL,
            ),
        )
        return cur.rowcount == 1


def revoke(
    conn,
    raw_token: str,
    reason: str,
    *,
    now_fn: Callable[[], datetime] = utc_now,
) -> bool:
    if not reason:
        raise ValueError("revoke reason không được để trống")
    now = _aware_now(now_fn)
    token_hash = _token_hash(raw_token)
    if token_hash is None:
        return False
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_session SET revoked_at=%s, revoke_reason=%s "
            "WHERE token_hash=%s AND revoked_at IS NULL",
            (now, reason, token_hash),
        )
        return cur.rowcount == 1


def revoke_all_for_user(
    conn,
    user_id: UUID,
    reason: str,
    *,
    now_fn: Callable[[], datetime] = utc_now,
) -> int:
    if not reason:
        raise ValueError("revoke reason không được để trống")
    now = _aware_now(now_fn)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_session SET revoked_at=%s, revoke_reason=%s "
            "WHERE user_id=%s AND revoked_at IS NULL",
            (now, reason, user_id),
        )
        return cur.rowcount
