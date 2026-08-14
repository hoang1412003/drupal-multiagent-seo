"""Hang doi cham diem, dat tren Postgres dang co.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md

VI SAO POSTGRES CHU KHONG PHAI REDIS/RABBITMQ (spec muc 2, quyet dinh Q1):
`FOR UPDATE SKIP LOCKED` cho dung nhung thu mot broker cho o quy mo nay -
nhieu worker khong giam chan nhau, job khong mat khi worker chet, retry co
backoff, dead-letter - ma khong them mot container phai van hanh, backup va
giai thich. Day la mau dung trong san pham that (pgmq, Oban, River,
Solid Queue). Khac biet chi xuat hien o quy mo hang nghin job/giay.
"""
import math
from pathlib import Path
import random
from uuid import UUID, uuid4

from review_platform.context import ReviewContext
from review_platform import migrations, sites

TEN_BANG = "review_job"

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
SUPERSEDED = "superseded"
DUPLICATE = "duplicate"

MAX_ATTEMPTS = 3
BACKOFF_GIAY = (60, 300)
KET_SAU_PHUT = 15


def dam_bao_bang(conn) -> None:
    """Compatibility guard: schema queue chi duoc tao boi migration runner."""
    migrations.require_current(
        conn,
        Path(__file__).resolve().parents[1] / "migrations",
    )


DEFAULT_SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_CONTENT_TYPE = "cam_nang"
DEFAULT_LANGCODE = "vi"


def _validate_non_empty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} khong duoc rong")
    return value


def _insert_scoped(
    conn,
    context: ReviewContext,
    external_content_id: str,
    content_hash: str,
    source: str,
    external_revision_id: str | None,
    correlation_id: UUID,
    supersedes_job_id: int | None,
    content_hash_version: int,
):
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TEN_BANG} ("
            "node_id, content_hash, status, source, site_id, profile_id, "
            "policy_version, external_content_id, external_revision_id, "
            "content_type, langcode, correlation_id, supersedes_job_id, "
            "content_hash_version"
            ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING RETURNING id, public_id",
            (
                external_content_id,
                content_hash,
                QUEUED,
                source,
                context.site.id,
                context.profile.id,
                context.profile.policy_version,
                external_content_id,
                external_revision_id,
                context.profile.content_type,
                context.profile.language_code,
                correlation_id,
                supersedes_job_id,
                content_hash_version,
            ),
        )
        return cur.fetchone()


def _active_duplicate_id(
    conn,
    *,
    site_id: UUID,
    external_content_id: str,
    content_hash: str,
    policy_version: str,
):
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, public_id FROM {TEN_BANG} "
            "WHERE site_id=%s AND external_content_id=%s AND content_hash=%s "
            "AND policy_version=%s AND status IN (%s,%s,%s) "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (
                site_id,
                external_content_id,
                content_hash,
                policy_version,
                QUEUED,
                RUNNING,
                DONE,
            ),
        )
        return cur.fetchone()


def enqueue_scoped(
    conn,
    context: ReviewContext,
    external_content_id: str,
    content_hash: str,
    source: str,
    *,
    external_revision_id: str | None = None,
    force: bool = False,
    correlation_id: UUID | None = None,
    supersedes_job_id: int | None = None,
    content_hash_version: int = 1,
) -> dict:
    """Xep job voi snapshot site/profile/policy; dedup khong xuyen site.

    `content_hash_version` mac dinh 1 de duong legacy `/jobs` giu nguyen hanh
    vi bon field. Chi `/api/v1/jobs` moi truyen 2 (sau field). Worker chon
    thuat toan fingerprint theo dung cot nay, nen sai o day la sai o ca cua
    so rollback.
    """
    if content_hash_version not in (1, 2):
        raise ValueError("content_hash_version chi duoc la 1 hoac 2")
    external_content_id = _validate_non_empty(
        "external_content_id", external_content_id
    )
    content_hash = _validate_non_empty("content_hash", content_hash)
    source = _validate_non_empty("source", source)
    if external_revision_id is not None:
        external_revision_id = _validate_non_empty(
            "external_revision_id", external_revision_id
        )
    if supersedes_job_id is not None and not force:
        raise ValueError("supersedes_job_id chi hop le khi force=True")
    correlation_id = correlation_id or uuid4()

    if not force:
        # Khoa moi job co the anh huong quyet dinh truoc khi INSERT. Neu mot
        # worker dang dua job running -> failed, hai transaction se xep hang
        # tren cung row; khong con khe "kiem dead-letter -> job thanh failed
        # -> INSERT queued" hoi sinh job da het retry.
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, status, public_id FROM {TEN_BANG} "
                    "WHERE site_id=%s AND external_content_id=%s "
                    "AND content_hash=%s AND policy_version=%s "
                    "AND status IN (%s,%s,%s,%s) "
                    "ORDER BY created_at DESC, id DESC FOR UPDATE",
                    (
                        context.site.id,
                        external_content_id,
                        content_hash,
                        context.profile.policy_version,
                        QUEUED,
                        RUNNING,
                        DONE,
                        FAILED,
                    ),
                )
                existing = list(cur.fetchall())

            failed_row = next(
                (row for row in existing if row[1] == FAILED),
                None,
            )
            if failed_row is not None:
                return {
                    "status": "dead_letter",
                    "job_id": failed_row[0],
                    "public_id": failed_row[2],
                }

            active_row = next(
                (row for row in existing if row[1] in (QUEUED, RUNNING, DONE)),
                None,
            )
            if active_row is not None:
                return {
                    "status": DUPLICATE,
                    "job_id": active_row[0],
                    "public_id": active_row[2],
                }

            row = _insert_scoped(
                conn,
                context,
                external_content_id,
                content_hash,
                source,
                external_revision_id,
                correlation_id,
                supersedes_job_id,
                content_hash_version,
            )
    else:
        with conn.transaction():
            target_id = supersedes_job_id
            if target_id is not None:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT site_id, external_content_id, profile_id, "
                        f"policy_version, status FROM {TEN_BANG} "
                        "WHERE id=%s FOR UPDATE",
                        (target_id,),
                    )
                    target = cur.fetchone()
                expected = (
                    context.site.id,
                    external_content_id,
                    context.profile.id,
                    context.profile.policy_version,
                )
                if target is None or target[:4] != expected or target[4] not in (
                    FAILED,
                    DONE,
                    SUPERSEDED,
                ):
                    raise ValueError("supersedes_job_id khong cung scope/trang thai")
                if target[4] == DONE:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() "
                            "WHERE id=%s",
                            (SUPERSEDED, target_id),
                        )
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT id, status FROM {TEN_BANG} "
                        "WHERE site_id=%s AND external_content_id=%s "
                        "AND profile_id=%s AND policy_version=%s "
                        "AND content_hash=%s AND status IN (%s,%s) "
                        "ORDER BY created_at DESC, id DESC LIMIT 1 FOR UPDATE",
                        (
                            context.site.id,
                            external_content_id,
                            context.profile.id,
                            context.profile.policy_version,
                            content_hash,
                            DONE,
                            FAILED,
                        ),
                    )
                    target = cur.fetchone()
                if target is not None:
                    target_id = target[0]
                    # Job DONE bi thay the nen chuyen `superseded`. Job FAILED
                    # thi GIU nguyen `failed`: no la bang chung dead-letter,
                    # job moi chi tro nguoc ve no qua supersedes_job_id.
                    if target[1] == DONE:
                        with conn.cursor() as cur:
                            cur.execute(
                                f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() "
                                "WHERE id=%s",
                                (SUPERSEDED, target_id),
                            )

            row = _insert_scoped(
                conn,
                context,
                external_content_id,
                content_hash,
                source,
                external_revision_id,
                correlation_id,
                target_id,
                content_hash_version,
            )

    if row is None:
        duplicate = _active_duplicate_id(
            conn,
            site_id=context.site.id,
            external_content_id=external_content_id,
            content_hash=content_hash,
            policy_version=context.profile.policy_version,
        )
        return {
            "status": DUPLICATE,
            "job_id": None if duplicate is None else duplicate[0],
            "public_id": None if duplicate is None else duplicate[1],
        }
    return {"status": QUEUED, "job_id": row[0], "public_id": row[1]}


def enqueue(
    conn,
    node_id: str,
    content_hash: str,
    source: str,
    force: bool = False,
) -> dict:
    """Compatibility wrapper cho endpoint Drupal legacy mot site."""
    context = sites.select_review_context(
        conn,
        DEFAULT_SITE_ID,
        DEFAULT_CONTENT_TYPE,
        DEFAULT_LANGCODE,
    )
    return enqueue_scoped(
        conn,
        context,
        node_id,
        content_hash,
        source,
        force=force,
    )


def claim(conn, worker_id: str):
    """Nhan mot job. Tra None khi khong co viec.

    SKIP LOCKED: worker A khoa dong no lay, worker B thay dong dang khoa thi
    BO QUA va lay dong ke tiep - khong khoa toan bang, khong can khoa phan tan.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} AS claimed SET status=%s, claimed_at=now(), claimed_by=%s, "
            f"attempts=attempts+1, updated_at=now() "
            f"WHERE claimed.id = (SELECT job.id FROM {TEN_BANG} AS job "
            f"            JOIN site AS owner ON owner.id=job.site_id "
            f"            WHERE job.status=%s AND job.run_after <= now() "
            f"              AND owner.active AND NOT owner.intake_paused "
            f"            ORDER BY job.created_at, job.id "
            f"            FOR UPDATE OF job SKIP LOCKED LIMIT 1) "
            f"RETURNING claimed.id, claimed.public_id, claimed.site_id, "
            f"claimed.profile_id, claimed.policy_version, "
            f"claimed.external_content_id, claimed.external_revision_id, "
            f"claimed.content_type, claimed.langcode, claimed.correlation_id, "
            f"claimed.content_hash, claimed.attempts, claimed.source, "
            f"claimed.supersedes_job_id",
            (RUNNING, worker_id, QUEUED),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "public_id": row[1],
        "site_id": row[2],
        "profile_id": row[3],
        "policy_version": row[4],
        "external_content_id": row[5],
        "node_id": row[5],
        "external_revision_id": row[6],
        "content_type": row[7],
        "langcode": row[8],
        "correlation_id": row[9],
        "content_hash": row[10],
        "attempts": row[11],
        "source": row[12],
        "supersedes_job_id": row[13],
    }


def complete(conn, job_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() WHERE id=%s",
            (DONE, job_id),
        )


def fail(
    conn,
    job_id: int,
    loi: str,
    attempts: int | None = None,
    *,
    retry_after_seconds: float | None = None,
    rng=random.random,
) -> str:
    """That bai mot lan. Chua het luot -> xep lai voi backoff; het -> dead-letter.

    So lan thu duoc doc tu DB (claim tang truoc khi chay), khong tin du lieu
    caller. Tham so `attempts` chi duoc giu tam de worker legacy chua gay API.
    """
    del attempts
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT attempts FROM {TEN_BANG} WHERE id=%s FOR UPDATE",
                (job_id,),
            )
            row = cur.fetchone()
        if row is None:
            raise ValueError(f"khong co job id={job_id}")
        actual_attempts = row[0]

        if actual_attempts >= MAX_ATTEMPTS:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {TEN_BANG} SET status=%s, last_error=%s, "
                    f"updated_at=now() WHERE id=%s",
                    (FAILED, loi, job_id),
                )
            return FAILED

        base = BACKOFF_GIAY[
            min(max(actual_attempts - 1, 0), len(BACKOFF_GIAY) - 1)
        ]
        jitter_ratio = 0.10
        giay = base + (float(rng()) * base * jitter_ratio)
        if retry_after_seconds is not None:
            retry_after = float(retry_after_seconds)
            if not math.isfinite(retry_after):
                raise ValueError("retry_after_seconds phai la so huu han")
            giay = max(giay, min(max(retry_after, 0.0), 600.0))
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TEN_BANG} SET status=%s, last_error=%s, "
                f"run_after = now() + (%s * interval '1 second'), updated_at=now() "
                f"WHERE id=%s",
                (QUEUED, loi, giay, job_id),
            )
        return QUEUED


def reclaim_stuck(conn) -> dict:
    """Thu hoi job ket o `running` vi worker chet giua chung (OOM, kill -9).

    Worker chet cung khong kip goi fail(), nen truoc day ham nay chi day job
    ve `queued` - KHONG co tran nao, nen claim -> worker chet -> thu hoi ->
    claim... lap vo han: `attempts` cu tang ma `status` khong bao gio toi
    `failed`. Day chinh la vong lap tieu tien API vo han ma spec muc 6.3.1
    dung co_job_that_bai() de chan, nhung co_job_that_bai() chi co tac dung
    khi job da TOI DUOC `failed` - duong nay truoc day khong bao gio toi.

    Nen o day ap luon tran MAX_ATTEMPTS: vuot nguong thi vao thang `failed`
    (dead-letter) thay vi `queued`. CASE WHEN trong CUNG mot UPDATE de giu
    tinh nguyen tu (khong tach hai cau UPDATE roi tu quyet dinh o Python).
    """
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET "
            f"  status = CASE WHEN attempts >= %s THEN %s ELSE %s END, "
            f"  last_error = CASE WHEN attempts >= %s THEN %s ELSE last_error END, "
            f"  run_after = CASE WHEN attempts >= %s THEN run_after ELSE now() END, "
            f"  updated_at = now() "
            f"WHERE status=%s AND claimed_at < now() - interval '{KET_SAU_PHUT} minutes' "
            f"RETURNING status",
            (MAX_ATTEMPTS, FAILED, QUEUED,
             MAX_ATTEMPTS, "worker chet giua chung (khong kip goi fail), vuot MAX_ATTEMPTS",
             MAX_ATTEMPTS,
             RUNNING),
        )
        rows = cur.fetchall()
    return {
        "queued": sum(1 for (s,) in rows if s == QUEUED),
        "failed": sum(1 for (s,) in rows if s == FAILED),
    }


def co_job_that_bai(conn, node_id: str, content_hash: str) -> bool:
    """Da co job dead-letter cho dung cap nay chua?

    Vong doi soat PHAI hoi cau nay truoc khi enqueue. Khong hoi thi no se
    hoi sinh job da dead-letter moi 5 phut, va co che dead-letter bi vo hieu
    hoan toan - thanh vong lap tieu tien API vo han (spec muc 6.3.1).
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {TEN_BANG} "
            f"WHERE node_id=%s AND content_hash=%s AND status=%s LIMIT 1",
            (node_id, content_hash, FAILED),
        )
        return cur.fetchone() is not None


def job_moi_nhat(conn, node_id: str):
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, status, attempts, last_error, created_at, updated_at "
            f"FROM {TEN_BANG} WHERE node_id=%s ORDER BY created_at DESC LIMIT 1",
            (node_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "status": row[1], "attempts": row[2],
            "last_error": row[3], "created_at": row[4], "updated_at": row[5]}


_COT_TRANG_THAI = (
    "public_id, status, attempts, last_error, external_content_id, "
    "external_revision_id, content_hash, content_hash_version, "
    "policy_version, source, created_at, updated_at"
)


def _trang_thai_tu_row(row) -> dict:
    return {
        "public_id": row[0],
        "status": row[1],
        "attempts": row[2],
        "last_error": row[3],
        "external_content_id": row[4],
        "external_revision_id": row[5],
        "content_hash": row[6],
        "content_hash_version": row[7],
        "policy_version": row[8],
        "source": row[9],
        "created_at": row[10],
        "updated_at": row[11],
    }


def job_theo_public_id(conn, *, site_id: UUID, public_id: UUID):
    """Tra job theo UUID cong khai, LUON loc theo site cua credential.

    Loc site o day chu khong o caller: mot job cua site khac phai khong tim
    thay duoc, de client khong do duoc UUID nao ton tai tren he thong.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COT_TRANG_THAI} FROM {TEN_BANG} "
            "WHERE public_id=%s AND site_id=%s",
            (public_id, site_id),
        )
        row = cur.fetchone()
    return None if row is None else _trang_thai_tu_row(row)


def job_moi_nhat_scoped(conn, *, site_id: UUID, external_content_id: str):
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COT_TRANG_THAI} FROM {TEN_BANG} "
            "WHERE site_id=%s AND external_content_id=%s "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (site_id, external_content_id),
        )
        row = cur.fetchone()
    return None if row is None else _trang_thai_tu_row(row)


def thong_ke(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status, count(*) FROM {TEN_BANG} GROUP BY status")
        dem = dict(cur.fetchall())
    return {QUEUED: dem.get(QUEUED, 0), RUNNING: dem.get(RUNNING, 0),
            FAILED: dem.get(FAILED, 0)}
