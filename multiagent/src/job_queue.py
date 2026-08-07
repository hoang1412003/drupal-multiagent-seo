"""Hang doi cham diem, dat tren Postgres dang co.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md

VI SAO POSTGRES CHU KHONG PHAI REDIS/RABBITMQ (spec muc 2, quyet dinh Q1):
`FOR UPDATE SKIP LOCKED` cho dung nhung thu mot broker cho o quy mo nay -
nhieu worker khong giam chan nhau, job khong mat khi worker chet, retry co
backoff, dead-letter - ma khong them mot container phai van hanh, backup va
giai thich. Day la mau dung trong san pham that (pgmq, Oban, River,
Solid Queue). Khac biet chi xuat hien o quy mo hang nghin job/giay.
"""
import db

TEN_BANG = "review_job"

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
SUPERSEDED = "superseded"

MAX_ATTEMPTS = 3
BACKOFF_GIAY = (60, 300, 900)
KET_SAU_PHUT = 15


def dam_bao_bang(conn) -> None:
    """Tao bang neu chua co. Cung mau voi db.dam_bao_bang cho kb_chunk -
    khong dung framework migration, o hai bang thi do la ha tang thua."""
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {TEN_BANG} ("
            "  id           bigserial PRIMARY KEY,"
            "  node_id      text        NOT NULL,"
            "  content_hash text        NOT NULL,"
            "  status       text        NOT NULL,"
            "  attempts     int         NOT NULL DEFAULT 0,"
            "  run_after    timestamptz NOT NULL DEFAULT now(),"
            "  claimed_at   timestamptz,"
            "  claimed_by   text,"
            "  last_error   text,"
            "  source       text        NOT NULL,"
            "  created_at   timestamptz NOT NULL DEFAULT now(),"
            "  updated_at   timestamptz NOT NULL DEFAULT now()"
            ")"
        )
        # Index BO PHAN: chi rang buoc tren job chua ket thuc. Co y loai
        # `failed` (job hong phai xep hang lai duoc) va `superseded` (danh
        # rieng cho nut "Cham lai" thu cong).
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {TEN_BANG}_dedup "
            f"ON {TEN_BANG} (node_id, content_hash) "
            f"WHERE status IN ('{QUEUED}', '{RUNNING}', '{DONE}')"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {TEN_BANG}_claim "
            f"ON {TEN_BANG} (status, run_after)"
        )


def enqueue(conn, node_id: str, content_hash: str, source: str,
            force: bool = False) -> dict:
    """Xep mot job. Trung dedup -> khong tao gi, tra status='duplicate'.

    `force=True` (nut "Cham lai" thu cong): danh dau job `done` cua dung cap
    (node_id, content_hash) thanh `superseded` de no roi khoi index dedup,
    roi chen job moi. KHONG xoa ban ghi cu - lich su van tra duoc.
    """
    if force:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() "
                f"WHERE node_id=%s AND content_hash=%s AND status=%s",
                (SUPERSEDED, node_id, content_hash, DONE),
            )
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TEN_BANG} (node_id, content_hash, status, source) "
            f"VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (node_id, content_hash, QUEUED, source),
        )
        row = cur.fetchone()
    if row is None:
        cu = job_moi_nhat(conn, node_id)
        return {"status": "duplicate", "job_id": cu["id"] if cu else None}
    return {"status": QUEUED, "job_id": row[0]}


def claim(conn, worker_id: str):
    """Nhan mot job. Tra None khi khong co viec.

    SKIP LOCKED: worker A khoa dong no lay, worker B thay dong dang khoa thi
    BO QUA va lay dong ke tiep - khong khoa toan bang, khong can khoa phan tan.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, claimed_at=now(), claimed_by=%s, "
            f"attempts=attempts+1, updated_at=now() "
            f"WHERE id = (SELECT id FROM {TEN_BANG} "
            f"            WHERE status=%s AND run_after <= now() "
            f"            ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) "
            f"RETURNING id, node_id, content_hash, attempts",
            (RUNNING, worker_id, QUEUED),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "node_id": row[1], "content_hash": row[2],
            "attempts": row[3]}


def complete(conn, job_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() WHERE id=%s",
            (DONE, job_id),
        )


def fail(conn, job_id: int, loi: str, attempts: int) -> str:
    """That bai mot lan. Chua het luot -> xep lai voi backoff; het -> dead-letter.

    `attempts` la so lan DA thu (claim() tang truoc khi chay), nen lan dau
    that bai co attempts = 1 va dung BACKOFF_GIAY[0].
    """
    if attempts >= MAX_ATTEMPTS:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TEN_BANG} SET status=%s, last_error=%s, updated_at=now() "
                f"WHERE id=%s",
                (FAILED, loi, job_id),
            )
        return FAILED

    giay = BACKOFF_GIAY[min(attempts - 1, len(BACKOFF_GIAY) - 1)]
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, last_error=%s, "
            f"run_after = now() + (%s * interval '1 second'), updated_at=now() "
            f"WHERE id=%s",
            (QUEUED, loi, giay, job_id),
        )
    return QUEUED


def reclaim_stuck(conn) -> int:
    """Thu hoi job ket o `running` vi worker chet giua chung."""
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, run_after=now(), updated_at=now() "
            f"WHERE status=%s AND claimed_at < now() - interval '{KET_SAU_PHUT} minutes'",
            (QUEUED, RUNNING),
        )
        return cur.rowcount


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


def thong_ke(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status, count(*) FROM {TEN_BANG} GROUP BY status")
        dem = dict(cur.fetchall())
    return {QUEUED: dem.get(QUEUED, 0), RUNNING: dem.get(RUNNING, 0),
            FAILED: dem.get(FAILED, 0)}
