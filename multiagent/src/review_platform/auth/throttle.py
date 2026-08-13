"""Persistent login throttle theo cap username/IP da HMAC."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Callable
import unicodedata


WINDOW = timedelta(minutes=15)
BLOCK_DURATION = timedelta(minutes=15)
MAX_FAILURES = 5


@dataclass(frozen=True)
class ThrottleDecision:
    subject_hash: str
    blocked: bool
    failure_count: int
    blocked_until: datetime | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware_now(now_fn: Callable[[], datetime]) -> datetime:
    value = now_fn()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("throttle time phải là timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _normalize_username(username: str) -> str:
    return unicodedata.normalize("NFKC", str(username)).casefold().strip()


class LoginThrottle:
    def __init__(self, conn, signing_key: bytes, *, now_fn=utc_now):
        if not isinstance(signing_key, bytes):
            raise TypeError("throttle signing key phải là bytes")
        self.conn = conn
        self.signing_key = signing_key
        self.now_fn = now_fn

    def subject_hash(self, username: str, ip_address: str) -> str:
        message = (
            _normalize_username(username) + "\0" + str(ip_address).strip()
        ).encode("utf-8")
        return hmac.new(self.signing_key, message, hashlib.sha256).hexdigest()

    def check(self, username: str, ip_address: str) -> ThrottleDecision:
        now = _aware_now(self.now_fn)
        subject_hash = self.subject_hash(username, ip_address)
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT failure_count, blocked_until FROM admin_login_throttle "
                "WHERE subject_hash=%s",
                (subject_hash,),
            )
            row = cur.fetchone()
        if row is None:
            return ThrottleDecision(subject_hash, False, 0, None)
        failure_count, blocked_until = row
        return ThrottleDecision(
            subject_hash,
            blocked_until is not None and blocked_until > now,
            failure_count,
            blocked_until,
        )

    def record_failure(self, username: str, ip_address: str) -> ThrottleDecision:
        now = _aware_now(self.now_fn)
        subject_hash = self.subject_hash(username, ip_address)
        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO admin_login_throttle "
                    "(subject_hash, failure_count, window_started_at, updated_at) "
                    "VALUES (%s, 0, %s, %s) ON CONFLICT DO NOTHING",
                    (subject_hash, now, now),
                )
                cur.execute(
                    "SELECT failure_count, window_started_at, blocked_until "
                    "FROM admin_login_throttle WHERE subject_hash=%s FOR UPDATE",
                    (subject_hash,),
                )
                failure_count, window_started_at, blocked_until = cur.fetchone()

                if blocked_until is not None and blocked_until > now:
                    return ThrottleDecision(
                        subject_hash,
                        True,
                        failure_count,
                        blocked_until,
                    )
                if now >= window_started_at + WINDOW:
                    failure_count = 0
                    window_started_at = now
                    blocked_until = None

                failure_count += 1
                if failure_count >= MAX_FAILURES:
                    blocked_until = now + BLOCK_DURATION
                cur.execute(
                    "UPDATE admin_login_throttle SET failure_count=%s, "
                    "window_started_at=%s, blocked_until=%s, updated_at=%s "
                    "WHERE subject_hash=%s",
                    (
                        failure_count,
                        window_started_at,
                        blocked_until,
                        now,
                        subject_hash,
                    ),
                )
                return ThrottleDecision(
                    subject_hash,
                    blocked_until is not None and blocked_until > now,
                    failure_count,
                    blocked_until,
                )

    def record_success(self, username: str, ip_address: str) -> None:
        subject_hash = self.subject_hash(username, ip_address)
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM admin_login_throttle WHERE subject_hash=%s",
                (subject_hash,),
            )
