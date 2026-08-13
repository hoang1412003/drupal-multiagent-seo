"""Service thay doi vong doi review job tu Platform Admin."""
from dataclasses import dataclass
from uuid import UUID

import job_queue
from review_platform.admin import sanitization
from review_platform.auth import audit_log
from review_platform.auth.rbac import Role, allows
from review_platform.context import ReviewContext, ReviewProfileContext, SiteContext


class JobRetryError(RuntimeError):
    pass


class JobRetryNotFound(JobRetryError):
    pass


class JobRetryConflict(JobRetryError):
    pass


class JobRetryContextError(JobRetryError):
    pass


@dataclass(frozen=True)
class RetryResult:
    new_job_public_id: UUID
    saved_result_available: bool


def _context_for_locked_job(conn, job) -> ReviewContext:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.id,s.slug,s.connector_type,s.base_url,s.secret_ref,s.active,"
            "s.intake_paused,p.id,p.code,p.market_code,p.language_code,p.content_type,"
            "p.status,p.policy_version,p.policy_snapshot,a.active "
            "FROM site AS s JOIN site_profile_assignment AS a ON a.site_id=s.id "
            "JOIN review_profile AS p ON p.id=a.profile_id "
            "WHERE s.id=%s AND p.id=%s FOR SHARE OF s,p,a",
            (job[2], job[3]),
        )
        row = cur.fetchone()
    if row is None:
        raise JobRetryContextError("site/profile snapshot khong con ton tai")
    if not row[5] or not row[15] or row[12] != "active":
        raise JobRetryContextError("site/profile snapshot khong con active")
    if (row[13], row[11], row[10]) != (job[4], job[7], job[8]):
        raise JobRetryContextError("policy/content/language snapshot khong con khop")
    return ReviewContext(
        site=SiteContext(
            id=row[0],
            slug=row[1],
            connector_type=row[2],
            base_url=row[3],
            secret_ref=row[4],
            active=row[5],
            intake_paused=row[6],
        ),
        profile=ReviewProfileContext(
            id=row[7],
            code=row[8],
            market_code=row[9],
            language_code=row[10],
            content_type=row[11],
            policy_version=row[13],
            policy_snapshot=dict(row[14]),
        ),
    )


def retry_failed(
    conn,
    *,
    job_public_id: UUID,
    actor,
    reason: str | None,
) -> RetryResult:
    if not actor.active or not allows(actor.role, Role.OPERATOR):
        raise PermissionError("operator role required")
    job_public_id = UUID(str(job_public_id))
    safe_reason = (
        None
        if reason is None
        else sanitization.sanitize_text(reason, max_length=500).strip() or None
    )

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,public_id,site_id,profile_id,policy_version,"
                "external_content_id,external_revision_id,content_type,langcode,"
                "content_hash,status FROM review_job WHERE public_id=%s FOR UPDATE",
                (job_public_id,),
            )
            job = cur.fetchone()
        if job is None:
            raise JobRetryNotFound("job khong ton tai")
        if job[10] != job_queue.FAILED:
            raise JobRetryConflict("chi job failed moi duoc retry")

        context = _context_for_locked_job(conn, job)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM run_log WHERE job_id=%s "
                "AND writeback_status='failed')",
                (job[0],),
            )
            saved_result_available = bool(cur.fetchone()[0])

        queued = job_queue.enqueue_scoped(
            conn,
            context,
            job[5],
            job[9],
            "admin_retry",
            external_revision_id=job[6],
            force=True,
            supersedes_job_id=job[0],
        )
        if queued["status"] != job_queue.QUEUED:
            raise JobRetryConflict("job da duoc retry boi request khac")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT public_id FROM review_job WHERE id=%s",
                (queued["job_id"],),
            )
            new_job_public_id = cur.fetchone()[0]

        audit_log.write_event(
            conn,
            action=audit_log.AuditAction.JOB_RETRIED,
            actor_user_id=actor.id,
            actor_username=actor.username,
            target_type="review_job",
            target_id=str(job_public_id),
            outcome="success",
            metadata={
                "saved_result_available": saved_result_available,
                "new_job_public_id": str(new_job_public_id),
                "reason": safe_reason,
            },
        )
    return RetryResult(new_job_public_id, saved_result_available)
