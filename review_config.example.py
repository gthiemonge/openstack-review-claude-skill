"""
Example configurations for different enterprise plans / accounts.

The live review_config.py groups presets by provider:

    PRESETS = {
        "claude": { "quick": {...}, "standard": {...}, "thorough": {...} },
        "openai": { "quick": {...}, "standard": {...}, "thorough": {...} },
    }

Each dict below is a set of {preset: {...}} entries you can drop in as
PRESETS["claude"] (or PRESETS["openai"] for the OpenAI examples).
"""

# ═══════════════════════════════════════════════════════════════════
# Example 1: Latest Claude models (default) -> PRESETS["claude"]
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_LATEST = {
    "quick": {
        "model": "claude-sonnet-4-5",
        "max_turns": 30,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-5",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-opus-5",
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Example 2: Enterprise plan with Opus 4 and Sonnet 4.5 only
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_ENTERPRISE_1 = {
    "quick": {
        "model": "claude-sonnet-4-5",
        "max_turns": 30,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-4-5",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-opus-4",
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Example 3: Only Sonnet 4.5 available
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_SONNET_ONLY = {
    "quick": {
        "model": "claude-sonnet-4-5",
        "max_turns": 25,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-4-5",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-sonnet-4-5",
        "max_turns": 100,  # More turns for deeper analysis
        "description": "Deep review for critical changes",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Example 4: Older models (Opus 4, Sonnet 4, Haiku 3.5)
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_OLDER = {
    "quick": {
        "model": "claude-sonnet-4",
        "max_turns": 30,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-4",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-opus-4",
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Example 5: Custom presets for different review types
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_CUSTOM = {
    "quick": {
        "model": "claude-sonnet-4-5",
        "max_turns": 30,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-5",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-opus-5",
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
    "security": {
        "model": "claude-opus-5",
        "max_turns": 60,
        "description": "Security-focused review",
    },
    "backport": {
        "model": "claude-sonnet-5",
        "max_turns": 40,
        "description": "Backport verification",
    },
    "docs": {
        "model": "claude-sonnet-4-5",
        "max_turns": 20,
        "description": "Documentation-only changes",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Example 6: Cost-optimized (prefer faster/cheaper models)
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_COST_OPTIMIZED = {
    "quick": {
        "model": "claude-haiku-4-5",
        "max_turns": 25,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-4-5",
        "max_turns": 40,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-sonnet-5",  # Use Sonnet 5 instead of Opus
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Example 7: OpenAI account -> PRESETS["openai"]
# (model names are account-dependent — adjust to what you have access to)
# ═══════════════════════════════════════════════════════════════════

MODEL_PRESETS_OPENAI = {
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
}

# ═══════════════════════════════════════════════════════════════════
# To use one of these configurations:
# 1. Copy the desired MODEL_PRESETS_* dict above
# 2. Open review_config.py
# 3. Assign it to the relevant provider, e.g.:
#        PRESETS["claude"] = MODEL_PRESETS_LATEST
#        PRESETS["openai"] = MODEL_PRESETS_OPENAI
# 4. Adjust DEFAULT_PROVIDER / DEFAULT_PRESET if needed
# ═══════════════════════════════════════════════════════════════════
