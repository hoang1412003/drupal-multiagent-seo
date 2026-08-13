"""Test server-side admin session va CSRF token.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_sessions.py
"""
from base64 import urlsafe_b64decode
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import migrations
from review_platform.auth import csrf, sessions, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_sessions"
START = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


class Clock:
    def __init__(self, now=START):
        self.now = now

    def __call__(self):
        return self.now


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
    return users.create_user(
        conn,
        username="session-user",
        password="Mat-khau-session-2026",
        role=Role.VIEWER,
        must_change_password=False,
    )


def _decoded_token_bytes(raw_token: str) -> bytes:
    return urlsafe_b64decode(raw_token + "=" * (-len(raw_token) % 4))


def test_issue_chi_luu_hash_va_resolve_token(conn):
    user = _reset_schema(conn)
    clock = Clock()
    issued = sessions.issue(conn, user.id, now_fn=clock)
    assert len(_decoded_token_bytes(issued.raw_token)) >= 32
    assert issued.absolute_expires_at == START + timedelta(hours=8)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT token_hash, csrf_secret, idle_expires_at, absolute_expires_at "
            "FROM admin_session WHERE user_id=%s",
            (user.id,),
        )
        token_hash, csrf_secret, idle_expires, absolute_expires = cur.fetchone()
    assert token_hash == hashlib.sha256(issued.raw_token.encode("ascii")).hexdigest()
    assert token_hash != issued.raw_token
    assert csrf_secret == issued.csrf_token
    assert idle_expires == START + timedelta(minutes=30)
    assert absolute_expires == START + timedelta(hours=8)

    resolved = sessions.resolve(conn, issued.raw_token, now_fn=clock)
    assert resolved is not None
    assert resolved.user == user
    assert resolved.csrf_token == issued.csrf_token
    assert resolved.must_change_password is False
    assert sessions.resolve(conn, "token-sai", now_fn=clock) is None
    print("[PASS] raw session token chi tra mot lan va DB chi luu SHA-256")


def test_expired_revoked_va_touch_khong_vuot_absolute(conn):
    user = _reset_schema(conn)
    clock = Clock()
    first = sessions.issue(conn, user.id, now_fn=clock)

    clock.now = START + timedelta(minutes=4)
    assert not sessions.touch(conn, first.raw_token, now_fn=clock)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_seen_at, idle_expires_at FROM admin_session "
            "WHERE token_hash=%s",
            (hashlib.sha256(first.raw_token.encode("ascii")).hexdigest(),),
        )
        assert cur.fetchone() == (START, START + timedelta(minutes=30))

    clock.now = START + timedelta(minutes=10)
    assert sessions.touch(conn, first.raw_token, now_fn=clock)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_seen_at, idle_expires_at FROM admin_session "
            "WHERE token_hash=%s",
            (hashlib.sha256(first.raw_token.encode("ascii")).hexdigest(),),
        )
        assert cur.fetchone() == (
            clock.now,
            START + timedelta(minutes=40),
        )

    clock.now = START + timedelta(hours=7, minutes=50)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_session SET idle_expires_at=%s WHERE user_id=%s",
            (START + timedelta(hours=7, minutes=55), user.id),
        )
    assert sessions.touch(conn, first.raw_token, now_fn=clock)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT idle_expires_at FROM admin_session WHERE user_id=%s",
            (user.id,),
        )
        assert cur.fetchone()[0] == START + timedelta(hours=8)

    clock.now = START + timedelta(hours=8)
    assert sessions.resolve(conn, first.raw_token, now_fn=clock) is None
    assert not sessions.touch(conn, first.raw_token, now_fn=clock)

    clock.now = START
    second = sessions.issue(conn, user.id, now_fn=clock)
    assert sessions.revoke(conn, second.raw_token, "logout", now_fn=clock)
    assert sessions.resolve(conn, second.raw_token, now_fn=clock) is None
    print("[PASS] idle/absolute expiry, touch cap va revoke session dung")


def test_revoke_all_for_user_va_timezone_aware(conn):
    user = _reset_schema(conn)
    clock = Clock()
    sessions.issue(conn, user.id, now_fn=clock)
    sessions.issue(conn, user.id, now_fn=clock)
    assert sessions.revoke_all_for_user(
        conn,
        user.id,
        "security_event",
        now_fn=clock,
    ) == 2
    with expect(ValueError, "timezone-aware"):
        sessions.issue(conn, user.id, now_fn=lambda: datetime(2026, 8, 13))
    print("[PASS] revoke all va bat buoc timestamp timezone-aware")


def test_login_va_session_csrf_constant_time_semantics(conn):
    _reset_schema(conn)
    signing_key = b"csrf-key-rieng-biet-du-32-byte-2026"
    other_key = b"csrf-key-hoan-toan-khac-du-32-byte"
    token = csrf.issue_login_csrf(signing_key)
    nonce, signature = token.split(".", 1)
    assert len(_decoded_token_bytes(nonce)) >= 32
    assert len(signature) == 64
    assert csrf.verify_login_csrf(token, token, signing_key)
    assert not csrf.verify_login_csrf(token, token, other_key)
    assert not csrf.verify_login_csrf(token, token + "x", signing_key)
    assert not csrf.verify_login_csrf(token, "khong-hop-le", signing_key)
    assert csrf.verify_session_csrf("session-csrf", "session-csrf")
    assert not csrf.verify_session_csrf("session-csrf", "session-CSRF")
    assert not csrf.verify_session_csrf("session-csrf", None)
    print("[PASS] pre-auth signed double-submit va session CSRF dung")


if __name__ == "__main__":
    try:
        connection = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            "[SKIP] khong phai [PASS]"
        )
        sys.exit(0)

    failed = False
    try:
        for fn in (
            test_issue_chi_luu_hash_va_resolve_token,
            test_expired_revoked_va_touch_khong_vuot_absolute,
            test_revoke_all_for_user_va_timezone_aware,
            test_login_va_session_csrf_constant_time_semantics,
        ):
            try:
                fn(connection)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
    finally:
        with connection.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        connection.close()

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
