"""Integration test CLI quan ly Platform Admin account.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_user_cli.py
"""
from contextlib import contextmanager, redirect_stderr
from io import StringIO
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import admin_user
import db
from review_platform import migrations
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_user_cli"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _getpass(values):
    iterator = iter(values)
    calls = []

    def fake(prompt):
        calls.append(prompt)
        return next(iterator)

    return fake, calls


def test_parser_tu_choi_password_argument(conn):
    parser = admin_user.build_parser()
    with redirect_stderr(StringIO()):
        with expect(SystemExit, "2"):
            parser.parse_args(
                [
                    "create",
                    "--username",
                    "viewer",
                    "--role",
                    "viewer",
                    "--password",
                    "lo-qua-argv",
                ]
            )
    print("[PASS] CLI khong co password argument")


def test_bootstrap_chi_khi_chua_co_user_va_bat_confirm(conn):
    _reset_schema(conn)
    getpass_fn, calls = _getpass(
        ["Mat-khau-bootstrap-2026", "Mat-khau-bootstrap-2026"]
    )
    args = admin_user.build_parser().parse_args(
        ["bootstrap", "--username", "admin"]
    )
    created = admin_user.execute(conn, args, getpass_fn=getpass_fn)
    assert len(calls) == 2
    assert created.role is Role.ADMIN
    assert created.must_change_password is True
    assert users.authenticate_candidate(conn, "ADMIN", "Mat-khau-bootstrap-2026")
    with expect(admin_user.AdminCLIError, "đã có user"):
        admin_user.execute(conn, args, getpass_fn=getpass_fn)

    _reset_schema(conn)
    mismatch_fn, _ = _getpass(["Mat-khau-mot-2026", "Mat-khau-hai-2026"])
    with expect(admin_user.AdminCLIError, "không khớp"):
        admin_user.execute(conn, args, getpass_fn=mismatch_fn)
    print("[PASS] bootstrap chi chay schema rong va password confirm")


def test_create_reset_password_in_dung_mot_lan_va_audit_khong_lo_secret(conn):
    _reset_schema(conn)
    getpass_fn, _ = _getpass(["Mat-khau-viewer-2026", "Mat-khau-viewer-2026"])
    create_args = admin_user.build_parser().parse_args(
        ["create", "--username", "viewer.user", "--role", "viewer"]
    )
    created = admin_user.execute(conn, create_args, getpass_fn=getpass_fn)
    assert created.role is Role.VIEWER

    output = []
    temporary = "Temporary-password-2026"
    reset_args = admin_user.build_parser().parse_args(
        ["reset-password", "--username", "viewer.user"]
    )
    admin_user.execute(
        conn,
        reset_args,
        print_fn=output.append,
        token_fn=lambda size: temporary,
    )
    assert output == [f"Mật khẩu tạm thời: {temporary}"]
    assert users.authenticate_candidate(conn, "viewer.user", temporary)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT actor_username, action, metadata::text "
            "FROM admin_audit_log ORDER BY id"
        )
        rows = cur.fetchall()
    assert [row[0] for row in rows] == ["system-cli", "system-cli"]
    assert [row[1] for row in rows] == ["user_created", "password_reset"]
    assert all(temporary not in row[2] for row in rows)
    print("[PASS] create/reset audit system-cli va password chi in mot lan")


def test_lock_unlock_set_role_dung_repository_guard(conn):
    _reset_schema(conn)
    first = users.create_user(
        conn,
        "admin-one",
        "Mat-khau-admin-one",
        Role.ADMIN,
    )
    parser = admin_user.build_parser()
    with expect(users.LastActiveAdminError, "admin active cuối"):
        admin_user.execute(
            conn,
            parser.parse_args(["lock", "--username", first.username]),
        )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT action, outcome, metadata FROM admin_audit_log ORDER BY id DESC LIMIT 1"
        )
        assert cur.fetchone() == (
            "last_admin_denied",
            "denied",
            {"operation": "lock"},
        )

    second = users.create_user(
        conn,
        "admin-two",
        "Mat-khau-admin-two",
        Role.ADMIN,
    )
    locked = admin_user.execute(
        conn,
        parser.parse_args(["lock", "--username", first.username]),
    )
    assert locked.active is False
    unlocked = admin_user.execute(
        conn,
        parser.parse_args(["unlock", "--username", first.username]),
    )
    assert unlocked.active is True
    changed = admin_user.execute(
        conn,
        parser.parse_args(
            ["set-role", "--username", first.username, "--role", "operator"]
        ),
    )
    assert changed.role is Role.OPERATOR
    assert users.get_user(conn, second.id).role is Role.ADMIN
    print("[PASS] lock/unlock/set-role giu last-admin guard va audit denied")


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
            test_parser_tu_choi_password_argument,
            test_bootstrap_chi_khi_chua_co_user_va_bat_confirm,
            test_create_reset_password_in_dung_mot_lan_va_audit_khong_lo_secret,
            test_lock_unlock_set_role_dung_repository_guard,
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
