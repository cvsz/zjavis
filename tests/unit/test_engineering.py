"""Unit tests for the JARVIS engineering intelligence (Phase 8).

Tests cover:
- Repository discovery (languages, dependency files, CI/CD, structure)
- Architecture analysis (layers, coupling, recommendations)
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from jarvis.core.exceptions import ValidationError
from jarvis.engineering import (
    get_capability,
    list_capabilities,
    register_capability,
)
from jarvis.engineering.analysis import (
    ArchitectureAnalyzer,
    ArchitectureReport,
    LayerInfo,
    analyzer,
)
from jarvis.engineering.discovery import (
    RepoInfo,
    RepositoryDiscovery,
    discovery,
)

# ---------------------------------------------------------------------------
# RepositoryDiscovery tests
# ---------------------------------------------------------------------------


class TestRepoInfo:
    """Tests for RepoInfo dataclass."""

    def test_repo_info_defaults(self) -> None:
        info = RepoInfo(root_path="/tmp/test", name="test")
        assert info.root_path == "/tmp/test"
        assert info.name == "test"
        assert info.languages == []
        assert info.dependency_files == []
        assert info.ci_cd_files == []
        assert info.has_dockerfile is False
        assert info.total_python_files == 0


class TestRepositoryDiscovery:
    """Tests for RepositoryDiscovery."""

    @pytest.fixture
    def tmp_repo(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            # Create a minimal repo structure
            os.makedirs(os.path.join(tmp, "src", "jarvis"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "tests", "unit"), exist_ok=True)
            with open(os.path.join(tmp, "requirements.txt"), "w") as fh:
                fh.write("fastapi>=0.115.0\n")
            with open(os.path.join(tmp, "README.md"), "w") as fh:
                fh.write("# Test\n")
            with open(os.path.join(tmp, "Dockerfile"), "w") as fh:
                fh.write("FROM python:3.14\n")
            with open(os.path.join(tmp, "Makefile"), "w") as fh:
                fh.write("help:\n\t@echo hi\n")
            with open(os.path.join(tmp, "AGENTS.md"), "w") as fh:
                fh.write("# Agents\n")
            with open(os.path.join(tmp, "SECURITY.md"), "w") as fh:
                fh.write("# Security\n")
            with open(os.path.join(tmp, "src", "jarvis", "__init__.py"), "w") as fh:
                fh.write('__version__ = "0.1.0"\n')
            with open(os.path.join(tmp, "tests", "unit", "test_x.py"), "w") as fh:
                fh.write("def test_x(): pass\n")
            yield tmp

    @pytest.mark.asyncio
    async def test_discover_basic(self, tmp_repo: str) -> None:
        disc = RepositoryDiscovery(root_path=tmp_repo)
        info = await disc.discover()
        assert info.name == os.path.basename(tmp_repo)
        assert "Python" in info.languages
        assert "requirements.txt" in info.dependency_files
        assert info.has_readme is True
        assert info.has_dockerfile is True
        assert info.has_makefile is True
        assert info.has_agents_md is True
        assert info.has_security_md is True
        assert info.total_python_files >= 2  # __init__.py + test_x.py
        assert info.total_test_files >= 1

    @pytest.mark.asyncio
    async def test_discover_invalid_root(self) -> None:
        with pytest.raises(ValidationError):
            RepositoryDiscovery(root_path="/nonexistent/path/xyz")

    def test_to_dict(self) -> None:
        info = RepoInfo(root_path="/tmp/x", name="x", languages=["Python"])
        d = discovery.to_dict(info)
        assert d["root_path"] == "/tmp/x"
        assert d["name"] == "x"
        assert d["languages"] == ["Python"]


# ---------------------------------------------------------------------------
# ArchitectureAnalyzer tests
# ---------------------------------------------------------------------------


class TestLayerInfo:
    """Tests for LayerInfo dataclass."""

    def test_layer_info(self) -> None:
        layer = LayerInfo(
            name="api",
            path="/tmp/api",
            file_count=5,
            responsibilities=["HTTP route handlers"],
        )
        assert layer.name == "api"
        assert layer.file_count == 5


class TestArchitectureReport:
    """Tests for ArchitectureReport dataclass."""

    def test_report_defaults(self) -> None:
        report = ArchitectureReport()
        assert report.layers == []
        assert report.total_files == 0
        assert report.total_lines == 0
        assert report.coupling_score == 0.0


class TestArchitectureAnalyzer:
    """Tests for ArchitectureAnalyzer."""

    @pytest.fixture
    def tmp_repo(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "api"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "core"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "db"), exist_ok=True)
            with open(os.path.join(tmp, "api", "routes.py"), "w") as fh:
                fh.write("from fastapi import APIRouter\n")
            with open(os.path.join(tmp, "core", "config.py"), "w") as fh:
                fh.write("from pydantic import BaseSettings\n")
            with open(os.path.join(tmp, "db", "models.py"), "w") as fh:
                fh.write("from sqlalchemy import Column\n")
            yield tmp

    @pytest.mark.asyncio
    async def test_analyze_basic(self, tmp_repo: str) -> None:
        anal = ArchitectureAnalyzer(root_path=tmp_repo)
        report = await anal.analyze()
        assert report.total_files >= 3
        assert report.total_lines > 0
        assert len(report.layers) >= 3
        layer_names = [l.name for l in report.layers]
        assert "api" in layer_names
        assert "core" in layer_names
        assert "db" in layer_names
        assert report.coupling_score >= 0.0
        assert len(report.recommendations) > 0

    def test_to_dict(self) -> None:
        report = ArchitectureReport()
        d = analyzer.to_dict(report)
        assert d["layers"] == []
        assert d["total_files"] == 0


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestEngineeringRegistry:
    """Tests for the engineering capability registry."""

    def test_register_and_get(self) -> None:
        cap = MagicMock()
        register_capability("test-capability", cap)
        assert get_capability("test-capability") is cap

    def test_list_capabilities(self) -> None:
        caps = list_capabilities()
        assert "repository_discovery" in caps
        assert "architecture_analysis" in caps

    def test_get_unknown(self) -> None:
        assert get_capability("nonexistent") is None
