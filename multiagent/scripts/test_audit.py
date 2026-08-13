"""Test nhat ky truy vet run_log (spec 2026-08-07 muc 5.2).

Can Postgres that, cung ly do va cung cach xu ly [SKIP] nhu test_job_queue.py.
Chay: .venv\\Scripts\\python.exe scripts\\test_audit.py
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import db
from review_platform import migrations

SCHEMA = "vf_test_audit"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

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
