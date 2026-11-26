"""Vision interface: image understanding provider abstraction.

Per JARVIS blueprint, vision capabilities are gated behind the
``vision_enabled`` configuration flag. Providers follow the same adapter
pattern as the model gateway. No credentials are embedded; provider API
keys come from configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.config import settings


class VisionProvider(ABC):
    """Abstract base class for vision providers."""

    @abstractmethod
    async def describe_image(
        self,
        *,
        image_bytes: bytes,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Describe or analyze an image.

        Args:
            image_bytes: Raw image data.
            prompt: Optional analysis prompt.

        Returns:
            Dict with ``description`` and optional ``confidence`` keys.
        """

    @abstractmethod
    async def analyze_image(
        self,
        *,
        image_bytes: bytes,
        questions: list[str],
    ) -> dict[str, Any]:
        """Answer questions about an image.

        Args:
            image_bytes: Raw image data.
            questions: List of questions to answer about the image.

        Returns:
            Dict mapping each question to its answer.
        """


class LocalVisionProvider(VisionProvider):
    """Local vision provider — placeholder implementation.

    Returns a stub result indicating vision processing is not available
    locally. This keeps the system functional without GPU hardware
    or external credentials while the ``vision_enabled`` flag is false.
    """

    async def describe_image(
        self,
        *,
        image_bytes: bytes,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        return {
            "description": "",
            "confidence": 0.0,
            "provider": "local",
            "error": "local vision not implemented",
        }

    async def analyze_image(
        self,
        *,
        image_bytes: bytes,
        questions: list[str],
    ) -> dict[str, Any]:
        return {
            "answers": {q: "" for q in questions},
            "provider": "local",
            "error": "local vision not implemented",
        }


class VisionService:
    """High-level vision service that delegates to a provider.

    Raises :class:`RuntimeError` if vision is not enabled in configuration.
    """

    def __init__(
        self,
        *,
        provider: VisionProvider | None = None,
        enabled: bool = False,
    ) -> None:
        self.provider = provider or LocalVisionProvider()
        self.enabled = enabled

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError(
                "Vision interface is disabled. Set JARVIS_VISION_ENABLED=true to enable."
            )

    async def describe_image(
        self,
        *,
        image_bytes: bytes,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        self._require_enabled()
        return await self.provider.describe_image(
            image_bytes=image_bytes, prompt=prompt
        )

    async def analyze_image(
        self,
        *,
        image_bytes: bytes,
        questions: list[str],
    ) -> dict[str, Any]:
        self._require_enabled()
        return await self.provider.analyze_image(
            image_bytes=image_bytes, questions=questions
        )


vision = VisionService(
    provider=LocalVisionProvider(),
    enabled=settings.vision_enabled,
)
