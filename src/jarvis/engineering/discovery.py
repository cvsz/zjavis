"""Repository discovery for engineering intelligence.

Discovers repository structure, languages, frameworks, dependencies,
and CI/CD configuration. All operations are read-only and governed
by the policy engine.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jarvis.core.exceptions import ValidationError
from jarvis.core.logging import get_logger
from jarvis.core.security import validate_safe_path
from jarvis.engineering import register_capability

logger = get_logger(__name__)

# Common dependency file names for discovery.
DEPENDENCY_FILES: frozenset[str] = frozenset(
    {
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "poetry.lock",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        "composer.json",
    }
)

# Common CI/CD configuration file names.
CI_CD_FILES: frozenset[str] = frozenset(
    {
        ".github/workflows/",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        ".circleci/config.yml",
        "azure-pipelines.yml",
    }
)


@dataclass
class RepoInfo:
    """Discovered repository metadata."""

    root_path: str
    name: str
    languages: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)
    ci_cd_files: list[str] = field(default_factory=list)
    has_dockerfile: bool = False
    has_docker_compose: bool = False
    has_makefile: bool = False
    has_readme: bool = False
    has_license: bool = False
    has_agents_md: bool = False
    has_security_md: bool = False
    has_contributing_md: bool = False
    test_directories: list[str] = field(default_factory=list)
    src_directories: list[str] = field(default_factory=list)
    total_python_files: int = 0
    total_test_files: int = 0


class RepositoryDiscovery:
    """Discovers repository structure and metadata.

    Scans the repository root (or a configured path) to identify
    languages, dependency files, CI/CD configuration, test directories,
    and source directories. All paths are validated to prevent
    directory escape.
    """

    def __init__(self, *, root_path: str | None = None) -> None:
        self.root_path = root_path or os.getcwd()
        try:
            validate_safe_path(self.root_path, ".")
        except ValidationError as exc:
            raise ValidationError(
                f"Invalid repository root: {exc.message}",
                code=exc.code,
                details=exc.details,
            ) from exc

    async def discover(self) -> RepoInfo:
        """Perform repository discovery and return metadata."""
        root = Path(self.root_path)
        if not root.is_dir():
            raise ValidationError(
                f"Repository root is not a directory: {self.root_path}",
                code="invalid_repository_root",
                details={"root_path": self.root_path},
            )

        info = RepoInfo(root_path=str(root.resolve()), name=root.name)

        # Detect languages from file extensions
        extensions: dict[str, int] = {}
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            parts = file_path.relative_to(root).parts
            if ".git" in parts or "__pycache__" in parts or "node_modules" in parts:
                continue
            suffix = file_path.suffix.lower()
            if suffix:
                extensions[suffix] = extensions.get(suffix, 0) + 1

        # Map extensions to languages
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".sh": "Shell",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".json": "JSON",
            ".toml": "TOML",
            ".md": "Markdown",
            ".dockerfile": "Dockerfile",
        }
        for ext, count in sorted(extensions.items(), key=lambda x: -x[1]):
            lang = lang_map.get(ext, ext.lstrip(".").upper())
            if lang not in info.languages:
                info.languages.append(lang)

        # Detect dependency files
        for dep_file in DEPENDENCY_FILES:
            if (root / dep_file).is_file():
                info.dependency_files.append(dep_file)

        # Detect CI/CD files
        for ci_file in CI_CD_FILES:
            ci_path = root / ci_file
            if ci_path.is_file() or ci_path.is_dir():
                info.ci_cd_files.append(ci_file)

        # Detect standard files
        info.has_dockerfile = (root / "Dockerfile").is_file()
        info.has_docker_compose = (root / "docker-compose.yml").is_file() or (
            root / "docker-compose.yaml"
        ).is_file()
        info.has_makefile = (root / "Makefile").is_file()
        info.has_readme = (root / "README.md").is_file()
        info.has_license = (root / "LICENSE").is_file() or (
            root / "LICENSE.txt"
        ).is_file()
        info.has_agents_md = (root / "AGENTS.md").is_file()
        info.has_security_md = (root / "SECURITY.md").is_file()
        info.has_contributing_md = (root / "CONTRIBUTING.md").is_file()

        # Detect test and source directories
        for subdir in root.iterdir():
            if not subdir.is_dir():
                continue
            name = subdir.name
            if name in (".git", "__pycache__", "node_modules", ".venv", "venv", "env"):
                continue
            if name == "tests" or name == "test":
                info.test_directories.append(name)
            elif name == "src":
                info.src_directories.append(name)

        # Count Python files
        info.total_python_files = len(
            [
                f
                for f in root.rglob("*.py")
                if f.is_file()
                and ".git" not in f.relative_to(root).parts
                and "__pycache__" not in f.relative_to(root).parts
            ]
        )
        info.total_test_files = len(
            [
                f
                for f in root.rglob("test_*.py")
                if f.is_file()
                and ".git" not in f.relative_to(root).parts
                and "__pycache__" not in f.relative_to(root).parts
            ]
        )
        info.total_test_files += len(
            [
                f
                for f in root.rglob("*_test.py")
                if f.is_file()
                and ".git" not in f.relative_to(root).parts
                and "__pycache__" not in f.relative_to(root).parts
            ]
        )

        logger.info(
            "Repository discovery complete",
            extra={
                "root": self.root_path,
                "languages": info.languages,
                "python_files": info.total_python_files,
                "test_files": info.total_test_files,
            },
        )
        return info

    def to_dict(self, info: RepoInfo) -> dict[str, Any]:
        """Serialize RepoInfo to a dict (no secrets)."""
        return {
            "root_path": info.root_path,
            "name": info.name,
            "languages": info.languages,
            "dependency_files": info.dependency_files,
            "ci_cd_files": info.ci_cd_files,
            "has_dockerfile": info.has_dockerfile,
            "has_docker_compose": info.has_docker_compose,
            "has_makefile": info.has_makefile,
            "has_readme": info.has_readme,
            "has_license": info.has_license,
            "has_agents_md": info.has_agents_md,
            "has_security_md": info.has_security_md,
            "has_contributing_md": info.has_contributing_md,
            "test_directories": info.test_directories,
            "src_directories": info.src_directories,
            "total_python_files": info.total_python_files,
            "total_test_files": info.total_test_files,
        }


discovery = RepositoryDiscovery()
register_capability("repository_discovery", discovery)

__all__ = [
    "CI_CD_FILES",
    "DEPENDENCY_FILES",
    "RepoInfo",
    "RepositoryDiscovery",
    "discovery",
]
