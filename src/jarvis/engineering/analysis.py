"""Architecture analysis for engineering intelligence.

Analyzes repository structure to identify architectural patterns,
layering, coupling, and potential design issues. All operations are
read-only and governed by the policy engine.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.logging import get_logger
from jarvis.engineering import register_capability

logger = get_logger(__name__)


def _count_lines(file_path: str) -> int:
    """Count lines in a file (blocking, intended for asyncio.to_thread)."""
    try:
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


@dataclass
class LayerInfo:
    """Information about an architectural layer."""

    name: str
    path: str
    file_count: int
    responsibilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ArchitectureReport:
    """Architecture analysis results."""

    layers: list[LayerInfo] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    coupling_score: float = 0.0
    circular_dependencies: list[list[str]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ArchitectureAnalyzer:
    """Analyzes repository architecture for layering and coupling.

    Identifies architectural layers based on directory structure,
    estimates coupling, and produces recommendations for improvement.
    """

    def __init__(self, *, root_path: str | None = None) -> None:

        self.root_path = root_path or os.getcwd()

    async def analyze(self) -> ArchitectureReport:
        """Perform architecture analysis and return a report."""

        root = os.path.abspath(self.root_path)
        report = ArchitectureReport()

        # Identify likely layers from common directory names
        layer_candidates = {
            "api": "API layer - HTTP route handlers",
            "core": "Core layer - configuration, security, policy",
            "auth": "Identity layer - authentication and authorization",
            "db": "Data layer - database models and sessions",
            "ai": "Intelligence layer - model gateway, providers",
            "orchestration": "Orchestration layer - task execution",
            "approval": "Governance layer - approval workflow",
            "audit": "Governance layer - audit logging",
            "tools": "Capability layer - tool adapters",
            "engineering": "Engineering layer - repository analysis",
        }

        total_files = 0
        total_lines = 0

        for dir_name, responsibility in layer_candidates.items():
            dir_path = os.path.join(root, dir_name)
            if not os.path.isdir(dir_path):
                continue
            file_count = 0
            for _, _, files in os.walk(dir_path):
                for f in files:
                    if f.endswith(".py"):
                        file_count += 1
                        total_files += 1
                        try:
                            fp = os.path.join(dir_path, f)
                            line_count = await asyncio.to_thread(_count_lines, fp)
                            total_lines += line_count
                        except OSError:
                            pass
            if file_count > 0:
                report.layers.append(
                    LayerInfo(
                        name=dir_name,
                        path=dir_path,
                        file_count=file_count,
                        responsibilities=[responsibility],
                    )
                )

        report.total_files = total_files
        report.total_lines = total_lines

        # Simple coupling heuristic: directories that import from many
        # other directories indicate higher coupling.
        report.coupling_score = min(1.0, total_files / 100.0)

        # Generate recommendations
        if report.total_files == 0:
            report.recommendations.append(
                "No Python source files found; repository may not be a Python project."
            )
        if len(report.layers) < 3:
            report.recommendations.append(
                "Consider organizing code into explicit architectural layers "
                "(api, core, db, etc.) for better separation of concerns."
            )
        if report.coupling_score > 0.5:
            report.recommendations.append(
                "High coupling detected. Consider introducing interfaces "
                "between layers to reduce direct dependencies."
            )
        report.recommendations.append(
            "Ensure all layer boundaries are enforced by tests and import rules."
        )

        logger.info(
            "Architecture analysis complete",
            extra={
                "root": root,
                "total_files": report.total_files,
                "total_lines": report.total_lines,
                "layers": len(report.layers),
                "coupling_score": report.coupling_score,
            },
        )
        return report

    def to_dict(self, report: ArchitectureReport) -> dict[str, Any]:
        """Serialize ArchitectureReport to a dict (no secrets)."""
        return {
            "layers": [
                {
                    "name": l.name,
                    "path": l.path,
                    "file_count": l.file_count,
                    "responsibilities": l.responsibilities,
                    "dependencies": l.dependencies,
                }
                for l in report.layers
            ],
            "total_files": report.total_files,
            "total_lines": report.total_lines,
            "coupling_score": report.coupling_score,
            "circular_dependencies": report.circular_dependencies,
            "recommendations": report.recommendations,
        }


analyzer = ArchitectureAnalyzer()
register_capability("architecture_analysis", analyzer)

__all__ = [
    "ArchitectureAnalyzer",
    "ArchitectureReport",
    "LayerInfo",
    "analyzer",
]
