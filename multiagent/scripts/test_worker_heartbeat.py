"""Test heartbeat cua worker (Plan 5 Task 1).

Moi khang dinh ve thoi gian dung `now` TIEM VAO, khong dung dong ho tuong:
test phu thuoc dong ho that se do ngau nhien tren may cham hoac CI ban.

Chay: .venv\\Scripts\\python.exe scripts\\test_worker_heartbeat.py
"""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import migrations, worker_health


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_worker_heartbeat"
MOC = datetime(2026, 8, 14, 10, 0, 0, tzinfo=timezone.utc)


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _drop(conn):
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


def test_khong_co_row_thi_unavailable_chu_khong_phai_stale(conn):
    _reset_schema(conn)
    try:
        view = worker_health.list_worker_health(conn, now=MOC)
        assert view.status == "unavailable", view
        assert view.instances == () and view.last_seen_at is None
    finally:
        _drop(conn)
    print("[PASS] chua bao gio chay -> unavailable, khac han stale")


def test_moi_beat_la_running_qua_30s_la_stale(conn):
    _reset_schema(conn)
    try:
        worker_health.beat(
            conn, instance_id="w1", started_at=MOC, version="abc123", now=MOC
        )

        ngay_sau = worker_health.list_worker_health(conn, now=MOC)
        assert ngay_sau.status == "running", ngay_sau
        assert ngay_sau.running_count == 1 and ngay_sau.stale_count == 0

        # 29 giay: van con trong nguong.
        gan = worker_health.list_worker_health(conn, now=MOC + timedelta(seconds=29))
        assert gan.status == "running", gan

        # 31 giay: qua han.
        xa = worker_health.list_worker_health(conn, now=MOC + timedelta(seconds=31))
        assert xa.status == "stale", xa
        assert xa.running_count == 0 and xa.stale_count == 1
        assert xa.last_seen_at == MOC
    finally:
        _drop(conn)
    print("[PASS] moi beat -> running; qua 30 giay -> stale")


def test_beat_lai_khong_ghi_de_started_at(conn):
    _reset_schema(conn)
    try:
        worker_health.beat(
            conn, instance_id="w1", started_at=MOC, version="v1", now=MOC
        )
        sau = MOC + timedelta(minutes=5)
        # Gia lap worker beat lai va TU KHAI mot started_at khac.
        worker_health.beat(
            conn, instance_id="w1", started_at=sau, version="v2", now=sau
        )

        view = worker_health.list_worker_health(conn, now=sau)
        instance = view.instances[0]
        assert instance.started_at == MOC, (
            "started_at phai giu nguyen de do duoc uptime, "
            f"nhung thanh {instance.started_at}"
        )
        assert instance.last_seen_at == sau
        assert instance.version == "v2", "version thi PHAI cap nhat"
    finally:
        _drop(conn)
    print("[PASS] beat lai cap nhat last_seen/version nhung giu started_at")


def test_current_job_doi_duoc_va_nullable(conn):
    _reset_schema(conn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO review_job (node_id, content_hash, status, source, "
                "site_id, profile_id, policy_version, external_content_id, "
                "content_type, langcode) VALUES ('n','h','queued','event',"
                "'00000000-0000-4000-8000-000000000001',"
                "'00000000-0000-4000-8000-000000000002','p','n','cam_nang','vi') "
                "RETURNING public_id"
            )
            job_public_id = cur.fetchone()[0]

        worker_health.beat(
            conn, instance_id="w1", started_at=MOC, version="v1",
            current_job_id=job_public_id, now=MOC,
        )
        assert worker_health.list_worker_health(
            conn, now=MOC
        ).instances[0].current_job_id == job_public_id

        worker_health.beat(
            conn, instance_id="w1", started_at=MOC, version="v1",
            current_job_id=None, now=MOC,
        )
        assert worker_health.list_worker_health(
            conn, now=MOC
        ).instances[0].current_job_id is None
    finally:
        _drop(conn)
    print("[PASS] current_job_id doi duoc va tro ve NULL khi worker ranh")


def test_mot_instance_song_thi_ca_he_van_running(conn):
    _reset_schema(conn)
    try:
        worker_health.beat(
            conn, instance_id="song", started_at=MOC, version="v1", now=MOC
        )
        worker_health.beat(
            conn, instance_id="treo", started_at=MOC, version="v1",
            now=MOC - timedelta(minutes=10),
        )

        view = worker_health.list_worker_health(conn, now=MOC)
        assert view.status == "running", view
        assert view.running_count == 1
        # Van phai bao co mot instance treo, khong duoc giau di.
        assert view.stale_count == 1, view
    finally:
        _drop(conn)
    print("[PASS] mot instance song -> running, nhung van bao so instance treo")


def test_forget_va_cleanup_chi_xoa_dung_row(conn):
    _reset_schema(conn)
    try:
        worker_health.beat(conn, instance_id="a", started_at=MOC, version="v", now=MOC)
        worker_health.beat(conn, instance_id="b", started_at=MOC, version="v", now=MOC)
        worker_health.forget(conn, instance_id="a")
        con_lai = worker_health.list_worker_health(conn, now=MOC)
        assert [i.instance_id for i in con_lai.instances] == ["b"], con_lai

        # cleanup chi dung toi row cu hon 7 ngay.
        assert worker_health.cleanup(conn, now=MOC) == 0
        assert worker_health.cleanup(conn, now=MOC + timedelta(days=6)) == 0
        assert worker_health.cleanup(conn, now=MOC + timedelta(days=8)) == 1
        assert worker_health.list_worker_health(conn, now=MOC).status == "unavailable"
    finally:
        _drop(conn)
    print("[PASS] forget xoa dung instance; cleanup chi xoa row cu hon 7 ngay")


def test_nhip_tim_cua_worker_dap_dung_va_khong_lam_chet_worker():
    """NhipTim chay khong can Postgres: connection duoc tiem vao."""
    from contextlib import contextmanager
    import worker

    ghi = []

    class ConnGia:
        pass

    @contextmanager
    def mo_conn():
        yield ConnGia()

    goc_beat, goc_forget = worker.worker_health.beat, worker.worker_health.forget
    worker.worker_health.beat = lambda c, **kw: ghi.append(("beat", kw))
    worker.worker_health.forget = lambda c, **kw: ghi.append(("forget", kw))
    try:
        # chu_ky lon de thread khong tu dap xen vao giua cac khang dinh.
        nhip = worker.NhipTim(
            instance_id="w-test", version="sha123", chu_ky=3600, open_conn=mo_conn
        )
        nhip.bat_dau()
        assert [ten for ten, _ in ghi] == ["beat"], ghi
        assert ghi[0][1]["instance_id"] == "w-test"
        assert ghi[0][1]["version"] == "sha123"
        assert ghi[0][1]["current_job_id"] is None

        nhip.dat_job("job-abc")
        assert ghi[1][1]["current_job_id"] == "job-abc", ghi
        nhip.dat_job(None)
        assert ghi[2][1]["current_job_id"] is None, ghi
        # started_at phai giu nguyen qua moi nhip.
        assert len({kw["started_at"] for _, kw in ghi}) == 1, ghi

        nhip.dung()
        assert ghi[-1][0] == "forget", ghi
        assert not nhip._thread.is_alive(), "thread heartbeat phai dung han"
    finally:
        worker.worker_health.beat = goc_beat
        worker.worker_health.forget = goc_forget
    print("[PASS] NhipTim dap dung instance/version/job va dung han khi tat")


def test_heartbeat_hong_khong_lam_chet_worker():
    """Database chet thi worker VAN chay - nhung khong bao khoe gia.

    Khong ghi duoc nhip nghia la dashboard se thay stale. Do la su that, va
    tot hon nhieu so voi viec nem loi lam chet ca tien trinh worker.
    """
    from contextlib import contextmanager
    import worker

    @contextmanager
    def mo_conn_hong():
        raise RuntimeError("mat ket noi database")
        yield  # pragma: no cover

    nhip = worker.NhipTim(
        instance_id="w-hong", version="v", chu_ky=3600, open_conn=mo_conn_hong
    )
    nhip.bat_dau()   # khong duoc nem
    nhip.dat_job("x")
    nhip.dung()      # cung khong duoc nem
    print("[PASS] heartbeat hong chi log canh bao, worker van chay tiep")


def test_danh_tinh_worker_doc_env_va_cat_do_dai():
    import worker

    goc = dict(os.environ)
    try:
        os.environ.pop("VF_WORKER_INSTANCE_ID", None)
        os.environ.pop("VF_RELEASE_SHA", None)
        instance_id, version = worker.danh_tinh_worker()
        assert ":" in instance_id, instance_id
        assert version == "unknown", version

        os.environ["VF_WORKER_INSTANCE_ID"] = "w" * 200
        os.environ["VF_RELEASE_SHA"] = "s" * 200
        instance_id, version = worker.danh_tinh_worker()
        # Cat theo dung CHECK constraint cua bang, khong de DB tu choi luc chay.
        assert len(instance_id) == 128 and len(version) == 128
    finally:
        os.environ.clear()
        os.environ.update(goc)
    print("[PASS] danh tinh worker doc env, mac dinh hostname:pid, cat 128 ky tu")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_nhip_tim_cua_worker_dap_dung_va_khong_lam_chet_worker,
        test_heartbeat_hong_khong_lam_chet_worker,
        test_danh_tinh_worker_doc_env_va_cat_do_dai,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            f"[SKIP] khong phai [PASS]"
        )
        print("OK" if not failed else "CO TEST DO")
        sys.exit(1 if failed else 0)

    for fn in (
        test_khong_co_row_thi_unavailable_chu_khong_phai_stale,
        test_moi_beat_la_running_qua_30s_la_stale,
        test_beat_lai_khong_ghi_de_started_at,
        test_current_job_doi_duoc_va_nullable,
        test_mot_instance_song_thi_ca_he_van_running,
        test_forget_va_cleanup_chi_xoa_dung_row,
    ):
        try:
            fn(postgres_conn)
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
