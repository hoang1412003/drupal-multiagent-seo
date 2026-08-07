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
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["VF_SERVICE_TOKEN"] = "token-test"

import api
import db
import job_queue as q

SCHEMA = "vf_test_api"


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    q.dam_bao_bang(conn)
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
        test_trang_thai_node_chua_co_job,
        test_trang_thai_tra_job_moi_nhat,
        test_health_dem_theo_trang_thai,
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
