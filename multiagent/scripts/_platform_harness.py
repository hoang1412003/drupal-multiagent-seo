"""Harness dung chung cho ba bo test E2E cua Plan 5.

Mot noi duy nhat dung: API router THAT + PostgreSQL THAT + worker THAT, chi
thay bien ngoai (Drupal connector, engine LLM) bang fake. Khong goi mang,
khong goi Anthropic.

Tach ra file rieng vi ba file test (end_to_end, failure_matrix,
no_sensitive_persistence) can cung mot bo lap - chep ba ban se troi lech.

File nay KHONG phai test: no khong co ham `test_*` va khong bi meta-test doi
phai chay.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
import job_queue as q
import text_utils
import worker
from fastapi import FastAPI
from fastapi.testclient import TestClient
from review_platform import fingerprint as platform_fingerprint
from review_platform import migrations, sites
from review_platform.api import auth, router as api_router
from review_platform.api.limits import RequestSizeLimitMiddleware
from review_platform.connectors import base as connector_base


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SITE_A = "00000000-0000-4000-8000-000000000001"

# Chuoi canary: neu bat ky chuoi nao trong so nay xuat hien trong database,
# log hay HTML admin thi da co ro ri.
CANARY = {
    "title": "CANARY_TITLE_khong_duoc_luu_o_dau",
    "body": "CANARY_BODY_toan_van_bai_nhap_khong_duoc_roi_khoi_Drupal",
    "summary": "CANARY_SUMMARY_rieng_tu",
    "prompt": "CANARY_PROMPT_he_thong",
    "password": "CANARY_PASSWORD_sieu_bi_mat",
    "cookie": "CANARY_COOKIE_phien",
    "database_url": "postgresql://canary:CANARY_DSN_PASSWORD@h/d",
}

FIELDS = {
    "title": CANARY["title"],
    "body": f"<p>{CANARY['body']}</p>",
    "summary": CANARY["summary"],
    "url_alias": "/canary",
    "meta_description": "Mo ta canary",
    "image_alt": "Anh canary",
}
HASH_V2 = platform_fingerprint.input_fingerprint(FIELDS)
HASH_V1 = text_utils.content_hash(FIELDS)


def tai_lieu(*, fields=None, revision="10"):
    return connector_base.ContentDocument(
        fields=dict(fields or FIELDS),
        raw_content={"id": "canary"},
        source_url="http://drupal.ddev.site/node/1",
        external_revision_id=revision,
        content_type="cam_nang",
        langcode="vi",
    )


class ConnectorGia:
    """Drupal gia. Dem moi lan cham va cho phep dat truoc loi/ket qua."""

    def __init__(self, *, doc=None, outcome="applied", loi_fetch=None,
                 loi_write=None):
        self._doc = doc if doc is not None else tai_lieu()
        self.outcome = outcome
        self.loi_fetch = loi_fetch
        self.loi_write = loi_write
        self.fetch_calls = []
        self.write_calls = []

    def fetch_content(self, external_content_id, *, external_revision_id=None,
                      working_copy=False):
        self.fetch_calls.append({
            "id": external_content_id,
            "revision": external_revision_id,
            "working_copy": working_copy,
        })
        if self.loi_fetch is not None:
            raise self.loi_fetch
        return self._doc

    def write_back(self, request):
        self.write_calls.append(request)
        if self.loi_write is not None:
            raise self.loi_write
        return connector_base.WriteBackResult(
            outcome=self.outcome, applied_revision_id="11"
        )

    def list_pending(self, *, after_revision_id=0, limit=50):
        return connector_base.PendingPage()

    def health(self):
        return connector_base.ConnectorHealth(
            ok=True, status_code=200, checked_at=datetime.now(timezone.utc),
            error_code=None,
        )


class EngineGia:
    """Thay cho graph. Dem so lan goi va cho phep dat truoc loi."""

    def __init__(self, *, loi=None, usage=None, missing_agents=None):
        self.loi = loi
        self.usage = usage or []
        self.missing_agents = missing_agents or []
        self.calls = []

    def __call__(self, state):
        self.calls.append(state)
        import ai_core
        for entry in self.usage:
            ai_core.USAGE_LOG.append(dict(entry))
        if self.loi is not None:
            raise self.loi
        return {
            "node_id": state["node_id"],
            "decision": "needs_revision",
            "final_score": 60.0,
            "report": {
                "node_id": state["node_id"],
                "decision": "needs_revision",
                "final_score": 60.0,
                "missing_agents": list(self.missing_agents),
                # Prompt canary di qua engine nhung TUYET DOI khong duoc luu.
                "note": None,
                "details": {},
            },
        }


class MoiTruong:
    """Mot schema PostgreSQL sach + client API + tien ich xep/chay job."""

    def __init__(self, schema: str):
        self.schema = schema
        self.conn = db.psycopg.connect(db.dsn(), autocommit=True)
        self._reset()
        self.token = self._cap_token()
        self.client = self._client()

    def _reset(self):
        with self.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {self.schema} CASCADE")
            cur.execute(f"CREATE SCHEMA {self.schema}")
            cur.execute(f"SET search_path TO {self.schema}, public")
        migrations.apply_pending(self.conn, MIGRATIONS_DIR)

    def _cap_token(self) -> str:
        token = auth.generate_token()
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO site_api_credential (site_id, token_prefix, token_hash) "
                "VALUES (%s,%s,%s)",
                (SITE_A, auth.token_prefix(token), auth.hash_token(token)),
            )
        return token

    def _client(self):
        app = FastAPI()
        app.include_router(api_router.router)
        app.add_middleware(RequestSizeLimitMiddleware, gioi_han=(("/api/v1", 16384),))
        app.dependency_overrides[api_router.get_db] = lambda: self.conn
        return TestClient(app, raise_server_exceptions=False)

    # ------------------------------------------------------------ tien ich

    def headers(self, token=None):
        return {"Authorization": f"Bearer {token or self.token}"}

    def post_job(self, **thay_doi):
        payload = {
            "external_content_id": "canary-node",
            "external_revision_id": "10",
            "content_type": "cam_nang",
            "langcode": "vi",
            "content_hash": HASH_V2,
            "content_hash_version": 2,
        }
        token = thay_doi.pop("_token", None)
        payload.update(thay_doi)
        return self.client.post("/api/v1/jobs", json=payload, headers=self.headers(token))

    def xep_job_legacy(self, external_id="legacy-node"):
        context = sites.select_review_context(
            self.conn, q.DEFAULT_SITE_ID, "cam_nang", "vi"
        )
        return q.enqueue_scoped(
            self.conn, context, external_id, HASH_V1, "event",
            external_revision_id=None, content_hash_version=1,
        )

    def claim(self):
        return q.claim(self.conn, "harness")

    def chay(self, *, connector=None, engine=None, job=None, fixture_run=False):
        job = job or self.claim()
        assert job is not None, "khong co job de chay"
        engine = engine or EngineGia()
        connector = connector or ConnectorGia()
        ket = worker.chay_mot_job(
            self.conn, job, invoke=engine,
            connector_factory=lambda _c, _j: connector,
            fixture_run=fixture_run,
        )
        return {"ket": ket, "job": job, "engine": engine, "connector": connector}

    def scalar(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return None if row is None else row[0]

    def rows(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def dong(self):
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {self.schema} CASCADE")
        self.conn.close()


@contextmanager
def moi_truong(schema: str):
    mt = MoiTruong(schema)
    try:
        yield mt
    finally:
        mt.dong()


def co_postgres() -> bool:
    try:
        db.psycopg.connect(db.dsn(), autocommit=True).close()
        return True
    except Exception:
        return False
