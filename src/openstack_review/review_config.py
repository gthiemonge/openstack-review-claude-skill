"""
Configuration for OpenStack review agent.

Presets are organized by provider. Customize PRESETS to match the models
available on your plan/account (enterprise plans and OpenAI accounts differ in
model availability).
"""

import os
from typing import Any, Dict

# Default provider when none is specified.
# Override with the REVIEW_PROVIDER environment variable or --provider flag.
DEFAULT_PROVIDER = "claude"

# Model presets per provider - CUSTOMIZE THESE for your plan/account.
PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "claude": {
        "quick": {
            "model": "claude-haiku-4-5",
            "max_turns": 30,
            "description": "Fast review for minor changes",
        },
        "standard": {
            "model": "claude-sonnet-4-6",
            "max_turns": 50,
            "description": "Standard comprehensive review",
        },
        "thorough": {
            "model": "claude-opus-4-8",
            "max_turns": 75,
            "description": "Deep review for critical changes",
        },
    },
    # OpenAI model names are account-dependent — adjust to what you have access to.
    "openai": {
        "quick": {
            "model": "gpt-5-mini",
            "max_turns": 30,
            "description": "Fast review for minor changes",
        },
        "standard": {
            "model": "gpt-5",
            "max_turns": 50,
            "description": "Standard comprehensive review",
        },
        "thorough": {
            "model": "gpt-5",
            "max_turns": 75,
            "description": "Deep review for critical changes",
        },
    },
}

# Default preset to use (within the selected provider).
DEFAULT_PRESET = "standard"

# Environment variable overrides allow per-review customization without editing
# this file:
#   REVIEW_PROVIDER=openai python review_agent.py 997182
#   REVIEW_PRESET=thorough python review_agent.py 997182
#   REVIEW_MODEL=gpt-5 python review_agent.py 997182


def _resolve_provider(provider: str = None) -> str:
    """Determine the active provider (flag > env > default)."""
    name = (provider or os.getenv("REVIEW_PROVIDER") or DEFAULT_PROVIDER).lower()
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")
    return name


def get_model_config(
    provider: str = None, preset: str = None, model_override: str = None
) -> Dict[str, Any]:
    """
    Get model configuration for a review.

    Provider resolution: --provider flag > REVIEW_PROVIDER env > DEFAULT_PROVIDER.

    Within the provider, model resolution priority:
    1. Direct model override (--model flag)
    2. REVIEW_MODEL environment variable
    3. Preset from argument (--preset flag)
    4. REVIEW_PRESET environment variable
    5. Default preset

    Returns:
        Dict with 'provider', 'model', 'max_turns', and 'source' keys.

    Raises:
        ValueError: If the provider or preset doesn't exist.
    """
    provider_name = _resolve_provider(provider)
    provider_presets = PRESETS[provider_name]

    # Direct model override takes precedence.
    if model_override:
        return {
            "provider": provider_name,
            "model": model_override,
            "max_turns": 50,
            "source": f"--model {model_override}",
        }

    # Direct model env var.
    env_model = os.getenv("REVIEW_MODEL")
    if env_model:
        return {
            "provider": provider_name,
            "model": env_model,
            "max_turns": 50,
            "source": f"REVIEW_MODEL={env_model}",
        }

    # Determine which preset to use.
    preset_name = preset or os.getenv("REVIEW_PRESET") or DEFAULT_PRESET

    if preset_name not in provider_presets:
        available = ", ".join(provider_presets.keys())
        raise ValueError(
            f"Unknown preset '{preset_name}' for provider '{provider_name}'. "
            f"Available: {available}\n"
            f"Customize PRESETS in review_config.py for your plan/account."
        )

    config = provider_presets[preset_name].copy()
    config["provider"] = provider_name
    config["source"] = f"preset '{preset_name}' (provider '{provider_name}')"
    return config


def list_presets() -> str:
    """Return formatted list of available presets, grouped by provider."""
    lines = ["Available presets (by provider):"]
    for provider_name, provider_presets in PRESETS.items():
        default_provider = " (default provider)" if provider_name == DEFAULT_PROVIDER else ""
        lines.append(f"\n{provider_name}{default_provider}:")
        for name, config in provider_presets.items():
            default = " (default preset)" if name == DEFAULT_PRESET else ""
            lines.append(
                f"  {name:12s} - {config['description']}\n"
                f"               Model: {config['model']}, "
                f"Max turns: {config['max_turns']}{default}"
            )
    return "\n".join(lines)
