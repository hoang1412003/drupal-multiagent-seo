"""Route Config & KB chi doc cua Platform Admin."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from review_platform.admin import dependencies, read_only_sources, rendering


router = APIRouter()


@router.get("/config-kb", response_class=HTMLResponse)
def config_kb_page(
    request: Request,
    resolved=Depends(dependencies.current_session),
    conn=Depends(dependencies.get_db),
):
    return rendering.render_template(
        request,
        "config_kb.html",
        user=resolved.user,
        csrf_token=resolved.csrf_token,
        policy_files=read_only_sources.load_policy_files(),
        profiles=read_only_sources.load_profile_assignments(conn),
        kb_summaries=read_only_sources.load_kb_summary(conn),
        error=None,
    )
