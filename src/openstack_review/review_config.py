"""
Configuration for OpenStack review agent.

Customize MODEL_PRESETS to match your available Claude models.
Enterprise plans may have different model availability.
"""

import os
from typing import Dict, Any

# Default model presets - CUSTOMIZE THESE for your enterprise plan
MODEL_PRESETS: Dict[str, Dict[str, Any]] = {
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
}

# Alternative presets for older model versions (uncomment if needed)
# MODEL_PRESETS = {
#     "quick": {
#         "model": "claude-sonnet-4",
#         "max_turns": 30,
#         "description": "Fast review for minor changes",
#     },
#     "standard": {
#         "model": "claude-sonnet-4-5",
#         "max_turns": 50,
#         "description": "Standard comprehensive review",
#     },
#     "thorough": {
#         "model": "claude-opus-4",
#         "max_turns": 75,
#         "description": "Deep review for critical changes",
#     },
# }

# Default preset to use
DEFAULT_PRESET = "standard"

# Environment variable overrides
# These allow per-review customization without editing this file:
#   REVIEW_PRESET=thorough python review_agent.py 997182
#   REVIEW_MODEL=claude-opus-5 python review_agent.py 997182


def get_model_config(preset: str = None, model_override: str = None) -> Dict[str, Any]:
    """
    Get model configuration for a review.

    Priority order:
    1. Direct model override (--model flag)
    2. Preset from argument (--preset flag)
    3. Environment variable REVIEW_PRESET
    4. Environment variable REVIEW_MODEL
    5. Default preset

    Args:
        preset: Preset name from command line
        model_override: Direct model name from command line

    Returns:
        Dict with 'model' and 'max_turns' keys

    Raises:
        ValueError: If preset doesn't exist
    """
    # Direct model override takes precedence
    if model_override:
        return {
            "model": model_override,
            "max_turns": 50,  # Default max_turns for custom models
            "source": f"--model {model_override}",
        }

    # Determine which preset to use
    preset_name = (
        preset
        or os.getenv("REVIEW_PRESET")
        or DEFAULT_PRESET
    )

    # Check for direct model env var
    env_model = os.getenv("REVIEW_MODEL")
    if env_model:
        return {
            "model": env_model,
            "max_turns": 50,
            "source": f"REVIEW_MODEL={env_model}",
        }

    # Get preset config
    if preset_name not in MODEL_PRESETS:
        available = ", ".join(MODEL_PRESETS.keys())
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available: {available}\n"
            f"Customize MODEL_PRESETS in review_config.py for your enterprise plan."
        )

    config = MODEL_PRESETS[preset_name].copy()
    config["source"] = f"preset '{preset_name}'"
    return config


def list_presets() -> str:
    """Return formatted list of available presets."""
    lines = ["Available presets:"]
    for name, config in MODEL_PRESETS.items():
        default = " (default)" if name == DEFAULT_PRESET else ""
        lines.append(
            f"  {name:12s} - {config['description']}\n"
            f"               Model: {config['model']}, Max turns: {config['max_turns']}{default}"
        )
    return "\n".join(lines)
