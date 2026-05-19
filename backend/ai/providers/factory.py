"""Factory: provider_name + api_key → AIProvider instance.

Centralized so business logic never names a concrete vendor class. Add new
providers here by extending the dispatch table.
"""
from __future__ import annotations

from .anthropic_provider import AnthropicProvider
from .base import AIProvider
from .openai_provider import OpenAICompatibleProvider

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MISTRAL_BASE_URL = "https://api.mistral.ai/v1"


SUPPORTED_PROVIDERS = ("anthropic", "openai", "groq", "mistral", "google")


def get_provider(provider_name: str, api_key: str) -> AIProvider:
    """Build an AIProvider for the given vendor. Raises ValueError on
    unknown provider, RuntimeError if Google SDK isn't installed."""
    if not api_key:
        raise ValueError(f"Empty API key for provider {provider_name}")

    p = provider_name.lower().strip()
    if p == "anthropic":
        return AnthropicProvider(api_key)
    if p == "openai":
        return OpenAICompatibleProvider(api_key, base_url=None, provider_name="openai",
                                        cheap_model="gpt-4o-mini")
    if p == "groq":
        return OpenAICompatibleProvider(api_key, base_url=GROQ_BASE_URL, provider_name="groq",
                                        cheap_model="llama-3.3-70b-versatile")
    if p == "mistral":
        return OpenAICompatibleProvider(api_key, base_url=MISTRAL_BASE_URL, provider_name="mistral",
                                        cheap_model="mistral-small-latest")
    if p == "google":
        # Lazy import — google-generativeai is optional.
        from .google_provider import GoogleProvider
        return GoogleProvider(api_key)
    raise ValueError(f"Unknown AI provider: {provider_name}")
