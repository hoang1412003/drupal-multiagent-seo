"""Integration test HTTP cho /api/v1.

Dung TestClient that (khac test_api.py goi thang ham) vi thu phai kiem o day
la HOP DONG HTTP: ma trang thai phan biet queued/duplicate/dead-letter, 413
truoc khi parse, va 404 thay vi 403 khi truy cap cheo site. Goi thang ham se
bo qua dung nhung tang do.

Chay: .venv\\Scripts\\python.exe scripts\\test_api_v1.py
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("VF_SERVICE_TOKEN", "token-legacy-test")
os.environ.setdefault("ADMIN_CSRF_KEY", "csrf-test-key-rieng-biet-du-32-byte")
os.environ.setdefault("ADMIN_THROTTLE_KEY", "throttle-test-key-rieng-biet-du-32b")
os.environ.setdefault("ADMIN_COOKIE_SECURE", "false")

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api as legacy_api
import db
import job_queue as q
from review_platform import migrations
from review_platform.api import auth, router as api_router
from review_platform.api.limits import RequestSizeLimitMiddleware


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_api_v1"
SITE_A = "00000000-0000-4000-8000-000000000001"
SITE_B = "00000000-0000-4000-8000-0000000000b1"
PROFILE_B = "00000000-0000-4000-8000-0000000000b2"
HASH_A = "a" * 64
HASH_B = "b" * 64


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _them_site_b(conn):
    """Site thu hai co profile cam_nang/vi rieng - dung cho test cheo site."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site (id, slug, name, connector_type, base_url, secret_ref) "
            "VALUES (%s, 'drupal-vn-thu-hai', 'Site B', 'drupal', "
            "'http://b.ddev.site', 'DRUPAL_B') ON CONFLICT DO NOTHING",
            (SITE_B,),
        )
        cur.execute(
            "INSERT INTO review_profile (id, code, market_code, language_code, "
            "content_type, status, policy_version, policy_snapshot) "
            "VALUES (%s, 'cam-nang-vn-b', 'VN', 'vi', 'cam_nang', 'active', "
            "'cam-nang-vn-b-v1', '{}'::jsonb) ON CONFLICT DO NOTHING",
            (PROFILE_B,),
        )
        cur.execute(
            "INSERT INTO site_profile_assignment (site_id, profile_id) "
            "VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (SITE_B, PROFILE_B),
        )


def _cap_token(conn, site_id) -> str:
    token = auth.generate_token()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site_api_credential (site_id, token_prefix, token_hash) "
            "VALUES (%s, %s, %s)",
            (site_id, auth.token_prefix(token), auth.hash_token(token)),
        )
    return token


def _client(conn, *, raise_server_exceptions=True):
    app = FastAPI()
    app.include_router(api_router.router)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.dependency_overrides[api_router.get_db] = lambda: conn
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _body(**thay_doi):
    payload = {
        "external_content_id": str(uuid4()),
        "external_revision_id": "10",
        "content_type": "cam_nang",
        "langcode": "vi",
        "content_hash": HASH_A,
        "content_hash_version": 2,
    }
    payload.update(thay_doi)
    return payload


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_moi_ly_do_xac_thuc_that_bai_deu_tra_cung_mot_401(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)

    phan_hoi = [
        client.post("/api/v1/jobs", json=_body()),
        client.post("/api/v1/jobs", json=_body(), headers={"Authorization": "Bearer sai"}),
        client.post("/api/v1/jobs", json=_body(), headers={"Authorization": f"Basic {token}"}),
        client.post("/api/v1/jobs", json=_body(), headers={"Authorization": "Bearer"}),
    ]
    for response in phan_hoi:
        assert response.status_code == 401, response.text
    # Cung mot body cho moi ly do: khong ro ri "token sai" hay "site tat".
    assert len({response.text for response in phan_hoi}) == 1, [
        response.text for response in phan_hoi
    ]

    with conn.cursor() as cur:
        cur.execute("UPDATE site_api_credential SET active=false WHERE site_id=%s", (SITE_A,))
    thu_hoi = client.post("/api/v1/jobs", json=_body(), headers=_auth(token))
    assert thu_hoi.status_code == 401, thu_hoi.text
    assert thu_hoi.text == phan_hoi[0].text
    with conn.cursor() as cur:
        cur.execute("UPDATE site_api_credential SET active=true WHERE site_id=%s", (SITE_A,))
    print("[PASS] thieu/sai/revoked token deu tra cung mot 401 khong chi tiet")


def test_body_co_site_id_hoac_field_la_bi_422(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)

    for payload in (
        _body(site_id=SITE_B),
        _body(profile_id=PROFILE_B),
        _body(khong_ton_tai="x"),
    ):
        response = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
        assert response.status_code == 422, (payload, response.text)
    print("[PASS] body mang site_id hoac field la deu bi 422, khong bo qua im lang")


def test_hash_lang_revision_sai_dinh_dang_bi_422(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)

    for payload in (
        _body(content_hash=HASH_A.upper()),
        _body(content_hash="abc"),
        _body(langcode="vie"),
        _body(langcode="VI"),
        _body(external_revision_id="0"),
        _body(external_revision_id="abc"),
        _body(content_hash_version=1),
        _body(external_content_id=""),
        _body(source="tu_dong"),
    ):
        response = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
        assert response.status_code == 422, (payload, response.text)
    print("[PASS] hash hoa, langcode/revision/version/source sai deu bi 422")


def test_job_moi_202_va_job_trung_200(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)
    payload = _body()

    moi = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
    assert moi.status_code == 202, moi.text
    assert moi.json()["status"] == "queued"
    assert moi.json()["duplicate"] is False
    assert moi.json()["policy_version"] == "cam-nang-vn-v1"

    trung = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
    assert trung.status_code == 200, trung.text
    assert trung.json()["duplicate"] is True
    assert trung.json()["job_id"] == moi.json()["job_id"]

    # Job luu dung version 2, khong phai default 1 cua migration.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash_version, external_revision_id FROM review_job "
            "WHERE external_content_id=%s",
            (payload["external_content_id"],),
        )
        assert cur.fetchone() == (2, "10")
    print("[PASS] job moi 202, job trung 200 cung job_id, luu hash version 2")


def test_dead_letter_409_va_force_tao_job_lien_ket_row_failed(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)
    payload = _body()

    tao = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
    assert tao.status_code == 202
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE review_job SET status='failed', attempts=3 WHERE public_id=%s "
            "RETURNING id",
            (tao.json()["job_id"],),
        )
        failed_id = cur.fetchone()[0]

    chan = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
    assert chan.status_code == 409, chan.text
    assert chan.json()["status"] == "dead_letter"

    ep = client.post(
        "/api/v1/jobs",
        json=_body(**{**payload, "force": True, "source": "manual"}),
        headers=_auth(token),
    )
    assert ep.status_code == 202, ep.text
    with conn.cursor() as cur:
        cur.execute(
            "SELECT supersedes_job_id, source FROM review_job WHERE public_id=%s",
            (ep.json()["job_id"],),
        )
        assert cur.fetchone() == (failed_id, "manual")
        # Row dead-letter phai GIU trang thai failed lam bang chung.
        cur.execute("SELECT status FROM review_job WHERE id=%s", (failed_id,))
        assert cur.fetchone()[0] == "failed"
    print("[PASS] dead-letter 409, force tao job moi lien ket dung row failed")


def test_site_tam_dung_intake_tra_423(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)
    with conn.cursor() as cur:
        cur.execute("UPDATE site SET intake_paused=true WHERE id=%s", (SITE_A,))
    try:
        response = client.post("/api/v1/jobs", json=_body(), headers=_auth(token))
        assert response.status_code == 423, response.text
    finally:
        with conn.cursor() as cur:
            cur.execute("UPDATE site SET intake_paused=false WHERE id=%s", (SITE_A,))
    print("[PASS] site tam dung intake tra 423, khong xep job")


def test_khong_co_profile_khop_tra_422_va_khong_default(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)

    response = client.post(
        "/api/v1/jobs",
        json=_body(content_type="landing_page"),
        headers=_auth(token),
    )
    assert response.status_code == 422, response.text
    assert "profile_not_found" in response.text

    response = client.post("/api/v1/jobs", json=_body(langcode="en"), headers=_auth(token))
    assert response.status_code == 422, response.text
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM review_job WHERE langcode='en'")
        assert cur.fetchone()[0] == 0
    print("[PASS] khong co profile khop tra 422 profile_not_found, khong dung mac dinh")


def test_loi_database_tra_503_khong_bao_queued_gia(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn, raise_server_exceptions=False)
    payload = _body()

    goc = api_router.q.enqueue_scoped

    def hong(*a, **kw):
        raise psycopg.OperationalError("connection to server failed")

    api_router.q.enqueue_scoped = hong
    try:
        response = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
    finally:
        api_router.q.enqueue_scoped = goc

    assert response.status_code == 503, response.text
    assert "queued" not in response.text
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM review_job WHERE external_content_id=%s",
            (payload["external_content_id"],),
        )
        assert cur.fetchone()[0] == 0
    print("[PASS] loi database tra 503 va khong tao job gia")


def test_token_site_a_khong_doc_duoc_job_cua_site_b(conn):
    _them_site_b(conn)
    token_a = _cap_token(conn, SITE_A)
    token_b = _cap_token(conn, SITE_B)
    client = _client(conn)

    payload = _body(content_hash=HASH_B)
    cua_b = client.post("/api/v1/jobs", json=payload, headers=_auth(token_b))
    assert cua_b.status_code == 202, cua_b.text
    job_id = cua_b.json()["job_id"]

    bi_chan = client.get(f"/api/v1/jobs/{job_id}", headers=_auth(token_a))
    assert bi_chan.status_code == 404, bi_chan.text

    theo_noi_dung = client.get(
        f"/api/v1/jobs/by-content/{payload['external_content_id']}",
        headers=_auth(token_a),
    )
    assert theo_noi_dung.status_code == 404, theo_noi_dung.text

    cua_minh = client.get(f"/api/v1/jobs/{job_id}", headers=_auth(token_b))
    assert cua_minh.status_code == 200, cua_minh.text
    assert cua_minh.json()["policy_version"] == "cam-nang-vn-b-v1"
    print("[PASS] token site A tra 404 (khong phai 403) voi job cua site B")


def test_last_error_chi_tra_ma_trong_allowlist(conn):
    token = _cap_token(conn, SITE_A)
    client = _client(conn)
    payload = _body()
    tao = client.post("/api/v1/jobs", json=payload, headers=_auth(token))
    job_id = tao.json()["job_id"]

    for luu, mong_doi in (
        ("connector_auth: Drupal tra 403", "connector_auth"),
        ("input_hash_mismatch", "input_hash_mismatch"),
        ("psycopg.OperationalError: host 10.0.0.5 timeout", "internal"),
        ("Traceback D:\\drupal-multiagent-seo\\src\\worker.py line 42", "internal"),
    ):
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE review_job SET last_error=%s WHERE public_id=%s",
                (luu, job_id),
            )
        response = client.get(f"/api/v1/jobs/{job_id}", headers=_auth(token))
        assert response.status_code == 200, response.text
        assert response.json()["last_error"] == mong_doi, (luu, response.text)
        assert "10.0.0.5" not in response.text
        assert "worker.py" not in response.text
    print("[PASS] last_error chi lo ma trong allowlist, khong lo host/traceback")


def test_body_qua_16kib_tra_413_truoc_khi_parse_va_xac_thuc(conn):
    client = _client(conn)
    qua_lon = _body(external_content_id="x" * 20000)

    # Khong co token va body sai hop dong: neu tra 401/422 nghia la da parse
    # truoc khi chan kich thuoc.
    response = client.post("/api/v1/jobs", json=qua_lon)
    assert response.status_code == 413, response.status_code

    khong_khai_bao = client.post(
        "/api/v1/jobs",
        content=(chunk for chunk in [b"x" * 9000, b"y" * 9000]),
        headers={"Content-Type": "application/json"},
    )
    assert khong_khai_bao.status_code == 413, khong_khai_bao.status_code

    vua_du = client.post("/api/v1/jobs", json=_body())
    assert vua_du.status_code == 401, vua_du.status_code
    print("[PASS] body >16KiB tra 413 truoc parse, ke ca khi khong khai Content-Length")


def test_endpoint_legacy_van_song_va_gan_header_deprecation(conn):
    legacy_api.app.dependency_overrides[legacy_api._conn] = lambda: conn
    client = TestClient(legacy_api.app)
    try:
        response = client.post(
            "/jobs",
            json={"node_id": "legacy-node-1", "content_hash": "legacy-hash-1"},
            headers={"Authorization": f"Bearer {os.environ['VF_SERVICE_TOKEN']}"},
        )
        assert response.status_code == 202, response.text
        assert response.headers.get("Deprecation") == "true", dict(response.headers)
        assert "Sunset" not in response.headers

        trang_thai = client.get(
            "/jobs/by-node/legacy-node-1",
            headers={"Authorization": f"Bearer {os.environ['VF_SERVICE_TOKEN']}"},
        )
        assert trang_thai.status_code == 200, trang_thai.text
        assert trang_thai.headers.get("Deprecation") == "true"
    finally:
        legacy_api.app.dependency_overrides.pop(legacy_api._conn, None)

    # Job legacy phai o hash version 1 de worker chon dung thuat toan cu.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash_version FROM review_job WHERE node_id='legacy-node-1'"
        )
        assert cur.fetchone()[0] == 1
    print("[PASS] /jobs legacy van chay, co Deprecation, chua co Sunset, hash version 1")


if __name__ == "__main__":
    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
        _reset_schema(postgres_conn)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            f"[SKIP] khong phai [PASS]"
        )
        sys.exit(0)

    failed = False
    for fn in (
        test_moi_ly_do_xac_thuc_that_bai_deu_tra_cung_mot_401,
        test_body_co_site_id_hoac_field_la_bi_422,
        test_hash_lang_revision_sai_dinh_dang_bi_422,
        test_job_moi_202_va_job_trung_200,
        test_dead_letter_409_va_force_tao_job_lien_ket_row_failed,
        test_site_tam_dung_intake_tra_423,
        test_khong_co_profile_khop_tra_422_va_khong_default,
        test_loi_database_tra_503_khong_bao_queued_gia,
        test_token_site_a_khong_doc_duoc_job_cua_site_b,
        test_last_error_chi_tra_ma_trong_allowlist,
        test_body_qua_16kib_tra_413_truoc_khi_parse_va_xac_thuc,
        test_endpoint_legacy_van_song_va_gan_header_deprecation,
    ):
        try:
            fn(postgres_conn)
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    with postgres_conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
