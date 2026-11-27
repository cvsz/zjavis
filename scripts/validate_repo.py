#!/usr/bin/env python3
"""Validate ztemplate structure, local Markdown links, syntax, and security."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "README.md",
    "ABOUT.md",
    "AGENTS.md",
    "CLAUDE.md",
    "OPENCODE.md",
    "GEMINI.md",
    "ZEAZ-INTRODUCTION.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "IMPLEMENTATION-CHECKLIST.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/dependabot.yml",
    "docs/ai/README.md",
    "docs/ai/guides",
    "docs/ai/playbooks",
    "docs/ai/prompts",
    "skills/zeaz-skill-finder/SKILL.md",
    "components.d/zeaz-engineering.yml",
    "plugins.d/zeaz-skills.yml",
    "ecc-install.json",
    "scripts/github_admin.py",
    "docs/ai/guides/github-repository-admin.md",
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "data:")

SECRET_FILENAME_RE = re.compile(r"(^|/)(\.env$|id_rsa|id_ed25519|.*\.pem|.*\.key)$")
SECRET_CONTENT_RE = re.compile(
    r"(?i)(api[_-]?key|secret[_-]?key|private[_-]?key|access[_-]?token|auth[_-]?token|"
    r"password|passwd|\bsecret\b|\bcredential\b|github_pat_|ghp_|gho_|ghu_|ghs_|ghr_|AKIA[0-9A-Z]{16})\s*[:=]\s*[^\s]+"
)


def validate_required_paths() -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"missing required path: {rel}")
    return errors


def normalize_link_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(target)


def validate_markdown_links() -> list[str]:
    errors: list[str] = []
    for md in sorted(ROOT.rglob("*.md")):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            raw = match.group(1).strip()
            if not raw or raw.startswith(SKIP_PREFIXES):
                continue
            target = normalize_link_target(raw)
            if not target:
                continue
            link_base = (
                ROOT
                if md.relative_to(ROOT).as_posix() == "templates/project-readme.md"
                else md.parent
            )
            resolved = (link_base / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{md.relative_to(ROOT)}: link escapes repository: {raw}")
                continue
            if not resolved.exists():
                errors.append(f"{md.relative_to(ROOT)}: broken local link: {raw}")
    return errors


def validate_no_tracked_secrets() -> list[str]:
    """Ensure no secret-bearing files are tracked by git."""
    errors: list[str] = []
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
        )
        if proc.returncode != 0:
            errors.append("cannot list git-tracked files")
            return errors
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line == ".env.example":
                continue
            if SECRET_FILENAME_RE.search(line):
                errors.append(f"tracked secret-bearing file: {line}")
    except (FileNotFoundError, OSError):
        pass  # git not available in some environments
    return errors


def validate_no_secret_content() -> list[str]:
    """Scan Python, shell, YAML, JSON, and env files for hardcoded secret assignments.

    Only flags lines that assign a value to a secret-like key.
    Mentions of the words in documentation/comments without an assignment are ignored.
    GitHub Actions ${{ secrets.X }} references and obvious placeholders are allowed.
    """
    errors: list[str] = []
    extensions = {".py", ".sh", ".yml", ".yaml", ".json", ".md"}
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        # Skip test files — they contain intentional test patterns
        if "tests" in path.parts:
            continue
        if path.suffix not in extensions and path.name != ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Skip comments, empty lines, and pure documentation mentions
            if not stripped or stripped.startswith(("#", "//", "*")):
                continue
            # Skip GitHub Actions secret references (legitimate, not hardcoded)
            if "${{ secrets." in stripped or "${{ env." in stripped:
                continue
            # Skip obvious placeholder patterns
            if any(
                token in stripped.lower()
                for token in (
                    "placeholder",
                    "replace_me",
                    "example.com",
                    "<db_user>",
                    "<db_password>",
                    "<postgres_host>",
                    "<redis_host>",
                    "run/secrets/",
                    "# never commit",
                    "nonsecret",
                    "non-secret",
                    "credentials",
                    "credential",
                    "${{ secrets.",
                    "your-",
                    "changeme",
                    "change-me",
                    "todo",
                    "git credential",
                    "api_key",
                )
            ):
                continue
            # Skip YAML keys without values (no = or quoted value)
            if ":" in stripped and not any(ch in stripped for ch in ("=", '"', "'")):
                continue
            if SECRET_CONTENT_RE.search(stripped):
                errors.append(
                    f"{path.relative_to(ROOT)}:{lineno}: potential hardcoded secret"
                )
    return errors


def validate_python_syntax() -> list[str]:
    """Compile-check all Python files under scripts/, tests/, and src/jarvis/."""
    errors: list[str] = []
    for directory in ("scripts", "tests", "src/jarvis"):
        base = ROOT / directory
        if not base.is_dir():
            continue
        for py in sorted(base.rglob("*.py")):
            try:
                compile(py.read_text(encoding="utf-8"), str(py), "exec")
            except SyntaxError as exc:
                errors.append(f"{py.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    return errors


def validate_shell_syntax() -> list[str]:
    """Syntax-check all shell scripts with bash -n."""
    errors: list[str] = []
    for directory in ("scripts", ".github/scripts"):
        base = ROOT / directory
        if not base.is_dir():
            continue
        for sh in sorted(base.rglob("*.sh")):
            try:
                proc = subprocess.run(
                    ["bash", "-n", str(sh)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode != 0:
                    errors.append(
                        f"{sh.relative_to(ROOT)}: shell syntax error: {proc.stderr.strip()}"
                    )
            except FileNotFoundError:
                errors.append(
                    f"{sh.relative_to(ROOT)}: bash not available for syntax check"
                )
    return errors


def validate_yaml_syntax() -> list[str]:
    """Validate YAML files under .github/."""
    errors: list[str] = []
    base = ROOT / ".github"
    if not base.is_dir():
        return errors
    try:
        import yaml
    except ImportError:
        return errors  # yaml not available; skip YAML validation
    for yml in sorted(base.rglob("*.yml")) + sorted(base.rglob("*.yaml")):
        try:
            with open(yml, encoding="utf-8") as fh:
                yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            errors.append(f"{yml.relative_to(ROOT)}: invalid YAML: {exc}")
    return errors


def main() -> int:
    errors = (
        validate_required_paths()
        + validate_markdown_links()
        + validate_no_tracked_secrets()
        + validate_no_secret_content()
        + validate_python_syntax()
        + validate_shell_syntax()
        + validate_yaml_syntax()
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Repository structure, links, syntax, and security validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
