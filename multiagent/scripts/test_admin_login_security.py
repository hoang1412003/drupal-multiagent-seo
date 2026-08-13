"""Test login throttle va auth audit metadata allowlist.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_login_security.py
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import migrations
from review_platform.auth import audit_log, throttle, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_login_security"
START = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"


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


def test_throttle_block_o_fail_thu_nam_va_reset_window(conn):
    _reset_schema(conn)
    clock = Clock()
    limiter = throttle.LoginThrottle(conn, THROTTLE_KEY, now_fn=clock)
    for expected_count in range(1, 5):
        decision = limiter.record_failure("  Ａdmin ", "127.0.0.1")
        assert decision.failure_count == expected_count
        assert decision.blocked is False
        assert limiter.check("admin", "127.0.0.1").blocked is False

    fifth = limiter.record_failure("ADMIN", "127.0.0.1")
    assert fifth.failure_count == 5
    assert fifth.blocked is True
    assert fifth.blocked_until == START + timedelta(minutes=15)
    assert limiter.check("admin", "127.0.0.1").blocked is True

    with conn.cursor() as cur:
        cur.execute(
            "SELECT subject_hash, failure_count FROM admin_login_throttle"
        )
        stored_hash, stored_count = cur.fetchone()
    assert stored_hash == limiter.subject_hash("admin", "127.0.0.1")
    assert "admin" not in stored_hash and "127.0.0.1" not in stored_hash
    assert stored_count == 5

    clock.now = START + timedelta(minutes=16)
    assert limiter.check("admin", "127.0.0.1").blocked is False
    reset = limiter.record_failure("admin", "127.0.0.1")
    assert reset.failure_count == 1 and reset.blocked is False
    print("[PASS] fail thu nam block 15 phut va reset dung window")


def test_throttle_tach_username_ip_va_success_xoa_counter(conn):
    _reset_schema(conn)
    limiter = throttle.LoginThrottle(conn, THROTTLE_KEY, now_fn=Clock())
    limiter.record_failure("admin", "127.0.0.1")
    limiter.record_failure("other", "127.0.0.1")
    limiter.record_failure("admin", "127.0.0.2")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_login_throttle")
        assert cur.fetchone()[0] == 3
    limiter.record_success("admin", "127.0.0.1")
    assert limiter.check("admin", "127.0.0.1").failure_count == 0
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_login_throttle")
        assert cur.fetchone()[0] == 2
    print("[PASS] throttle subject tach username/IP va success xoa counter")


def test_audit_allowlist_ghi_event_hop_le(conn):
    _reset_schema(conn)
    actor = users.create_user(
        conn,
        username="audit-admin",
        password="Mat-khau-audit-2026",
        role=Role.ADMIN,
    )
    event_id = audit_log.write_event(
        conn,
        action=audit_log.AuditAction.USER_ROLE_CHANGED,
        actor_user_id=actor.id,
        actor_username=actor.username,
        target_type="admin_user",
        target_id=str(actor.id),
        outcome="success",
        metadata={"old_role": "operator", "new_role": "admin"},
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT action, outcome, metadata FROM admin_audit_log WHERE id=%s",
            (event_id,),
        )
        assert cur.fetchone() == (
            "user_role_changed",
            "success",
            {"old_role": "operator", "new_role": "admin"},
        )
    print("[PASS] audit event chi ghi metadata duoc allowlist")


def test_audit_tu_choi_secret_nested_va_key_la(conn):
    _reset_schema(conn)
    base = dict(
        action=audit_log.AuditAction.LOGIN_FAILED,
        actor_user_id=None,
        actor_username="anonymous",
        target_type="admin_session",
        target_id=None,
        outcome="denied",
    )
    for key in ("password", "session_token", "authorization", "cookie", "secret"):
        with expect(audit_log.AuditMetadataError, "nhạy cảm"):
            audit_log.write_event(conn, metadata={key: "khong-duoc-ghi"}, **base)
    with expect(audit_log.AuditMetadataError, "allowlist"):
        audit_log.write_event(conn, metadata={"unexpected": "value"}, **base)
    with expect(audit_log.AuditMetadataError, "lồng"):
        audit_log.write_event(
            conn,
            metadata={"reason": {"nested": "value"}},
            **base,
        )
    with expect(audit_log.AuditMetadataError, "bytes"):
        audit_log.write_event(conn, metadata={"reason": b"raw"}, **base)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_audit_log")
        assert cur.fetchone()[0] == 0
    print("[PASS] audit reject secret, nested mapping, bytes va key ngoai allowlist")


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
            test_throttle_block_o_fail_thu_nam_va_reset_window,
            test_throttle_tach_username_ip_va_success_xoa_counter,
            test_audit_allowlist_ghi_event_hop_le,
            test_audit_tu_choi_secret_nested_va_key_la,
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
