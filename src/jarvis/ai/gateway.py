"""Model gateway: provider abstraction, model registry, and routing.

Per javis-blueprint.md section 4, all model access must pass through
this gateway. Application modules must not embed provider credentials
or APIs. Cloud fallback is disabled by default.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from jarvis.ai.context import assemble_context, estimate_budget_usage
from jarvis.ai.provider import (
    LocalProviderAdapter,
    ModelCapability,
    ModelRoute,
    OllamaProviderAdapter,
    OpenAIProviderAdapter,
    ProviderAdapter,
)
from jarvis.core.config import settings
from jarvis.core.exceptions import ProviderError
from jarvis.core.logging import get_logger

logger = get_logger(__name__)


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

        # Register OpenAI provider if credentials available
        if settings.openai_api_key:
            self.register_provider(
                "openai",
                OpenAIProviderAdapter(
                    "openai", settings.openai_api_key, settings.openai_base_url
                ),
            )
            self._models["gpt-3.5-turbo"] = ModelCapability(
                name="gpt-3.5-turbo",
                tool_calling=True,
                structured_output=True,
                streaming=True,
                vision=False,
                max_context_tokens=4096,
            )
            self._models["gpt-4"] = ModelCapability(
                name="gpt-4",
                tool_calling=True,
                structured_output=True,
                streaming=True,
                vision=False,
                max_context_tokens=8192,
            )
            self.logger.info("OpenAI provider registered")

        # Register Ollama provider if configured
        if settings.ollama_base_url:
            self.register_provider(
                "ollama",
                OllamaProviderAdapter("ollama", None, settings.ollama_base_url),
            )
            self._models["llama3"] = ModelCapability(
                name="llama3",
                tool_calling=False,
                structured_output=False,
                streaming=True,
                vision=False,
                max_context_tokens=8192,
            )
            self.logger.info("Ollama provider registered")

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

    def register_route(self, task_type: str, route: ModelRoute) -> None:
        """Register a route for a task type.

        Args:
            task_type: Task type identifier.
            route: Route configuration.
        """
        self._routes[task_type] = route
        self.logger.info(
            "Route registered",
            extra={"task_type": task_type, "provider": route.provider, "model": route.model},
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

    def _check_budget(self, provider: str, model: str, estimated_tokens: int = 0) -> None:
        """Check budget limits before allowing a request.

        Args:
            provider: Provider name.
            model: Model name.
            estimated_tokens: Estimated tokens for the request.

        Raises:
            ProviderError: If budget is exceeded.
        """
        if not settings.model_gateway_budget_enabled:
            return

        key = f"{provider}:{model}"
        current_usage = self._usage.get(key, 0)
        budget = settings.model_gateway_budget_limit

        metrics = estimate_budget_usage(current_usage + estimated_tokens, budget)
        if metrics["exceeded"]:
            raise ProviderError(
                f"Budget exceeded for {provider}:{model}. "
                f"Used: {metrics['used']}, Limit: {metrics['limit']}"
            )

    def _record_usage(self, provider: str, model: str, tokens: int = 0) -> None:
        """Record usage for provider:model.

        Args:
            provider: Provider name.
            model: Model name.
            tokens: Token count to add.
        """
        key = f"{provider}:{model}"
        self._usage[key] = self._usage.get(key, 0) + max(tokens, 1)

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

        # Assemble context with token budget
        max_tokens = route.capability.max_context_tokens
        assembled_messages = assemble_context(
            messages, max_tokens=max_tokens
        )

        # Estimate token count for budget check
        estimated_tokens = sum(
            len(str(m.get("content", ""))) // 4 for m in assembled_messages
        )

        # Check budget before execution
        self._check_budget(route.provider, route.model, estimated_tokens)

        self.logger.info(
            "Model completion requested",
            extra={
                "provider": route.provider,
                "model": route.model,
                "task_type": task_type,
                "message_count": len(messages),
                "assembled_messages": len(assembled_messages),
                "estimated_tokens": estimated_tokens,
            },
        )

        try:
            result = await adapter.complete(model=route.model, messages=assembled_messages, **kwargs)
        except Exception as exc:
            self.logger.error(
                "Provider completion failed",
                extra={"provider": route.provider, "model": route.model, "error": str(exc)},
            )
            raise ProviderError(f"Provider {route.provider} failed: {exc}") from exc

        # Usage accounting
        used_tokens = result.get("usage", {}).get("total_tokens", estimated_tokens)
        self._record_usage(route.provider, route.model, used_tokens)

        return {
            **result,
            "provider": route.provider,
            "model": route.model,
            "task_type": task_type,
        }

    async def complete_stream(
        self,
        *,
        task_type: str = "default",
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion through the model gateway.

        Args:
            task_type: Task type for routing.
            messages: Chat messages.
            **kwargs: Additional completion parameters.

        Yields:
            Chunks of the completion response.

        Raises:
            ProviderError: If routing or completion fails.
        """
        route = self.route(task_type=task_type)
        adapter = self._providers.get(route.provider)
        if adapter is None:
            raise ProviderError(f"Provider not registered: {route.provider}")

        self.logger.info(
            "Model streaming requested",
            extra={
                "provider": route.provider,
                "model": route.model,
                "task_type": task_type,
                "message_count": len(messages),
            },
        )

        # Assemble context
        assembled_messages = assemble_context(
            messages, max_tokens=route.capability.max_context_tokens
        )

        # Estimate token count for budget check
        estimated_tokens = sum(
            len(str(m.get("content", ""))) // 4 for m in assembled_messages
        )

        # Check budget before execution
        self._check_budget(route.provider, route.model, estimated_tokens)

        try:
            async for chunk in adapter.complete_stream(
                model=route.model, messages=assembled_messages, **kwargs
            ):
                yield {
                    **chunk,
                    "provider": route.provider,
                    "model": route.model,
                    "task_type": task_type,
                }
        except Exception as exc:
            self.logger.error(
                "Provider streaming failed",
                extra={"provider": route.provider, "model": route.model, "error": str(exc)},
            )
            raise ProviderError(f"Provider {route.provider} failed: {exc}") from exc

    def usage(self) -> dict[str, int]:
        """Return usage accounting by provider:model."""
        return dict(self._usage)

    def usage_stats(self) -> dict[str, dict[str, Any]]:
        """Return detailed usage accounting with budget information.

        Returns:
            Dict mapping provider:model to usage stats including budget info.
        """
        result: dict[str, dict[str, Any]] = {}
        for key, used in self._usage.items():
            result[key] = estimate_budget_usage(
                used, settings.model_gateway_budget_limit
            )
            result[key]["provider"] = key.split(":", 1)[0]
            result[key]["model"] = key.split(":", 1)[1] if ":" in key else ""
        return result


gateway = ModelGateway()