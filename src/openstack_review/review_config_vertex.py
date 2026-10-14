"""
Configuration for OpenStack review agent with Vertex AI.

This is an example configuration for Vertex AI (Google Cloud), which is used by
the `claude` provider.

To apply: copy the dict below into review_config.py as PRESETS["claude"]
(the live config groups presets by provider: PRESETS[provider][preset]).
"""

import os
from typing import Dict, Any

# Vertex AI model presets for the claude provider.
# These use Vertex AI model IDs (different from Anthropic API).
# In review_config.py this becomes:  PRESETS["claude"] = CLAUDE_VERTEX_PRESETS
CLAUDE_VERTEX_PRESETS: Dict[str, Dict[str, Any]] = {
    "quick": {
        "model": "claude-haiku-4.5",
        "max_turns": 25,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-4.6",  # Claude Sonnet 4.6
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-opus-4.8",  # Claude Opus 4.8
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
}

# Google Cloud configuration
# Set these via environment variables
VERTEX_PROJECT_ID = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID")
VERTEX_REGION = os.getenv("CLOUD_ML_REGION", "global")
USE_VERTEX = os.getenv("CLAUDE_CODE_USE_VERTEX")

DEFAULT_PRESET = "standard"
