"""Nhat ky truy vet: mot ban ghi append-only cho moi lan cham.

Thiet ke: docs/operations.md muc 2 (ghi cai gi, khong ghi cai gi).
Cho luu: Postgres thay vi JSONL - ly do doi ket luan o spec 2026-08-07 muc 2.1
(tien de da doi: luc operations.md viet thi phia Multi-Agent chua co CSDL nao).

Tra loi duoc cau "bai nay bi chan hoi thang truoc, vi sao" - Drupal giu duoc
DIEM BAO NHIEU qua revision, nhung khong giu BOI CANH sinh ra no.
"""
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from review_platform import migrations, sites

TEN_BANG = "run_log"


class AuditStateError(RuntimeError):
    pass


def dam_bao_bang(conn) -> None:
    """Compatibility guard: schema audit chi duoc tao boi migration runner."""
    migrations.require_current(
        conn,
        Path(__file__).resolve().parents[1] / "migrations",
    )


def _js(x) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)


def ghi_scoped(
    conn,
    *,
    run_public_id: UUID,
    job: dict,
    content_hash: str,
    duration_ms: int,
    report: dict,
    config_meta: dict,
    usage: list,
    model: str,
    payload: dict,
) -> int:
    """Ghi immutable review result cung snapshot scope cua job."""
    forbidden = {"title", "body", "summary"} & set(payload)
    if forbidden:
        raise ValueError(
            "payload khong duoc chua full content top-level: "
            + ", ".join(sorted(forbidden))
        )

    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TEN_BANG} ("
            "job_id, node_id, content_hash, duration_ms, decision, final_score, "
            "missing_agents, veto_reason, note, agent_results, config_meta, "
            "usage, model, payload, public_id, site_id, profile_id, policy_version, "
            "external_content_id, external_revision_id, content_type, langcode, "
            "correlation_id, writeback_status"
            ") VALUES ("
            "%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s::jsonb,"
            "%s::jsonb,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s"
            ") RETURNING id",
            (
                job["id"],
                job["external_content_id"],
                content_hash,
                duration_ms,
                report.get("decision"),
                report.get("final_score"),
                _js(report.get("missing_agents") or []),
                report.get("veto_reason"),
                report.get("note"),
                _js(report.get("details") or {}),
                _js(config_meta),
                _js(usage),
                model,
                _js(payload),
                run_public_id,
                job["site_id"],
                job["profile_id"],
                job["policy_version"],
                job["external_content_id"],
                job.get("external_revision_id"),
                job["content_type"],
                job["langcode"],
                job["correlation_id"],
                "pending",
            ),
        )
        return cur.fetchone()[0]


def ghi(conn, *, job_id, node_id: str, content_hash: str, duration_ms: int,
        report: dict, config_meta: dict, usage: list, model: str,
        payload: dict) -> int:
    """Ghi mot ban ghi. CHI INSERT - khong bao gio UPDATE hay DELETE.

    `final_score = None` duoc giu nguyen NULL, KHONG quy ve 0: None nghia la
    CHUA cham duoc (Compliance loi), khac han voi 0 diem.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, public_id, site_id, profile_id, policy_version, "
            "external_content_id, external_revision_id, content_type, langcode, "
            "correlation_id, source, supersedes_job_id "
            "FROM review_job WHERE id=%s",
            (job_id,),
        )
        row = cur.fetchone()
    if row is None:
        # Compatibility cho caller/test legacy khong co review_job tuong ung.
        context = sites.select_review_context(
            conn,
            UUID("00000000-0000-4000-8000-000000000001"),
            "cam_nang",
            "vi",
        )
        job = {
            "id": job_id,
            "public_id": uuid4(),
            "site_id": context.site.id,
            "profile_id": context.profile.id,
            "policy_version": context.profile.policy_version,
            "external_content_id": node_id,
            "external_revision_id": None,
            "content_type": context.profile.content_type,
            "langcode": context.profile.language_code,
            "correlation_id": uuid4(),
            "source": "legacy",
            "supersedes_job_id": None,
        }
    else:
        job = {
            "id": row[0],
            "public_id": row[1],
            "site_id": row[2],
            "profile_id": row[3],
            "policy_version": row[4],
            "external_content_id": row[5],
            "external_revision_id": row[6],
            "content_type": row[7],
            "langcode": row[8],
            "correlation_id": row[9],
            "source": row[10],
            "supersedes_job_id": row[11],
        }
    return ghi_scoped(
        conn,
        run_public_id=uuid4(),
        job=job,
        content_hash=content_hash,
        duration_ms=duration_ms,
        report=report,
        config_meta=config_meta,
        usage=usage,
        model=model,
        payload=payload,
    )


def da_cham_scoped(
    conn,
    *,
    site_id: UUID,
    external_content_id: str,
    content_hash: str,
    policy_version: str,
):
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, public_id, payload, writeback_status FROM {TEN_BANG} "
            "WHERE site_id=%s AND external_content_id=%s AND content_hash=%s "
            "AND policy_version=%s ORDER BY scored_at DESC, id DESC LIMIT 1",
            (site_id, external_content_id, content_hash, policy_version),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "run_id": row[1],
        "payload": row[2],
        "writeback_status": row[3],
    }


def da_cham(conn, node_id: str, content_hash: str):
    """Da co ket qua cho dung cap (node_id, content_hash) chua?

    Worker hoi cau nay TRUOC khi goi LLM. Co roi -> chi ghi lai `payload` cu
    sang Drupal, khong chay lai pipeline. Day la cho chan duong mat tien khi
    write_back that bai: cham lai mot bai ton $0,057 that.
    """
    return da_cham_scoped(
        conn,
        site_id=UUID("00000000-0000-4000-8000-000000000001"),
        external_content_id=node_id,
        content_hash=content_hash,
        policy_version="cam-nang-vn-v1",
    )


def _reusable_result(row):
    if row is None:
        return None
    return {
        "id": row[0],
        "run_id": row[1],
        "payload": row[2],
        "external_revision_id": row[3],
        "content_hash": row[4],
        "policy_version": row[5],
        "writeback_status": row[6],
    }


def find_reusable_writeback(conn, *, job: dict):
    """Tim saved callback result chi theo lien ket job tuong minh.

    ``run.content_hash`` la hash noi dung thuc te da cham, co the khac hash
    mong doi tren job legacy. Phai tra nguyen precondition da audit de result
    callback CAS o Plan 4 tu choi stale data; khong doi hash va khong goi LLM
    lan hai cho chinh job da co saved result.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, public_id, payload, external_revision_id, content_hash, "
            f"policy_version, writeback_status FROM {TEN_BANG} "
            "WHERE job_id=%s AND writeback_status IN ('pending','failed') "
            "ORDER BY scored_at DESC, id DESC LIMIT 1",
            (job["id"],),
        )
        own = cur.fetchone()
    if own is not None:
        return _reusable_result(own)

    if job.get("source") != "admin_retry" or job.get("supersedes_job_id") is None:
        return None
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT run.id, run.public_id, run.payload, run.external_revision_id, "
            f"run.content_hash, run.policy_version, run.writeback_status "
            f"FROM {TEN_BANG} AS run "
            "JOIN review_job AS target ON target.id=run.job_id "
            "WHERE target.id=%s AND target.status='failed' "
            "AND target.site_id=%s AND target.external_content_id=%s "
            "AND target.profile_id=%s AND target.policy_version=%s "
            "AND target.content_hash=%s "
            "AND target.external_revision_id IS NOT DISTINCT FROM %s "
            "AND run.site_id=%s AND run.external_content_id=%s "
            "AND run.profile_id=%s AND run.policy_version=%s "
            "AND run.external_revision_id IS NOT DISTINCT FROM "
            "target.external_revision_id "
            "AND run.writeback_status='failed' "
            "ORDER BY run.scored_at DESC, run.id DESC LIMIT 1",
            (
                job["supersedes_job_id"],
                job["site_id"],
                job["external_content_id"],
                job["profile_id"],
                job["policy_version"],
                job["content_hash"],
                job.get("external_revision_id"),
                job["site_id"],
                job["external_content_id"],
                job["profile_id"],
                job["policy_version"],
            ),
        )
        return _reusable_result(cur.fetchone())


def mark_writeback(
    conn,
    run_id: int,
    *,
    status: Literal["succeeded", "failed", "superseded"],
    error: str | None = None,
) -> None:
    """Chi cap nhat transport state; result/decision/payload luon immutable."""
    if status not in ("succeeded", "failed", "superseded"):
        raise ValueError(f"writeback status khong hop le: {status}")
    safe_error = None if error is None else str(error)[:1000]
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET writeback_status=%s, writeback_error=%s "
            "WHERE id=%s AND writeback_status IN ('pending','failed') RETURNING id",
            (status, safe_error, run_id),
        )
        updated = cur.fetchone()
    if updated is not None:
        return
    with conn.cursor() as cur:
        cur.execute(f"SELECT writeback_status FROM {TEN_BANG} WHERE id=%s", (run_id,))
        row = cur.fetchone()
    current = "khong ton tai" if row is None else row[0]
    raise AuditStateError(
        f"run {run_id} dang o trang thai {current}, khong the mark {status}"
    )
