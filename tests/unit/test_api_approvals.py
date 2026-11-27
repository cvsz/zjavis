"""Unit tests for the JARVIS approvals API endpoints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jarvis.api.approvals import ApprovalRequest


class TestApprovalRequest:
    """Tests for ApprovalRequest model."""

    def test_approval_request_valid(self) -> None:
        import uuid

        req = ApprovalRequest(task_id=uuid.uuid4(), expires_in_minutes=60)
        assert req.expires_in_minutes == 60

    def test_approval_request_defaults(self) -> None:
        import uuid

        req = ApprovalRequest(task_id=uuid.uuid4())
        assert req.expires_in_minutes == 60

    def test_approval_request_expires_too_short(self) -> None:
        import uuid

        with pytest.raises(ValidationError):
            ApprovalRequest(task_id=uuid.uuid4(), expires_in_minutes=0)

    def test_approval_request_expires_too_long(self) -> None:
        import uuid

        with pytest.raises(ValidationError):
            ApprovalRequest(task_id=uuid.uuid4(), expires_in_minutes=10081)