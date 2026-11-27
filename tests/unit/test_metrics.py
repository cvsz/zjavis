"""Unit tests for the JARVIS metrics module."""

from __future__ import annotations

from jarvis.core.metrics import (
    get_metrics,
    record_agent_concurrent,
    record_agent_execution,
    record_approval,
    record_authn_failure,
    record_authz_denial,
    record_model_request,
    record_request,
    record_tool_execution,
)


class TestRecordRequest:
    """Tests for request metrics."""

    def test_record_request(self) -> None:
        record_request("GET", "/health", 200, 0.05)
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_requests_total" in metrics
        assert "jarvis_request_duration_seconds" in metrics


class TestRecordModelRequest:
    """Tests for model gateway metrics."""

    def test_record_model_request(self) -> None:
        record_model_request("local", "local-model", "chat", 0.1, 10, 20)
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_model_requests_total" in metrics
        assert "jarvis_model_tokens_total" in metrics


class TestRecordAgentExecution:
    """Tests for agent execution metrics."""

    def test_record_agent_execution(self) -> None:
        record_agent_execution("test-agent", "completed", 1.5)
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_agent_executions_total" in metrics

    def test_record_agent_concurrent(self) -> None:
        record_agent_concurrent(1)
        record_agent_concurrent(-1)
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_agent_concurrent_executions" in metrics


class TestRecordToolExecution:
    """Tests for tool execution metrics."""

    def test_record_tool_execution(self) -> None:
        record_tool_execution("test-tool", "success", 0.5)
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_tool_executions_total" in metrics


class TestRecordMemoryItem:
    """Tests for memory item metrics."""

    def test_record_memory_item(self) -> None:
        from jarvis.core.metrics import record_memory_item

        record_memory_item("conversation", 1)
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_memory_items_total" in metrics


class TestRecordApproval:
    """Tests for approval metrics."""

    def test_record_approval(self) -> None:
        record_approval("granted")
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_approvals_total" in metrics


class TestSecurityMetrics:
    """Tests for security metrics."""

    def test_record_authz_denial(self) -> None:
        record_authz_denial("database.mutate", "user-1")
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_authz_denials_total" in metrics

    def test_record_authn_failure(self) -> None:
        record_authn_failure()
        metrics = get_metrics().decode("utf-8")
        assert "jarvis_authn_failures_total" in metrics