"""Tier → model mapping per provider, plus cost tables.

Tier semantics (consistent across providers):
  - "eco":         cheapest reasonable quality. Default for high-volume tasks.
  - "intelligent": default for chat. Balanced cost + quality.
  - "scientist":   most capable, slowest, most expensive. Uses extended
                   thinking on providers that support it.

Each entry is (model_id, thinking_budget_tokens_or_None, max_output_tokens).
thinking_budget is only honored by AnthropicProvider; other providers ignore it.

Costs are USD per 1M tokens (input, output). Used for the token monitor UI.
"""
from __future__ import annotations

# (model_id, thinking_budget, max_output_tokens)
TIER_MODELS: dict[str, dict[str, tuple[str, int | None, int]]] = {
    "eco": {
        "anthropic": ("claude-haiku-4-5", None, 2048),
        "openai":    ("gpt-4o-mini", None, 4096),
        "groq":      ("llama-3.3-70b-versatile", None, 4096),
        "mistral":   ("mistral-small-latest", None, 4096),
        "google":    ("gemini-2.5-flash-lite", None, 4096),
    },
    "intelligent": {
        # Sonnet 4.5 supports thinking, but we default to off for the
        # everyday tier — opt in via "scientist". Saves tokens.
        "anthropic": ("claude-sonnet-4-5", None, 4096),
        "openai":    ("gpt-4o", None, 4096),
        "groq":      ("llama-3.1-70b-versatile", None, 4096),
        "mistral":   ("mistral-large-latest", None, 4096),
        "google":    ("gemini-2.5-pro", None, 4096),
    },
    "scientist": {
        "anthropic": ("claude-opus-4-1", 10000, 8192),
        "openai":    ("o3", None, 8192),
        "groq":      ("llama-3.1-70b-versatile", None, 8192),
        "mistral":   ("mistral-large-latest", None, 8192),
        "google":    ("gemini-2.5-pro", None, 8192),
    },
}

# USD per 1M tokens — (input, output). Source: vendor pricing pages as of 2026-05.
# Update when vendors change rates; surfaced to users via /api/tokens/dashboard.
TIER_COSTS: dict[str, dict[str, tuple[float, float]]] = {
    "eco": {
        "anthropic": (1.00, 5.00),
        "openai":    (0.15, 0.60),
        "groq":      (0.59, 0.79),
        "mistral":   (0.10, 0.30),
        "google":    (0.10, 0.40),
    },
    "intelligent": {
        "anthropic": (3.00, 15.00),
        "openai":    (2.50, 10.00),
        "groq":      (0.59, 0.79),
        "mistral":   (2.00, 6.00),
        "google":    (1.25, 10.00),
    },
    "scientist": {
        "anthropic": (15.00, 75.00),
        "openai":    (2.00, 8.00),
        "groq":      (0.59, 0.79),
        "mistral":   (2.00, 6.00),
        "google":    (2.50, 15.00),
    },
}


def resolve_tier(tier_or_model: str, provider: str) -> tuple[str, int | None, int]:
    """Accept either a tier slug (eco/intelligent/scientist) or an explicit
    model id. Returns (model_id, thinking_budget, max_tokens)."""
    tier = (tier_or_model or "intelligent").lower().strip()
    if tier in TIER_MODELS:
        return TIER_MODELS[tier][provider]
    # Treat as explicit model id — pick intelligent tier defaults for budget/max.
    intel = TIER_MODELS["intelligent"].get(provider, ("", None, 4096))
    return (tier_or_model, intel[1], intel[2])


def estimate_cost(provider: str, tier: str, input_tokens: int, output_tokens: int) -> float:
    """Returns USD cost. Falls back to 0.0 if combination unknown."""
    try:
        in_rate, out_rate = TIER_COSTS[tier][provider]
    except KeyError:
        return 0.0
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000.0
