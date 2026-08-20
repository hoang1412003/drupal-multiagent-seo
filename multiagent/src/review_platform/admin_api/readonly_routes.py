"""Cau hinh/KB va ket qua phep do — hai man CHI DOC.

Khong co endpoint ghi nao, va khong duoc them: day la cau hinh he thong va
bang chung do luong, khong phai du lieu nghiep vu sua duoc tu giao dien.
"""
from fastapi import APIRouter, Depends, Response

from review_platform.admin import dependencies as admin_dependencies
from review_platform.admin import evaluation, read_only_sources
from review_platform.admin_api import dependencies, errors, models
from review_platform.auth.rbac import Role


router = APIRouter()


@router.get("/config-kb", response_model=models.ConfigKbResponse)
def config_kb(
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
    conn=Depends(admin_dependencies.get_db),
):
    return models.ConfigKbResponse(
        policy_files=[
            models.PolicyFileModel.from_view(item)
            for item in read_only_sources.load_policy_files()
        ],
        profile_assignments=[
            models.ProfileAssignmentModel.from_view(item)
            for item in read_only_sources.load_profile_assignments(conn)
        ],
        kb_summary=[
            models.KBSummaryModel.from_view(item)
            for item in read_only_sources.load_kb_summary(conn)
        ],
    )


@router.get("/evaluation", response_model=models.EvaluationResponse)
def evaluation_list(
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
):
    return models.EvaluationResponse(
        experiments=[
            models.ExperimentModel.from_view(item)
            for item in evaluation.load_manifest()
        ],
    )


@router.get("/evaluation/evidence/{experiment}")
def evaluation_evidence(
    experiment: str,
    resolved=Depends(dependencies.require_console_role(Role.VIEWER)),
):
    """Tra FILE THO, khong phai JSON.

    Giu nguyen hai header cua admin cu. `nosniff` la thu ngan trinh duyet doan
    kieu mot file .txt thanh HTML roi chay script trong do; bo di la mo mot
    duong XSS qua noi dung file bang chung.
    """
    entry = evaluation.find_experiment(evaluation.load_manifest(), experiment)
    if entry is None or entry.evidence_file is None:
        raise errors.not_found("Không có evidence cho phép đo này")
    try:
        content, media_type = evaluation.read_evidence(entry)
    except FileNotFoundError as exc:
        raise errors.not_found("Không có evidence cho phép đo này") from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
