"""CLI tuong tac de bootstrap va quan ly tai khoan Platform Admin."""
import argparse
import getpass
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from review_platform import database, migrations
from review_platform.auth import audit_log, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SYSTEM_ACTOR = "system-cli"


class AdminCLIError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Quan ly tai khoan Platform Admin",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    bootstrap = commands.add_parser(
        "bootstrap",
        help="Tao admin dau tien khi database chua co user",
    )
    bootstrap.add_argument("--username", required=True)

    create = commands.add_parser("create", help="Tao tai khoan moi")
    create.add_argument("--username", required=True)
    create.add_argument("--role", choices=[role.value for role in Role], required=True)

    reset = commands.add_parser("reset-password", help="Sinh mat khau tam thoi")
    reset.add_argument("--username", required=True)

    lock = commands.add_parser("lock", help="Khoa tai khoan")
    lock.add_argument("--username", required=True)

    unlock = commands.add_parser("unlock", help="Mo khoa tai khoan")
    unlock.add_argument("--username", required=True)

    set_role = commands.add_parser("set-role", help="Doi role tai khoan")
    set_role.add_argument("--username", required=True)
    set_role.add_argument("--role", choices=[role.value for role in Role], required=True)
    return parser


def _confirmed_password(getpass_fn) -> str:
    first = getpass_fn("Mật khẩu: ")
    second = getpass_fn("Nhập lại mật khẩu: ")
    if not secrets.compare_digest(first.encode("utf-8"), second.encode("utf-8")):
        raise AdminCLIError("hai lần nhập mật khẩu không khớp")
    return first


def _audit(
    conn,
    action: audit_log.AuditAction,
    target: users.AdminUser,
    *,
    outcome="success",
    metadata=None,
) -> int:
    return audit_log.write_event(
        conn,
        action=action,
        actor_user_id=None,
        actor_username=SYSTEM_ACTOR,
        target_type="admin_user",
        target_id=str(target.id),
        outcome=outcome,
        metadata={} if metadata is None else metadata,
    )


def _find(conn, username: str) -> users.AdminUser:
    try:
        user = users.find_by_username(conn, username)
    except ValueError as exc:
        raise AdminCLIError("username không hợp lệ") from exc
    if user is None:
        raise AdminCLIError(f"không tìm thấy user '{username}'")
    return user


def _bootstrap(conn, username: str, getpass_fn):
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM admin_user)")
        if cur.fetchone()[0]:
            raise AdminCLIError("database đã có user; không được bootstrap lần nữa")
    password = _confirmed_password(getpass_fn)
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("LOCK TABLE admin_user IN EXCLUSIVE MODE")
            cur.execute("SELECT count(*) FROM admin_user")
            if cur.fetchone()[0] != 0:
                raise AdminCLIError("database đã có user; không được bootstrap lần nữa")
        created = users.create_user(
            conn,
            username,
            password,
            Role.ADMIN,
            must_change_password=True,
        )
        _audit(
            conn,
            audit_log.AuditAction.USER_CREATED,
            created,
            metadata={"role": Role.ADMIN.value},
        )
        return created


def _create(conn, username: str, role: Role, getpass_fn):
    password = _confirmed_password(getpass_fn)
    with conn.transaction():
        created = users.create_user(
            conn,
            username,
            password,
            role,
            must_change_password=True,
        )
        _audit(
            conn,
            audit_log.AuditAction.USER_CREATED,
            created,
            metadata={"role": role.value},
        )
        return created


def _reset_password(conn, username: str, print_fn, token_fn):
    target = _find(conn, username)
    temporary_password = token_fn(18)
    with conn.transaction():
        updated = users.reset_password(conn, target.id, temporary_password)
        _audit(conn, audit_log.AuditAction.PASSWORD_RESET, updated)
    print_fn(f"Mật khẩu tạm thời: {temporary_password}")
    return updated


def _record_last_admin_denied(conn, target, operation: str) -> None:
    _audit(
        conn,
        audit_log.AuditAction.LAST_ADMIN_DENIED,
        target,
        outcome="denied",
        metadata={"operation": operation},
    )


def _set_active(conn, username: str, active: bool):
    target = _find(conn, username)
    operation = "unlock" if active else "lock"
    try:
        with conn.transaction():
            updated = users.set_active(conn, target.id, active)
            _audit(
                conn,
                audit_log.AuditAction.USER_UNLOCKED
                if active
                else audit_log.AuditAction.USER_LOCKED,
                updated,
            )
            return updated
    except users.LastActiveAdminError:
        _record_last_admin_denied(conn, target, operation)
        raise


def _set_role(conn, username: str, role: Role):
    target = _find(conn, username)
    try:
        with conn.transaction():
            updated = users.set_role(conn, target.id, role)
            _audit(
                conn,
                audit_log.AuditAction.USER_ROLE_CHANGED,
                updated,
                metadata={"old_role": target.role.value, "new_role": role.value},
            )
            return updated
    except users.LastActiveAdminError:
        _record_last_admin_denied(conn, target, "set-role")
        raise


def execute(
    conn,
    args,
    *,
    getpass_fn=getpass.getpass,
    print_fn=print,
    token_fn=secrets.token_urlsafe,
):
    if args.command == "bootstrap":
        return _bootstrap(conn, args.username, getpass_fn)
    if args.command == "create":
        return _create(conn, args.username, Role(args.role), getpass_fn)
    if args.command == "reset-password":
        return _reset_password(conn, args.username, print_fn, token_fn)
    if args.command == "lock":
        return _set_active(conn, args.username, False)
    if args.command == "unlock":
        return _set_active(conn, args.username, True)
    if args.command == "set-role":
        return _set_role(conn, args.username, Role(args.role))
    raise AdminCLIError(f"command không được hỗ trợ: {args.command}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with database.open_connection() as conn:
            migrations.require_current(conn, MIGRATIONS_DIR)
            execute(conn, args)
    except (AdminCLIError, users.UserRepositoryError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
