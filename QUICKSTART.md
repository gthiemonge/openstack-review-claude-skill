# Quick Start Guide

## First Time Setup

### 1. Install Dependencies

**For Anthropic API:**
```bash
pip install claude-agent-sdk anthropic
```

**For Vertex AI (Google Cloud):**
```bash
pip install claude-agent-sdk 'anthropic[vertex]'
```

The `'anthropic[vertex]'` installs additional dependencies needed for Vertex AI:
- `google-auth` - Google Cloud authentication
- `google-cloud-aiplatform` - Vertex AI platform client

### 2. Set Your API Key

**For Anthropic API:**
```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

**For Vertex AI (Google Cloud):**
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set project (optional, can also use --vertex-project flag)
export ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
export CLOUD_ML_REGION=global  # Optional, defaults to global (use your org's required region)
```

See [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md) for detailed Vertex AI setup.

### 3. Detect Available Models (Enterprise Plans)

If you're on an enterprise plan and don't know which models you have access to:

**For Anthropic API:**
```bash
# Detect available models
python detect_models.py

# Detect and automatically configure
python detect_models.py --update-config
```

**For Vertex AI:**
```bash
# Detect available models
python detect_models.py --vertex --project YOUR_PROJECT_ID

# Detect and automatically configure
python detect_models.py --vertex --project YOUR_PROJECT_ID --update-config
```

This will:
- Test common Claude models with your API
- Show which models work on your plan
- Suggest optimized presets
- Optionally auto-update `review_config.py`

**Skip this step if you already know your available models.**

### 4. Customize Configuration (Optional)

Edit `review_config.py` to match your preferences. Presets are grouped by
provider (`PRESETS[provider][preset]`):

```python
DEFAULT_PROVIDER = "claude"

PRESETS = {
    "claude": {
        "quick": {
            "model": "claude-sonnet-4-5",
            "max_turns": 30,
            "description": "Fast review for minor changes",
        },
        # ... more presets
    },
    "openai": {
        "standard": {
            "model": "gpt-5",
            "max_turns": 50,
            "description": "Standard comprehensive review",
        },
        # ... more presets
    },
}
```

See `review_config.example.py` for examples.

## Running Reviews

### Basic Review

```bash
# Use default preset (standard)
python review_agent.py 970404
```

### Choose a Preset

```bash
# Quick review (faster, lower cost)
python review_agent.py 970404 --preset quick

# Thorough review (slower, higher quality)
python review_agent.py 970404 --preset thorough
```

### Override Model Directly

```bash
# Use specific model
python review_agent.py 970404 --model claude-opus-5
```

### Choose a Provider (Claude or OpenAI)

```bash
# Claude (default) — needs ANTHROPIC_API_KEY
python review_agent.py 970404

# OpenAI — needs OPENAI_API_KEY
export OPENAI_API_KEY=your-api-key
python review_agent.py 970404 --provider openai

# OpenAI against a custom endpoint (Azure / OpenAI-compatible / proxy)
python review_agent.py 970404 --provider openai --openai-base-url https://your-endpoint/v1
```

### Check Available Presets

```bash
python review_agent.py --list-presets
```

## Common Workflows

### Minor Changes (Docs, Small Fixes)

```bash
python review_agent.py 970404 --preset quick
```

### Standard Code Review

```bash
python review_agent.py 970404
# or explicitly:
python review_agent.py 970404 --preset standard
```

### Critical Changes (Security, Backports)

```bash
python review_agent.py 970404 --preset thorough
```

### Custom Gerrit Host

```bash
python review_agent.py 970404 --gerrit-host review.example.com
```

### Custom Output Directory

```bash
python review_agent.py 970404 --output-dir ./reviews
```

## Environment Variables

Set defaults without command-line flags:

```bash
# Set default preset
export AGENT_PRESET=thorough
python review_agent.py 970404

# Set default model
export AGENT_MODEL=claude-opus-5
python review_agent.py 970404

# Set model reasoning effort
export AGENT_EFFORT=high
python review_agent.py 970404

# Combine with other settings
export AGENT_PRESET=standard
export GERRIT_HOST=review.example.com
python review_agent.py 970404
```

## Troubleshooting

### "No module named 'anthropic'"

```bash
pip install anthropic claude-agent-sdk
```

### "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY=your-api-key
```

### "Model not available" or "Permission denied"

Your enterprise plan doesn't include that model. Run detection:

```bash
python detect_models.py
```

### Review Fails or Hits Turn Limit

Try a preset with more turns or a better model:

```bash
# More turns
python review_agent.py 970404 --preset thorough

# Better model
python review_agent.py 970404 --model claude-opus-5
```

## What Gets Reviewed

The agent will:

1. **Fetch the change** from Gerrit
2. **Analyze previous comments** from other reviewers
3. **Check if feedback was addressed**
4. **Review code quality**
   - HACKING.rst compliance
   - Import order
   - Logging patterns
   - Security issues
5. **Check tests**
   - Test coverage
   - Test structure
6. **Review database changes**
   - Migrations
   - Model compatibility
7. **Check API changes**
   - Versioning
   - Backward compatibility
8. **Generate comprehensive report**
   - REVIEW_<number>.md with findings

## Output

The review generates `REVIEW_<number>.md` with:

- Summary
- Previous review feedback status
- Code quality issues
- Testing analysis
- Security assessment
- Recommendation (Approve/Needs Work/Reject)

## Next Steps

- Read [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) for advanced configuration
- See [README.md](README.md) for detailed feature list
- Check [CHANGELOG.md](CHANGELOG.md) for version history
- Review [reference.md](reference.md) for OpenStack coding standards

## Tips

1. **Use quick preset** for documentation changes
2. **Use standard preset** for most code reviews (default)
3. **Use thorough preset** for security or complex changes
4. **Monitor costs** if your plan has token limits
5. **Check previous comments** - the agent will verify if they were addressed
