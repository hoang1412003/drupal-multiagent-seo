"""Test hang doi review_job (spec 2026-08-07 muc 5.1, 6.2).

CAN POSTGRES THAT, khac voi cac bo test khac cua du an. Ly do: `FOR UPDATE
SKIP LOCKED` la thu dang kiem nhat o day va no KHONG gia lap duoc - mot
FakeConn se cho qua ca mot ban cai dat khong he co SKIP LOCKED.

Khong ket noi duoc -> in [SKIP] va thoat 0, de bo test van "chay duoc o bat cu
dau". NHUNG [SKIP] KHONG PHAI [PASS] - xem docs/pre-demo-checklist.md muc 5.

Chay: .venv\\Scripts\\python.exe scripts\\test_job_queue.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
import job_queue as q

SCHEMA = "vf_test_job_queue"


def _mo_conn():
    """Mot ket noi RIENG (khong dung db.get_conn cache) tro vao schema tam."""
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}")
    return conn


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    q.dam_bao_bang(conn)
    return conn


def test_enqueue_va_claim(conn):
    kq = q.enqueue(conn, "uuid-1", "hash-a", "event")
    assert kq["status"] == "queued", kq
    job = q.claim(conn, "w1")
    assert job["node_id"] == "uuid-1" and job["content_hash"] == "hash-a", job
    assert job["attempts"] == 1, job
    assert q.claim(conn, "w1") is None, "khong con job nao ma van claim duoc"
    print("[PASS] enqueue roi claim ra dung job, claim lan hai tra None")


def test_dedup_chan_job_trung(conn):
    q.enqueue(conn, "uuid-2", "hash-b", "event")
    kq = q.enqueue(conn, "uuid-2", "hash-b", "reconcile")
    assert kq["status"] == "duplicate", kq
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM review_job WHERE node_id='uuid-2'")
        assert cur.fetchone()[0] == 1, "dedup khong chan"
    print("[PASS] cung (node_id, content_hash) -> chi mot job")
    # Don sach job vua tao: claim() la FIFO tren CA BANG (dung thiet ke), nen
    # job "queued" bo quen o day se bi cac test SAU nhan nham thay vi job cua
    # chinh no. Cac test enqueue-roi-khong-claim deu phai tu don o cuoi.
    job = q.claim(conn, "w-don")
    q.complete(conn, job["id"])


def test_noi_dung_doi_thi_tao_job_moi(conn):
    q.enqueue(conn, "uuid-3", "hash-c", "event")
    kq = q.enqueue(conn, "uuid-3", "hash-KHAC", "event")
    assert kq["status"] == "queued", kq
    print("[PASS] content_hash khac -> job moi")
    # Don ca hai job (xem ly do o test_dedup_chan_job_trung).
    for _ in range(2):
        job = q.claim(conn, "w-don")
        q.complete(conn, job["id"])


def test_skip_locked_hai_worker_khong_giam_chan(conn):
    """Phep kiem QUAN TRONG NHAT cua file nay.

    Mo mot giao dich tren conn A va giu no, roi cho conn B claim. Neu cau
    UPDATE thieu SKIP LOCKED thi B se DOI khoa cua A - va vi B dat
    lock_timeout = 2s nen no nem loi thay vi treo mai. Treo mai la kieu that
    bai te nhat cho mot bo test.
    """
    q.enqueue(conn, "uuid-4a", "h4a", "event")
    q.enqueue(conn, "uuid-4b", "h4b", "event")

    conn_b = _mo_conn()
    with conn_b.cursor() as cur:
        cur.execute("SET lock_timeout = '2s'")
    try:
        with conn.transaction():
            job_a = q.claim(conn, "wA")
            job_b = q.claim(conn_b, "wB")
            assert job_a is not None and job_b is not None, (job_a, job_b)
            assert job_a["id"] != job_b["id"], "hai worker claim trung mot job"
        print("[PASS] SKIP LOCKED: hai worker nhan hai job khac nhau")
    finally:
        conn_b.close()


def test_fail_backoff_roi_dead_letter(conn):
    q.enqueue(conn, "uuid-5", "h5", "event")
    job = q.claim(conn, "w1")
    assert q.fail(conn, job["id"], "loi 1", job["attempts"]) == "queued"
    with conn.cursor() as cur:
        cur.execute("SELECT run_after > now() FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] is True, "backoff khong day run_after ra sau"
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s", (job["id"],))

    job = q.claim(conn, "w1")
    assert job["attempts"] == 2, job
    assert q.fail(conn, job["id"], "loi 2", job["attempts"]) == "queued"
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s", (job["id"],))

    job = q.claim(conn, "w1")
    assert job["attempts"] == 3, job
    assert q.fail(conn, job["id"], "loi 3", job["attempts"]) == "failed"
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE id=%s", (job["id"],))
        status, loi = cur.fetchone()
    assert status == "failed" and loi == "loi 3", (status, loi)
    print("[PASS] 3 lan that bai -> dead-letter, giu last_error")


def test_job_failed_khong_bi_dedup_chan(conn):
    """Dedup CO Y loai `failed` - job hong phai xep hang lai duoc."""
    kq = q.enqueue(conn, "uuid-5", "h5", "manual")
    assert kq["status"] == "queued", kq
    print("[PASS] job da failed khong chan job moi cung hash")
    # Don job "queued" vua tao (xem ly do o test_dedup_chan_job_trung).
    job = q.claim(conn, "w-don")
    q.complete(conn, job["id"])


def test_co_job_that_bai(conn):
    assert q.co_job_that_bai(conn, "uuid-5", "h5") is True
    assert q.co_job_that_bai(conn, "uuid-5", "hash-khong-co") is False
    print("[PASS] co_job_that_bai tra dung ca hai chieu")


def test_thu_hoi_job_ket(conn):
    q.enqueue(conn, "uuid-6", "h6", "event")
    job = q.claim(conn, "w-chet")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE review_job SET claimed_at = now() - interval '20 minutes' "
            "WHERE id=%s", (job["id"],))
    assert q.reclaim_stuck(conn) == 1
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "queued"
    print("[PASS] job ket qua 15 phut duoc thu hoi ve queued")
    # Job vua thu hoi lai dang "queued" - don no (xem ly do o
    # test_dedup_chan_job_trung).
    job2 = q.claim(conn, "w-don")
    q.complete(conn, job2["id"])


def test_force_dat_superseded_va_tao_job_moi(conn):
    q.enqueue(conn, "uuid-7", "h7", "event")
    job = q.claim(conn, "w1")
    q.complete(conn, job["id"])
    assert q.enqueue(conn, "uuid-7", "h7", "event")["status"] == "duplicate"

    kq = q.enqueue(conn, "uuid-7", "h7", "manual", force=True)
    assert kq["status"] == "queued", kq
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "superseded"
    print("[PASS] force -> job cu superseded, job moi tao duoc")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"Chay `docker compose up -d` roi thu lai. LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_enqueue_va_claim,
        test_dedup_chan_job_trung,
        test_noi_dung_doi_thi_tao_job_moi,
        test_skip_locked_hai_worker_khong_giam_chan,
        test_fail_backoff_roi_dead_letter,
        test_job_failed_khong_bi_dedup_chan,
        test_co_job_that_bai,
        test_thu_hoi_job_ket,
        test_force_dat_superseded_va_tao_job_moi,
    ):
        try:
            fn(conn)
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
