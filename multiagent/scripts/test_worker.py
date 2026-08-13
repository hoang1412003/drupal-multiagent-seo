"""Test worker: xu ly mot job (spec 2026-08-07 muc 6.1, 7).

KHONG goi LLM, KHONG can Drupal: tiem `invoke` va `write_back_fn` gia.
Can Postgres that cho queue/run_log - [SKIP] neu khong co.
Chay: .venv\\Scripts\\python.exe scripts\\test_worker.py
"""
import logging
from contextlib import contextmanager
import os
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import db
import job_queue as q
import text_utils
import worker
from review_platform import migrations

SCHEMA = "vf_test_worker"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

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
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
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
        cur.execute("SELECT writeback_status FROM run_log WHERE node_id='uuid-1'")
        assert cur.fetchone()[0] == "succeeded"
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
        cur.execute("SELECT count(*), min(writeback_status) FROM run_log WHERE node_id='uuid-2'")
        count, writeback_status = cur.fetchone()
        assert count == 1, "run_log phai ghi TRUOC khi write_back"
        assert writeback_status == "failed", writeback_status
    print("[PASS] write_back False -> job ve queued, run_log da ghi")


def test_da_co_run_log_thi_KHONG_goi_lai_pipeline(conn):
    """Chot chan tien: cham lai mot bai ton $0,057 that.

    Hash cua job PHAI khop hash noi dung THAT cua _STATE_XONG["fields"]: tu
    khi sua loi CRITICAL (worker ghi run_log theo hash noi dung that, khong
    theo hash job), do la dung tinh huong BINH THUONG (khong loi revision) -
    hash job va hash noi dung fetch duoc phai trung nhau. Truong hop chung
    lech nhau (bug JSON:API tra revision mac dinh) co test rieng:
    test_ghi_run_log_theo_hash_noi_dung_that_khong_theo_hash_job.
    """
    hash_that = text_utils.content_hash(_STATE_XONG["fields"])
    job1 = _job(conn, "uuid-3", hash_that)
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
    with conn.cursor() as cur:
        cur.execute("SELECT writeback_status FROM run_log WHERE job_id=%s", (job1["id"],))
        assert cur.fetchone()[0] == "succeeded"
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


def test_usage_log_duoc_don_khi_invoke_nem_loi(conn):
    """USAGE_LOG phai rong sau khi chay_mot_job() tra ve, KE CA nhanh thoat
    som (invoke() nem loi giua chung) - khong duoc de lai cho job SAU tu
    clear() ho, vi tien LLM da tieu cua lan hong nay se bien mat khong dau
    vet (khong co run_log cho ca nay)."""
    import ai_core

    def _no(state):
        ai_core.USAGE_LOG.append({"model": "x", "input_tokens": 5, "output_tokens": 1})
        raise RuntimeError("mo phong loi giua chung, da goi 1 agent truoc do")

    job = _job(conn, "uuid-8", "h8")
    ket = worker.chay_mot_job(conn, job, invoke=_no, write_back_fn=lambda **kw: True)
    assert ket == "queued", ket
    assert ai_core.USAGE_LOG == [], ai_core.USAGE_LOG
    print("[PASS] invoke() nem loi -> USAGE_LOG van duoc don ngay, khong de lai")


def test_usage_log_duoc_don_khi_ca_4_agent_loi(conn):
    """Nhanh thoat som con lai (4/4 agent thieu) cung phai don USAGE_LOG."""
    import ai_core

    def _4_loi(state):
        ai_core.USAGE_LOG.append({"model": "x", "input_tokens": 3, "output_tokens": 1})
        return dict(_STATE_XONG, final_score=None, report=dict(
            _STATE_XONG["report"], missing_agents=[
                "content_quality", "seo", "brand", "compliance"]))

    job = _job(conn, "uuid-9", "h9")
    ket = worker.chay_mot_job(conn, job, invoke=_4_loi, write_back_fn=lambda **kw: True)
    assert ket == "queued", ket
    assert ai_core.USAGE_LOG == [], ai_core.USAGE_LOG
    print("[PASS] 4/4 agent loi -> USAGE_LOG van duoc don")


def test_loi_bat_ngo_khong_lam_chet_vong_lap(conn):
    """audit.ghi_scoped() nem loi SAU khi pipeline da chay ton tien nhung TRUOC khi
    ghi xong run_log - _xu_ly_tiep_theo() phai bat duoc, dua job ve
    queued/failed, KHONG duoc de ngoai le thoat ra ngoai (se giet vong_lap)."""
    q.enqueue(conn, "uuid-10", "h10", "event")
    ghi_that = audit.ghi_scoped
    audit.ghi_scoped = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("mat ket noi Postgres giua chung"))
    try:
        ket = worker._xu_ly_tiep_theo(conn, "test-vonglap", invoke=lambda s: _STATE_XONG,
                                      write_back_fn=lambda **kw: True)
    finally:
        audit.ghi_scoped = ghi_that
    assert ket in (q.QUEUED, q.FAILED), ket
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE node_id='uuid-10'")
        status, loi = cur.fetchone()
    assert status in (q.QUEUED, q.FAILED), status
    assert "RuntimeError" in loi, loi
    print("[PASS] loi bat ngo trong chay_mot_job -> vong_lap khong chet, job duoc fail")


def test_config_meta_theo_dung_khoa_cua_state(conn):
    """config_meta ghi vao run_log phai theo (content_type, langcode) CUA
    STATE dang cham, khong phai mac dinh cung cua config.load() khong tham
    so (hai hang so DEFAULT_* nam o hai file doc lap, khong dam bao mai
    trung nhau)."""
    import config

    state = dict(_STATE_XONG, content_type="tin_tuc", langcode="en")
    load_that = config.load

    def _load_gia(content_type="cam_nang", langcode="vi", **kw):
        return {"meta": {"content_type": content_type, "langcode": langcode}}

    config.load = _load_gia
    try:
        job = _job(conn, "uuid-11", "h11")
        ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                                  write_back_fn=lambda **kw: True)
    finally:
        config.load = load_that
    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT config_meta FROM run_log WHERE node_id='uuid-11'")
        meta = cur.fetchone()[0]
    assert meta == {"content_type": "tin_tuc", "langcode": "en"}, meta
    print("[PASS] config_meta ghi dung khoa cua state, khong phai mac dinh cung")


def test_ghi_run_log_theo_hash_noi_dung_that_khong_theo_hash_job(conn):
    """Sua loi CRITICAL: worker truoc day ghi run_log.content_hash = hash CUA
    JOB (job["content_hash"]), khong phai hash NOI DUNG THAT DA CHAM.

    Loi lo ra khi worker.fetch_content() lay revision MAC DINH cua node
    (khong resourceVersion=rel:working-copy): voi bai DA XUAT BAN roi dua
    sang needs_review (default_revision=false), revision mac dinh la BAN CU
    da xuat ban, trong khi hook gui hash cua BAN NHAP MOI. invoke() vi vay
    cham nham noi dung cu, nhung run_log lai ghi nhan duoi hash cua ban moi -
    tra sai payload vinh vien cho ca hai hash tu do ve sau.

    Tai hien: invoke() tra ve state co `fields` KHAC hash voi job["content_hash"]
    (mo phong dung tinh huong tren). Xac nhan (a) run_log.content_hash la hash
    cua `fields` chu khong phai cua job; (b) co canh bao duoc ghi neu ca hai
    gia tri lech nhau.
    """
    state_khac = dict(_STATE_XONG, fields={
        "title": "NOI DUNG THAT KHAC BAN NHAP", "body": "B that",
        "summary": "S that", "meta_description": "M that",
    })
    hash_that = text_utils.content_hash(state_khac["fields"])

    job = _job(conn, "uuid-20", "hash-cua-job-khac-hash-noi-dung-that")
    assert hash_that != job["content_hash"], "fixture loi: hai hash phai khac nhau"

    ghi_canh_bao = []
    canh_bao_that = logging.warning
    logging.warning = lambda *a, **kw: ghi_canh_bao.append(a)
    try:
        ket = worker.chay_mot_job(conn, job, invoke=lambda s: state_khac,
                                  write_back_fn=lambda **kw: True)
    finally:
        logging.warning = canh_bao_that

    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT content_hash FROM run_log WHERE node_id='uuid-20'")
        hash_ghi = cur.fetchone()[0]
    assert hash_ghi == hash_that, (
        f"run_log phai ghi theo hash NOI DUNG THAT ({hash_that}), "
        f"khong phai hash cua job ({job['content_hash']}): got {hash_ghi}")

    assert ghi_canh_bao, "phai co canh bao khi hash that khac hash job"
    noi_dung_canh_bao = " ".join(str(x) for x in ghi_canh_bao[0])
    assert job["content_hash"] in noi_dung_canh_bao, ghi_canh_bao[0]
    assert hash_that in noi_dung_canh_bao, ghi_canh_bao[0]
    print("[PASS] run_log ghi theo hash noi dung THAT, co canh bao khi lech hash job")


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


def test_worker_truyen_nguyen_job_snapshot_va_run_public_id(conn):
    job = _job(conn, "uuid-30", text_utils.content_hash(_STATE_XONG["fields"]))
    captured = {}
    original_find = audit.find_reusable_writeback
    original_write = audit.ghi_scoped
    original_mark = audit.mark_writeback
    audit.find_reusable_writeback = lambda _conn, *, job: None

    def write_spy(_conn, **kwargs):
        captured["write"] = kwargs
        return 3030

    def mark_spy(_conn, run_id, **kwargs):
        captured["mark"] = (run_id, kwargs)

    audit.ghi_scoped = write_spy
    audit.mark_writeback = mark_spy
    try:
        result = worker.chay_mot_job(
            conn,
            job,
            invoke=lambda state: _STATE_XONG,
            write_back_fn=lambda **payload: True,
        )
    finally:
        audit.find_reusable_writeback = original_find
        audit.ghi_scoped = original_write
        audit.mark_writeback = original_mark

    assert result == q.DONE, result
    assert captured["write"]["job"] is job, captured
    assert isinstance(captured["write"]["run_public_id"], UUID), captured
    assert captured["write"]["content_hash"] == text_utils.content_hash(
        _STATE_XONG["fields"]
    )
    assert captured["mark"] == (3030, {"status": "succeeded"}), captured
    print("[PASS] worker truyen job snapshot, app run UUID va mark dung run")


def test_worker_reuse_saved_run_public_id_khong_goi_pipeline(conn):
    job = _job(conn, "uuid-31", "saved-hash")
    public_run_id = UUID("00000000-0000-4000-8000-000000000031")
    saved_payload = {
        "status": "needs_revision",
        "score": 76.5,
        "suggestions": "saved",
        "report_json": {"version": 1},
    }
    saved = {
        "id": 3131,
        "run_id": public_run_id,
        "payload": saved_payload,
        "external_revision_id": job["external_revision_id"],
        "content_hash": job["content_hash"],
        "policy_version": job["policy_version"],
        "writeback_status": "failed",
    }
    calls = {"invoke": 0, "write": [], "mark": []}
    original_find = audit.find_reusable_writeback
    original_mark = audit.mark_writeback
    audit.find_reusable_writeback = lambda _conn, *, job: saved
    audit.mark_writeback = lambda _conn, run_id, **kw: calls["mark"].append((run_id, kw))
    try:
        result = worker.chay_mot_job(
            conn,
            job,
            invoke=lambda state: calls.__setitem__("invoke", calls["invoke"] + 1),
            write_back_fn=lambda **payload: (calls["write"].append(payload), True)[1],
        )
    finally:
        audit.find_reusable_writeback = original_find
        audit.mark_writeback = original_mark

    assert result == q.DONE, result
    assert calls["invoke"] == 0, calls
    assert calls["write"] == [{"node_id": job["node_id"], **saved_payload}], calls
    assert calls["mark"] == [(3131, {"status": "succeeded"})], calls
    assert saved["run_id"] == public_run_id
    print("[PASS] worker reuse dung saved public run/precondition, khong goi pipeline")


def test_callback_nem_loi_giu_pending_de_retry_khong_cham_lai(conn):
    content_hash = text_utils.content_hash(_STATE_XONG["fields"])
    q.enqueue(conn, "uuid-32", content_hash, "event")

    def callback_timeout(**payload):
        raise RuntimeError("response mat sau khi callback co the da apply")

    first = worker._xu_ly_tiep_theo(
        conn,
        "callback-timeout",
        invoke=lambda state: _STATE_XONG,
        write_back_fn=callback_timeout,
    )
    assert first == q.QUEUED, first
    with conn.cursor() as cur:
        cur.execute(
            "SELECT job.id, run.id, run.writeback_status FROM review_job AS job "
            "JOIN run_log AS run ON run.job_id=job.id WHERE job.node_id='uuid-32'"
        )
        job_id, run_id, status = cur.fetchone()
        assert status == "pending", status
        cur.execute("UPDATE review_job SET run_after=now() WHERE id=%s", (job_id,))

    invoke_calls = []
    second = worker._xu_ly_tiep_theo(
        conn,
        "callback-retry",
        invoke=lambda state: invoke_calls.append(state),
        write_back_fn=lambda **payload: True,
    )
    assert second == q.DONE, second
    assert invoke_calls == [], invoke_calls
    with conn.cursor() as cur:
        cur.execute("SELECT writeback_status FROM run_log WHERE id=%s", (run_id,))
        assert cur.fetchone()[0] == "succeeded"
    print("[PASS] callback exception giu pending; retry saved payload khong cham lai")


def test_worker_mo_dedicated_connection_va_gate_schema_truoc_model(conn):
    assert hasattr(worker, "platform_database"), "worker chua co dedicated connection"
    assert hasattr(worker, "migrations"), "worker chua co startup migration gate"
    import embeddings

    events = []

    class DedicatedConnection:
        closed = False

    dedicated = DedicatedConnection()

    @contextmanager
    def open_connection():
        events.append("open")
        try:
            yield dedicated
        finally:
            dedicated.closed = True
            events.append("close")

    class StopLoop(RuntimeError):
        pass

    original_open = worker.platform_database.open_connection
    original_require = worker.migrations.require_current
    original_embedder = embeddings.get_default_embedder
    original_reclaim = q.reclaim_stuck
    worker.platform_database.open_connection = open_connection
    worker.migrations.require_current = lambda startup_conn, path: events.append(
        "schema"
    )
    embeddings.get_default_embedder = lambda: events.append("model")

    def stop_after_startup(loop_conn):
        assert loop_conn is dedicated
        events.append("loop")
        raise StopLoop

    q.reclaim_stuck = stop_after_startup
    try:
        try:
            worker.vong_lap(ten="startup-test")
        except StopLoop:
            pass
        else:
            raise AssertionError("test phai dung o lan lap dau")
    finally:
        worker.platform_database.open_connection = original_open
        worker.migrations.require_current = original_require
        embeddings.get_default_embedder = original_embedder
        q.reclaim_stuck = original_reclaim

    assert events == ["open", "schema", "model", "loop", "close"], events
    assert dedicated.closed
    print("[PASS] worker gate schema truoc model va dong dedicated connection")


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
        test_usage_log_duoc_don_khi_invoke_nem_loi,
        test_usage_log_duoc_don_khi_ca_4_agent_loi,
        test_loi_bat_ngo_khong_lam_chet_vong_lap,
        test_config_meta_theo_dung_khoa_cua_state,
        test_ghi_run_log_theo_hash_noi_dung_that_khong_theo_hash_job,
        test_usage_log_duoc_reset,
        test_worker_truyen_nguyen_job_snapshot_va_run_public_id,
        test_worker_reuse_saved_run_public_id_khong_goi_pipeline,
        test_callback_nem_loi_giu_pending_de_retry_khong_cham_lai,
        test_worker_mo_dedicated_connection_va_gate_schema_truoc_model,
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
