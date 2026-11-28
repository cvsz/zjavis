"""Unit tests for the Phase 10 web UI route handlers and templates."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "jarvis" / "ui" / "templates"
)


class TestTemplates:
    def test_login_template_exists(self) -> None:
        path = TEMPLATES_DIR / "login.html"
        assert path.is_file()
        html = path.read_text(encoding="utf-8")
        assert "JARVIS" in html
        assert '<form id="loginForm"' in html
        assert 'name="username"' in html
        assert 'name="password"' in html

    def test_dashboard_template_exists(self) -> None:
        path = TEMPLATES_DIR / "dashboard.html"
        assert path.is_file()
        html = path.read_text(encoding="utf-8")
        assert "JARVIS" in html
        assert "System Health" in html
        assert "Model Status" in html
        assert "Task Center" in html
        assert "Agent Monitor" in html
        assert "Approvals" in html
        assert "Memory Center" in html
        assert "localStorage.getItem('jarvis_token'" in html
        assert "/dashboard" in html

    def test_templates_are_valid_html_snippets(self) -> None:
        for name in ("login.html", "dashboard.html"):
            html = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            assert html.strip().startswith("<!DOCTYPE html>")
            assert html.count("<html") == 1
            assert html.count("</html>") == 1

    def test_routes_module_importable(self) -> None:
        from jarvis.ui.routes import router

        assert router is not None
        # Both page routes are registered.
        paths = {route.path for route in router.routes}
        assert "/login" in paths
        assert "/dashboard" in paths
        assert "/" in paths
