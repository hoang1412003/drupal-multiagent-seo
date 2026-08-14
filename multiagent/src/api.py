"""Service HTTP nhan job tu Drupal va tra trang thai.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md muc 5.4

CHI nhan va tra trang thai - khong cham gi, khong nap model. Tra loi trong
vai ms vi Drupal dang cho trong luc editor bam Save.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe -m uvicorn api:app --port 8900 --app-dir src
"""
import hmac
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

import job_queue as q
from review_platform import database as platform_database
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import router as admin_router
from review_platform import security as platform_security
from review_platform.api import router as api_v1_router
from review_platform.api.limits import RequestSizeLimitMiddleware

load_dotenv()

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Fail-fast neu schema chua current; startup khong tu apply migration."""
    app.state.auth_config = admin_dependencies.load_auth_config()
    with platform_database.open_connection() as conn:
        migrations.require_current(conn, _MIGRATIONS_DIR)
    yield


app = FastAPI(title="VF O2O Multi-Agent", lifespan=_lifespan)
app.add_exception_handler(
    admin_dependencies.AdminForbidden,
    admin_router.forbidden_response,
)
app.include_router(admin_router.router)
app.include_router(api_v1_router.router)
# Thu tu quan trong: add_middleware xep tu trong ra ngoai, nen SecurityMiddleware
# them SAU se boc NGOAI limiter. Nho vay exception cua chinh limiter cung duoc
# quy ve response an toan, va moi response deu co security header.
app.add_middleware(
    RequestSizeLimitMiddleware,
    gioi_han=(("/api/v1", 16 * 1024), ("/admin", platform_security.MAX_ADMIN_BODY)),
)
app.add_middleware(platform_security.SecurityMiddleware)
app.mount(
    "/admin/static",
    StaticFiles(directory=admin_router.STATIC_DIR),
    name="admin-static",
)


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
    """Moi request so huu mot connection va FastAPI dong no sau response."""
    with platform_database.open_connection() as conn:
        yield conn


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


@app.post("/jobs", dependencies=[Depends(kiem_token)])
def post_jobs(body: JobIn, response: Response, conn=Depends(_conn)):
    """Ma HTTP theo dung ket qua: spec muc 5.4 quy dinh job trung phai la 200,
    chi job MOI moi la 202. Truoc day status_code=202 khai bao co dinh tren
    decorator ep moi phan hoi thanh cong thanh 202 - dung, vi ServiceClient
    ben Drupal khong doc ma HTTP (chi bat Throwable), nhung sai hop dong da
    ghi trong spec va se bay bat ky client nao sau nay phan biet "job moi"
    voi "job trung" bang ma HTTP.

    `dead_letter` -> 409 Conflict: job khong duoc tao vi cap (node_id,
    content_hash) nay da bo cuoc truoc do (het MAX_ATTEMPTS). Khong phai loi
    cua request nay - dung 409 chu khong phai 4xx/5xx khac de phan biet voi
    loi xac thuc (401) hay loi payload (422).

    Endpoint nay da DEPRECATED tu khi co /api/v1/jobs, nhung phai song suot
    cua so rollback: neu Drupal quay ve client cu ma endpoint nay da bi go
    thi bai se khong duoc cham va khong ai thay loi. Chua phat `Sunset` vi
    chua co ngay go duoc phe duyet."""
    response.headers["Deprecation"] = "true"
    kq = tao_job(body, conn)
    if kq["status"] == "dead_letter":
        response.status_code = 409
    elif kq["status"] == "duplicate":
        response.status_code = 200
    else:
        response.status_code = 202
    return kq


@app.get("/jobs/by-node/{node_id}", dependencies=[Depends(kiem_token)])
def get_trang_thai(node_id: str, response: Response, conn=Depends(_conn)):
    response.headers["Deprecation"] = "true"
    return trang_thai(node_id, conn)


@app.get("/health")
def get_health(conn=Depends(_conn)):
    return health(conn)
