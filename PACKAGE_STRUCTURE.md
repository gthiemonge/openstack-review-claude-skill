# Package Structure

This document explains the Python package structure for openstack-review.

## Directory Layout

```
openstack-review-claude-skill/
├── src/
│   └── openstack_review/          # Main package
│       ├── __init__.py             # Package initialization
│       ├── review_agent.py         # Main review agent
│       ├── detect_models.py        # Model detection script
│       ├── gerrit_review.py        # Gerrit operations CLI
│       ├── review_config.py        # Configuration module
│       ├── review_config_vertex.py # Vertex AI config example
│       ├── SKILL.md -> ../../SKILL.md        # Symlink to skill file
│       └── reference.md -> ../../reference.md # Symlink to reference
├── pyproject.toml                  # Package metadata (PEP 621)
├── setup.py                        # Backward compatibility
├── MANIFEST.in                     # Data files to include
├── requirements.txt                # Dependencies
├── README.md                       # Main documentation
├── INSTALL.md                      # Installation guide
├── CHANGELOG.md                    # Version history
├── SKILL.md                        # Claude skill instructions
├── reference.md                    # OpenStack review reference
├── MODEL_CONFIGURATION.md          # Model config guide
├── VERTEX_AI_SETUP.md             # Vertex AI setup guide
├── QUICKSTART.md                   # Quick start guide
├── TROUBLESHOOTING.md             # Troubleshooting guide
├── Containerfile                   # Docker/Podman build
├── test_install.sh                 # Installation test script
└── .gitignore                      # Git ignore patterns
```

## Package Installation

### Development Mode

```bash
pip install -e .
```

Changes to source files are immediately reflected without reinstalling.

### Normal Installation

```bash
pip install .
```

Installs the package to your Python environment.

## Entry Points

The package provides three CLI commands (defined in `pyproject.toml`):

1. **`openstack-review`** - Main review agent
   - Entry point: `openstack_review.review_agent:main`
   - Usage: `openstack-review 970404 --preset thorough`

2. **`detect-models`** - Model detection
   - Entry point: `openstack_review.detect_models:main`
   - Usage: `detect-models --vertex --project YOUR_PROJECT`

3. **`gerrit-review`** - Gerrit operations
   - Entry point: `openstack_review.gerrit_review:main`
   - Usage: `gerrit-review fetch 970404`

## Package Data

Skill files (SKILL.md, reference.md) are included as package data via symlinks in `src/openstack_review/`. This ensures they're available both during development and after installation.

## Import Structure

### As an installed package

```python
import openstack_review
print(openstack_review.__version__)

from openstack_review import get_model_config, list_presets
config = get_model_config(preset='thorough')
```

### Module imports

```python
from openstack_review.review_agent import main as review_main
from openstack_review.detect_models import main as detect_main
from openstack_review.gerrit_review import main as gerrit_main
```

## Dependencies

Defined in `pyproject.toml`:

- **Required**: claude-agent-sdk, anthropic, google-auth, google-cloud-aiplatform
- **Optional [dev]**: pytest, black, ruff

## Building Distribution

```bash
# Install build tools
pip install build

# Build wheel and sdist
python -m build

# Install from wheel
pip install dist/openstack_review-2.3.0-py3-none-any.whl
```

## Docker/Container

The Containerfile now installs the package using pip:

```dockerfile
COPY pyproject.toml setup.py MANIFEST.in requirements.txt ./
COPY src/ ./src/
COPY SKILL.md reference.md ./
RUN pip install .
```

This ensures consistent behavior between local and containerized installations.

## Testing Installation

Run the test script:

```bash
./test_install.sh
```

This verifies:
1. Package imports correctly
2. CLI commands are available
3. Configuration functions work
4. Help output is accessible

## Migration from Old Structure

### Old (script-based)

```bash
python review_agent.py 970404
python detect_models.py --vertex --project X
```

### New (package-based)

```bash
openstack-review 970404
detect-models --vertex --project X
```

The old scripts are still in the repo root for backward compatibility, but the package installation is recommended.

## Versioning

Version is defined in:
- `src/openstack_review/__init__.py` (`__version__`)
- `pyproject.toml` (`project.version`)

These should be kept in sync.

## License

Apache License 2.0 - See LICENSE file
