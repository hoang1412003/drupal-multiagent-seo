r"""Integration test cho /config-kb va /evaluation cua Console API.

Hai man chi doc. Diem can khoa:
- Khong co endpoint ghi nao (day la cau hinh va ket qua do, khong phai du lieu
  nghiep vu sua duoc tu UI).
- /evaluation/evidence tra FILE THO, nen phai giu nguyen header nosniff cua
  admin cu: thieu no thi mot file .txt co the bi trinh duyet doan thanh HTML
  va chay script trong do.
- ExperimentView co `provenance_warning` khi metadata chua day du. Bo truong
  do di la de nguoi doc suy dien tu cac truong con thieu.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_readonly.py
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import evaluation
from review_platform.admin_api import errors, router as console_router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_console_api_readonly"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _make_client(conn):
    app = FastAPI()
    app.state.auth_config = admin_dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=False,
    )
    app.add_exception_handler(errors.ConsoleError, errors.console_error_handler)
    app.include_router(console_router.router)
    app.dependency_overrides[admin_dependencies.get_db] = lambda: conn
    return TestClient(app, follow_redirects=False, client=("198.51.100.96", 50000))


def _login_viewer(conn, username: str):
    users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    response = client.post(
        "/api/console/v1/auth/login",
        json={"username": username, "password": f"Mat-khau-{username}-2026"},
    )
    assert response.status_code == 200, response.text
    return client


def test_config_kb_tra_ba_nhom_va_viewer_xem_duoc(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "ro.configkb")

    response = client.get("/api/console/v1/config-kb")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"policy_files", "profile_assignments", "kb_summary"}

    assert body["policy_files"], "phai co it nhat mot file policy"
    first = body["policy_files"][0]
    assert set(first) == {
        "label", "relative_path", "sha256", "modified_at", "metadata", "error",
    }, set(first)
    assert first["modified_at"].endswith("Z"), first["modified_at"]
    # metadata la cap nhan-gia tri co THU TU, khong phai dict.
    assert isinstance(first["metadata"], list)
    if first["metadata"]:
        assert set(first["metadata"][0]) == {"label", "value"}
    print("[PASS] config-kb tra ba nhom, viewer xem duoc, metadata giu thu tu")


def test_evaluation_tra_du_phep_do_va_canh_bao_provenance(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "ro.evaluation")

    body = client.get("/api/console/v1/evaluation").json()
    assert set(body) == {"experiments"}

    goc = evaluation.load_manifest()
    assert len(body["experiments"]) == len(goc)

    first = body["experiments"][0]
    assert set(first) == {
        "experiment", "status", "score_path_snapshot", "head_commit",
        "prompt_version", "model", "run_at", "evidence_path",
        "metadata_complete", "summary", "has_evidence", "provenance_warning",
    }, set(first)

    # provenance_warning phai di kem, khong duoc bo: no la loi nhac dung suy
    # dien tu cac truong con thieu.
    for item, nguon in zip(body["experiments"], goc):
        assert item["provenance_warning"] == nguon.provenance_warning
        assert item["has_evidence"] == bool(nguon.evidence_file)
    print("[PASS] evaluation tra du phep do, giu canh bao provenance")


def test_evidence_giu_header_chong_doan_kieu(conn):
    """nosniff la thu ngan trinh duyet doan mot file .txt thanh HTML."""
    _reset_schema(conn)
    client = _login_viewer(conn, "ro.evidence")

    co_evidence = [e for e in evaluation.load_manifest() if e.evidence_file]
    assert co_evidence, "manifest phai co it nhat mot phep do co evidence"
    ten = co_evidence[0].experiment

    response = client.get(f"/api/console/v1/evaluation/evidence/{ten}")
    assert response.status_code == 200, response.text
    assert response.headers.get("x-content-type-options") == "nosniff", (
        "thieu nosniff: trinh duyet co the doan kieu file va chay script trong do"
    )
    assert response.headers.get("cache-control") == "no-store"
    assert len(response.content) > 0
    print("[PASS] evidence giu nosniff va no-store")


def test_evidence_khong_ton_tai_tra_404(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "ro.evidence404")

    khong_co = client.get("/api/console/v1/evaluation/evidence/KHONG-TON-TAI")
    assert khong_co.status_code == 404, khong_co.status_code
    assert khong_co.json()["error"]["code"] == "not_found"

    # Phep do co that nhung khong co evidence cung phai la 404.
    khong_evidence = [e for e in evaluation.load_manifest() if not e.evidence_file]
    if khong_evidence:
        r = client.get(
            f"/api/console/v1/evaluation/evidence/{khong_evidence[0].experiment}"
        )
        assert r.status_code == 404, r.status_code
    print("[PASS] evidence khong ton tai va phep do khong co evidence deu 404")


def test_hai_man_khong_co_endpoint_ghi(conn):
    _reset_schema(conn)
    client = _login_viewer(conn, "ro.readonly")
    for path in ("/api/console/v1/config-kb", "/api/console/v1/evaluation"):
        for method in ("post", "put", "patch", "delete"):
            r = getattr(client, method)(path)
            assert r.status_code == 405, f"{method} {path}: {r.status_code}"
    print("[PASS] config-kb va evaluation khong co endpoint ghi nao")


if __name__ == "__main__":
    try:
        connection = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            "[SKIP] khong phai [PASS]"
        )
        sys.exit(0)

    failed = False
    try:
        for fn in (
            test_config_kb_tra_ba_nhom_va_viewer_xem_duoc,
            test_evaluation_tra_du_phep_do_va_canh_bao_provenance,
            test_evidence_giu_header_chong_doan_kieu,
            test_evidence_khong_ton_tai_tra_404,
            test_hai_man_khong_co_endpoint_ghi,
        ):
            try:
                fn(connection)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
    finally:
        with connection.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        connection.close()

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
