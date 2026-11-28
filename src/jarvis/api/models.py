"""Model status API endpoints.

Provides the model registry, provider inventory, routing table, and usage
accounting used by the Phase 10 dashboard "Model status" panel. All model
access is surfaced through the model gateway singleton so provider
credentials and internals are never exposed to clients.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from jarvis.ai.gateway import gateway
from jarvis.api.auth import get_current_user
from jarvis.auth import get_or_create_user_tenant
from jarvis.core.config import settings
from jarvis.core.logging import get_logger
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ModelCapabilityResponse(BaseModel):
    name: str
    tool_calling: bool
    structured_output: bool
    streaming: bool
    vision: bool
    max_context_tokens: int


class ModelResponse(BaseModel):
    name: str
    provider: str | None
    capability: ModelCapabilityResponse


class ProviderResponse(BaseModel):
    name: str
    credential_configured: bool


class RouteResponse(BaseModel):
    task_type: str
    provider: str
    model: str
    capability: ModelCapabilityResponse


class UsageStatsResponse(BaseModel):
    provider: str
    model: str
    used: int
    limit: int
    remaining: int
    percent_used: float
    exceeded: bool


def _capability_response(capability: Any) -> ModelCapabilityResponse:
    return ModelCapabilityResponse(
        name=getattr(capability, "name", "unknown"),
        tool_calling=bool(getattr(capability, "tool_calling", False)),
        structured_output=bool(getattr(capability, "structured_output", False)),
        streaming=bool(getattr(capability, "streaming", False)),
        vision=bool(getattr(capability, "vision", False)),
        max_context_tokens=int(getattr(capability, "max_context_tokens", 0)),
    )


@router.get(
    "/providers",
    response_model=list[ProviderResponse],
    status_code=status.HTTP_200_OK,
    summary="List registered model providers",
)
async def list_providers(
    session=Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> list[ProviderResponse]:
    """Return every provider registered with the model gateway."""
    _ = await get_current_user(session, authorization)
    tenant = await get_or_create_user_tenant(session, _)
    _ = tenant  # tenant scope enforced for future multi-tenant model routing
    providers: list[ProviderResponse] = []
    for name, adapter in gateway._providers.items():
        providers.append(
            ProviderResponse(
                name=name,
                credential_configured=adapter._credential is not None,
            )
        )
    return providers


@router.get(
    "",
    response_model=list[ModelResponse],
    status_code=status.HTTP_200_OK,
    summary="List registered models and capabilities",
)
async def list_models(
    session=Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> list[ModelResponse]:
    """Return every model registered with the model gateway."""
    _ = await get_current_user(session, authorization)
    tenant = await get_or_create_user_tenant(session, _)
    _ = tenant
    models: list[ModelResponse] = []
    for name, capability in gateway._models.items():
        provider = None
        for pname, adapter in gateway._providers.items():
            if adapter.provider_name == name:
                provider = pname
                break
        models.append(
            ModelResponse(
                name=name,
                provider=provider,
                capability=_capability_response(capability),
            )
        )
    return models


@router.get(
    "/routes",
    response_model=list[RouteResponse],
    status_code=status.HTTP_200_OK,
    summary="List model routing table",
)
async def list_routes(
    session=Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> list[RouteResponse]:
    """Return the model routing table (task type -> provider/model)."""
    _ = await get_current_user(session, authorization)
    tenant = await get_or_create_user_tenant(session, _)
    _ = tenant
    routes: list[RouteResponse] = []
    for task_type, route in gateway._routes.items():
        routes.append(
            RouteResponse(
                task_type=task_type,
                provider=route.provider,
                model=route.model,
                capability=_capability_response(route.capability),
            )
        )
    return routes


@router.get(
    "/usage",
    response_model=list[UsageStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="List model usage accounting and budget stats",
)
async def list_usage(
    session=Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> list[UsageStatsResponse]:
    """Return per provider:model usage and budget statistics."""
    _ = await get_current_user(session, authorization)
    tenant = await get_or_create_user_tenant(session, _)
    _ = tenant
    budget_limit = int(settings.model_gateway_budget_limit)
    stats: list[UsageStatsResponse] = []
    for key, detail in gateway.usage_stats().items():
        used = int(detail.get("used", 0))
        stats.append(
            UsageStatsResponse(
                provider=str(detail.get("provider", key.split(":", 1)[0])),
                model=str(
                    detail.get("model", key.split(":", 1)[1] if ":" in key else "")
                ),
                used=used,
                limit=budget_limit,
                remaining=max(budget_limit - used, 0),
                percent_used=round((used / budget_limit) * 100, 2)
                if budget_limit
                else 0.0,
                exceeded=bool(detail.get("exceeded", False)),
            )
        )
    return stats
