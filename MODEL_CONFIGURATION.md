# Model Configuration Guide

The OpenStack review agent supports multiple AI providers and models through a flexible preset system. This is designed to work with enterprise plans / accounts that may have different model availability.

## Providers

Two providers are available:

- **claude** (default) — via the Claude Agent SDK. Needs `ANTHROPIC_API_KEY`, or Vertex AI env vars (`CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`).
- **openai** — via the OpenAI Responses API. Needs `OPENAI_API_KEY`. Optionally point at a custom endpoint (Azure / OpenAI-compatible / proxy / self-hosted) with `--openai-base-url` or `OPENAI_BASE_URL`.

Select with `--provider {claude,openai}` or `AGENT_PROVIDER`:

```bash
python review_agent.py 970404 --provider openai
python review_agent.py 970404 --provider openai --openai-base-url https://your-endpoint/v1
```

> **Preset structure note:** presets are grouped by provider in `review_config.py`:
> `PRESETS[provider][preset]` (e.g. `PRESETS["claude"]["standard"]`), with a
> top-level `DEFAULT_PROVIDER`. The flat `MODEL_PRESETS = { ... }` snippets shown
> below illustrate the per-provider dict — assign them to `PRESETS["claude"]` or
> `PRESETS["openai"]` rather than to a bare `MODEL_PRESETS` variable.

## Detecting Available Models

If you're on an enterprise plan and don't know which models you have access to, use the detection script:

```bash
# Detect available models
python detect_models.py

# Detect and automatically update review_config.py
python detect_models.py --update-config

# Show detailed error messages
python detect_models.py --verbose
```

The script will:
1. Test common Claude model IDs against your API key
2. Report which models are available
3. Suggest an optimized preset configuration
4. Optionally update `review_config.py` automatically

**Example output:**
```
Testing claude-opus-5                      ... ✗ Model not found
Testing claude-sonnet-5                    ... ✓ Available
Testing claude-sonnet-4-5                  ... ✓ Available
Testing claude-haiku-4-5                   ... ✓ Available

Available models by tier:
  Sonnet (balanced):
    - claude-sonnet-5
    - claude-sonnet-4-5
  
  Haiku (fastest):
    - claude-haiku-4-5

Suggested preset configuration:
------------------------------------------------------------
MODEL_PRESETS = {
    "quick": {
        "model": "claude-haiku-4-5",
        "max_turns": 25,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-sonnet-5",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-sonnet-5",
        "max_turns": 100,
        "description": "Deep review for critical changes",
    },
}
```

## Quick Start

### Using Presets

```bash
# Quick review (faster, lower cost)
python review_agent.py 997182 --preset quick

# Standard review (default)
python review_agent.py 997182 --preset standard

# Thorough review (slower, higher quality)
python review_agent.py 997182 --preset thorough
```

### Using Specific Models

```bash
# Override with a specific model
python review_agent.py 997182 --model claude-sonnet-4-5

# Via environment variable
AGENT_MODEL=claude-opus-5 python review_agent.py 997182

# Set model reasoning effort (provider/model support varies)
python review_agent.py 997182 --effort high
AGENT_EFFORT=high python review_agent.py 997182
```

### List Available Presets

```bash
python review_agent.py --list-presets
```

## Configuration Priority

The agent selects models in this order (highest priority first):

1. **`--model` flag** - Direct model override
2. **`--preset` flag** - Named preset (quick/standard/thorough)
3. **`AGENT_MODEL` env var** - Direct model from environment
4. **`AGENT_PRESET` env var** - Preset from environment
5. **Default preset** - Falls back to "standard"

Model effort is selected separately: `--effort` takes precedence over
`AGENT_EFFORT`. If neither is set, the provider uses its model default. The
accepted effort values depend on the selected provider and model; `low`,
`medium`, and `high` are common values.

## Customizing for Enterprise Plans

Enterprise Claude plans may have different model availability. To customize the presets for your plan:

### Step 1: Identify Your Available Models

Check which models are available on your enterprise plan. Common options:
- `claude-opus-5` / `claude-opus-4`
- `claude-sonnet-5` / `claude-sonnet-4-5` / `claude-sonnet-4`
- `claude-haiku-4-5`

### Step 2: Edit `review_config.py`

Open `review_config.py` and modify the `MODEL_PRESETS` dictionary:

```python
# Example: Enterprise plan with only Sonnet 4.5 and Opus 4
MODEL_PRESETS = {
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
```

### Step 3: Set Default Preset (Optional)

Change the default if needed:

```python
DEFAULT_PRESET = "standard"  # or "quick" / "thorough"
```

## Preset Guidelines

### Quick Preset
- **Use for**: Minor changes, documentation updates, simple bug fixes
- **Model**: Faster model (Sonnet 4.5 or Haiku)
- **Turns**: 30 (sufficient for small reviews)

### Standard Preset
- **Use for**: Most code reviews, feature additions, refactoring
- **Model**: Balanced model (Sonnet 5 or Sonnet 4.5)
- **Turns**: 50 (comprehensive review)

### Thorough Preset
- **Use for**: Critical changes, security updates, complex features, backports
- **Model**: Most capable model (Opus 5 or Opus 4)
- **Turns**: 75 (deep analysis with follow-up investigation)

## Environment Variables

Useful for CI/CD or scripting:

```bash
# Set default for all reviews in this session
export AGENT_PRESET=thorough
python review_agent.py 997182
python review_agent.py 997183

# Override for specific review
AGENT_MODEL=claude-opus-5 python review_agent.py 997184
```

## Examples

### Standard Workflow

```bash
# Small documentation fix
python review_agent.py 997182 --preset quick

# Regular feature addition
python review_agent.py 997183

# Security-critical change
python review_agent.py 997184 --preset thorough
```

### Enterprise Plan with Limited Models

If you only have access to `claude-sonnet-4-5`:

```python
# In review_config.py
MODEL_PRESETS = {
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
        "max_turns": 100,  # More turns compensates for same model
        "description": "Deep review for critical changes",
    },
}
```

### Testing New Models

```bash
# Test a specific model without editing config
python review_agent.py 997182 --model claude-haiku-4-5
```

## Adding Custom Presets

You can add your own presets in `review_config.py`:

```python
MODEL_PRESETS = {
    "quick": { ... },
    "standard": { ... },
    "thorough": { ... },
    
    # Custom presets
    "security": {
        "model": "claude-opus-5",
        "max_turns": 60,
        "description": "Security-focused deep review",
    },
    "backport": {
        "model": "claude-sonnet-5",
        "max_turns": 40,
        "description": "Backport verification review",
    },
}
```

Then use them:
```bash
python review_agent.py 997182 --preset security
```

## Troubleshooting

### "Model not available" errors

If you get API errors about model availability:

1. Check your enterprise plan's available models
2. Update `MODEL_PRESETS` in `review_config.py`
3. Test with `--model` flag first to verify the model works
4. Update the preset once confirmed

### Unknown preset error

```
ValueError: Unknown preset 'xyz'. Available: quick, standard, thorough
```

This means you tried to use a preset that doesn't exist. Either:
- Use an existing preset: `--preset standard`
- Add the preset to `review_config.py`
- Use direct model override: `--model claude-sonnet-5`

## Best Practices

1. **Start with standard** - Use the default preset for most reviews
2. **Escalate when needed** - Use `thorough` for complex/critical changes
3. **Track costs** - Monitor usage if your plan has token limits
4. **Document changes** - If you modify presets, document why in `review_config.py`
5. **Test before committing** - Test new models with `--model` before updating presets
