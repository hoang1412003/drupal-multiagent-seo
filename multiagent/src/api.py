"""Service HTTP nhan job tu Drupal va tra trang thai.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md muc 5.4

CHI nhan va tra trang thai - khong cham gi, khong nap model. Tra loi trong
vai ms vi Drupal dang cho trong luc editor bam Save.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe -m uvicorn api:app --port 8900 --app-dir src
"""
import hmac
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

import db
import job_queue as q

load_dotenv()

app = FastAPI(title="VF O2O Multi-Agent")


class JobIn(BaseModel):
    node_id: str
    content_hash: str
    source: str = "event"
    force: bool = False


def kiem_token(authorization: str = Header(default="")) -> None:
    """So token bang hmac.compare_digest - so bang `==` tren chuoi bi mat la
    ro ri thoi gian, du o loopback thi day van la thoi quen phai dung."""
    mong_doi = os.environ.get("VF_SERVICE_TOKEN", "")
    if not mong_doi:
        raise HTTPException(500, "VF_SERVICE_TOKEN chua dat trong .env")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "thieu Bearer token")
    if not hmac.compare_digest(authorization[7:], mong_doi):
        raise HTTPException(401, "token sai")


def _conn():
    conn = db.get_conn()
    q.dam_bao_bang(conn)
    return conn


def tao_job(body: JobIn, conn) -> dict:
    return q.enqueue(conn, body.node_id, body.content_hash, body.source,
                     force=body.force)


def trang_thai(node_id: str, conn) -> dict:
    job = q.job_moi_nhat(conn, node_id)
    if job is None:
        return {"status": "none", "job_id": None, "attempts": 0,
                "last_error": None, "updated_at": None}
    return {"status": job["status"], "job_id": job["id"],
            "attempts": job["attempts"], "last_error": job["last_error"],
            "updated_at": job["updated_at"].isoformat()}


def health(conn) -> dict:
    return {"ok": True, **q.thong_ke(conn)}


@app.post("/jobs", status_code=202, dependencies=[Depends(kiem_token)])
def post_jobs(body: JobIn):
    return tao_job(body, _conn())


@app.get("/jobs/by-node/{node_id}", dependencies=[Depends(kiem_token)])
def get_trang_thai(node_id: str):
    return trang_thai(node_id, _conn())


@app.get("/health")
def get_health():
    return health(_conn())
