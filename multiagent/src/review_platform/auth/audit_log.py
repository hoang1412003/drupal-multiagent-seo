"""Append-only security audit events voi metadata allowlist theo action."""
from collections.abc import Mapping
from enum import Enum
from uuid import UUID

from psycopg.types.json import Jsonb


class AuditAction(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    USER_CREATED = "user_created"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"
    PASSWORD_RESET = "password_reset"
    LAST_ADMIN_DENIED = "last_admin_denied"
    JOB_RETRIED = "job_retried"


class AuditMetadataError(ValueError):
    pass


_ALLOWED_METADATA = {
    AuditAction.LOGIN_SUCCESS: frozenset({"subject_hash"}),
    AuditAction.LOGIN_FAILED: frozenset({"subject_hash", "reason"}),
    AuditAction.LOGOUT: frozenset({"session_id"}),
    AuditAction.PASSWORD_CHANGED: frozenset(),
    AuditAction.USER_CREATED: frozenset({"role"}),
    AuditAction.USER_ROLE_CHANGED: frozenset({"old_role", "new_role"}),
    AuditAction.USER_LOCKED: frozenset(),
    AuditAction.USER_UNLOCKED: frozenset(),
    AuditAction.PASSWORD_RESET: frozenset(),
    AuditAction.LAST_ADMIN_DENIED: frozenset({"operation"}),
    AuditAction.JOB_RETRIED: frozenset(
        {"saved_result_available", "new_job_public_id", "reason"}
    ),
}
_SENSITIVE_KEY_PARTS = ("password", "token", "authorization", "cookie", "secret")
_OUTCOMES = frozenset({"success", "denied", "failed"})


def _validate_metadata(action: AuditAction, metadata: Mapping) -> dict:
    if not isinstance(metadata, Mapping):
        raise AuditMetadataError("audit metadata phải là mapping")
    result = {}
    for raw_key, value in metadata.items():
        if not isinstance(raw_key, str):
            raise AuditMetadataError("audit metadata key phải là chuỗi")
        key = raw_key.casefold()
        if any(part in key for part in _SENSITIVE_KEY_PARTS):
            raise AuditMetadataError("audit metadata chứa key nhạy cảm")
        if key not in _ALLOWED_METADATA[action]:
            raise AuditMetadataError(f"audit metadata key ngoài allowlist: {raw_key}")
        if isinstance(value, Mapping):
            raise AuditMetadataError("audit metadata không cho mapping lồng")
        if isinstance(value, bytes):
            raise AuditMetadataError("audit metadata không cho bytes")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise AuditMetadataError("audit metadata chỉ cho scalar JSON")
        result[key] = value
    return result


def write_event(
    conn,
    *,
    action: AuditAction,
    actor_user_id: UUID | None,
    actor_username: str,
    target_type: str,
    target_id: str | None,
    outcome: str,
    metadata: Mapping,
) -> int:
    action = AuditAction(action)
    if outcome not in _OUTCOMES:
        raise ValueError("audit outcome phải là success, denied hoặc failed")
    safe_metadata = _validate_metadata(action, metadata)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admin_audit_log "
            "(actor_user_id, actor_username, action, target_type, target_id, "
            "outcome, metadata) VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id",
            (
                actor_user_id,
                actor_username,
                action.value,
                target_type,
                target_id,
                outcome,
                Jsonb(safe_metadata),
            ),
        )
        return cur.fetchone()[0]
