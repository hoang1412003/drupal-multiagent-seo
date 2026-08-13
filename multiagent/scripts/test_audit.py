"""Test nhat ky truy vet run_log (spec 2026-08-07 muc 5.2).

Can Postgres that, cung ly do va cung cach xu ly [SKIP] nhu test_job_queue.py.
Chay: .venv\\Scripts\\python.exe scripts\\test_audit.py
"""
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import db
import job_queue as q
from review_platform import migrations, sites

SCHEMA = "vf_test_audit"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
DEFAULT_SITE_ID = UUID("00000000-0000-4000-8000-000000000001")

_REPORT = {
    "node_id": "uuid-1",
    "final_score": 76.5,
    "decision": "needs_revision",
    "missing_agents": ["seo"],
    "note": "Diem so chua day du",
    "details": {"compliance": {"score": 80.0, "flags": []}, "seo": None},
}
_CONFIG_META = {"calibrated": False, "model": None, "rubric_version": None}
_USAGE = [{"model": "claude-haiku-4-5-20251001", "input_tokens": 100,
           "output_tokens": 20}]
_PAYLOAD = {"status": "needs_revision", "score": 76.5,
            "suggestions": "day la goi y", "report_json": {"version": 1}}


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
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
    audit.dam_bao_bang(conn)
    return conn


def _ghi_mau(conn, node_id="uuid-1", content_hash="hash-a"):
    return audit.ghi(conn, job_id=1, node_id=node_id, content_hash=content_hash,
                     duration_ms=42000, report=_REPORT, config_meta=_CONFIG_META,
                     usage=_USAGE, model="claude-haiku-4-5-20251001",
                     payload=_PAYLOAD)


def test_ghi_du_truong(conn):
    rid = _ghi_mau(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT node_id, decision, final_score, missing_agents, note, "
            "agent_results, config_meta, usage, model, payload, duration_ms "
            "FROM run_log WHERE id=%s", (rid,))
        r = cur.fetchone()
    assert r[0] == "uuid-1" and r[1] == "needs_revision", r
    assert float(r[2]) == 76.5, r
    assert r[3] == ["seo"], r
    assert r[5]["compliance"]["score"] == 80.0, r[5]
    assert r[6]["calibrated"] is False, r[6]
    assert r[7][0]["input_tokens"] == 100, r[7]
    assert r[9]["suggestions"] == "day la goi y", r[9]
    assert r[10] == 42000, r
    print("[PASS] ban ghi run_log co du truong, jsonb doc lai dung kieu")


def test_final_score_none_khong_thanh_0(conn):
    """Compliance loi -> final_score = None nghia la CHUA cham duoc.

    Ghi 0 vao day se khien moi phan tich ve sau hieu nham la bai cuc te -
    dung nguyen tac architecture.md muc 6.4.
    """
    bao_cao = dict(_REPORT, final_score=None, decision="needs_revision")
    rid = audit.ghi(conn, job_id=2, node_id="uuid-2", content_hash="h2",
                    duration_ms=100, report=bao_cao, config_meta=_CONFIG_META,
                    usage=[], model="m", payload=_PAYLOAD)
    with conn.cursor() as cur:
        cur.execute("SELECT final_score FROM run_log WHERE id=%s", (rid,))
        assert cur.fetchone()[0] is None
    print("[PASS] final_score None duoc giu la NULL, khong quy thanh 0")


def test_da_cham_tra_payload(conn):
    _ghi_mau(conn, "uuid-3", "h3")
    kq = audit.da_cham(conn, "uuid-3", "h3")
    assert kq is not None and kq["payload"]["status"] == "needs_revision", kq
    print("[PASS] da_cham tra ve payload da PATCH lan truoc")


def test_da_cham_khac_hash_tra_none(conn):
    """Noi dung doi -> phai cham lai that, khong duoc dung ket qua cu."""
    _ghi_mau(conn, "uuid-4", "h4")
    assert audit.da_cham(conn, "uuid-4", "hash-moi") is None
    print("[PASS] hash khac -> khong tai su dung ket qua cu")


def test_khong_luu_bi_mat(conn):
    """operations.md muc 2.5: khong ghi API key, khong ghi toan van system prompt."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name='run_log' AND table_schema=%s "
                    "AND column_name IN ('api_key','system_prompt','body')",
                    (SCHEMA,))
        assert cur.fetchone()[0] == 0
    print("[PASS] schema khong co cot cho bi mat/toan van bai")


def _default_context(conn):
    return sites.select_review_context(conn, DEFAULT_SITE_ID, "cam_nang", "vi")


def _second_context(conn):
    site_id = UUID("00000000-0000-4000-8000-000000000010")
    profile_id = UUID("00000000-0000-4000-8000-000000000011")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site (id, slug, name, connector_type, base_url, secret_ref) "
            "VALUES (%s, 'audit-secondary', 'Audit secondary', 'drupal', "
            "'http://audit-secondary.local', 'DRUPAL_AUDIT_SECONDARY') "
            "ON CONFLICT DO NOTHING",
            (site_id,),
        )
        cur.execute(
            "INSERT INTO review_profile "
            "(id, code, market_code, language_code, content_type, status, "
            "policy_version, policy_snapshot) "
            "VALUES (%s, 'audit-secondary', 'VN', 'vi', 'cam_nang', 'active', "
            "'cam-nang-vn-v1', '{}'::jsonb) ON CONFLICT DO NOTHING",
            (profile_id,),
        )
        cur.execute(
            "INSERT INTO site_profile_assignment (site_id, profile_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (site_id, profile_id),
        )
    return sites.select_review_context(conn, site_id, "cam_nang", "vi")


def _claim_job(conn, context, external_id, content_hash, source="event", **kwargs):
    queued = q.enqueue_scoped(
        conn,
        context,
        external_id,
        content_hash,
        source,
        **kwargs,
    )
    assert queued["status"] == q.QUEUED, queued
    job = q.claim(conn, "audit-test")
    assert job["id"] == queued["job_id"], job
    return job


def _ghi_scoped(conn, job, payload=None):
    return audit.ghi_scoped(
        conn,
        run_public_id=uuid4(),
        job=job,
        content_hash=job["content_hash"],
        duration_ms=321,
        report=_REPORT,
        config_meta=_CONFIG_META,
        usage=_USAGE,
        model="claude-haiku-4-5-20251001",
        payload=payload or _PAYLOAD,
    )


def test_scoped_audit_cach_ly_hai_site_va_ghi_du_metadata(conn):
    primary = _default_context(conn)
    secondary = _second_context(conn)
    first = _claim_job(
        conn,
        primary,
        "same-external",
        "same-content",
        external_revision_id="revision-primary-10",
    )
    first_run = _ghi_scoped(conn, first, dict(_PAYLOAD, suggestions="primary"))
    q.complete(conn, first["id"])
    second = _claim_job(conn, secondary, "same-external", "same-content")
    second_run = _ghi_scoped(conn, second, dict(_PAYLOAD, suggestions="secondary"))

    found_first = audit.da_cham_scoped(
        conn,
        site_id=primary.site.id,
        external_content_id="same-external",
        content_hash="same-content",
        policy_version=primary.profile.policy_version,
    )
    found_second = audit.da_cham_scoped(
        conn,
        site_id=secondary.site.id,
        external_content_id="same-external",
        content_hash="same-content",
        policy_version=secondary.profile.policy_version,
    )
    assert found_first["id"] == first_run, found_first
    assert found_first["payload"]["suggestions"] == "primary", found_first
    assert found_second["id"] == second_run, found_second
    assert found_second["payload"]["suggestions"] == "secondary", found_second

    with conn.cursor() as cur:
        cur.execute(
            "SELECT site_id, profile_id, policy_version, external_content_id, "
            "external_revision_id, content_type, langcode, correlation_id, "
            "writeback_status, payload FROM run_log WHERE id=%s",
            (first_run,),
        )
        row = cur.fetchone()
    assert row[:8] == (
        first["site_id"],
        first["profile_id"],
        first["policy_version"],
        first["external_content_id"],
        first["external_revision_id"],
        first["content_type"],
        first["langcode"],
        first["correlation_id"],
    ), row
    assert row[8] == "pending", row
    assert not ({"title", "body", "summary"} & set(row[9])), row[9]
    q.complete(conn, second["id"])
    print("[PASS] audit scoped cach ly site va ghi du job snapshot")


def test_ghi_scoped_tu_choi_full_content_top_level(conn):
    job = _claim_job(conn, _default_context(conn), "payload-guard", "payload-hash")
    try:
        _ghi_scoped(conn, job, dict(_PAYLOAD, body="toan van bai"))
    except ValueError as exc:
        assert "body" in str(exc), exc
    else:
        raise AssertionError("payload co full content phai bi tu choi")
    q.complete(conn, job["id"])
    print("[PASS] ghi_scoped chan full content top-level trong payload")


def test_reusable_cung_job_pending_failed_va_mark_terminal(conn):
    job = _claim_job(conn, _default_context(conn), "reusable-own", "reusable-hash")
    run_public_id = uuid4()
    run_db_id = audit.ghi_scoped(
        conn,
        run_public_id=run_public_id,
        job=job,
        content_hash=job["content_hash"],
        duration_ms=100,
        report=_REPORT,
        config_meta=_CONFIG_META,
        usage=_USAGE,
        model="m",
        payload=_PAYLOAD,
    )
    pending = audit.find_reusable_writeback(conn, job=job)
    assert pending["id"] == run_db_id and pending["run_id"] == run_public_id, pending
    assert pending["content_hash"] == job["content_hash"], pending
    assert pending["policy_version"] == job["policy_version"], pending
    assert pending["writeback_status"] == "pending", pending

    audit.mark_writeback(conn, run_db_id, status="failed", error="x" * 1200)
    failed = audit.find_reusable_writeback(conn, job=job)
    assert failed["run_id"] == run_public_id and failed["writeback_status"] == "failed"
    with conn.cursor() as cur:
        cur.execute("SELECT length(writeback_error) FROM run_log WHERE id=%s", (run_db_id,))
        assert cur.fetchone()[0] == 1000

    audit.mark_writeback(conn, run_db_id, status="failed", error="retry van fail")
    audit.mark_writeback(conn, run_db_id, status="succeeded")
    assert audit.find_reusable_writeback(conn, job=job) is None
    try:
        audit.mark_writeback(conn, run_db_id, status="failed", error="mo lai")
    except audit.AuditStateError as exc:
        assert "succeeded" in str(exc), exc
    else:
        raise AssertionError("run succeeded khong duoc mo lai")
    q.complete(conn, job["id"])
    print("[PASS] reusable pending/failed va terminal transition dung")


def test_unknown_va_superseded_la_terminal_khong_reusable(conn):
    context = _default_context(conn)
    unknown_job = _claim_job(conn, context, "legacy-unknown", "legacy-hash")
    unknown_run = _ghi_scoped(conn, unknown_job)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE run_log SET writeback_status='unknown' WHERE id=%s",
            (unknown_run,),
        )
    assert audit.find_reusable_writeback(conn, job=unknown_job) is None
    try:
        audit.mark_writeback(conn, unknown_run, status="succeeded")
    except audit.AuditStateError as exc:
        assert "unknown" in str(exc), exc
    else:
        raise AssertionError("unknown phai terminal")
    q.complete(conn, unknown_job["id"])

    superseded_job = _claim_job(conn, context, "terminal-superseded", "terminal-hash")
    superseded_run = _ghi_scoped(conn, superseded_job)
    audit.mark_writeback(conn, superseded_run, status="superseded")
    assert audit.find_reusable_writeback(conn, job=superseded_job) is None
    try:
        audit.mark_writeback(conn, superseded_run, status="failed")
    except audit.AuditStateError as exc:
        assert "superseded" in str(exc), exc
    else:
        raise AssertionError("superseded phai terminal")
    q.complete(conn, superseded_job["id"])
    print("[PASS] unknown/superseded la terminal va khong reusable")


def test_admin_retry_reuse_failed_target_nhung_manual_force_khong_reuse(conn):
    context = _default_context(conn)
    failed_job = _claim_job(conn, context, "admin-target", "admin-target-hash")
    failed_run = _ghi_scoped(conn, failed_job)
    audit.mark_writeback(conn, failed_run, status="failed", error="callback fail")
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET attempts=3 WHERE id=%s", (failed_job["id"],))
    assert q.fail(conn, failed_job["id"], "callback fail") == q.FAILED

    admin_retry = _claim_job(
        conn,
        context,
        "admin-target",
        "admin-target-hash",
        source="admin_retry",
        force=True,
        supersedes_job_id=failed_job["id"],
    )
    reusable = audit.find_reusable_writeback(conn, job=admin_retry)
    assert reusable["id"] == failed_run, reusable
    q.complete(conn, admin_retry["id"])

    done_job = _claim_job(conn, context, "manual-force", "manual-force-hash")
    done_run = _ghi_scoped(conn, done_job)
    audit.mark_writeback(conn, done_run, status="succeeded")
    q.complete(conn, done_job["id"])
    manual = _claim_job(
        conn,
        context,
        "manual-force",
        "manual-force-hash",
        source="manual",
        force=True,
    )
    assert audit.find_reusable_writeback(conn, job=manual) is None
    q.complete(conn, manual["id"])
    print("[PASS] admin_retry reuse failed target; manual force succeeded thi cham lai")


def test_admin_retry_khong_reuse_run_cua_revision_cu(conn):
    context = _default_context(conn)
    failed_job = _claim_job(
        conn,
        context,
        "admin-stale-revision",
        "admin-stale-hash",
        external_revision_id="revision-10",
    )
    failed_run = _ghi_scoped(conn, failed_job)
    audit.mark_writeback(conn, failed_run, status="failed", error="callback fail")
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET attempts=3 WHERE id=%s", (failed_job["id"],))
    assert q.fail(conn, failed_job["id"], "callback fail") == q.FAILED

    newer_revision = _claim_job(
        conn,
        context,
        "admin-stale-revision",
        "admin-stale-hash",
        source="admin_retry",
        external_revision_id="revision-11",
        force=True,
        supersedes_job_id=failed_job["id"],
    )
    assert audit.find_reusable_writeback(conn, job=newer_revision) is None
    q.complete(conn, newer_revision["id"])
    print("[PASS] admin_retry khong reuse failed run cua revision cu")


if __name__ == "__main__":
    try:
        conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)
    conn = _dung_schema_sach(conn)

    failed = False
    for fn in (
        test_ghi_du_truong,
        test_final_score_none_khong_thanh_0,
        test_da_cham_tra_payload,
        test_da_cham_khac_hash_tra_none,
        test_khong_luu_bi_mat,
        test_scoped_audit_cach_ly_hai_site_va_ghi_du_metadata,
        test_ghi_scoped_tu_choi_full_content_top_level,
        test_reusable_cung_job_pending_failed_va_mark_terminal,
        test_unknown_va_superseded_la_terminal_khong_reusable,
        test_admin_retry_reuse_failed_target_nhung_manual_force_khong_reuse,
        test_admin_retry_khong_reuse_run_cua_revision_cu,
    ):
        try:
            fn(conn)
        except Exception as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
