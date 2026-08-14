"""Test worker: xu ly mot job (spec 2026-08-07 muc 6.1, 7; Plan 4 Task 5).

KHONG goi LLM, KHONG can Drupal: tiem `invoke` va connector gia.
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
from review_platform import fingerprint as platform_fingerprint
from review_platform import migrations, sites
from review_platform.connectors import base as connector_base

SCHEMA = "vf_test_worker"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_FIELDS = {"title": "T", "body": "B", "summary": "S", "meta_description": "M"}
_HASH_V1 = text_utils.content_hash(_FIELDS)
_HASH_V2 = platform_fingerprint.input_fingerprint(_FIELDS)

_STATE_XONG = {
    "node_id": "uuid-1",
    "decision": "needs_revision",
    "final_score": 76.5,
    "fields": dict(_FIELDS),
    "report": {
        "node_id": "uuid-1", "final_score": 76.5, "decision": "needs_revision",
        "missing_agents": [], "details": {"seo": {"score": 70, "issues": []}},
    },
}


def _tai_lieu(fields=None, revision="123"):
    return connector_base.ContentDocument(
        fields=dict(_FIELDS if fields is None else fields),
        raw_content={"id": "resource"},
        source_url="http://drupal.ddev.site/node/7",
        external_revision_id=revision,
        content_type="cam_nang",
        langcode="vi",
    )


class ConnectorGia:
    """Connector gia dem so lan fetch/callback - do la thu phai khoa o day."""

    def __init__(self, *, tai_lieu=None, outcome="applied", loi_fetch=None,
                 loi_write=None):
        self._tai_lieu = _tai_lieu() if tai_lieu is None else tai_lieu
        self.outcome = outcome
        self.loi_fetch = loi_fetch
        self.loi_write = loi_write
        self.fetch_calls = []
        self.write_calls = []

    def fetch_content(self, external_content_id, *, external_revision_id=None,
                      working_copy=False):
        self.fetch_calls.append({
            "external_content_id": external_content_id,
            "external_revision_id": external_revision_id,
            "working_copy": working_copy,
        })
        if self.loi_fetch is not None:
            raise self.loi_fetch
        return self._tai_lieu

    def write_back(self, request):
        self.write_calls.append(request)
        if self.loi_write is not None:
            raise self.loi_write
        return connector_base.WriteBackResult(
            outcome=self.outcome, applied_revision_id="124"
        )


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


def _job(conn, node_id, content_hash=None, *, version=1, revision=None):
    """Job co hash KHOP tai lieu gia, tru khi test co y truyen hash khac."""
    context = sites.select_review_context(
        conn, q.DEFAULT_SITE_ID, "cam_nang", "vi"
    )
    q.enqueue_scoped(
        conn,
        context,
        node_id,
        content_hash or (_HASH_V2 if version == 2 else _HASH_V1),
        "event",
        external_revision_id=revision,
        content_hash_version=version,
    )
    return q.claim(conn, "test")


def test_job_thanh_cong_ghi_run_log_va_dong_job(conn):
    job = _job(conn, "uuid-1")
    connector = ConnectorGia()
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=connector)
    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "done"
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-1'")
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT writeback_status FROM run_log WHERE node_id='uuid-1'")
        assert cur.fetchone()[0] == "succeeded"
    # Dung mot fetch va dung mot callback cho ca job.
    assert len(connector.fetch_calls) == 1, connector.fetch_calls
    assert len(connector.write_calls) == 1, connector.write_calls
    print("[PASS] job thanh cong -> run_log co ban ghi, job = done, 1 fetch 1 callback")


def test_write_back_that_bai_thi_job_xep_lai(conn):
    job = _job(conn, "uuid-2")
    connector = ConnectorGia(
        loi_write=connector_base.ConnectorTransientError("Drupal tra 503")
    )
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=connector)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE id=%s",
                    (job["id"],))
        status, loi = cur.fetchone()
    assert status == "queued" and "transient" in loi.lower(), (status, loi)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), min(writeback_status) FROM run_log WHERE node_id='uuid-2'"
        )
        count, writeback_status = cur.fetchone()
        assert count == 1, "run_log phai ghi TRUOC khi callback"
        assert writeback_status == "failed", writeback_status
    print("[PASS] callback loi tam thoi -> job ve queued, run_log da ghi")


def test_da_co_run_log_thi_KHONG_goi_lai_pipeline(conn):
    """Chot chan tien: cham lai mot bai ton $0,057 that."""
    job1 = _job(conn, "uuid-3")
    worker.chay_mot_job(
        conn, job1, invoke=lambda s: _STATE_XONG,
        connector=ConnectorGia(
            loi_write=connector_base.ConnectorTransientError("mat ket noi")
        ),
    )
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s",
                    (job1["id"],))

    da_goi = []

    def _invoke_khong_duoc_goi(state):
        da_goi.append(state)
        return _STATE_XONG

    job2 = q.claim(conn, "test")
    connector = ConnectorGia()
    ket = worker.chay_mot_job(conn, job2, invoke=_invoke_khong_duoc_goi,
                              connector=connector)
    assert ket == "done", ket
    assert da_goi == [], "da goi lai pipeline du run_log da co ket qua"
    # Duong reuse KHONG duoc fetch lai: khong co gi de cham, chi gui lai ket qua.
    assert connector.fetch_calls == [], connector.fetch_calls
    with conn.cursor() as cur:
        cur.execute("SELECT writeback_status FROM run_log WHERE job_id=%s", (job1["id"],))
        assert cur.fetchone()[0] == "succeeded"
    print("[PASS] da co run_log -> chi gui lai callback, khong goi LLM, khong fetch")


def test_pipeline_nem_loi_thi_job_that_bai(conn):
    def _no(state):
        raise RuntimeError("Drupal tra 404")

    job = _job(conn, "uuid-4")
    ket = worker.chay_mot_job(conn, job, invoke=_no, connector=ConnectorGia())
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
    job = _job(conn, "uuid-5")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                              connector=ConnectorGia())
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-5'")
        assert cur.fetchone()[0] == 0, "khong duoc ghi log cho lan hong ha tang"
    print("[PASS] 4/4 agent loi -> retry, khong ghi run_log")


def test_1_agent_loi_van_chap_nhan(conn):
    """1-3 agent loi la dung tinh huong fail-safe architecture.md 6.4."""
    state = dict(_STATE_XONG, report=dict(_STATE_XONG["report"],
                                          missing_agents=["seo"]))
    job = _job(conn, "uuid-6")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                              connector=ConnectorGia())
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

    job = _job(conn, "uuid-8")
    ket = worker.chay_mot_job(conn, job, invoke=_no, connector=ConnectorGia())
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

    job = _job(conn, "uuid-9")
    ket = worker.chay_mot_job(conn, job, invoke=_4_loi, connector=ConnectorGia())
    assert ket == "queued", ket
    assert ai_core.USAGE_LOG == [], ai_core.USAGE_LOG
    print("[PASS] 4/4 agent loi -> USAGE_LOG van duoc don")


def test_loi_bat_ngo_khong_lam_chet_vong_lap(conn):
    """audit.ghi_scoped() nem loi SAU khi pipeline da chay ton tien nhung TRUOC khi
    ghi xong run_log - _xu_ly_tiep_theo() phai bat duoc, dua job ve
    queued/failed, KHONG duoc de ngoai le thoat ra ngoai (se giet vong_lap)."""
    _job(conn, "uuid-10")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE review_job SET status='queued', claimed_at=NULL "
            "WHERE node_id='uuid-10'"
        )
    ghi_that = audit.ghi_scoped
    audit.ghi_scoped = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("mat ket noi Postgres giua chung"))
    try:
        ket = worker._xu_ly_tiep_theo(conn, "test-vonglap",
                                      invoke=lambda s: _STATE_XONG,
                                      connector=ConnectorGia())
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
        job = _job(conn, "uuid-11")
        ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                                  connector=ConnectorGia())
    finally:
        config.load = load_that
    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT config_meta FROM run_log WHERE node_id='uuid-11'")
        meta = cur.fetchone()[0]
    assert meta == {"content_type": "tin_tuc", "langcode": "en"}, meta
    print("[PASS] config_meta ghi dung khoa cua state, khong phai mac dinh cung")


def test_hash_lech_thi_dung_TRUOC_khi_goi_LLM(conn):
    """Thay cho test cu 'ghi run_log theo hash noi dung that'.

    Truoc Plan 4, worker khong fetch truoc nen graph co the cham nham revision
    mac dinh; luc do viec dung nhat la ghi run_log theo hash noi dung THAT va
    canh bao. Nay worker fetch DUNG revision roi so fingerprint TRUOC khi goi
    LLM, nen tinh huong do khong con ton tai duoc nua - va cach xu ly dung la
    dung han, khong tieu tien LLM de cham mot noi dung ma job khong mo ta.
    """
    job = _job(conn, "uuid-20", "0" * 64)
    connector = ConnectorGia()
    da_goi = []

    ket = worker.chay_mot_job(
        conn, job, invoke=lambda s: da_goi.append(s), connector=connector
    )

    assert ket == q.FAILED, ket
    assert da_goi == [], "khong duoc goi LLM khi hash da lech"
    assert connector.write_calls == [], "khong duoc callback khi chua cham"
    with conn.cursor() as cur:
        cur.execute("SELECT last_error FROM review_job WHERE node_id='uuid-20'")
        assert cur.fetchone()[0].startswith("input_hash_mismatch")
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-20'")
        assert cur.fetchone()[0] == 0, "khong duoc ghi run_log cho lan khong cham"
    print("[PASS] hash lech -> dead-letter truoc LLM, khong run_log, khong callback")


def test_job_legacy_v1_doc_working_copy_va_dung_hash_bon_field(conn):
    """Cua so rollback: job tu endpoint legacy mang version 1 va khong revision.

    Worker phai doc working copy, lay revision that tu response, va tinh hash
    bang text_utils.content_hash() bon field. Ep no qua fingerprint v2 se lam
    MOI job legacy bao input_hash_mismatch, tuc rollback coi nhu khong co.
    """
    job = _job(conn, "uuid-21", version=1, revision=None)
    assert job["content_hash"] == _HASH_V1
    connector = ConnectorGia()

    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=connector)

    assert ket == "done", ket
    assert connector.fetch_calls[0]["working_copy"] is True, connector.fetch_calls
    assert connector.fetch_calls[0]["external_revision_id"] is None
    yeu_cau = connector.write_calls[0]
    assert yeu_cau.content_hash_version == 1, yeu_cau
    # Revision that lay tu response, khong phai tu job (job khong co).
    assert yeu_cau.expected_revision_id == "123", yeu_cau
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash_version, external_revision_id FROM run_log "
            "WHERE node_id='uuid-21'"
        )
        assert cur.fetchone() == (1, "123")
    print("[PASS] job legacy v1 doc working copy, hash bon field, revision tu response")


def test_job_v2_bat_buoc_exact_revision_va_hash_sau_field(conn):
    job = _job(conn, "uuid-22", version=2, revision="45")
    assert job["content_hash"] == _HASH_V2
    connector = ConnectorGia(tai_lieu=_tai_lieu(revision="45"))

    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=connector)

    assert ket == "done", ket
    assert connector.fetch_calls[0]["external_revision_id"] == "45"
    assert connector.fetch_calls[0]["working_copy"] is False
    assert connector.write_calls[0].content_hash_version == 2
    assert connector.write_calls[0].expected_revision_id == "45"
    print("[PASS] job v2 fetch dung exact revision va dung hash sau field")


def test_so_v1_bang_thuat_toan_v2_phai_do(conn):
    """Test am: khoa dung nguyen nhan tung lam rollback hong.

    Job legacy mang hash bon field. Neu worker tinh bang fingerprint v2 thi
    hai gia tri khac nhau va job bi input_hash_mismatch. Test nay chung minh
    hai thuat toan that su khac nhau tren cung du lieu, nen viec chon dung
    nhanh la co y nghia chu khong phai trung hop.
    """
    assert _HASH_V1 != _HASH_V2, "fixture loi: hai hash phai khac nhau"

    job = _job(conn, "uuid-23", _HASH_V2, version=1)
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=ConnectorGia())
    assert ket == q.FAILED, ket
    with conn.cursor() as cur:
        cur.execute("SELECT last_error FROM review_job WHERE node_id='uuid-23'")
        assert cur.fetchone()[0].startswith("input_hash_mismatch")
    print("[PASS] job v1 mang hash v2 bi tu choi - hai nhanh hash that su khac nhau")


def test_stale_write_race_ket_thuc_superseded_khong_ghi_de(conn):
    """Job cua revision cu hoan tat sau job cua revision moi.

    Callback tra content_superseded. Job cu phai ket thuc o `superseded`, run
    cua no writeback_status='superseded', va tuyet doi khong retry payload cu
    len revision moi.
    """
    job = _job(conn, "uuid-24", version=2, revision="10")
    connector = ConnectorGia(
        tai_lieu=_tai_lieu(revision="10"), outcome="content_superseded"
    )

    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=connector)

    assert ket == q.SUPERSEDED, ket
    assert len(connector.write_calls) == 1, "khong duoc goi callback lan hai"
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE node_id='uuid-24'")
        status, loi = cur.fetchone()
        assert status == "superseded", status
        assert loi == "content_superseded", loi
        cur.execute("SELECT writeback_status FROM run_log WHERE node_id='uuid-24'")
        assert cur.fetchone()[0] == "superseded"
    print("[PASS] stale write -> job superseded, run superseded, khong retry")


def test_timeout_mo_ho_retry_cung_run_id_nhan_already_applied(conn):
    """Callback da apply nhung response mat: retry PHAI dung lai run_id cu.

    Neu retry sinh run_id moi, Drupal khong nhan ra day la lan gui lai va se
    tao them mot revision thu hai cho cung mot lan cham.
    """
    job = _job(conn, "uuid-25", version=2, revision="10")
    mat_response = ConnectorGia(
        tai_lieu=_tai_lieu(revision="10"),
        loi_write=connector_base.ConnectorTransientError("response mat"),
    )
    dau = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=mat_response)
    assert dau == q.QUEUED, dau
    run_id_lan_dau = mat_response.write_calls[0].run_id

    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET run_after=now() WHERE id=%s", (job["id"],))
    job_lan_hai = q.claim(conn, "test")

    invoke_calls = []
    lan_hai = ConnectorGia(outcome="already_applied")
    ket = worker.chay_mot_job(
        conn, job_lan_hai, invoke=lambda s: invoke_calls.append(s),
        connector=lan_hai,
    )

    assert ket == q.DONE, ket
    assert invoke_calls == [], "khong duoc goi LLM lan hai"
    assert lan_hai.fetch_calls == [], "khong duoc fetch lan hai"
    assert lan_hai.write_calls[0].run_id == run_id_lan_dau, (
        lan_hai.write_calls[0].run_id, run_id_lan_dau
    )
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-25'")
        assert cur.fetchone()[0] == 1, "khong duoc tao run thu hai"
        cur.execute("SELECT writeback_status FROM run_log WHERE node_id='uuid-25'")
        assert cur.fetchone()[0] == "succeeded"
    print("[PASS] timeout mo ho -> retry cung run_id, already_applied, mot run duy nhat")


def test_loi_auth_vao_thang_dead_letter_khong_goi_LLM(conn):
    job = _job(conn, "uuid-26")
    da_goi = []
    connector = ConnectorGia(
        loi_fetch=connector_base.ConnectorAuthError("connector_auth: Drupal tra 403")
    )

    ket = worker.chay_mot_job(conn, job, invoke=lambda s: da_goi.append(s),
                              connector=connector)

    assert ket == q.FAILED, ket
    assert da_goi == []
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error, attempts FROM review_job WHERE id=%s",
                    (job["id"],))
        status, loi, attempts = cur.fetchone()
    assert status == "failed", status
    assert loi.startswith("connector_auth"), loi
    # Dead-letter ngay o lan dau: khong de no chay het ba luot roi that bai.
    assert attempts == 1, attempts
    print("[PASS] loi auth vao thang dead-letter o lan dau, khong goi LLM")


def test_fixture_run_duoc_danh_dau_de_loai_khoi_metric(conn):
    job = _job(conn, "uuid-27")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              connector=ConnectorGia(), fixture_run=True)
    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT is_fixture FROM run_log WHERE node_id='uuid-27'")
        assert cur.fetchone()[0] is True
    print("[PASS] fixture_run ghi is_fixture=true de dashboard loai khoi metric")


def test_bao_cao_mang_hash_version_va_platform_run_id(conn):
    job = _job(conn, "uuid-28", version=2, revision="10")
    connector = ConnectorGia(tai_lieu=_tai_lieu(revision="10"))
    worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG, connector=connector)

    report_json = connector.write_calls[0].report_json
    assert report_json["content_hash"] == _HASH_V2, report_json
    assert report_json["content_hash_version"] == 2, report_json
    assert report_json["platform_run_id"] == str(connector.write_calls[0].run_id)
    print("[PASS] report_json mang hash, hash version va platform_run_id lam khoa idempotency")


def test_usage_log_duoc_reset(conn):
    """USAGE_LOG la list muc module, co y khong tu xoa - worker chay nen
    vo han thi no phinh mai (technical-debt.md nhom C)."""
    import ai_core
    ai_core.USAGE_LOG.append({"model": "x", "input_tokens": 1, "output_tokens": 1})
    job = _job(conn, "uuid-7")
    worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                        connector=ConnectorGia())
    assert ai_core.USAGE_LOG == [], ai_core.USAGE_LOG
    print("[PASS] USAGE_LOG duoc reset sau moi job")


def test_worker_truyen_nguyen_job_snapshot_va_run_public_id(conn):
    job = _job(conn, "uuid-30")
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
            connector=ConnectorGia(),
        )
    finally:
        audit.find_reusable_writeback = original_find
        audit.ghi_scoped = original_write
        audit.mark_writeback = original_mark

    assert result == q.DONE, result
    assert captured["write"]["job"] is job, captured
    assert isinstance(captured["write"]["run_public_id"], UUID), captured
    assert captured["write"]["content_hash"] == _HASH_V1
    assert captured["write"]["content_hash_version"] == 1, captured
    assert captured["write"]["external_revision_id"] == "123", captured
    assert captured["write"]["source_url"] == "http://drupal.ddev.site/node/7"
    assert captured["write"]["is_fixture"] is False, captured
    assert captured["mark"] == (3030, {"status": "succeeded"}), captured
    print("[PASS] worker truyen job snapshot, app run UUID va mark dung run")


def test_worker_truyen_khoa_scope_cua_job_xuong_graph(conn):
    """Tu Plan 4, scope den tu profile cua site chu khong con la hang so."""
    job = _job(conn, "uuid-33")
    nhan_duoc = {}

    def _invoke(state):
        nhan_duoc.update(state)
        return _STATE_XONG

    worker.chay_mot_job(conn, job, invoke=_invoke, connector=ConnectorGia())

    assert nhan_duoc["node_id"] == "uuid-33", nhan_duoc
    assert nhan_duoc["content_type"] == "cam_nang", nhan_duoc
    assert nhan_duoc["langcode"] == "vi", nhan_duoc
    print("[PASS] worker truyen node_id + content_type + langcode cua job xuong graph")


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
        "external_revision_id": "77",
        "content_hash": job["content_hash"],
        "policy_version": job["policy_version"],
        "writeback_status": "failed",
    }
    calls = {"invoke": 0, "mark": []}
    original_find = audit.find_reusable_writeback
    original_mark = audit.mark_writeback
    audit.find_reusable_writeback = lambda _conn, *, job: saved
    audit.mark_writeback = lambda _conn, run_id, **kw: calls["mark"].append((run_id, kw))
    connector = ConnectorGia()
    try:
        result = worker.chay_mot_job(
            conn,
            job,
            invoke=lambda state: calls.__setitem__("invoke", calls["invoke"] + 1),
            connector=connector,
        )
    finally:
        audit.find_reusable_writeback = original_find
        audit.mark_writeback = original_mark

    assert result == q.DONE, result
    assert calls["invoke"] == 0, calls
    assert connector.fetch_calls == [], connector.fetch_calls
    assert len(connector.write_calls) == 1, connector.write_calls
    yeu_cau = connector.write_calls[0]
    # Gui lai DUNG precondition da audit, khong tu tinh lai.
    assert yeu_cau.run_id == public_run_id, yeu_cau
    assert yeu_cau.expected_revision_id == "77", yeu_cau
    assert yeu_cau.content_hash == job["content_hash"], yeu_cau
    assert yeu_cau.suggestions == "saved", yeu_cau
    assert calls["mark"] == [(3131, {"status": "succeeded"})], calls
    print("[PASS] worker reuse dung saved public run/precondition, khong goi pipeline")


def test_callback_nem_loi_bat_ngo_giu_pending_de_retry_khong_cham_lai(conn):
    """Loi KHONG phai ConnectorError (bug lap trinh) van khong duoc cham lai.

    run giu writeback_status='pending', va find_reusable_writeback nhan ca
    'pending' lan 'failed' nen luot sau van gui lai payload cu.
    """
    _job(conn, "uuid-32")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE review_job SET status='queued', claimed_at=NULL "
            "WHERE node_id='uuid-32'"
        )

    class CallbackHong(ConnectorGia):
        def write_back(self, request):
            raise RuntimeError("response mat sau khi callback co the da apply")

    first = worker._xu_ly_tiep_theo(
        conn,
        "callback-timeout",
        invoke=lambda state: _STATE_XONG,
        connector=CallbackHong(),
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
        connector=ConnectorGia(),
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

    # Thu tu bat buoc: gate schema TRUOC khi nap model (~2GB), roi moi vao vong.
    #
    # Cap open/close xen giua la cua HEARTBEAT, va do la dung thiet ke: nhip
    # dap trong thread rieng nen phai co connection RIENG. psycopg connection
    # khong an toan khi hai thread dung chung, nen neu heartbeat muon connection
    # cua worker thi ca hai duong deu hong luc graph dang chay.
    assert events == [
        "open",             # connection rieng cua worker
        "schema",           # gate migration
        "model",            # nap embedder
        "open", "close",    # heartbeat: nhip dau tien
        "loop",             # vong lap (test nem StopLoop o day)
        "open", "close",    # heartbeat: xoa nhip khi tat
        "close",            # dong connection cua worker
    ], events
    assert dedicated.closed
    # Heartbeat KHONG duoc cham vao connection cua worker.
    assert events.index("open") == 0 and events[-1] == "close"
    print("[PASS] worker gate schema truoc model, heartbeat dung connection rieng")


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
        test_hash_lech_thi_dung_TRUOC_khi_goi_LLM,
        test_job_legacy_v1_doc_working_copy_va_dung_hash_bon_field,
        test_job_v2_bat_buoc_exact_revision_va_hash_sau_field,
        test_so_v1_bang_thuat_toan_v2_phai_do,
        test_stale_write_race_ket_thuc_superseded_khong_ghi_de,
        test_timeout_mo_ho_retry_cung_run_id_nhan_already_applied,
        test_loi_auth_vao_thang_dead_letter_khong_goi_LLM,
        test_fixture_run_duoc_danh_dau_de_loai_khoi_metric,
        test_bao_cao_mang_hash_version_va_platform_run_id,
        test_usage_log_duoc_reset,
        test_worker_truyen_nguyen_job_snapshot_va_run_public_id,
        test_worker_truyen_khoa_scope_cua_job_xuong_graph,
        test_worker_reuse_saved_run_public_id_khong_goi_pipeline,
        test_callback_nem_loi_bat_ngo_giu_pending_de_retry_khong_cham_lai,
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
