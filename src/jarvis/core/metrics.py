"""Observability metrics — Prometheus counters, gauges, and histograms.

Per javis-blueprint.md section 17.1, all telemetry must be recorded
without leaking secrets, passwords, access tokens, or unnecessary private
content into logs, metrics, or traces.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# --- Request metrics ---
REQUEST_COUNT = Counter(
    "jarvis_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "jarvis_request_duration_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
)

# --- Model gateway metrics ---
MODEL_REQUEST_COUNT = Counter(
    "jarvis_model_requests_total",
    "Total number of model gateway requests",
    ["provider", "model", "task_type"],
)

MODEL_TOKEN_COUNT = Counter(
    "jarvis_model_tokens_total",
    "Total number of tokens processed by model gateway",
    ["provider", "model", "direction"],  # direction: input or output
)

MODEL_REQUEST_LATENCY = Histogram(
    "jarvis_model_request_duration_seconds",
    "Model gateway request latency in seconds",
    ["provider", "model"],
)

# --- Agent metrics ---
AGENT_EXECUTION_COUNT = Counter(
    "jarvis_agent_executions_total",
    "Total number of agent executions",
    ["agent_name", "state"],
)

AGENT_EXECUTION_LATENCY = Histogram(
    "jarvis_agent_execution_duration_seconds",
    "Agent execution latency in seconds",
    ["agent_name"],
)

AGENT_CONCURRENT = Gauge(
    "jarvis_agent_concurrent_executions",
    "Number of currently running agent executions",
)

# --- Tool metrics ---
TOOL_EXECUTION_COUNT = Counter(
    "jarvis_tool_executions_total",
    "Total number of tool executions",
    ["tool_name", "outcome"],
)

TOOL_EXECUTION_LATENCY = Histogram(
    "jarvis_tool_execution_duration_seconds",
    "Tool execution latency in seconds",
    ["tool_name"],
)

# --- Memory metrics ---
MEMORY_ITEM_COUNT = Gauge(
    "jarvis_memory_items_total",
    "Number of memory items in store",
    ["memory_type"],
)

# --- Approval metrics ---
APPROVAL_COUNT = Counter(
    "jarvis_approvals_total",
    "Total number of approval requests",
    ["state"],  # pending, granted, denied, expired
)

# --- Security metrics ---
AUTHZ_DENIAL_COUNT = Counter(
    "jarvis_authz_denials_total",
    "Total number of authorization denials",
    ["permission", "actor_id"],
)

AUTHN_FAILURE_COUNT = Counter(
    "jarvis_authn_failures_total",
    "Total number of authentication failures",
)


def get_metrics() -> bytes:
    """Return Prometheus metrics in text format for scraping."""
    return generate_latest()


def record_request(
    method: str, endpoint: str, status_code: int, duration: float
) -> None:
    """Record an HTTP request metric."""
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_model_request(
    provider: str,
    model: str,
    task_type: str,
    duration: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Record a model gateway request metric."""
    MODEL_REQUEST_COUNT.labels(
        provider=provider, model=model, task_type=task_type
    ).inc()
    MODEL_REQUEST_LATENCY.labels(provider=provider, model=model).observe(duration)
    if input_tokens > 0:
        MODEL_TOKEN_COUNT.labels(provider=provider, model=model, direction="input").inc(
            input_tokens
        )
    if output_tokens > 0:
        MODEL_TOKEN_COUNT.labels(
            provider=provider, model=model, direction="output"
        ).inc(output_tokens)


def record_agent_execution(
    agent_name: str,
    state: str,
    duration: float | None = None,
) -> None:
    """Record an agent execution metric."""
    AGENT_EXECUTION_COUNT.labels(agent_name=agent_name, state=state).inc()
    if duration is not None:
        AGENT_EXECUTION_LATENCY.labels(agent_name=agent_name).observe(duration)


def record_agent_concurrent(delta: int) -> None:
    """Update concurrent agent execution gauge."""
    AGENT_CONCURRENT.inc(delta)


def record_tool_execution(tool_name: str, outcome: str, duration: float) -> None:
    """Record a tool execution metric."""
    TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, outcome=outcome).inc()
    TOOL_EXECUTION_LATENCY.labels(tool_name=tool_name).observe(duration)


def record_memory_item(memory_type: str, delta: int = 1) -> None:
    """Record memory item count change."""
    MEMORY_ITEM_COUNT.labels(memory_type=memory_type).inc(delta)


def record_approval(state: str) -> None:
    """Record an approval request metric."""
    APPROVAL_COUNT.labels(state=state).inc()


def record_authz_denial(permission: str, actor_id: str) -> None:
    """Record an authorization denial metric."""
    AUTHZ_DENIAL_COUNT.labels(permission=permission, actor_id=actor_id).inc()


def record_authn_failure() -> None:
    """Record an authentication failure metric."""
    AUTHN_FAILURE_COUNT.inc()


def record_voice_request(
    operation: str, provider: str, outcome: str, duration: float, audio_bytes: int = 0
) -> None:
    """Record a voice interface request metric."""
    VOICE_REQUEST_COUNT.labels(
        operation=operation, provider=provider, outcome=outcome
    ).inc()
    VOICE_REQUEST_LATENCY.labels(operation=operation, provider=provider).observe(
        duration
    )
    if audio_bytes > 0:
        VOICE_AUDIO_BYTES.labels(operation=operation, provider=provider).inc(
            audio_bytes
        )


def record_vision_request(
    operation: str,
    provider: str,
    outcome: str,
    duration: float,
    image_bytes: int = 0,
) -> None:
    """Record a vision interface request metric."""
    VISION_REQUEST_COUNT.labels(
        operation=operation, provider=provider, outcome=outcome
    ).inc()
    VISION_REQUEST_LATENCY.labels(operation=operation, provider=provider).observe(
        duration
    )
    if image_bytes > 0:
        VISION_IMAGE_BYTES.labels(operation=operation, provider=provider).inc(
            image_bytes
        )


# --- Voice metrics ---
VOICE_REQUEST_COUNT = Counter(
    "jarvis_voice_requests_total",
    "Total number of voice interface requests",
    ["operation", "provider", "outcome"],  # operation: stt or tts
)

VOICE_REQUEST_LATENCY = Histogram(
    "jarvis_voice_request_duration_seconds",
    "Voice interface request latency in seconds",
    ["operation", "provider"],
)

VOICE_AUDIO_BYTES = Counter(
    "jarvis_voice_audio_bytes_total",
    "Total audio bytes processed by the voice interface",
    ["operation", "provider"],
)


# --- Vision metrics ---
VISION_REQUEST_COUNT = Counter(
    "jarvis_vision_requests_total",
    "Total number of vision interface requests",
    ["operation", "provider", "outcome"],  # operation: describe or analyze
)

VISION_REQUEST_LATENCY = Histogram(
    "jarvis_vision_request_duration_seconds",
    "Vision interface request latency in seconds",
    ["operation", "provider"],
)

VISION_IMAGE_BYTES = Counter(
    "jarvis_vision_image_bytes_total",
    "Total image bytes processed by the vision interface",
    ["operation", "provider"],
)
