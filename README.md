# OpenStack Review Skill

A comprehensive Claude Code skill for reviewing OpenStack Gerrit changes with automated checks and best practices.

## Features

- **Automated Fetch**: Fetches reviews from OpenStack Gerrit automatically
- **Previous Comment Analysis**: Fetches and analyzes comments from other reviewers on previous patchsets
- **Feedback Verification**: Checks if issues raised in previous patchsets have been addressed
- **Code Quality Analysis**: Checks for HACKING.rst compliance and OpenStack coding standards
- **Security Review**: Identifies common security issues (SQL injection, command injection, etc.)
- **Test Coverage**: Validates test structure and coverage requirements
- **Database Changes**: Reviews migrations, repository pattern usage, and model changes
- **API Compatibility**: Checks for breaking changes and versioning issues
- **Performance Analysis**: Identifies N+1 queries and other performance issues
- **Comprehensive Reporting**: Generates detailed markdown review reports with feedback tracking

## Installation

### As a Python Package (Recommended)

```bash
# Install from source
git clone https://github.com/yourusername/openstack-review-claude-skill.git
cd openstack-review-claude-skill
pip install .

# Or install in development mode
pip install -e .
```

After installation, the commands are available globally:
- `openstack-review` - Run code reviews
- `detect-models` - Detect available Claude models
- `gerrit-review` - Gerrit operations (fetch, comments, backport-compare)

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

### As a Claude Code Skill

This also works as a Claude Code skill for any OpenStack project that uses Gerrit for code review.

### Detect Available Models (First Time Setup)

If you're on an enterprise plan, detect which Claude models are available:

**For Anthropic API:**
```bash
# Detect available models and get preset suggestions
python detect_models.py

# Automatically update review_config.py with detected models
python detect_models.py --update-config
```

**For Vertex AI (Google Cloud):**
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Detect available models
python detect_models.py --vertex --project YOUR_PROJECT_ID

# Automatically update review_config.py
python detect_models.py --vertex --project YOUR_PROJECT_ID --update-config
```

See [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md) for complete Vertex AI setup instructions.

This will test your API against common Claude models and suggest an optimized configuration.

### For a Specific Project

The skill is already available in this repository at `.claude/skills/openstack-review/`.

### For All Projects

To use this skill across all OpenStack projects, copy it to your global skills directory:

```bash
cp -r .claude/skills/openstack-review ~/.claude/skills/
```

## Usage

### Basic Usage

```bash
/openstack-review 970404
```

This will:
1. Fetch review 970404 from Gerrit
2. **Fetch and analyze previous review comments from other reviewers**
3. **Check if previous feedback has been addressed**
4. Analyze all code changes
5. Run code quality checks
6. Generate a comprehensive review report including feedback tracking

### Direct Script Usage with Model Selection

```bash
# Standard review (default)
python review_agent.py 970404

# Quick review for minor changes
python review_agent.py 970404 --preset quick

# Thorough review for critical changes
python review_agent.py 970404 --preset thorough

# Use specific model
python review_agent.py 970404 --model claude-opus-5

# List available presets (grouped by provider)
python review_agent.py --list-presets
```

### Choosing an AI Provider (Claude or OpenAI)

The agent supports two providers. **claude** (via the Claude Agent SDK) is the
default; **openai** (via the OpenAI Responses API) is opt-in.

```bash
# Claude (default) — needs ANTHROPIC_API_KEY (or Vertex AI env vars)
export ANTHROPIC_API_KEY=your-api-key
python review_agent.py 970404

# OpenAI — needs OPENAI_API_KEY
export OPENAI_API_KEY=your-api-key
python review_agent.py 970404 --provider openai
python review_agent.py 970404 --provider openai --preset thorough
python review_agent.py 970404 --provider openai --model gpt-5

# OpenAI against a custom endpoint (Azure / OpenAI-compatible / proxy / self-hosted)
python review_agent.py 970404 --provider openai --openai-base-url https://your-endpoint/v1
```

Equivalent environment variables: `REVIEW_PROVIDER=openai` and
`OPENAI_BASE_URL=https://your-endpoint/v1`. Install only the provider you need:
`pip install openstack-review[openai]` or `pip install openstack-review[claude]`.

See [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) for detailed model configuration options, especially for enterprise plans with different model availability.

### Manual Fetch (Alternative)

You can also use the helper script directly:

```bash
# Set SKILL_DIR based on where the skill is installed
SKILL_DIR="${SKILL_DIR:-$HOME/.claude/skills/openstack-review}"

# Fetch the review
${SKILL_DIR}/fetch_review.sh 970404
```

Or use the direct path for your installation:
```bash
# Global install (default):
~/.claude/skills/openstack-review/fetch_review.sh 970404

# Project-specific install:
./.claude/skills/openstack-review/fetch_review.sh 970404
```

## What Gets Checked

### Previous Review Feedback
- Fetches all comments from previous patchsets
- Identifies issues marked by other reviewers (-1 votes, requests, questions)
- Verifies that requested changes have been made
- Checks if reviewers' questions have been answered
- Flags unaddressed feedback

### Code Quality
- Import order (stdlib, third-party, project)
- Logging patterns (LOG.warning vs LOG.warn, no translation)
- JSON module usage (jsonutils vs json)
- Line continuation (parentheses vs backslashes)
- Mutable default arguments
- TaskFlow revert signatures

### Testing
- Test structure mirrors code structure
- Coverage ≥92%
- Bug fixes have regression tests
- New features have unit tests

### Database
- Migrations for schema changes
- Repository pattern usage
- Model compatibility

### API
- Versioning
- Type validation
- Backward compatibility
- Documentation updates

### Security
- SQL injection prevention
- Command injection prevention
- Path traversal prevention
- Secrets in code
- TLS/SSL validation

### Performance
- N+1 query detection
- Eager loading usage
- Pagination for large datasets

## Review Output

The skill generates a markdown report (`REVIEW_<number>.md`) containing:

1. **Summary**: What the change does
2. **Files Changed**: List of modified files with statistics
3. **Code Quality Issues**: HACKING.rst violations and style issues
4. **Testing Analysis**: Test coverage and adequacy
5. **Security Assessment**: Potential security concerns
6. **Performance Impact**: Performance considerations
7. **Compatibility**: Breaking changes analysis
8. **Documentation**: Documentation updates needed
9. **Recommendation**: Approve/Needs Work/Reject with reasoning

## Review Workflow

1. **Fetch** the review from Gerrit
2. **Analyze** code changes automatically
3. **Run** automated checks (pep8, tests, coverage)
4. **Generate** comprehensive review report
5. **Post** feedback on Gerrit or share with team

## Example Review Process

```bash
# Invoke the skill
/openstack-review 970404

# Claude will:
# 1. Fetch the review from Gerrit
# 2. Download review history and comments
# 3. Analyze previous reviewer feedback
# 4. Show commit details
# 5. Verify if previous issues were addressed
# 6. Analyze current code changes
# 7. Run tox environments
# 8. Check for common issues
# 9. Generate REVIEW_970404.md with feedback tracking

# Review the generated report
cat REVIEW_970404.md

# The report will include:
# - Previous patchset comments
# - Which issues were addressed
# - Which issues remain open
# - Your new review findings

# Use the report to post feedback on Gerrit
```

## Files in This Skill

- **SKILL.md**: Main skill instructions and workflow
- **reference.md**: Detailed reference for common issues and examples
- **review_agent.py**: Main agent script with Claude Agent SDK integration (supports Anthropic API and Vertex AI)
- **review_config.py**: Model preset configuration (customize for your enterprise plan)
- **review_config.example.py**: Example configurations for different enterprise plans
- **review_config_vertex.py**: Example Vertex AI configuration
- **detect_models.py**: Automatic model detection script (supports both Anthropic API and Vertex AI)
- **gerrit_review.py**: Unified CLI for Gerrit operations (fetch, comments, backport-compare)
- **MODEL_CONFIGURATION.md**: Detailed guide for customizing models and presets
- **VERTEX_AI_SETUP.md**: Complete Vertex AI setup guide
- **QUICKSTART.md**: Quick start guide
- **README.md**: This file
- **CHANGELOG.md**: Version history and updates

## Requirements

- Git repository with an OpenStack project
- `.gitreview` file in the repository root
- Access to the Gerrit host (typically review.opendev.org)
- Python 3 with tox installed
- curl for API access

## Supported Projects

This skill works with any OpenStack project that has:
- A `.gitreview` file
- Gerrit-based code review workflow
- Standard OpenStack project structure (tox, tests, etc.)

Examples: Nova, Neutron, Octavia, Cinder, Keystone, Glance, Heat, etc.

## Tips

### Review Large Changes

For large changes (like performance optimizations), focus on:
1. High-level architecture changes
2. Critical paths (hot code paths)
3. Test coverage for new logic
4. Performance benchmark results
5. Backward compatibility

### Review Bug Fixes

For bug fixes, verify:
1. Root cause analysis in commit message
2. Test that reproduces the bug
3. Test passes with the fix
4. No unintended side effects
5. Appropriate bug reference (Closes-Bug: #XXXXXX)

### Review API Changes

For API changes, check:
1. Versioning strategy
2. Input validation
3. Error handling
4. Documentation updates
5. API reference updates
6. Backward compatibility

## References

- [OpenStack Contributor Guide](https://docs.openstack.org/contributors/)
- [Code Review Guidelines](https://docs.openstack.org/contributors/code-and-documentation/code-review.html)
- [Commit Message Guidelines](https://wiki.openstack.org/wiki/GitCommitMessages)
- [Project Documentation](https://docs.openstack.org/) - Find your project's docs
- HACKING.rst - Check your project's root directory for coding standards

## Troubleshooting

### Can't Fetch Review

If `git fetch` fails:
- Verify `.gitreview` file exists in repository root
- Check network connectivity to the Gerrit host
- Verify the review number is correct
- Try accessing the review in browser: `https://<gerrit-host>/c/<project>/+/<review-number>`
- Check that the project name in `.gitreview` is correct

### Tox Failures

If tox commands fail:
- Ensure tox is installed: `pip install tox`
- Check Python version compatibility
- Verify all dependencies are installed

### Permission Issues

If permission denied on scripts:
- Make scripts executable: `chmod +x .claude/skills/openstack-review/*.sh`

## Contributing

To improve this skill:
1. Edit SKILL.md for workflow changes
2. Update reference.md for new examples
3. Enhance fetch_review.sh for better automation
4. Add new checks and patterns as needed

## License

This skill follows the same license as the Octavia project (Apache License 2.0).
