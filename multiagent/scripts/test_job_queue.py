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


def _dung_schema_sach(conn):
    """Dung mot schema tam sach de test, tren KET NOI DA MO SAN.

    Nhan `conn` co san thay vi tu goi `db.psycopg.connect(...)`: chi buoc MO
    KET NOI moi duoc coi la "khong co Postgres" -> [SKIP] (xem __main__ ben
    duoi). DDL o day (DROP/CREATE SCHEMA, dam_bao_bang) phai duoc de loi that
    ra ngoai va lam test DO, khong duoc lot vao khoi try/except cua [SKIP] -
    lam vay se bien mot loi DDL that (sai cu phap, thieu quyen, xung dot
    index) thanh [SKIP] roi thoat 0, tuc bao XANH GIA.
    """
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


def test_duplicate_tra_dung_job_id_khi_node_co_nhieu_hash(conn):
    """Sua loi: job_moi_nhat(conn, node_id) chi loc theo node_id, khong loc
    content_hash, nen nhanh 'duplicate' cua enqueue() tung tra nham job MOI
    NHAT CUA NODE thay vi job dang THAT SU trung dedup voi cap (node_id,
    content_hash) dang hoi. Tai hien dung kich ban loi: mot node co hai job
    active khac hash, enqueue lai job dau tien phai tra ve id CUA NO, khong
    phai id cua job thu hai (moi hon)."""
    kq1 = q.enqueue(conn, "uuid-11", "hashA", "event")
    kq2 = q.enqueue(conn, "uuid-11", "hashB", "event")
    assert kq1["status"] == "queued" and kq2["status"] == "queued", (kq1, kq2)
    assert kq1["job_id"] != kq2["job_id"]

    kq3 = q.enqueue(conn, "uuid-11", "hashA", "event")
    assert kq3["status"] == "duplicate", kq3
    assert kq3["job_id"] == kq1["job_id"], (
        f"phai tra id cua job trung hash ({kq1['job_id']}), "
        f"khong phai job moi nhat cua node ({kq2['job_id']}): {kq3}")
    print("[PASS] duplicate tra dung job_id cua cap (node_id, content_hash) trung")
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
    kq = q.reclaim_stuck(conn)
    assert kq == {"queued": 1, "failed": 0}, kq
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "queued"
    print("[PASS] job ket qua 15 phut, attempts=1 < MAX_ATTEMPTS -> thu hoi ve queued")
    # Job vua thu hoi lai dang "queued" - don no (xem ly do o
    # test_dedup_chan_job_trung).
    job2 = q.claim(conn, "w-don")
    q.complete(conn, job2["id"])


def test_thu_hoi_job_ket_vuot_max_attempts_thi_dead_letter(conn):
    """Sua loi CRITICAL: truoc day reclaim_stuck() khong co tran, nen worker
    chet lien tuc se claim -> reclaim -> claim... VO HAN, attempts tang mai
    ma status khong bao gio toi `failed`. Tai hien dung kich ban do: mot job
    bi "worker chet" 3 lan lien tiep (khong bao gio goi fail()), xac nhan lan
    thu 3 di thang vao `failed` thay vi quay lai `queued` lan thu 4.
    """
    q.enqueue(conn, "uuid-10", "h10", "event")

    for lan in (1, 2):
        job = q.claim(conn, "w-chet")
        assert job["attempts"] == lan, job
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE review_job SET claimed_at = now() - interval '20 minutes' "
                "WHERE id=%s", (job["id"],))
        kq = q.reclaim_stuck(conn)
        assert kq == {"queued": 1, "failed": 0}, (lan, kq)

    # Lan claim thu 3: attempts=3=MAX_ATTEMPTS. Worker lai chet, khong goi
    # fail(). Neu reclaim_stuck() khong co tran (ban loi), no se tra job nay
    # ve "queued" - vong lap vo han. Ban da sua phai tra ve "failed".
    job = q.claim(conn, "w-chet")
    assert job["attempts"] == 3, job
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE review_job SET claimed_at = now() - interval '20 minutes' "
            "WHERE id=%s", (job["id"],))
    kq = q.reclaim_stuck(conn)
    assert kq == {"queued": 0, "failed": 1}, kq
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE id=%s", (job["id"],))
        status, loi = cur.fetchone()
    assert status == "failed", status
    assert loi and "worker" in loi.lower(), loi
    assert q.co_job_that_bai(conn, "uuid-10", "h10") is True
    print("[PASS] worker chet lien tuc: reclaim_stuck vao dead-letter o lan thu 3, "
          "khong lap vo han")


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
    # Don job moi (tao boi force=True) - xem ly do o test_dedup_chan_job_trung.
    job2 = q.claim(conn, "w-don")
    q.complete(conn, job2["id"])


def test_force_nguyen_tu_loi_giua_chung_khong_mat_job(conn):
    """Sua loi Important: UPDATE (superseded) va INSERT (job moi) o nhanh
    force truoc day la hai cau lenh rieng tren autocommit=True. Gian doan
    giua hai cau (crash, mat ket noi) se de lai job cu da `superseded` MA
    KHONG CO job thay the - nut "Cham lai" mat job im lang. Tai hien bang
    loi that (khong mock): ep INSERT loi NOT NULL that bang `source=None`
    (KHONG dung content_hash=None - lam vay se lam chinh cau UPDATE khop 0
    dong vi so sanh NULL trong WHERE luon false, che mat dieu dang kiem: da
    dung `content_hash="h12"` that de UPDATE khop dung dong can superseded,
    chi INSERT moi loi). Sau do xac nhan job cu KHONG bi doi sang superseded
    - ca cap UPDATE+INSERT phai cung ROLLBACK vi nam chung mot
    conn.transaction().
    """
    q.enqueue(conn, "uuid-12", "h12", "event")
    job = q.claim(conn, "w1")
    q.complete(conn, job["id"])

    da_nem_loi = False
    try:
        q.enqueue(conn, "uuid-12", "h12", None, force=True)
    except Exception:
        da_nem_loi = True  # dung ky vong: NotNullViolation tu source=None
    assert da_nem_loi, "phai nem loi NOT NULL, khong duoc chay lot qua"

    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        status = cur.fetchone()[0]
    assert status == "done", (
        f"loi giua UPDATE va INSERT lam mat job: trang thai la '{status}' "
        f"thay vi 'done' (phai duoc rollback ve nguyen trang)")
    print("[PASS] force nguyen tu: loi giua UPDATE va INSERT duoc rollback, khong mat job")


if __name__ == "__main__":
    try:
        conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"Chay `docker compose up -d` roi thu lai. LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)
    conn = _dung_schema_sach(conn)

    failed = False
    for fn in (
        test_enqueue_va_claim,
        test_dedup_chan_job_trung,
        test_noi_dung_doi_thi_tao_job_moi,
        test_duplicate_tra_dung_job_id_khi_node_co_nhieu_hash,
        test_skip_locked_hai_worker_khong_giam_chan,
        test_fail_backoff_roi_dead_letter,
        test_job_failed_khong_bi_dedup_chan,
        test_co_job_that_bai,
        test_thu_hoi_job_ket_vuot_max_attempts_thi_dead_letter,
        test_thu_hoi_job_ket,
        test_force_dat_superseded_va_tao_job_moi,
        test_force_nguyen_tu_loi_giua_chung_khong_mat_job,
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
