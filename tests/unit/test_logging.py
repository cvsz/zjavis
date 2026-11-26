"""Unit tests for JARVIS logging module."""

from __future__ import annotations

import logging

from jarvis.core.logging import SecretFilter, get_logger, setup_logging


def test_setup_logging_configures_root() -> None:
    """setup_logging configures the root logger."""
    setup_logging(log_level="debug")
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_get_logger_returns_logger() -> None:
    """get_logger returns a logging.Logger instance."""
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_secret_filter_redacts() -> None:
    """SecretFilter redacts secret-like values from log records."""
    f = SecretFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="password=secret123",
        args=(),
        exc_info=None,
    )
    result = f.filter(record)
    assert result is True
    assert "[REDACTED]" in record.msg
    assert "secret123" not in record.msg
