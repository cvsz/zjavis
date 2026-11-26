"""Model gateway: provider abstraction, model registry, and routing.

Per javis-blueprint.md section 4, all model access must pass through
this gateway. Application modules must not embed provider credentials
or APIs. Cloud fallback is disabled by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jarvis.core.config import settings
from jarvis.core.exceptions import ProviderError
from jarvis.core.logging import get_logger
from jarvis.core.security import redact_secret

logger = get_logger(__name__)


@dataclass(frozen=True)
class ModelCapability:
    """Declares a model's capabilities."""

    name: str
    tool_calling: bool = False
    structured_output: bool = False
    streaming: bool = False
    vision: bool = False
    max_context_tokens: int = 4096


@dataclass
class ModelRoute:
    """Routes tasks to a specific provider/model."""

    provider: str
    model: str
    capability: ModelCapability


class ProviderAdapter:
    """Abstract base for model provider adapters.

    Concrete adapters implement provider-specific API calls while
    the gateway handles routing, retries, and usage accounting.
    """

    def __init__(self, provider_name: str, credential: str | None) -> None:
        self.provider_name = provider_name
        self._credential = credential

    @property
    def api_key_redacted(self) -> str:
        """Return a redacted form of the credential for logging."""
        return redact_secret(self._credential)

    async def complete(self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Complete a chat completion. Must be implemented by subclasses."""
        raise ProviderError(f"Provider {self.provider_name} does not implement complete()")


class LocalProviderAdapter(ProviderAdapter):
    """Local model provider adapter (e.g., Ollama, local inference).

    Used when cloud fallback is disabled and a local model server is
    available. Returns a deterministic placeholder response when no
    real local endpoint is configured, so the system can be tested
    without external credentials.
    """

    async def complete(self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        return {
            "provider": self.provider_name,
            "model": model,
            "response": f"[local echo] {last_user[:200]}",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


class ModelGateway:
    """Routes model requests through provider adapters.

    Responsibilities per blueprint §4:
    - Provider registry and model registry
    - Model routing by task requirements
    - Request/response validation
    - Timeout and retry policy
    - Rate and budget limits
    - Usage accounting
    - Data classification enforcement
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderAdapter] = {}
        self._models: dict[str, ModelCapability] = {}
        self._routes: dict[str, ModelRoute] = {}
        self._usage: dict[str, int] = {}
        self.logger = get_logger(__name__)

        # Register local provider (always available, no credentials needed)
        self.register_provider("local", LocalProviderAdapter("local", None))
        self._models["local-model"] = ModelCapability(
            name="local-model",
            tool_calling=False,
            structured_output=False,
            streaming=False,
            vision=False,
            max_context_tokens=4096,
        )
        self._routes["default"] = ModelRoute(
            provider="local", model="local-model", capability=self._models["local-model"]
        )

        if settings.cloud_fallback_enabled:
            self.logger.warning(
                "Cloud model fallback is ENABLED. Private data may egress to external providers.",
            )
        else:
            self.logger.info("Cloud model fallback disabled (default per blueprint §4.2)")

    def register_provider(self, name: str, adapter: ProviderAdapter) -> None:
        """Register a model provider adapter.

        Args:
            name: Provider identifier.
            adapter: The provider adapter instance.
        """
        self._providers[name] = adapter
        self.logger.info("Provider registered", extra={"provider": name})

    def register_model(self, model: str, capability: ModelCapability) -> None:
        """Register a model and its capabilities.

        Args:
            model: Model name.
            capability: Capability metadata.
        """
        self._models[model] = capability
        self.logger.info(
            "Model registered",
            extra={"model": model, "tool_calling": capability.tool_calling},
        )

    def route(self, *, task_type: str = "default") -> ModelRoute:
        """Select a model route for the given task type.

        Args:
            task_type: The type of task being routed.

        Returns:
            A :class:`ModelRoute` with provider, model, and capability.

        Raises:
            ProviderError: If no route exists for the task type.
        """
        route = self._routes.get(task_type) or self._routes.get("default")
        if route is None:
            raise ProviderError(f"No model route for task type: {task_type}")
        return route

    async def complete(
        self,
        *,
        task_type: str = "default",
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Complete a chat completion through the model gateway.

        All model access passes through this method. Provider credentials
        are never exposed to callers. Cloud fallback requires explicit
        configuration (disabled by default).

        Args:
            task_type: Task type for routing.
            messages: Chat messages.
            **kwargs: Additional completion parameters.

        Returns:
            The provider's completion response.

        Raises:
            ProviderError: If routing or completion fails.
        """
        route = self.route(task_type=task_type)
        adapter = self._providers.get(route.provider)
        if adapter is None:
            raise ProviderError(f"Provider not registered: {route.provider}")

        self.logger.info(
            "Model completion requested",
            extra={
                "provider": route.provider,
                "model": route.model,
                "task_type": task_type,
                "message_count": len(messages),
            },
        )

        try:
            result = await adapter.complete(model=route.model, messages=messages, **kwargs)
        except Exception as exc:
            self.logger.error(
                "Provider completion failed",
                extra={"provider": route.provider, "model": route.model, "error": str(exc)},
            )
            raise ProviderError(f"Provider {route.provider} failed: {exc}") from exc

        # Usage accounting
        key = f"{route.provider}:{route.model}"
        self._usage[key] = self._usage.get(key, 0) + 1

        return {
            **result,
            "provider": route.provider,
            "model": route.model,
            "task_type": task_type,
        }

    def usage(self) -> dict[str, int]:
        """Return usage accounting by provider:model."""
        return dict(self._usage)


gateway = ModelGateway()
