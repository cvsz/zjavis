"""Vision interface: image understanding provider abstraction.

Per JARVIS blueprint, vision capabilities are gated behind the
``vision_enabled`` configuration flag. Providers follow the same adapter
pattern as the model gateway. No credentials are embedded; provider API
keys come from configuration.

Security controls:
- Image size and content-type validation before processing
- Base64 image input is decoded and bounded to prevent abuse
- Provider API keys are never logged or embedded
- Vision is disabled by default (secure-by-default)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from jarvis.core.config import settings
from jarvis.core.exceptions import ProviderError, ValidationError
from jarvis.core.logging import get_logger
from jarvis.core.metrics import record_vision_request
from jarvis.core.security import redact_secret

logger = get_logger(__name__)

# Maximum image size enforced as a defense-in-depth cap (10 MB).
MAX_IMAGE_BYTES = settings.vision_max_image_bytes

# Allowed image content types detected from magic bytes.
_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

# Magic-byte signatures for common image formats.
_IMAGE_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),  # WEBP starts with RIFF....WEBP
]


def detect_image_content_type(image_bytes: bytes) -> str | None:
    """Detect the content type of image bytes from magic bytes.

    Args:
        image_bytes: Raw image data.

    Returns:
        The detected content type string, or None if unrecognized.
    """
    for signature, content_type in _IMAGE_SIGNATURES:
        if image_bytes.startswith(signature):
            if content_type == "image/webp":
                # WEBP requires the "WEBP" chunk at offset 8.
                if len(image_bytes) >= 12 and image_bytes[8:12] == b"WEBP":
                    return "image/webp"
                continue
            return content_type
    return None


def validate_image(image_bytes: bytes) -> str:
    """Validate an image payload and return its content type.

    Enforces size limits and allowed content types. Raises
    :class:`ValidationError` for unsafe or unsupported images.

    Args:
        image_bytes: Raw image data.

    Returns:
        The detected content type string.

    Raises:
        ValidationError: If the image is too large, empty, or has an
            unsupported/invalid format.
    """
    if not image_bytes:
        raise ValidationError(
            "Image data is empty",
            code="image_empty",
            details={},
        )
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValidationError(
            f"Image exceeds maximum size of {MAX_IMAGE_BYTES} bytes "
            f"({len(image_bytes)} bytes provided)",
            code="image_too_large",
            details={
                "max_bytes": MAX_IMAGE_BYTES,
                "provided_bytes": len(image_bytes),
            },
        )
    content_type = detect_image_content_type(image_bytes)
    if content_type is None:
        raise ValidationError(
            "Unsupported or unrecognized image format",
            code="image_unsupported_format",
            details={},
        )
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Image content type not allowed: {content_type}",
            code="image_content_type_not_allowed",
            details={"content_type": content_type},
        )
    return content_type


class VisionProvider(ABC):
    """Abstract base class for vision providers."""

    device: str

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

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

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
            "device": self.device,
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
            "device": self.device,
            "error": "local vision not implemented",
        }


class NVIDIANimVisionProvider(VisionProvider):
    """NVIDIA NIM vision-language model provider.

    Uses the NVIDIA NIM OpenAI-compatible ``/v1/chat/completions`` endpoint
    with multimodal image input (base64 data URLs) for image understanding.
    Authentication is Bearer-token based via the API key. No credentials
    are embedded; the API key comes from configuration.
    """

    def __init__(
        self,
        *,
        credential: str | None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._credential = credential
        self.base_url = base_url or "https://integrate.api.nvidia.com/v1"
        self.model = model or "nvidia/nemotron-3-ultra-550b-a55b"
        self._api_key_redacted = redact_secret(credential)
        self.device = "nvidia-nim"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._credential}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _image_url(self, image_bytes: bytes, content_type: str) -> str:
        """Build a base64 data URL for the image payload."""
        import base64

        b64 = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{content_type};base64,{b64}"

    async def _chat_completion(
        self, *, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not self._credential:
            raise ProviderError("NVIDIA NIM API key not configured")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "NVIDIA NIM vision error",
                extra={
                    "provider": "nvidia-nim",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"NVIDIA NIM vision error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "NVIDIA NIM vision connection error",
                extra={"provider": "nvidia-nim", "error": str(exc)},
            )
            raise ProviderError(f"NVIDIA NIM vision connection error: {exc}") from exc
        return data

    async def describe_image(
        self,
        *,
        image_bytes: bytes,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Describe an image via NVIDIA NIM vision-language model."""
        content_type = validate_image(image_bytes)
        image_url = self._image_url(image_bytes, content_type)
        text = prompt or "Describe this image in detail."
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        data = await self._chat_completion(messages=messages)
        description = ""
        try:
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            description = message.get("content", "")
        except (AttributeError, IndexError, TypeError):
            description = ""
        return {
            "description": description,
            "confidence": 0.0,
            "provider": "nvidia-nim",
            "device": self.device,
            "model": self.model,
        }

    async def analyze_image(
        self,
        *,
        image_bytes: bytes,
        questions: list[str],
    ) -> dict[str, Any]:
        """Answer questions about an image via NVIDIA NIM vision model."""
        content_type = validate_image(image_bytes)
        image_url = self._image_url(image_bytes, content_type)
        joined = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
        text = (
            "Answer the following questions about the image. "
            "Return each answer on its own line.\n" + joined
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        data = await self._chat_completion(messages=messages)
        answers: dict[str, str] = {}
        try:
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            for i, q in enumerate(questions):
                answers[q] = lines[i] if i < len(lines) else ""
        except (AttributeError, IndexError, TypeError):
            for q in questions:
                answers[q] = ""
        return {
            "answers": answers,
            "provider": "nvidia-nim",
            "device": self.device,
            "model": self.model,
        }


def _build_provider(
    *,
    provider: str,
    api_key: str | None,
    api_url: str | None,
    model: str | None,
) -> VisionProvider:
    """Select and build the vision provider from configuration."""
    # ``nvidia`` is accepted as an alias for ``nvidia-nim``.
    provider_name = "nvidia-nim" if provider == "nvidia" else provider
    if provider_name == "nvidia-nim":
        return NVIDIANimVisionProvider(
            credential=api_key, base_url=api_url, model=model
        )
    if provider_name == "local":
        return LocalVisionProvider(device=settings.vision_gpu_device)
    logger.warning("Unknown vision provider '%s', falling back to local stub", provider)
    return LocalVisionProvider(device=settings.vision_gpu_device)


class VisionService:
    """High-level vision service that delegates to a provider.

    Raises :class:`RuntimeError` if vision is not enabled in configuration.
    """

    def __init__(
        self,
        *,
        provider: VisionProvider | None = None,
        enabled: bool = False,
        device: str = "cpu",
    ) -> None:
        self.provider = provider or LocalVisionProvider(device=device)
        self.enabled = enabled
        self.device = self.provider.device

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
        validate_image(image_bytes)
        start = time.time()
        outcome = "success"
        try:
            result = await self.provider.describe_image(
                image_bytes=image_bytes, prompt=prompt
            )
            return result
        except Exception:
            outcome = "error"
            raise
        finally:
            duration = time.time() - start
            record_vision_request(
                operation="describe",
                provider=getattr(self.provider, "device", "unknown"),
                outcome=outcome,
                duration=duration,
                image_bytes=len(image_bytes),
            )

    async def analyze_image(
        self,
        *,
        image_bytes: bytes,
        questions: list[str],
    ) -> dict[str, Any]:
        self._require_enabled()
        validate_image(image_bytes)
        start = time.time()
        outcome = "success"
        try:
            result = await self.provider.analyze_image(
                image_bytes=image_bytes, questions=questions
            )
            return result
        except Exception:
            outcome = "error"
            raise
        finally:
            duration = time.time() - start
            record_vision_request(
                operation="analyze",
                provider=getattr(self.provider, "device", "unknown"),
                outcome=outcome,
                duration=duration,
                image_bytes=len(image_bytes),
            )


vision = VisionService(
    provider=_build_provider(
        provider=settings.vision_provider,
        api_key=settings.vision_api_key,
        api_url=settings.vision_api_url,
        model=settings.vision_model,
    ),
    enabled=settings.vision_enabled,
    device=settings.vision_gpu_device,
)
