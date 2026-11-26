"""JARVIS application entry point.

Run with: ``python -m jarvis`` or ``uvicorn jarvis.api.main:create_app --factory``
"""

from __future__ import annotations

import uvicorn

from jarvis.api.main import create_app
from jarvis.core.config import settings
from jarvis.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def main() -> None:
    """Run the JARVIS API server."""
    setup_logging(log_level=settings.log_level)
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
