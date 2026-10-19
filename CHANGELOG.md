# OpenStack Review Skill - Changelog

## Version 2.4 - Multi-Provider Support (Claude + OpenAI)

### New Features

**Multiple AI providers** - The review agent now supports two providers behind a
common abstraction (`src/openstack_review/providers/`):

- **claude** - via the Claude Agent SDK (unchanged behavior, still the default).
- **openai** - via the OpenAI Responses API, with a hand-written agentic loop and
  local tool implementations (Read/Write/Bash/Grep/Glob/WebFetch) that mirror the
  Claude Agent SDK's built-in tools, so the same `SKILL.md` workflow runs on both.

**Selecting a provider:**
```bash
# Claude (default)
openstack-review 997182

# OpenAI
export OPENAI_API_KEY=your-api-key
openstack-review --provider 997182 openai      # or REVIEW_PROVIDER=openai
```

**Custom OpenAI endpoint** - Point OpenAI at Azure / an OpenAI-compatible /
proxy / self-hosted endpoint:
```bash
openstack-review --provider openai --openai-base-url https://your-endpoint/v1 997182
# or: export OPENAI_BASE_URL=https://your-endpoint/v1
```

**OpenAI cost reporting** - The OpenAI API doesn't return a USD cost, so the
agent now derives it:
- If the endpoint is an OpenAI-compatible gateway that reports cost in a response
  header (e.g. litellm's `x-litellm-response-cost`), that value is used directly.
- Otherwise, cost is computed from token usage against the `OPENAI_PRICING` table
  in `review_config.py`, or from `--openai-price-input` / `--openai-price-output`
  (`OPENAI_PRICE_INPUT` / `OPENAI_PRICE_OUTPUT`) overrides.

**Configuration changes:**
- `review_config.py` presets are now organized by provider (`PRESETS[provider][preset]`)
  with a new `DEFAULT_PROVIDER` setting, plus an `OPENAI_PRICING` table.
- New `--provider` / `REVIEW_PROVIDER`, `--openai-base-url` / `OPENAI_BASE_URL`,
  `--max-turns`, and `--openai-price-input` / `--openai-price-output`.
- Provider SDKs are imported lazily — install only the one you use
  (`pip install openstack-review[openai]` or `[claude]`).

## Version 2.3 - Claude 4.x Model Support

### New Features

**Support for Claude 4.x Models** - Added support for latest Claude models:
- Claude Opus 4.8
- Claude Sonnet 4.6

These models are now included in:
- Detection script model lists (both Anthropic API and Vertex AI)
- Default presets in `review_config.py`
- Vertex AI example configuration
- Documentation

**Default Configuration Updated:**
- `quick`: claude-sonnet-4-6
- `standard`: claude-sonnet-4-6
- `thorough`: claude-opus-4-8

Run detection to find which models are available on your plan:
```bash
python detect_models.py --vertex --project YOUR_PROJECT
```

## Version 2.2 - Model Configuration System

### New Features

**Flexible Model Selection** - Added comprehensive model configuration system designed for enterprise plans with different model availability, including full Vertex AI support.

#### 1. Review Presets
Three built-in presets for different review scenarios:
- **quick**: Fast review for minor changes (Sonnet 4.5, 30 turns)
- **standard**: Comprehensive review for most changes (Sonnet 5, 50 turns)
- **thorough**: Deep review for critical changes (Opus 5, 75 turns)

#### 2. Multiple Configuration Options
- Command-line flags: `--preset` and `--model`
- Environment variables: `REVIEW_PRESET` and `REVIEW_MODEL`
- Configuration file: `review_config.py` for permanent customization
- Priority system: CLI > env vars > config defaults

#### 3. Enterprise Plan Support
- Easy customization via `review_config.py`
- Example configurations for common enterprise scenarios
- Graceful handling of unavailable models
- Documentation for adapting to plan-specific model availability

#### 4. Automatic Model Detection
- **detect_models.py**: New utility script to detect available models
- Supports both Anthropic API and Vertex AI
- Tests your API against common Claude model IDs
- Reports which models work on your enterprise plan
- Suggests optimized preset configuration
- Can automatically update review_config.py
- Handles enterprise plans with limited model access

**Anthropic API:**
```bash
# Detect available models
python detect_models.py

# Auto-update configuration
python detect_models.py --update-config
```

**Vertex AI:**
```bash
# Detect available models
python detect_models.py --vertex --project YOUR_PROJECT_ID

# Auto-update configuration
python detect_models.py --vertex --project YOUR_PROJECT_ID --update-config
```

#### 5. Vertex AI Support
Full support for Google Cloud's Vertex AI:
- Automatic detection of Vertex AI models
- Different model naming conventions (e.g., `claude-3-5-sonnet-v2@20241022`)
- Google Cloud authentication integration
- Region selection via environment variables
- Environment variables: `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`

**Usage:**
```bash
# Set environment variables
export CLAUDE_CODE_USE_VERTEX=1
export ANTHROPIC_VERTEX_PROJECT_ID=my-project
export CLOUD_ML_REGION=global

# Run review
openstack-review 970404
```

See [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md) for complete setup guide.

#### 6. New Files
- **review_config.py**: Model preset configuration (user-customizable)
- **review_config.example.py**: Example configurations for different plans
- **review_config_vertex.py**: Example Vertex AI configuration
- **detect_models.py**: Automatic model detection for both Anthropic API and Vertex AI
- **MODEL_CONFIGURATION.md**: Comprehensive configuration guide
- **VERTEX_AI_SETUP.md**: Complete Vertex AI setup guide

#### 7. Enhanced CLI
```bash
# Use presets
python review_agent.py 970404 --preset thorough

# Override model directly
python review_agent.py 970404 --model claude-opus-5

# List available presets
python review_agent.py --list-presets

# Environment variable control
REVIEW_PRESET=thorough python review_agent.py 970404
```

### Use Cases
1. **Enterprise plans**: Easily adapt to available models in your plan
2. **Cost control**: Choose appropriate model tier for each review
3. **Quality scaling**: Use thorough reviews for critical changes
4. **Flexibility**: Override on-the-fly without editing config files

### Files Added
- `review_config.py`: Configurable model presets
- `review_config.example.py`: Example configurations
- `MODEL_CONFIGURATION.md`: Configuration documentation

### Files Modified
- `review_agent.py`: Integrated model configuration system
- `README.md`: Added model selection usage examples

## Version 2.1 - Previous Comment Analysis

### New Features

**Automatic Previous Review Comment Analysis** - Major enhancement to track and verify reviewer feedback across patchsets.

#### 1. Comment Fetching and Analysis
- New section in SKILL.md to fetch previous review comments from Gerrit API
- Fetches all review messages, inline comments, and vote history
- Analyzes comments from all previous patchsets

#### 2. analyze_comments.py Script
New Python script that:
- Parses Gerrit review JSON data
- Extracts actionable issues from review messages
- Identifies patterns like "-1:", "please", "should", "needs", "missing"
- Categorizes comments by patchset
- Shows which reviewers commented and when
- Displays current review scores
- Highlights potential unaddressed issues from old patchsets

#### 3. Feedback Verification Process
Added critical step in review workflow:
- **Step 4: Verify Previous Feedback Has Been Addressed**
  - Check each comment from previous patchsets
  - Verify fixes in current patchset
  - Common unaddressed issues checklist
  - Guidance on handling unresolved feedback

#### 4. Enhanced Review Report
Updated report template to include:
- **Patchset History**: Current vs previous patchsets, review scores
- **Previous Review Feedback**: Summary of other reviewers' comments
- **Issues Addressed**: Which feedback has been handled
- **Issues Unresolved**: What still needs attention
- **Response to Previous Feedback**: Overall assessment

#### 5. Comprehensive Documentation
Added to reference.md:
- **Checking Previous Review Comments** section
- Why this matters
- How to check previous comments
- Common scenarios (tests requested, docs requested, security issues, refactoring)
- Red flags for unaddressed comments
- Example review comments for unaddressed feedback

### Use Cases

This feature helps with:
1. **Avoiding duplicate reviews**: See what others already found
2. **Tracking progress**: Verify author addressed feedback
3. **Collaborative reviewing**: Build on other reviewers' work
4. **Quality assurance**: Ensure nothing slips through
5. **Reviewer accountability**: Author must respond to all feedback

### Example Workflow

```bash
/openstack-review 970404

# Skill now:
# 1. Fetches review 970404
# 2. Downloads all review history
# 3. Shows previous comments: "Alice asked for tests in PS3"
# 4. Checks current code: "Tests are now present in PS9"
# 5. Verifies: ✓ Alice's feedback addressed
# 6. Continues with normal review
# 7. Reports: "All previous feedback addressed, code looks good +1"
```

### Files Added
- `analyze_comments.py`: Comment analysis script

### Files Modified
- `SKILL.md`: Added step 2 (Fetch Previous Review Comments) and step 4 (Verify Previous Feedback)
- `reference.md`: Added comprehensive section on checking previous comments
- `README.md`: Updated features list and example workflow
- `CHANGELOG.md`: This file

## Version 2.0 - Generic OpenStack Support

### Major Changes

Made the skill generic to work with all OpenStack projects, not just Octavia.

### Key Updates

#### 1. Automatic Project Detection
- Reads project name from `.gitreview` file
- Extracts Gerrit host from `.gitreview`
- Works with any OpenStack project (Nova, Neutron, Cinder, Keystone, etc.)

#### 2. fetch_review.sh Script
**Before:**
```bash
# Hardcoded to openstack/octavia
git fetch https://review.opendev.org/openstack/octavia refs/changes/...
```

**After:**
```bash
# Reads from .gitreview
PROJECT=$(grep "^project=" .gitreview | cut -d= -f2 | sed 's/\.git$//')
GERRIT_HOST=$(grep "^host=" .gitreview | cut -d= -f2)
git fetch https://${GERRIT_HOST}/${PROJECT} refs/changes/...
```

#### 3. Documentation Updates

All references to specific Octavia paths changed to generic placeholders:
- `octavia/api/v2/` → `<project>/api/v2/` or "check project's API structure"
- `octavia/tests/unit/` → `<project>/tests/unit/`
- `octavia/db/models.py` → `<project>/db/models.py` or "check project structure"

#### 4. Project-Specific Guidance

Added notes about project variations:
- Coverage requirements (Octavia ≥92%, may vary)
- API validation methods (WSME, JSON Schema, etc.)
- Database patterns (repository pattern vs direct ORM)
- TaskFlow usage (not all projects use it)

### Backward Compatibility

✅ Fully backward compatible with Octavia
✅ Works with existing workflows
✅ Same skill invocation: `/openstack-review <review-number>`

### Testing

Tested with:
- ✅ Octavia project (.gitreview: `openstack/octavia.git`)
- ✅ Script extracts project correctly
- ✅ Script extracts Gerrit host correctly
- ✅ Documentation is project-agnostic

### Migration Guide

#### For Individual Projects
No action needed - skill already works in `.claude/skills/openstack-review/`

#### For Global Installation
To use across all OpenStack projects:
```bash
cp -r .claude/skills/openstack-review ~/.claude/skills/
```

Then use from any OpenStack project directory:
```bash
cd ~/devel/nova
/openstack-review 123456

cd ~/devel/neutron
/openstack-review 789012
```

### Supported Projects

Any OpenStack project with:
- `.gitreview` file in repository root
- Gerrit-based workflow
- Standard tox environments (py3, pep8, cover)

Examples:
- Nova (compute)
- Neutron (networking)
- Octavia (load balancer)
- Cinder (block storage)
- Keystone (identity)
- Glance (image)
- Heat (orchestration)
- And all other OpenStack projects!

## Version 1.0 - Initial Release

- Octavia-specific code review skill
- Automated fetching from Gerrit
- Code quality checks
- Security analysis
- Test validation
- Comprehensive reporting
