"""Context assembly for model gateway.

Assembles conversation context from conversation history,
respecting token limits and relevance constraints.
"""

from __future__ import annotations

from typing import Any


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Rough estimate: ~4 characters per token for English text.

    Args:
        text: Text to estimate token count for.

    Returns:
        Estimated token count (minimum 1).
    """
    return max(1, len(text) // 4)


def assemble_context(
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
    system_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """Assemble context from conversation history.

    Selects the most recent messages that fit within the token budget,
    preserving system messages and recent conversation turns.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        max_tokens: Maximum token budget for the context.
        system_prompt: Optional system prompt to prepend.

    Returns:
        List of message dicts that fit within the token budget,
        in chronological order (oldest to newest).
    """
    selected: list[dict[str, Any]] = []
    total_tokens = 0

    # Always include system prompt first if provided
    if system_prompt:
        system_tokens = estimate_tokens(system_prompt)
        if system_tokens <= max_tokens:
            selected.append({"role": "system", "content": system_prompt})
            total_tokens += system_tokens

    # Add messages from most recent to oldest
    for message in reversed(messages):
        msg_tokens = estimate_tokens(message.get("content", ""))
        if total_tokens + msg_tokens > max_tokens:
            break
        selected.insert(0, message)
        total_tokens += msg_tokens

    return selected


def estimate_budget_usage(
    current_usage: int,
    budget_limit: int,
) -> dict[str, Any]:
    """Calculate budget usage metrics.

    Args:
        current_usage: Current token usage.
        budget_limit: Budget limit in tokens.

    Returns:
        Dict with usage metrics including remaining and percentage used.
    """
    if budget_limit <= 0:
        return {
            "used": current_usage,
            "limit": budget_limit,
            "remaining": 0,
            "percentage_used": 0.0,
            "exceeded": current_usage > 0,
        }

    remaining = max(0, budget_limit - current_usage)
    percentage = min(100.0, (current_usage / budget_limit) * 100.0)

    return {
        "used": current_usage,
        "limit": budget_limit,
        "remaining": remaining,
        "percentage_used": round(percentage, 2),
        "exceeded": current_usage > budget_limit,
    }
