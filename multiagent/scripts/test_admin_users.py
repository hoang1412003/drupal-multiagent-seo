"""Test password policy, admin user repository va last-admin invariant.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_users.py
"""
import os
from pathlib import Path
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import migrations
from review_platform.auth import passwords, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_users"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _session_for(conn, user_id) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admin_session "
            "(user_id, token_hash, csrf_secret, idle_expires_at, absolute_expires_at) "
            "VALUES (%s, repeat('a', 64), 'csrf', now() + interval '30 minutes', "
            "now() + interval '8 hours')",
            (user_id,),
        )


def test_argon2id_dung_tham_so_va_password_policy(conn):
    _reset_schema(conn)
    with expect(passwords.PasswordPolicyError, "12"):
        passwords.hash_password("qua-ngan")
    with expect(passwords.PasswordPolicyError, "128"):
        passwords.hash_password("x" * 129)

    plain = "Mật-khẩu-rất-dài-2026"
    value = passwords.hash_password(plain)
    assert value.startswith("$argon2id$v=19$m=19456,t=2,p=1$"), value
    assert passwords.verify_password(value, plain)
    assert not passwords.verify_password(value, "sai-hoan-toan")
    assert not passwords.verify_password("khong-phai-argon2", plain)
    assert not passwords.needs_rehash(value)

    spaced = "  Mat-khau-co-khoang-trang  "
    spaced_hash = passwords.hash_password(spaced)
    assert passwords.verify_password(spaced_hash, spaced)
    assert not passwords.verify_password(spaced_hash, spaced.strip())
    print("[PASS] Argon2id exact parameters va password khong bi trim")


def test_username_nfkc_casefold_strip_va_khong_trung(conn):
    _reset_schema(conn)
    first = users.create_user(
        conn,
        username="  Ａdmin  ",
        password="Mat-khau-admin-2026",
        role=Role.ADMIN,
    )
    assert first.username == "Ａdmin"
    assert first.username_normalized == "admin"
    assert users.authenticate_candidate(conn, "ADMIN", "Mat-khau-admin-2026") == first
    assert users.authenticate_candidate(conn, "admin", "mat-khau-sai") is None

    with expect(users.UsernameConflictError, "tồn tại"):
        users.create_user(
            conn,
            username="admin",
            password="Mat-khau-khac-2026",
            role=Role.VIEWER,
        )
    print("[PASS] username NFKC/casefold/strip va unique tren normalized value")


def test_last_active_admin_guard_khi_ha_role_va_khoa(conn):
    _reset_schema(conn)
    first = users.create_user(
        conn,
        username="admin-one",
        password="Mat-khau-admin-one",
        role=Role.ADMIN,
    )
    with expect(users.LastActiveAdminError, "admin active cuối"):
        users.set_role(conn, first.id, Role.OPERATOR)
    with expect(users.LastActiveAdminError, "admin active cuối"):
        users.set_active(conn, first.id, False)

    second = users.create_user(
        conn,
        username="admin-two",
        password="Mat-khau-admin-two",
        role=Role.ADMIN,
    )
    demoted = users.set_role(conn, first.id, Role.OPERATOR)
    assert demoted.role is Role.OPERATOR
    with expect(users.LastActiveAdminError, "admin active cuối"):
        users.set_active(conn, second.id, False)
    print("[PASS] khong the ha role/lock admin active cuoi cung")


def test_reset_va_change_password_revoke_session(conn):
    _reset_schema(conn)
    user = users.create_user(
        conn,
        username="operator",
        password="Mat-khau-ban-dau-2026",
        role=Role.OPERATOR,
        must_change_password=False,
    )
    _session_for(conn, user.id)
    reset = users.reset_password(conn, user.id, "Mat-khau-reset-2026")
    assert reset.must_change_password is True
    assert users.authenticate_candidate(conn, "operator", "Mat-khau-reset-2026")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT revoked_at IS NOT NULL, revoke_reason FROM admin_session "
            "WHERE user_id=%s",
            (user.id,),
        )
        assert cur.fetchone() == (True, "password_reset")

    with conn.cursor() as cur:
        cur.execute("DELETE FROM admin_session WHERE user_id=%s", (user.id,))
    _session_for(conn, user.id)
    with expect(users.InvalidCurrentPasswordError, "không đúng"):
        users.change_password(
            conn,
            user.id,
            "Mat-khau-sai-2026",
            "Mat-khau-moi-2026",
        )
    changed = users.change_password(
        conn,
        user.id,
        "Mat-khau-reset-2026",
        "Mat-khau-moi-2026",
    )
    assert changed.must_change_password is False
    assert users.authenticate_candidate(conn, "operator", "Mat-khau-moi-2026")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT revoked_at IS NOT NULL, revoke_reason FROM admin_session "
            "WHERE user_id=%s",
            (user.id,),
        )
        assert cur.fetchone() == (True, "password_changed")
    print("[PASS] reset/change password cap nhat flag va revoke session cung transaction")


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
            test_argon2id_dung_tham_so_va_password_policy,
            test_username_nfkc_casefold_strip_va_khong_trung,
            test_last_active_admin_guard_khi_ha_role_va_khoa,
            test_reset_va_change_password_revoke_session,
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
