"""Route Evaluation va evidence allowlist, hoan toan read-only."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from review_platform.admin import dependencies, evaluation, rendering


router = APIRouter()


@router.get("/evaluation", response_class=HTMLResponse)
def evaluation_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
):
    return rendering.render_template(
        request,
        "evaluation.html",
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        experiments=evaluation.load_manifest(),
        error=None,
    )


@router.get("/evaluation/evidence/{experiment}")
def evaluation_evidence(
    experiment: str,
    _resolved=Depends(dependencies.current_session),
):
    entry = evaluation.find_experiment(evaluation.load_manifest(), experiment)
    if entry is None or entry.evidence_file is None:
        raise HTTPException(404, "Không có evidence cho phép đo này")
    try:
        content, media_type = evaluation.read_evidence(entry)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Không có evidence cho phép đo này") from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
