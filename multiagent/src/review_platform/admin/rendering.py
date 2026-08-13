"""Jinja environment va duong dan static dung chung cho Platform Admin."""
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import select_autoescape


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

templates = Jinja2Templates(directory=TEMPLATE_DIR)
templates.env.autoescape = select_autoescape(("html", "xml"), default=True)


def render_template(
    request: Request,
    name: str,
    *,
    status_code: int = 200,
    **context,
):
    """Render mot admin template voi autoescape bat buoc."""
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=context,
        status_code=status_code,
    )
