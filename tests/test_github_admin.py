"""Tests for independent-review administration prerequisites."""

import unittest
from unittest.mock import patch

from scripts.github_admin import (
    REQUIRED_CHECKS,
    VALID_PERMISSIONS,
    add_collaborators,
    configured_independent_reviewer,
    protection_payload,
    validate_github_login,
    validate_independent_reviewer,
    verify_collaborators,
)


class IndependentReviewerAdminTests(unittest.TestCase):
    def test_independent_approval_is_a_required_status_check(self):
        self.assertIn("verify-independent-approval", REQUIRED_CHECKS)
        payload = protection_payload()
        self.assertIn(
            "verify-independent-approval", payload["required_status_checks"]["contexts"]
        )
        self.assertTrue(payload["required_status_checks"]["strict"])

    def test_review_policy_keeps_review_and_codeowner_requirements(self):
        reviews = protection_payload()["required_pull_request_reviews"]
        self.assertGreaterEqual(reviews["required_approving_review_count"], 1)
        self.assertTrue(reviews["require_code_owner_reviews"])
        self.assertTrue(reviews["dismiss_stale_reviews"])
        self.assertTrue(reviews["require_last_push_approval"])

    def test_reviewer_must_be_a_valid_login_distinct_from_owner(self):
        self.assertEqual(
            validate_independent_reviewer("cvsz/ztemplate", "policedbc"), "policedbc"
        )
        for reviewer in ("", "invalid/login", "cvsz", "bad name"):
            with self.subTest(reviewer=reviewer), self.assertRaises(ValueError):
                validate_independent_reviewer("cvsz/ztemplate", reviewer)

    @patch("scripts.github_admin.gh_api")
    def test_configured_reviewer_reads_repository_variable(self, gh_api):
        gh_api.return_value = {
            "variables": [
                {"name": "OTHER_VARIABLE", "value": "unused"},
                {"name": "INDEPENDENT_REVIEWER", "value": "policedbc"},
            ]
        }
        self.assertEqual(configured_independent_reviewer("cvsz/ztemplate"), "policedbc")
        gh_api.assert_called_once_with(
            "GET", "repos/cvsz/ztemplate/actions/variables?per_page=100"
        )

    @patch("scripts.github_admin.gh_api")
    def test_missing_reviewer_variable_is_not_assumed(self, gh_api):
        gh_api.return_value = {"variables": []}
        self.assertIsNone(configured_independent_reviewer("cvsz/ztemplate"))


class GitHubLoginValidationTests(unittest.TestCase):
    def test_valid_logins(self):
        for login in (
            "user1",
            "user-2",
            "a",
            "org-name",
            "maintainer-bot",
            "policedbc",
        ):
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
            "user.name",
        ):
            with self.subTest(login=login), self.assertRaises(ValueError):
                validate_github_login(login)


class AddCollaboratorsTests(unittest.TestCase):
    @patch("scripts.github_admin.gh_api")
    def test_adds_each_collaborator_with_permission(self, gh_api):
        add_collaborators(
            "cvsz/ztemplate", ["user1", "user2", "user3"], permission="pull"
        )
        self.assertEqual(gh_api.call_count, 3)
        calls = gh_api.call_args_list
        self.assertEqual(
            calls[0][0],
            ("PUT", "repos/cvsz/ztemplate/collaborators/user1", {"permission": "pull"}),
        )
        self.assertEqual(
            calls[1][0],
            ("PUT", "repos/cvsz/ztemplate/collaborators/user2", {"permission": "pull"}),
        )
        self.assertEqual(
            calls[2][0],
            ("PUT", "repos/cvsz/ztemplate/collaborators/user3", {"permission": "pull"}),
        )

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
