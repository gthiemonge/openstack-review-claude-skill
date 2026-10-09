# Installation Guide

## Installing as a Python Package

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/openstack-review-claude-skill.git
cd openstack-review-claude-skill

# Install in development mode (editable)
pip install -e .

# Or install normally
pip install .
```

### From PyPI (when published)

```bash
pip install openstack-review
```

## Verify Installation

```bash
# Check installed version
python -c "import openstack_review; print(openstack_review.__version__)"

# Verify CLI commands are available
openstack-review --help
detect-models --help
gerrit-review --help
```

## Post-Installation Setup

### 1. Configure Authentication

**For Anthropic API:**
```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

**For Vertex AI:**
```bash
gcloud auth application-default login
export CLAUDE_CODE_USE_VERTEX=1
export ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
export CLOUD_ML_REGION=global
```

### 2. Detect Available Models

```bash
# For Anthropic API
detect-models

# For Vertex AI
detect-models --vertex --project YOUR_PROJECT_ID
```

### 3. Run a Review

```bash
# Basic usage
openstack-review 970404

# With presets
openstack-review 970404 --preset thorough

# With Vertex AI (set environment variables)
export CLAUDE_CODE_USE_VERTEX=1
export ANTHROPIC_VERTEX_PROJECT_ID=YOUR_PROJECT
export CLOUD_ML_REGION=global
openstack-review 970404
```

## Uninstall

```bash
pip uninstall openstack-review
```

## Upgrade

```bash
# From source
cd openstack-review-claude-skill
git pull
pip install --upgrade .

# From PyPI (when published)
pip install --upgrade openstack-review
```

## Troubleshooting

### Command not found: openstack-review

The installation directory is not in your PATH. Either:

**Option 1: Add to PATH**
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Option 2: Use python -m**
```bash
python -m openstack_review.review_agent 970404
```

### Import errors

Reinstall with all dependencies:
```bash
pip install --force-reinstall openstack-review
```

### Missing SKILL.md errors

The package data wasn't installed correctly. Reinstall:
```bash
pip uninstall openstack-review
pip install .
```

## Development Installation

For development work:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest

# Format code
black src/
ruff check src/
```

## Docker Installation

See the Containerfile for containerized deployment:

```bash
docker build -t openstack-review .
docker run -it openstack-review openstack-review --help
```
