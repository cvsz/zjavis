"""Tests for collaborator management in github_admin."""

import unittest
from unittest.mock import patch

from scripts.github_admin import (
    VALID_PERMISSIONS,
    add_collaborators,
    validate_github_login,
    verify_collaborators,
)


class CollaboratorLoginValidationTests(unittest.TestCase):
    def test_valid_logins(self):
        for login in ("user1", "user-2", "a", "org-name", "maintainer-bot"):
            with self.subTest(login=login):
                self.assertEqual(validate_github_login(login), login)

    def test_invalid_logins(self):
        for login in (
            "",
            "invalid/login",
            "bad name",
            "-leading",
            "trailing-",
            "a" * 40,
        ):
            with self.subTest(login=login), self.assertRaises(ValueError):
                validate_github_login(login)


class AddCollaboratorsTests(unittest.TestCase):
    @patch("scripts.github_admin.gh_api")
    def test_adds_each_collaborator_with_permission(self, gh_api):
        add_collaborators(
            "cvsz/ztemplate", ["user1", "user2", "user3"], permission="pull"
        )
        expected_calls: list[
            tuple[tuple[str, str, dict[str, str]], dict[str, object]]
        ] = [
            (
                (
                    "PUT",
                    "repos/cvsz/ztemplate/collaborators/user1",
                    {"permission": "pull"},
                ),
                {},
            ),
            (
                (
                    "PUT",
                    "repos/cvsz/ztemplate/collaborators/user2",
                    {"permission": "pull"},
                ),
                {},
            ),
            (
                (
                    "PUT",
                    "repos/cvsz/ztemplate/collaborators/user3",
                    {"permission": "pull"},
                ),
                {},
            ),
        ]
        self.assertEqual(gh_api.call_count, 3)
        for i, (args, kwargs) in enumerate(expected_calls):
            self.assertEqual(gh_api.call_args_list[i], (args, kwargs))

    @patch("scripts.github_admin.gh_api")
    def test_rejects_invalid_permission(self, gh_api):
        with self.assertRaises(ValueError):
            add_collaborators("cvsz/ztemplate", ["user1"], permission="invalid")
        gh_api.assert_not_called()

    @patch("scripts.github_admin.gh_api")
    def test_rejects_invalid_login(self, gh_api):
        with self.assertRaises(ValueError):
            add_collaborators("cvsz/ztemplate", ["bad/login"], permission="pull")
        gh_api.assert_not_called()

    @patch("scripts.github_admin.gh_api")
    def test_supports_all_valid_permissions(self, gh_api):
        for permission in sorted(VALID_PERMISSIONS):
            with self.subTest(permission=permission):
                add_collaborators("cvsz/ztemplate", ["user1"], permission=permission)
                args, _ = gh_api.call_args
                self.assertEqual(args[1], "repos/cvsz/ztemplate/collaborators/user1")
                self.assertEqual(args[2]["permission"], permission)


class VerifyCollaboratorsTests(unittest.TestCase):
    @patch("scripts.github_admin.gh_api")
    def test_verifies_correct_permissions(self, gh_api):
        gh_api.side_effect = [
            {"permission": "pull"},
            {"permission": "pull"},
            {"permission": "triage"},
        ]
        errors = verify_collaborators(
            "cvsz/ztemplate", ["user1", "user2", "user3"], "pull"
        )
        self.assertEqual(errors, ["user3: expected permission 'pull', got 'triage'"])

    @patch("scripts.github_admin.gh_api")
    def test_handles_missing_collaborator(self, gh_api):
        gh_api.side_effect = RuntimeError("Not Found")
        errors = verify_collaborators("cvsz/ztemplate", ["ghost"], "pull")
        self.assertEqual(len(errors), 1)
        self.assertIn("ghost", errors[0])

    @patch("scripts.github_admin.gh_api")
    def test_handles_no_permission_data(self, gh_api):
        gh_api.return_value = None
        errors = verify_collaborators("cvsz/ztemplate", ["user1"], "pull")
        self.assertEqual(len(errors), 1)
        self.assertIn("user1", errors[0])


if __name__ == "__main__":
    unittest.main()
