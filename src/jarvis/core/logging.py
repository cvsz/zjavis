"""Structured application logging.

Logs are emitted as JSON where possible to support log aggregation.
Secrets, credentials, and private data must never be logged.
"""

from __future__ import annotations

import logging
import sys


class SecretFilter(logging.Filter):
    """Filter that redacts secret-like values from log records."""

    SECRET_KEYS = (
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "private_key",
        "session",
        "cookie",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(
                self._redact(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        record.msg = self._redact(str(record.msg))
        return True

    @staticmethod
    def _redact(value: str) -> str:
        lower = value.lower()
        if any(key in lower for key in SecretFilter.SECRET_KEYS):
            # Redact the entire value if it looks like a secret assignment
            if "=" in value or ":" in value:
                for key in SecretFilter.SECRET_KEYS:
                    if key in lower:
                        idx = lower.find(key)
                        if idx >= 0:
                            # Find the separator after the key
                            sep_idx = value.find("=", idx)
                            if sep_idx < 0:
                                sep_idx = value.find(":", idx)
                            if sep_idx >= 0:
                                return value[: sep_idx + 1] + " [REDACTED]"
            return "[REDACTED]"
        return value


def setup_logging(log_level: str = "info") -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level string (debug, info, warning, error, critical).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(SecretFilter())

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if called multiple times
    if not root.handlers:
        root.addHandler(handler)

    # Silence noisy third-party loggers
    for name in ("uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger`.
    """
    return logging.getLogger(name)
