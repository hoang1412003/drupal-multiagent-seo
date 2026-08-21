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
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import job_queue as q
from review_platform import database as platform_database
from review_platform import migrations
from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin_api import errors as console_errors
from review_platform.admin_api import router as console_router
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
app.include_router(api_v1_router.router)
app.add_exception_handler(
    console_errors.ConsoleError,
    console_errors.console_error_handler,
)
# Chi doi hinh dang 422 cho /api/console; handler tu ne cac duong dan khac.
app.add_exception_handler(
    RequestValidationError,
    console_errors.validation_error_handler,
)
app.include_router(console_router.router)
# Thu tu quan trong: add_middleware xep tu trong ra ngoai, nen SecurityMiddleware
# them SAU se boc NGOAI limiter. Nho vay exception cua chinh limiter cung duoc
# quy ve response an toan, va moi response deu co security header.
app.add_middleware(
    RequestSizeLimitMiddleware,
    gioi_han=(
        ("/api/v1", 16 * 1024),
        # Duong dan khong khop prefix nao se di THANG, khong bi chan. Thieu
        # dong nay thi Console API nhan body kich thuoc tuy y.
        ("/api/console", platform_security.MAX_ADMIN_BODY),
        ("/admin", platform_security.MAX_ADMIN_BODY),
    ),
)
app.add_middleware(platform_security.SecurityMiddleware)

class SpaStaticFiles(StaticFiles):
    """StaticFiles tra index.html cho moi duong dan khong phai file.

    `html=True` cua Starlette KHONG du: no chi tra index.html cho duong dan
    thu muc. Bam F5 tren /console/jobs se 404 ngay trong mount va khong roi
    xuong route nao khac, vi Mount tu xu ly 404 cua chinh no.

    React Router giu lich su o phia client nen moi duong dan con deu phai tra
    ve cung mot index.html.
    """

    async def get_response(self, path: str, scope):
        # Starlette NEM HTTPException(404) chu khong tra ve response 404, nen
        # chi kiem tra status_code thoi la khong bao gio chay toi.
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


# Ban build cua Console React. Mount SAU moi include_router, neu khong mount
# se nuot cac route /api/console.
#
# Boc trong `if`: app phai khoi dong duoc khi chua ai chay `npm run build`.
# Thieu dieu nay thi backend khong chay noi tren may chua cai Node.
_CONSOLE_DIST = Path(__file__).resolve().parents[1] / "console_ui" / "dist"
if _CONSOLE_DIST.is_dir():
    app.mount(
        "/console",
        SpaStaticFiles(directory=_CONSOLE_DIST, html=True),
        name="console",
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
