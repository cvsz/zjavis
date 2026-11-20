"""Tests for enhanced validate_repo.py functions."""

import tempfile
import unittest
from pathlib import Path

from scripts.validate_repo import (
    SECRET_CONTENT_RE,
    SECRET_FILENAME_RE,
    normalize_link_target,
    validate_python_syntax,
    validate_shell_syntax,
    validate_yaml_syntax,
)


class SecretFilenameTests(unittest.TestCase):
    def test_matches_secret_files(self):
        for name in (
            ".env",
            "id_rsa",
            "id_ed25519",
            "cert.pem",
            "private.key",
            "secrets/id_rsa",
            "config/.env",
        ):
            with self.subTest(name=name):
                self.assertIsNotNone(SECRET_FILENAME_RE.search(name))

    def test_allows_env_example(self):
        self.assertIsNone(SECRET_FILENAME_RE.search(".env.example"))


class SecretContentTests(unittest.TestCase):
    def test_detects_hardcoded_secrets(self):
        self.assertIsNotNone(SECRET_CONTENT_RE.search("API_KEY = 'sk-1234567890'"))
        self.assertIsNotNone(SECRET_CONTENT_RE.search("password='secret123'"))
        self.assertIsNotNone(SECRET_CONTENT_RE.search("access_token = 'ghp_xxxxxx'"))
        self.assertIsNotNone(
            SECRET_CONTENT_RE.search("api_key = 'AKIAIOSFODNN7EXAMPLE'")
        )

    def test_allows_placeholders(self):
        self.assertIsNone(SECRET_CONTENT_RE.search("# Never commit real credentials"))
        self.assertIsNone(
            SECRET_CONTENT_RE.search(
                "DATABASE_URL=postgresql://<db_user>:<db_password>@host/db"
            )
        )
        self.assertIsNone(
            SECRET_CONTENT_RE.search(
                "REPONAME_POSTGRES_PASSWORD_FILE=/run/secrets/<project>_postgres_password"
            )
        )
        self.assertIsNone(SECRET_CONTENT_RE.search("https://example.com/api"))


class NormalizeLinkTargetTests(unittest.TestCase):
    def test_strips_fragment_and_query(self):
        self.assertEqual(normalize_link_target("page.md#section"), "page.md")
        self.assertEqual(normalize_link_target("page.md?v=1"), "page.md")
        self.assertEqual(normalize_link_target("<page.md>"), "page.md")

    def test_returns_empty_for_fragment_only(self):
        self.assertEqual(normalize_link_target("#section"), "")


class PythonSyntaxTests(unittest.TestCase):
    def test_valid_python_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "valid.py").write_text("x = 1\n", encoding="utf-8")
            # Temporarily patch ROOT by calling with a monkeypatched module
            import scripts.validate_repo as vr

            old_root = vr.ROOT
            vr.ROOT = root
            try:
                errors = validate_python_syntax()
                self.assertEqual(errors, [])
            finally:
                vr.ROOT = old_root

    def test_invalid_python_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "broken.py").write_text("x =\n", encoding="utf-8")
            import scripts.validate_repo as vr

            old_root = vr.ROOT
            vr.ROOT = root
            try:
                errors = validate_python_syntax()
                self.assertGreater(len(errors), 0)
            finally:
                vr.ROOT = old_root


class ShellSyntaxTests(unittest.TestCase):
    def test_valid_shell_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "valid.sh").write_text(
                "#!/usr/bin/env bash\necho hello\n", encoding="utf-8"
            )
            import scripts.validate_repo as vr

            old_root = vr.ROOT
            vr.ROOT = root
            try:
                errors = validate_shell_syntax()
                self.assertEqual(errors, [])
            finally:
                vr.ROOT = old_root

    def test_invalid_shell_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "broken.sh").write_text("if true; then\n", encoding="utf-8")
            import scripts.validate_repo as vr

            old_root = vr.ROOT
            vr.ROOT = root
            try:
                errors = validate_shell_syntax()
                self.assertGreater(len(errors), 0)
            finally:
                vr.ROOT = old_root


class YAMLSyntaxTests(unittest.TestCase):
    def test_valid_yaml_passes(self):
        try:
            import yaml  # type: ignore  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            github_dir = root / ".github"
            github_dir.mkdir()
            (github_dir / "valid.yml").write_text(
                "key: value\nlist:\n  - item1\n", encoding="utf-8"
            )
            import scripts.validate_repo as vr

            old_root = vr.ROOT
            vr.ROOT = root
            try:
                errors = validate_yaml_syntax()
                self.assertEqual(errors, [])
            finally:
                vr.ROOT = old_root

    def test_invalid_yaml_fails(self):
        try:
            import yaml  # type: ignore  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            github_dir = root / ".github"
            github_dir.mkdir()
            (github_dir / "broken.yml").write_text("key: [unclosed\n", encoding="utf-8")
            import scripts.validate_repo as vr

            old_root = vr.ROOT
            vr.ROOT = root
            try:
                errors = validate_yaml_syntax()
                self.assertGreater(len(errors), 0)
            finally:
                vr.ROOT = old_root


if __name__ == "__main__":
    unittest.main()
