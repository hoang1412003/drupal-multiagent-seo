"""Test chot chan cua smoke cutover (Plan 4 Task 9).

Thu quan trong nhat o day KHONG phai "script chay duoc", ma la "script tu
choi chay khi khong duoc phep" va "khong bao gio goi LLM". Mot script smoke
chay nham tren production se ghi bao cao gia vao bai that.

Chay: .venv\\Scripts\\python.exe scripts\\test_staging_connector_smoke.py
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import ai_core
import db
import job_queue as q
import text_utils
from review_platform import migrations, sites
from review_platform.connectors import base as connector_base

import staging_connector_smoke as smoke


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_smoke"
FIELDS = {"title": "T", "body": "B", "summary": "S", "meta_description": "M"}
HASH_V1 = text_utils.content_hash(FIELDS)


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


class ConnectorGia:
    def __init__(self, outcome="applied"):
        self.outcome = outcome
        self.fetch_calls = 0
        self.write_calls = []

    def fetch_content(self, external_content_id, *, external_revision_id=None,
                      working_copy=False):
        self.fetch_calls += 1
        return connector_base.ContentDocument(
            fields=dict(FIELDS),
            raw_content={"id": external_content_id},
            source_url="http://drupal.ddev.site/node/7",
            external_revision_id=external_revision_id or "123",
            content_type="cam_nang",
            langcode="vi",
        )

    def write_back(self, request):
        self.write_calls.append(request)
        return connector_base.WriteBackResult(
            outcome=self.outcome, applied_revision_id="124"
        )


# ------------------------------------------------------- chot chan thuan


def test_host_khong_phai_staging_bi_tu_choi():
    assert smoke.kiem_host_staging("http://drupal.ddev.site") == "drupal.ddev.site"
    assert smoke.kiem_host_staging("https://abc.ddev.site/con/duong") == "abc.ddev.site"

    for xau in (
        "https://vinfastauto.com",
        "https://cms.vinfastauto.com",
        "http://10.0.0.5",
        "https://ddev.site.evil.com",
        "http://localhost",
    ):
        with expect(smoke.SmokeError, "allowlist staging"):
            smoke.kiem_host_staging(xau)
    print("[PASS] chi host staging duoc chay smoke; production bi tu choi")


def test_thieu_co_xac_nhan_thi_khong_chay():
    ma = smoke.main(["--job-id", "00000000-0000-4000-8000-000000000001"])
    assert ma == 1, ma
    print("[PASS] thieu --confirm-staging-fixture thi thoat ngay, khong cham DB")


def test_engine_gia_danh_dau_ro_va_khong_tra_fields():
    state = smoke.engine_gia({"node_id": "n1", "content_type": "cam_nang",
                              "langcode": "vi"})
    assert state["report"]["note"] == smoke.FIXTURE_NOTE
    assert state["report"]["fixture"] is True
    # Khong tra `fields` de worker dung fields cua tai lieu THAT da fetch.
    assert "fields" not in state, state
    print("[PASS] engine gia danh dau fixture va khong bia fields")


def test_engine_gia_khong_bao_gio_cham_ai_core():
    goc = ai_core.get_client

    def khong_duoc_goi(*a, **kw):
        raise AssertionError("smoke KHONG duoc goi LLM")

    ai_core.get_client = khong_duoc_goi
    try:
        smoke.engine_gia({"node_id": "n1"})
    finally:
        ai_core.get_client = goc
    print("[PASS] engine gia chay ma khong cham ai_core.get_client")


# ------------------------------------------------------------ integration


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _xep_job(conn, external_id="smoke-1", content_hash=None):
    context = sites.select_review_context(conn, q.DEFAULT_SITE_ID, "cam_nang", "vi")
    ket = q.enqueue_scoped(
        conn, context, external_id, content_hash or HASH_V1, "event",
        external_revision_id="123", content_hash_version=1,
    )
    return ket["public_id"]


def test_hang_doi_ban_thi_tu_choi(conn):
    _reset_schema(conn)
    try:
        with expect(smoke.SmokeError, "can dung 1 job queued"):
            smoke.kiem_hang_doi_sach(conn)

        _xep_job(conn, "smoke-a")
        smoke.kiem_hang_doi_sach(conn)

        _xep_job(conn, "smoke-b")
        with expect(smoke.SmokeError, "can dung 1 job queued"):
            smoke.kiem_hang_doi_sach(conn)

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE review_job SET status='running' WHERE external_content_id='smoke-a'"
            )
        with expect(smoke.SmokeError, "dang chay"):
            smoke.kiem_hang_doi_sach(conn)
    finally:
        _drop(conn)
    print("[PASS] hang doi con job khac hoac job dang chay thi smoke tu choi")


def _drop(conn):
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


def test_chay_that_ghi_run_fixture_va_mot_callback(conn):
    _reset_schema(conn)
    try:
        job_id = _xep_job(conn)
        connector = ConnectorGia()
        goc = ai_core.get_client
        ai_core.get_client = lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("smoke KHONG duoc goi LLM")
        )
        try:
            tom_tat = smoke.chay(
                conn,
                job_id=str(job_id),
                connector_factory=lambda _conn, _job: connector,
            )
        finally:
            ai_core.get_client = goc

        assert tom_tat["job_status"] == q.DONE, tom_tat
        assert tom_tat["run_is_fixture"] is True, tom_tat
        assert tom_tat["writeback_status"] == "succeeded", tom_tat
        assert tom_tat["run_revision_id"] == "123", tom_tat
        assert tom_tat["host"] == "drupal.ddev.site", tom_tat
        assert connector.fetch_calls == 1, connector.fetch_calls
        assert len(connector.write_calls) == 1, connector.write_calls

        # Run fixture PHAI bi loai khoi metric production.
        from review_platform.admin import queries

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM run_log WHERE is_fixture")
            assert cur.fetchone()[0] == 1
        clause = queries._fixture_clause(False)
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM run_log WHERE TRUE {clause}")
            assert cur.fetchone()[0] == 0, "run fixture van lot vao metric"
    finally:
        _drop(conn)
    print("[PASS] smoke tao run fixture, mot callback, va bi loai khoi metric")


def test_job_id_khong_khop_thi_dung_han(conn):
    _reset_schema(conn)
    try:
        _xep_job(conn)
        with expect(smoke.SmokeError, "khong phai"):
            smoke.chay(
                conn,
                job_id="00000000-0000-4000-8000-0000000000ff",
                connector_factory=lambda _conn, _job: ConnectorGia(),
            )
    finally:
        _drop(conn)
    print("[PASS] job claim ra khac --job-id thi dung han, khong cham nham bai")


def test_retry_mo_ho_dung_lai_run_id_va_khong_tao_run_thu_hai(conn):
    """Callback apply nhung mat response -> gui lai phai la already_applied."""
    _reset_schema(conn)
    try:
        job_id = _xep_job(conn, "smoke-retry")
        mat_response = ConnectorGia()
        mat_response.write_back = lambda request: (_ for _ in ()).throw(
            connector_base.ConnectorTransientError("response mat")
        )
        lan_dau = smoke.chay(
            conn, job_id=str(job_id),
            connector_factory=lambda _conn, _job: mat_response,
        )
        assert lan_dau["job_status"] == q.QUEUED, lan_dau

        with conn.cursor() as cur:
            cur.execute("UPDATE review_job SET run_after=now(), status='queued'")
            cur.execute("SELECT public_id FROM run_log")
            run_dau = cur.fetchone()[0]

        lan_hai_connector = ConnectorGia(outcome="already_applied")
        lan_hai = smoke.chay(
            conn, job_id=str(job_id),
            connector_factory=lambda _conn, _job: lan_hai_connector,
        )

        assert lan_hai["job_status"] == q.DONE, lan_hai
        assert lan_hai_connector.fetch_calls == 0, "khong duoc fetch lan hai"
        assert lan_hai_connector.write_calls[0].run_id == run_dau, (
            lan_hai_connector.write_calls[0].run_id, run_dau
        )
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM run_log")
            assert cur.fetchone()[0] == 1, "khong duoc tao run thu hai"
    finally:
        _drop(conn)
    print("[PASS] retry mo ho dung lai run_id cu, khong tao run/usage thu hai")


def test_race_revision_cu_khong_ghi_de_revision_moi(conn):
    _reset_schema(conn)
    try:
        job_id = _xep_job(conn, "smoke-race")
        connector = ConnectorGia(outcome="content_superseded")
        tom_tat = smoke.chay(
            conn, job_id=str(job_id),
            connector_factory=lambda _conn, _job: connector,
        )
        assert tom_tat["job_status"] == q.SUPERSEDED, tom_tat
        assert tom_tat["writeback_status"] == "superseded", tom_tat
        assert len(connector.write_calls) == 1, "khong duoc goi callback lan hai"
    finally:
        _drop(conn)
    print("[PASS] callback bao superseded -> job ket thuc superseded, khong ghi de")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_host_khong_phai_staging_bi_tu_choi,
        test_thieu_co_xac_nhan_thi_khong_chay,
        test_engine_gia_danh_dau_ro_va_khong_tra_fields,
        test_engine_gia_khong_bao_gio_cham_ai_core,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        postgres_conn = None
        print(
            f"[SKIP] integration smoke khong ket noi duoc Postgres "
            f"({exc.__class__.__name__}); [SKIP] khong phai [PASS]"
        )
    if postgres_conn is not None:
        for fn in (
            test_hang_doi_ban_thi_tu_choi,
            test_chay_that_ghi_run_fixture_va_mot_callback,
            test_job_id_khong_khop_thi_dung_han,
            test_retry_mo_ho_dung_lai_run_id_va_khong_tao_run_thu_hai,
            test_race_revision_cu_khong_ghi_de_revision_moi,
        ):
            try:
                fn(postgres_conn)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
        postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
