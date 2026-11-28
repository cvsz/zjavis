"""Phase 10 JARVIS web UI route handlers.

Serves the login page and the server-rendered dashboard. Templates are
static HTML files under ``src/jarvis/ui/templates/``; no templating engine
or frontend build step is required.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _render(name: str, status_code: int = status.HTTP_200_OK) -> HTMLResponse:
    """Read a template file and return it as an HTML response."""
    path = _TEMPLATES_DIR / name
    html = path.read_text(encoding="utf-8")
    return HTMLResponse(content=html, status_code=status_code)


def _has_token(request: Request) -> bool:
    """Return True if a bearer token cookie is present."""
    cookie = request.cookies.get("jarvis_token", "")
    return bool(cookie)


@router.get("/login", response_class=HTMLResponse, summary="Login page")
async def login_page(request: Request) -> Response:
    """Serve the sign-in page. Redirects authenticated users to the dashboard."""
    if _has_token(request):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return _render("login.html")


@router.get("/dashboard", response_class=HTMLResponse, summary="Dashboard")
async def dashboard(request: Request) -> Response:
    """Serve the dashboard.

    Always renders; the embedded JavaScript redirects to /login when the
    API returns 401, so no server-side session cookie is required.
    """
    return _render("dashboard.html")


@router.get("/", include_in_schema=False)
async def root() -> Response:
    """Redirect the root path to the dashboard (or login)."""
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
