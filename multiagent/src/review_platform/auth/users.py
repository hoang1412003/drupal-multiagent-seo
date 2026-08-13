"""PostgreSQL repository cho admin user va cac bat bien bao mat."""
from dataclasses import dataclass
from datetime import datetime
import unicodedata
from uuid import UUID

import psycopg

from review_platform.auth import passwords
from review_platform.auth.rbac import Role


class UserRepositoryError(RuntimeError):
    pass


class UsernameConflictError(UserRepositoryError):
    pass


class UserNotFoundError(UserRepositoryError):
    pass


class LastActiveAdminError(UserRepositoryError):
    pass


class InvalidCurrentPasswordError(UserRepositoryError):
    pass


@dataclass(frozen=True)
class AdminUser:
    id: UUID
    username: str
    username_normalized: str
    password_hash: str
    role: Role
    active: bool
    must_change_password: bool
    password_changed_at: datetime
    last_login_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


_USER_COLUMNS = (
    "id, username, username_normalized, password_hash, role, active, "
    "must_change_password, password_changed_at, last_login_at, created_by, "
    "created_at, updated_at"
)


def normalize_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError("username phải là chuỗi")
    normalized = unicodedata.normalize("NFKC", username).casefold().strip()
    if not normalized:
        raise ValueError("username không được để trống")
    return normalized


def _from_row(row) -> AdminUser:
    return AdminUser(
        id=row[0],
        username=row[1],
        username_normalized=row[2],
        password_hash=row[3],
        role=Role(row[4]),
        active=row[5],
        must_change_password=row[6],
        password_changed_at=row[7],
        last_login_at=row[8],
        created_by=row[9],
        created_at=row[10],
        updated_at=row[11],
    )


def create_user(
    conn,
    username: str,
    password: str,
    role: Role = Role.VIEWER,
    *,
    created_by: UUID | None = None,
    must_change_password: bool = True,
) -> AdminUser:
    display_username = username.strip()
    normalized = normalize_username(username)
    password_hash = passwords.hash_password(password)
    role = Role(role)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO admin_user "
                "(username, username_normalized, password_hash, role, created_by, "
                "must_change_password) VALUES (%s, %s, %s, %s, %s, %s) "
                f"RETURNING {_USER_COLUMNS}",
                (
                    display_username,
                    normalized,
                    password_hash,
                    role.value,
                    created_by,
                    must_change_password,
                ),
            )
            return _from_row(cur.fetchone())
    except psycopg.errors.UniqueViolation as exc:
        raise UsernameConflictError("username đã tồn tại") from exc


def get_user(conn, user_id: UUID) -> AdminUser:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_USER_COLUMNS} FROM admin_user WHERE id=%s",
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise UserNotFoundError("không tìm thấy admin user")
    return _from_row(row)


def find_by_username(
    conn,
    username: str,
    *,
    for_update: bool = False,
) -> AdminUser | None:
    normalized = normalize_username(username)
    lock_clause = " FOR UPDATE" if for_update else ""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_USER_COLUMNS} FROM admin_user "
            f"WHERE username_normalized=%s{lock_clause}",
            (normalized,),
        )
        row = cur.fetchone()
    return None if row is None else _from_row(row)


def authenticate_candidate(conn, username: str, password: str) -> AdminUser | None:
    candidate = find_by_username(conn, username)
    if candidate is None or not passwords.verify_password(
        candidate.password_hash,
        password,
    ):
        return None
    return candidate


def mark_login_success(conn, user_id: UUID) -> AdminUser:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_user SET last_login_at=now(), updated_at=now() "
            f"WHERE id=%s RETURNING {_USER_COLUMNS}",
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise UserNotFoundError("không tìm thấy admin user")
    return _from_row(row)


def _lock_active_admins(cur) -> tuple[UUID, ...]:
    cur.execute(
        "SELECT id FROM admin_user WHERE active AND role='admin' "
        "ORDER BY id FOR UPDATE"
    )
    return tuple(row[0] for row in cur.fetchall())


def _lock_user(cur, user_id: UUID) -> AdminUser:
    cur.execute(
        f"SELECT {_USER_COLUMNS} FROM admin_user WHERE id=%s FOR UPDATE",
        (user_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise UserNotFoundError("không tìm thấy admin user")
    return _from_row(row)


def set_role(conn, user_id: UUID, role: Role) -> AdminUser:
    new_role = Role(role)
    with conn.transaction():
        with conn.cursor() as cur:
            active_admin_ids = _lock_active_admins(cur)
            current = _lock_user(cur, user_id)
            if (
                current.active
                and current.role is Role.ADMIN
                and new_role is not Role.ADMIN
                and len(active_admin_ids) <= 1
            ):
                raise LastActiveAdminError("không thể hạ role admin active cuối cùng")
            cur.execute(
                "UPDATE admin_user SET role=%s, updated_at=now() WHERE id=%s "
                f"RETURNING {_USER_COLUMNS}",
                (new_role.value, user_id),
            )
            return _from_row(cur.fetchone())


def set_active(conn, user_id: UUID, active: bool) -> AdminUser:
    with conn.transaction():
        with conn.cursor() as cur:
            active_admin_ids = _lock_active_admins(cur)
            current = _lock_user(cur, user_id)
            if (
                current.active
                and current.role is Role.ADMIN
                and not active
                and len(active_admin_ids) <= 1
            ):
                raise LastActiveAdminError("không thể khóa admin active cuối cùng")
            cur.execute(
                "UPDATE admin_user SET active=%s, updated_at=now() WHERE id=%s "
                f"RETURNING {_USER_COLUMNS}",
                (active, user_id),
            )
            return _from_row(cur.fetchone())


def _revoke_sessions(cur, user_id: UUID, reason: str) -> None:
    cur.execute(
        "UPDATE admin_session SET revoked_at=now(), revoke_reason=%s "
        "WHERE user_id=%s AND revoked_at IS NULL",
        (reason, user_id),
    )


def reset_password(conn, user_id: UUID, new_password: str) -> AdminUser:
    password_hash = passwords.hash_password(new_password)
    with conn.transaction():
        with conn.cursor() as cur:
            _lock_user(cur, user_id)
            cur.execute(
                "UPDATE admin_user SET password_hash=%s, must_change_password=true, "
                "password_changed_at=now(), updated_at=now() WHERE id=%s "
                f"RETURNING {_USER_COLUMNS}",
                (password_hash, user_id),
            )
            updated = _from_row(cur.fetchone())
            _revoke_sessions(cur, user_id, "password_reset")
            return updated


def change_password(
    conn,
    user_id: UUID,
    current_password: str,
    new_password: str,
) -> AdminUser:
    passwords.validate_password(new_password)
    with conn.transaction():
        with conn.cursor() as cur:
            current = _lock_user(cur, user_id)
            if not passwords.verify_password(current.password_hash, current_password):
                raise InvalidCurrentPasswordError("mật khẩu hiện tại không đúng")
            password_hash = passwords.hash_password(new_password)
            cur.execute(
                "UPDATE admin_user SET password_hash=%s, must_change_password=false, "
                "password_changed_at=now(), updated_at=now() WHERE id=%s "
                f"RETURNING {_USER_COLUMNS}",
                (password_hash, user_id),
            )
            updated = _from_row(cur.fetchone())
            _revoke_sessions(cur, user_id, "password_changed")
            return updated
