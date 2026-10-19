"""
Provider factory for the OpenStack review agent.

Providers are imported lazily so that a user who only has one provider's SDK
installed can still use that provider without the other's dependency.
"""

from .base import ReviewProvider, ReviewResult, print_usage_summary

__all__ = ["ReviewProvider", "ReviewResult", "print_usage_summary", "get_provider"]


def get_provider(
    name: str,
    *,
    openai_base_url: str = None,
    openai_price_input: float = None,
    openai_price_output: float = None,
) -> ReviewProvider:
    """Return a provider instance for the given name.

    Args:
        name: "claude" or "openai".
        openai_base_url: optional custom endpoint for the openai provider.
        openai_price_input: optional USD-per-1M-token input rate override.
        openai_price_output: optional USD-per-1M-token output rate override.
    """
    key = (name or "").lower()
    if key == "claude":
        from .claude import ClaudeProvider

        return ClaudeProvider()
    if key == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(
            base_url=openai_base_url,
            price_input=openai_price_input,
            price_output=openai_price_output,
        )

    raise ValueError(f"Unknown provider '{name}'. Available: claude, openai")
