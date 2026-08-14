"""Router /api/v1: site suy tu credential, khong bao gio tu body.

Ba quy tac khong duoc noi long o day:

1. Moi ly do xac thuc that bai deu tra CUNG mot 401 khong chi tiet. Phan biet
   "token sai" voi "site da tat" la chi cho ke tan cong biet no dang o dau.
2. Job cua site khac tra 404 chu khong 403. 403 xac nhan UUID do co ton tai.
3. `last_error` chi tra ma da nam trong allowlist. Exception tho co the chua
   duong dan, cau SQL hoac ten host noi bo.
"""
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Response

import job_queue as q
from review_platform import database as platform_database
from review_platform import sites
from review_platform.api import auth
from review_platform.api.models import JobAccepted, JobCreate, JobStatus


router = APIRouter(prefix="/api/v1", tags=["api-v1"])

# Ma loi an toan de lo ra ngoai. Moi thu khac quy ve `internal`.
MA_LOI_AN_TOAN = frozenset({
    "connector_auth",
    "input_hash_mismatch",
    "llm_transient",
    "writeback_failed",
    "internal",
})


def get_db():
    """Connection theo request. App that va test deu override dependency nay."""
    with platform_database.open_connection() as conn:
        yield conn


def site_principal(
    authorization: str = Header(default=""),
    conn=Depends(get_db),
) -> auth.SitePrincipal:
    try:
        return auth.authenticate_bearer(conn, authorization)
    except auth.CredentialError as exc:
        raise HTTPException(401, "unauthorized") from exc


def ma_loi_an_toan(raw: str | None) -> str | None:
    """Chi giu ma dau tien neu no nam trong allowlist, con lai la `internal`."""
    if raw is None:
        return None
    ma = raw.split(":", 1)[0].strip()
    return ma if ma in MA_LOI_AN_TOAN else "internal"


def _trang_thai(row: dict) -> JobStatus:
    return JobStatus(
        job_id=row["public_id"],
        status=row["status"],
        attempts=row["attempts"],
        last_error=ma_loi_an_toan(row["last_error"]),
        external_content_id=row["external_content_id"],
        external_revision_id=row["external_revision_id"],
        content_hash=row["content_hash"],
        content_hash_version=row["content_hash_version"],
        policy_version=row["policy_version"],
        source=row["source"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/jobs", response_model=JobAccepted)
def post_jobs(
    body: JobCreate,
    response: Response,
    principal: auth.SitePrincipal = Depends(site_principal),
    conn=Depends(get_db),
):
    site = principal.site
    if site.intake_paused:
        raise HTTPException(423, "intake_paused")

    try:
        context = sites.select_review_context(
            conn, site.id, body.content_type, body.langcode
        )
    except sites.ContextSelectionError as exc:
        # Tuyet doi khong fallback ve profile mac dinh: cham mot bai bang
        # policy cua scope khac la sai ket qua ma khong ai nhin thay.
        raise HTTPException(422, "profile_not_found") from exc

    try:
        ket_qua = q.enqueue_scoped(
            conn,
            context,
            body.external_content_id,
            body.content_hash,
            body.source,
            external_revision_id=body.external_revision_id,
            force=body.force,
            content_hash_version=body.content_hash_version,
        )
    except psycopg.Error as exc:
        # Bao 503 chu khong bao "queued" gia: client tin da xep hang thi bai
        # se khong bao gio duoc cham lai. Chi bat loi driver - ValueError la
        # loi lap trinh va phai noi len thanh 500 that.
        raise HTTPException(503, "database_unavailable") from exc

    trang_thai = ket_qua["status"]
    if trang_thai == "dead_letter":
        response.status_code = 409
    elif trang_thai == q.DUPLICATE:
        response.status_code = 200
    else:
        response.status_code = 202

    return JobAccepted(
        job_id=ket_qua["public_id"],
        status=trang_thai,
        duplicate=trang_thai == q.DUPLICATE,
        policy_version=context.profile.policy_version,
    )


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(
    job_id: UUID,
    principal: auth.SitePrincipal = Depends(site_principal),
    conn=Depends(get_db),
):
    row = q.job_theo_public_id(conn, site_id=principal.site.id, public_id=job_id)
    if row is None:
        raise HTTPException(404, "job_not_found")
    return _trang_thai(row)


@router.get("/jobs/by-content/{external_content_id}", response_model=JobStatus)
def get_job_by_content(
    external_content_id: str,
    principal: auth.SitePrincipal = Depends(site_principal),
    conn=Depends(get_db),
):
    row = q.job_moi_nhat_scoped(
        conn,
        site_id=principal.site.id,
        external_content_id=external_content_id,
    )
    if row is None:
        raise HTTPException(404, "job_not_found")
    return _trang_thai(row)
