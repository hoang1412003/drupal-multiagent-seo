"""Test logic cua service HTTP (spec 2026-08-07 muc 5.4, 8).

Goi THANG cac ham xu ly thay vi dung TestClient: TestClient keo them phu
thuoc `httpx`, va thu dang kiem o day la logic cua minh (so token hang thoi
gian, hinh dang tra ve, dedup) chu khong phai tang HTTP cua FastAPI. Danh
doi nay BO QUA phan kiem tang HTTP (routing, status_code khai bao tren
route, Header/Depends cua FastAPI that su chay dung khong) - bu lai bang
buoc curl that o Step 6 cua brief (goi service that qua HTTP).

Can Postgres that cho phan hang doi - [SKIP] neu khong co.
Chay: .venv\\Scripts\\python.exe scripts\\test_api.py
"""
import asyncio
from contextlib import contextmanager
import inspect
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["VF_SERVICE_TOKEN"] = "token-test"

import api
import db
import job_queue as q
from fastapi.params import Depends as DependsParam
from review_platform import migrations

SCHEMA = "vf_test_api"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


class _TrackedConnection:
    def __init__(self, number):
        self.number = number
        self.closed = False


class _ConnectionFactory:
    def __init__(self):
        self.connections = []

    @contextmanager
    def open(self):
        conn = _TrackedConnection(len(self.connections) + 1)
        self.connections.append(conn)
        try:
            yield conn
        finally:
            conn.closed = True


class _MissingTableCursor:
    def __init__(self, statements):
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.statements.append(sql)

    def fetchone(self):
        return None


class _MissingTableConnection:
    def __init__(self):
        self.statements = []

    def cursor(self):
        return _MissingTableCursor(self.statements)


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
    return conn


def _loi(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except api.HTTPException as e:
        return e.status_code
    return None


def test_thieu_token_thi_401(conn):
    assert _loi(api.kiem_token, "") == 401
    print("[PASS] khong co header Authorization -> 401")


def test_token_sai_thi_401(conn):
    assert _loi(api.kiem_token, "Bearer token-sai") == 401
    print("[PASS] token sai -> 401")


def test_token_dung_thi_qua(conn):
    api.kiem_token("Bearer token-test")
    print("[PASS] token dung -> khong nem gi")


def test_tao_job_moi_tra_queued(conn):
    kq = api.tao_job(api.JobIn(node_id="u1", content_hash="h1"), conn)
    assert kq["status"] == "queued" and kq["job_id"] > 0, kq
    print("[PASS] job moi -> status queued kem job_id")


def test_tao_job_trung_tra_duplicate(conn):
    api.tao_job(api.JobIn(node_id="u2", content_hash="h2"), conn)
    kq = api.tao_job(api.JobIn(node_id="u2", content_hash="h2"), conn)
    assert kq["status"] == "duplicate", kq
    print("[PASS] job trung -> duplicate, khong tao them")


def test_force_tao_duoc_job_moi(conn):
    api.tao_job(api.JobIn(node_id="u3", content_hash="h3"), conn)
    # Dung job_moi_nhat de lay DUNG job cua u3, khong dung q.claim(): claim()
    # lay job CU NHAT trong toan hang doi (khong loc theo node), ma u1/u2 tu
    # cac test truoc van con dang `queued` truoc u3 - claim() se bat nham job
    # cua u1, khong phai cua u3, va test het y nghia.
    job = q.job_moi_nhat(conn, "u3")
    q.complete(conn, job["id"])
    kq = api.tao_job(api.JobIn(node_id="u3", content_hash="h3", force=True), conn)
    assert kq["status"] == "queued", kq
    print("[PASS] force=True -> tao duoc job moi du da done")


def test_tao_job_tren_cap_da_dead_letter_tra_dead_letter(conn):
    """Sua loi Important (muc 2): dead-letter phai chan CA O DUONG CHINH
    (api.tao_job -> q.enqueue), khong chi o vong doi soat. api.py doi
    status='dead_letter' thanh HTTP 409 - test nay chi khoa logic tra ve
    status dung, phan ma HTTP bu bang buoc curl thu cong (xem docstring
    dau file).

    Goi q.fail() truc tiep voi `attempts` tu 1..3 thay vi di qua q.claim():
    claim() la FIFO tren CA BANG (khong loc theo node), ma cac test truoc do
    (u1, u2, job force cua u3) co y de lai job dang `queued` - claim() se bat
    nham job cua node khac. fail() chi doc tham so `attempts` truyen vao,
    khong doc cot attempts that trong DB, nen goi truc tiep van dung ket qua.
    """
    kq0 = api.tao_job(api.JobIn(node_id="u5", content_hash="h5"), conn)
    for lan in (1, 2, 3):
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE review_job SET attempts=%s, status='running' WHERE id=%s",
                (lan, kq0["job_id"]),
            )
        q.fail(conn, kq0["job_id"], f"loi {lan}", lan)
    assert q.job_moi_nhat(conn, "u5")["status"] == "failed"

    kq = api.tao_job(api.JobIn(node_id="u5", content_hash="h5"), conn)
    assert kq["status"] == "dead_letter", kq
    print("[PASS] tao_job tren cap da dead-letter -> tra dead_letter (api.py -> HTTP 409)")


def test_trang_thai_node_chua_co_job(conn):
    assert api.trang_thai("khong-ton-tai", conn)["status"] == "none"
    print("[PASS] node chua co job -> status 'none'")


def test_trang_thai_tra_job_moi_nhat(conn):
    api.tao_job(api.JobIn(node_id="u4", content_hash="h4"), conn)
    kq = api.trang_thai("u4", conn)
    assert kq["status"] == "queued" and kq["attempts"] == 0, kq
    print("[PASS] trang thai tra job moi nhat cua node")


def test_health_dem_theo_trang_thai(conn):
    kq = api.health(conn)
    assert kq["ok"] is True and kq["queued"] >= 1, kq
    print("[PASS] health tra so job theo tung trang thai")


def _goi_dependency_mot_lan(handler):
    dependency = api._conn()
    request_conn = next(dependency)
    try:
        handler(request_conn)
    finally:
        try:
            next(dependency)
        except StopIteration:
            pass
        else:
            raise AssertionError("connection dependency phai yield dung mot lan")
    return request_conn


def test_moi_request_mo_va_dong_connection_rieng(conn):
    assert hasattr(api, "platform_database"), "api chua dung connection lifecycle moi"
    factory = _ConnectionFactory()
    original = api.platform_database.open_connection
    api.platform_database.open_connection = factory.open
    try:
        first = _goi_dependency_mot_lan(lambda request_conn: None)
        second = _goi_dependency_mot_lan(lambda request_conn: None)
    finally:
        api.platform_database.open_connection = original

    assert first is not second
    assert first.closed and second.closed
    assert factory.connections == [first, second]
    print("[PASS] moi request co connection rieng va luon dong sau response")


def test_moi_route_database_deu_dung_dependency(conn):
    for handler in (api.post_jobs, api.get_trang_thai, api.get_health):
        parameter = inspect.signature(handler).parameters.get("conn")
        assert parameter is not None, handler.__name__
        assert isinstance(parameter.default, DependsParam), handler.__name__
        assert parameter.default.dependency is api._conn, handler.__name__
    print("[PASS] moi route database deu resolve connection qua Depends")


def test_lifespan_chan_schema_pending_va_dong_connection(conn):
    assert hasattr(api, "migrations"), "api chua co startup migration gate"
    assert hasattr(api, "platform_database"), "api chua co startup connection scope"
    factory = _ConnectionFactory()
    original_open = api.platform_database.open_connection
    original_require = api.migrations.require_current

    class PendingMigration(RuntimeError):
        pass

    def reject_pending(startup_conn, migrations_dir):
        assert startup_conn is factory.connections[-1]
        raise PendingMigration("schema pending")

    async def enter_lifespan():
        async with api._lifespan(api.app):
            raise AssertionError("lifespan khong duoc yield khi schema pending")

    api.platform_database.open_connection = factory.open
    api.migrations.require_current = reject_pending
    try:
        try:
            asyncio.run(enter_lifespan())
        except PendingMigration:
            pass
        else:
            raise AssertionError("startup phai fail khi migration con pending")
    finally:
        api.platform_database.open_connection = original_open
        api.migrations.require_current = original_require

    assert len(factory.connections) == 1
    assert factory.connections[0].closed
    print("[PASS] lifespan chan schema pending truoc route va dong connection")


def test_kb_guard_khong_am_tham_tao_schema_thieu(conn):
    missing = _MissingTableConnection()
    try:
        db.dam_bao_bang(missing, 1024)
    except RuntimeError as exc:
        assert "migrate" in str(exc).lower(), exc
    else:
        raise AssertionError("kb guard phai fail khi chua migrate")

    ddl = "\n".join(missing.statements).upper()
    assert "CREATE TABLE" not in ddl, ddl
    assert "CREATE EXTENSION" not in ddl, ddl
    print("[PASS] KB guard khong tu tao schema khi migration con thieu")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_thieu_token_thi_401,
        test_token_sai_thi_401,
        test_token_dung_thi_qua,
        test_tao_job_moi_tra_queued,
        test_tao_job_trung_tra_duplicate,
        test_force_tao_duoc_job_moi,
        test_tao_job_tren_cap_da_dead_letter_tra_dead_letter,
        test_trang_thai_node_chua_co_job,
        test_trang_thai_tra_job_moi_nhat,
        test_health_dem_theo_trang_thai,
        test_moi_request_mo_va_dong_connection_rieng,
        test_moi_route_database_deu_dung_dependency,
        test_lifespan_chan_schema_pending_va_dong_connection,
        test_kb_guard_khong_am_tham_tao_schema_thieu,
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
