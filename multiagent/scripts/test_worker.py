"""Test worker: xu ly mot job (spec 2026-08-07 muc 6.1, 7).

KHONG goi LLM, KHONG can Drupal: tiem `invoke` va `write_back_fn` gia.
Can Postgres that cho queue/run_log - [SKIP] neu khong co.
Chay: .venv\\Scripts\\python.exe scripts\\test_worker.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import db
import job_queue as q
import worker

SCHEMA = "vf_test_worker"

_STATE_XONG = {
    "node_id": "uuid-1",
    "decision": "needs_revision",
    "final_score": 76.5,
    "fields": {"title": "T", "body": "B", "summary": "S", "meta_description": "M"},
    "report": {
        "node_id": "uuid-1", "final_score": 76.5, "decision": "needs_revision",
        "missing_agents": [], "details": {"seo": {"score": 70, "issues": []}},
    },
}


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    q.dam_bao_bang(conn)
    audit.dam_bao_bang(conn)
    return conn


def _job(conn, node_id, content_hash):
    q.enqueue(conn, node_id, content_hash, "event")
    return q.claim(conn, "test")


def test_job_thanh_cong_ghi_run_log_va_dong_job(conn):
    job = _job(conn, "uuid-1", "h1")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              write_back_fn=lambda **kw: True)
    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "done"
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-1'")
        assert cur.fetchone()[0] == 1
    print("[PASS] job thanh cong -> run_log co ban ghi, job = done")


def test_write_back_that_bai_thi_job_xep_lai(conn):
    job = _job(conn, "uuid-2", "h2")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              write_back_fn=lambda **kw: False)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE id=%s",
                    (job["id"],))
        status, loi = cur.fetchone()
    assert status == "queued" and "write-back" in loi.lower(), (status, loi)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-2'")
        assert cur.fetchone()[0] == 1, "run_log phai ghi TRUOC khi write_back"
    print("[PASS] write_back False -> job ve queued, run_log da ghi")


def test_da_co_run_log_thi_KHONG_goi_lai_pipeline(conn):
    """Chot chan tien: cham lai mot bai ton $0,057 that."""
    job1 = _job(conn, "uuid-3", "h3")
    worker.chay_mot_job(conn, job1, invoke=lambda s: _STATE_XONG,
                        write_back_fn=lambda **kw: False)
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s",
                    (job1["id"],))

    da_goi = []

    def _invoke_khong_duoc_goi(state):
        da_goi.append(state)
        return _STATE_XONG

    job2 = q.claim(conn, "test")
    ket = worker.chay_mot_job(conn, job2, invoke=_invoke_khong_duoc_goi,
                              write_back_fn=lambda **kw: True)
    assert ket == "done", ket
    assert da_goi == [], "da goi lai pipeline du run_log da co ket qua"
    print("[PASS] da co run_log -> chi write_back lai, khong goi LLM")


def test_pipeline_nem_loi_thi_job_that_bai(conn):
    def _no(state):
        raise RuntimeError("Drupal tra 404")

    job = _job(conn, "uuid-4", "h4")
    ket = worker.chay_mot_job(conn, job, invoke=_no,
                              write_back_fn=lambda **kw: True)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT last_error FROM review_job WHERE id=%s", (job["id"],))
        assert "404" in cur.fetchone()[0]
    print("[PASS] pipeline nem loi -> job xep lai, giu nguyen van loi")


def test_ca_4_agent_loi_thi_KHONG_ghi_log_ma_retry(conn):
    """4/4 agent thieu = hong ha tang, khong phai ket qua danh gia."""
    state = dict(_STATE_XONG, final_score=None, report=dict(
        _STATE_XONG["report"], missing_agents=[
            "content_quality", "seo", "brand", "compliance"]))
    job = _job(conn, "uuid-5", "h5")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                              write_back_fn=lambda **kw: True)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-5'")
        assert cur.fetchone()[0] == 0, "khong duoc ghi log cho lan hong ha tang"
    print("[PASS] 4/4 agent loi -> retry, khong ghi run_log")


def test_1_agent_loi_van_chap_nhan(conn):
    """1-3 agent loi la dung tinh huong fail-safe architecture.md 6.4."""
    state = dict(_STATE_XONG, report=dict(_STATE_XONG["report"],
                                          missing_agents=["seo"]))
    job = _job(conn, "uuid-6", "h6")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                              write_back_fn=lambda **kw: True)
    assert ket == "done", ket
    print("[PASS] 1 agent loi -> chap nhan ket qua, khong tra tien lan hai")


def test_usage_log_duoc_reset(conn):
    """USAGE_LOG la list muc module, co y khong tu xoa - worker chay nen
    vo han thi no phinh mai (technical-debt.md nhom C)."""
    import ai_core
    ai_core.USAGE_LOG.append({"model": "x", "input_tokens": 1, "output_tokens": 1})
    job = _job(conn, "uuid-7", "h7")
    worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                        write_back_fn=lambda **kw: True)
    assert ai_core.USAGE_LOG == [], ai_core.USAGE_LOG
    print("[PASS] USAGE_LOG duoc reset sau moi job")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_job_thanh_cong_ghi_run_log_va_dong_job,
        test_write_back_that_bai_thi_job_xep_lai,
        test_da_co_run_log_thi_KHONG_goi_lai_pipeline,
        test_pipeline_nem_loi_thi_job_that_bai,
        test_ca_4_agent_loi_thi_KHONG_ghi_log_ma_retry,
        test_1_agent_loi_van_chap_nhan,
        test_usage_log_duoc_reset,
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
