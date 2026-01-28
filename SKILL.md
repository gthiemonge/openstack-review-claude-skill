---
name: openstack-review
description: Review OpenStack Gerrit changes for code quality, correctness, and OpenStack best practices
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebFetch, Write
---

# OpenStack Code Review Skill

Review OpenStack Gerrit change $ARGUMENTS for code quality, compliance with OpenStack standards, and correctness.

## Review Process

### 1. Fetch the Change

If not already checked out, fetch the review using the helper script:

```bash
# Use the helper script which reads project info from .gitreview
./.claude/skills/openstack-review/fetch_review.sh $ARGUMENTS
```

Or manually:

```bash
# Extract project from .gitreview
PROJECT=$(grep "^project=" .gitreview | cut -d= -f2 | sed 's/\.git$//')
GERRIT_HOST=$(grep "^host=" .gitreview | cut -d= -f2)
PROJECT_ENCODED=$(echo "$PROJECT" | sed 's/\//%2F/g')

REVIEW_NUM=$ARGUMENTS
LAST_TWO=$(printf "%02d" $((REVIEW_NUM % 100)))

# Get latest patchset
PATCHSET=$(curl -s "https://${GERRIT_HOST}/changes/${PROJECT_ENCODED}~${REVIEW_NUM}/detail" | tail -n +2 | python3 -c "import sys, json; print(json.load(sys.stdin)['current_revision_number'])")

# Fetch and checkout
git fetch https://${GERRIT_HOST}/${PROJECT} refs/changes/${LAST_TWO}/${REVIEW_NUM}/${PATCHSET}
git checkout FETCH_HEAD
```

### 2. Fetch Previous Review Comments

Before analyzing the code, check what feedback other reviewers have already given:

1. **Fetch review metadata and comments:**
   ```bash
   # Extract project info
   PROJECT=$(grep "^project=" .gitreview | cut -d= -f2 | sed 's/\.git$//')
   GERRIT_HOST=$(grep "^host=" .gitreview | cut -d= -f2)
   PROJECT_ENCODED=$(echo "$PROJECT" | sed 's/\//%2F/g')
   REVIEW_NUM=$ARGUMENTS

   # Get all review data including comments
   curl -s "https://${GERRIT_HOST}/changes/${PROJECT_ENCODED}~${REVIEW_NUM}/detail?o=ALL_REVISIONS&o=ALL_COMMITS&o=ALL_FILES&o=MESSAGES&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS" | tail -n +2 > /tmp/review_${REVIEW_NUM}.json

   # Parse and display key information
   python3 << 'EOF'
   import json
   import sys

   with open('/tmp/review_${REVIEW_NUM}.json') as f:
       review = json.load(f)

   print("=" * 80)
   print(f"Review #{review['_number']}: {review['subject']}")
   print(f"Author: {review['owner']['name']} <{review['owner']['email']}>")
   print(f"Status: {review['status']}")
   print(f"Current revision: {review['current_revision_number']}")
   print("=" * 80)

   # Show review messages (comments from reviewers)
   if 'messages' in review:
       print("\n### REVIEW COMMENTS FROM PREVIOUS PATCHSETS ###\n")
       for msg in review['messages']:
           print(f"Patchset {msg.get('_revision_number', 'N/A')} - {msg['author'].get('name', 'Unknown')} ({msg['date']}):")
           print(f"  {msg['message']}")
           print()

   # Show current scores
   if 'labels' in review:
       print("\n### CURRENT SCORES ###")
       for label, data in review['labels'].items():
           if 'all' in data:
               print(f"\n{label}:")
               for vote in data['all']:
                   value = vote.get('value', 0)
                   if value != 0:
                       print(f"  {vote['name']}: {value:+d}")
   EOF
   ```

2. **Fetch inline comments on specific files:**
   ```bash
   # Get comments for each patchset
   for ps in $(seq 1 $(curl -s "https://${GERRIT_HOST}/changes/${PROJECT_ENCODED}~${REVIEW_NUM}/detail" | tail -n +2 | python3 -c "import sys, json; print(json.load(sys.stdin)['current_revision_number'])")); do
       echo "=== Patchset $ps Comments ==="
       curl -s "https://${GERRIT_HOST}/changes/${PROJECT_ENCODED}~${REVIEW_NUM}/revisions/$ps/comments" | tail -n +2 | python3 -m json.tool 2>/dev/null || echo "No inline comments"
   done
   ```

### 3. Analyze the Changes

Run the following analysis:

1. **Get commit details:**
   ```bash
   git show --stat
   git show --format=fuller
   ```

2. **List modified files:**
   ```bash
   git diff --name-only HEAD~1
   git diff --stat HEAD~1
   ```

3. **Review the actual changes:**
   ```bash
   git show HEAD
   ```

### 4. Verify Previous Feedback Has Been Addressed

**CRITICAL**: Review all previous comments from other reviewers:

1. **Check each comment from previous patchsets:**
   - Read through all review messages
   - Identify issues marked as needing fixes
   - Look for -1 votes with specific concerns
   - Note any unresolved discussions

2. **Verify fixes in current patchset:**
   - For each issue raised, check if it's been addressed in the current code
   - Look for changes in files that were previously criticized
   - Verify test additions if tests were requested
   - Check documentation updates if docs were requested

3. **Common unaddressed issues to watch for:**
   - Reviewer asked for tests → Are they added?
   - Reviewer asked for documentation → Is it updated?
   - Reviewer pointed out security issue → Is it fixed?
   - Reviewer suggested refactoring → Was it done?
   - Reviewer asked questions → Are they answered in code or commit message?

4. **If issues remain unaddressed:**
   - Note them in your review report
   - Consider giving -1 with reference to the unaddressed feedback
   - Ask the author to respond to previous comments

### 5. Code Quality Checks

Review the changes for OpenStack-specific requirements:

#### a. HACKING.rst Compliance

Check the project's HACKING.rst file for project-specific rules. Common OpenStack standards:

- **Import Order**: Check that imports follow OpenStack ordering (stdlib, third-party, project)
- **Logging**:
  - Use `LOG.warning()` not `LOG.warn()`
  - Don't translate log messages (no `_()` around logs)
  - DO translate exception messages
- **JSON**: Use `oslo_serialization.jsonutils` instead of `json` module
- **Line Continuation**: No backslashes for line continuation (use parentheses)
- **Mutable Defaults**: Method default arguments shouldn't be mutable
- **TaskFlow Reverts**: TaskFlow revert methods must accept `**kwargs` (if project uses TaskFlow)

#### b. Test Coverage

- **Unit Tests Required**: All new features must have unit tests
- **Bug Fix Tests**: Bug fixes must include a test that fails without the fix
- **Test Structure**: Test tree must mirror code structure
  - Code: `<project>/common/utils.py` → Test: `<project>/tests/unit/common/test_utils.py`
- Run structure validator if available: `./tools/check_unit_test_structure.sh`
- Check project's test requirements (often ≥92% coverage for Octavia, may vary by project)

#### c. Database Changes

- **Migration Required**: Schema changes need an Alembic migration (location varies by project, typically `<project>/db/migration/`)
- **Repository Pattern**: Check if project uses repository pattern for DB access
- **Model Updates**: Changes to DB models must be compatible with existing data
- **Oslo.db**: Verify proper use of oslo.db utilities

#### d. API Changes

- **Versioning**: API changes must be versioned (check project's API structure)
- **Type Validation**: Verify input validation (may use WSME, JSON Schema, or other frameworks)
- **Backward Compatibility**: Don't break existing API contracts
- **Documentation**: Update API reference docs
- **Microversions**: Check if project uses API microversions

#### e. Configuration Changes

- **oslo.config**: New config options need proper definitions
- **Sample Config**: Run `tox -e genconfig` to update sample config
- **Documentation**: Document new options in appropriate RST files

#### f. Security

- **Input Validation**: All user inputs must be validated
- **SQL Injection**: Use SQLAlchemy ORM, not raw SQL
- **Command Injection**: Sanitize inputs to shell commands
- **Secrets**: No hardcoded credentials or secrets
- **TLS/SSL**: Check certificate validation is not disabled

### 6. Run Automated Checks

Execute the following tox environments:

1. **Linting:**
   ```bash
   tox -e pep8
   ```

2. **Unit Tests:**
   ```bash
   tox -e py3
   ```

3. **Affected Tests:** If you can identify specific affected tests, run them:
   ```bash
   tox -e py3 <project>.tests.unit.path.to.test_module
   ```

4. **Coverage Check:**
   ```bash
   tox -e cover
   # Check project requirements (coverage thresholds vary by project)
   ```

### 7. Review Commit Message

Check that the commit message follows OpenStack format:

```
Short summary (50 chars max, no period)

Longer description explaining what and why (not how).
Wrap at 72 characters.

Can have multiple paragraphs.

Closes-Bug: #XXXXXX
Implements: blueprint name-of-blueprint
Change-Id: IXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Required elements:
- Clear, descriptive summary
- Detailed explanation in body
- References to bugs/blueprints if applicable
- `Change-Id` footer (added by git-review commit hook)
- `Signed-off-by` if present

### 8. Generate Review Report

Create a markdown report with:

1. **Summary**: What the change does
2. **Patchset History**:
   - Current patchset number
   - Number of previous patchsets
   - Previous review scores
3. **Previous Review Feedback**:
   - Summary of comments from other reviewers
   - Which issues have been addressed
   - Which issues remain unresolved
   - Any unanswered questions from reviewers
4. **Files Changed**: List of modified files
5. **Code Quality Issues**: Any HACKING.rst violations or style issues found
6. **Testing**:
   - Are there tests?
   - Do tests pass?
   - Is coverage adequate?
   - Were tests added per previous reviewer requests?
7. **Security Concerns**: Any security issues identified
8. **Performance Impact**: Any performance considerations
9. **Backward Compatibility**: Breaking changes?
10. **Documentation**: Is documentation updated/needed?
11. **Response to Previous Feedback**: Did the author address all previous comments?
12. **Recommendation**:
   - ✅ **Approve** (+2/+1): Ready to merge, all feedback addressed
   - ⚠️ **Needs Work** (-1): Issues to address (list specific items including unaddressed previous feedback)
   - ❌ **Reject** (-2): Major problems

### 9. Additional Considerations

- **Design Principles**: Check project-specific design principles (see project documentation)
  - Is it idempotent?
  - Is it scalable and resilient?
  - Does it follow project conventions?
- **Dependencies**: Any new dependencies added? Are they in requirements.txt?
  - Check for conflicts with global-requirements
  - Verify license compatibility
- **Documentation**: Should this have a release note? (`reno new slug-name`)
- **Upgrade Impact**: Does this affect rolling upgrades?
- **Configuration**: New config options properly defined with oslo.config?

## Example Usage

```
/openstack-review 970404
```

This will fetch review 970404, analyze it, run checks, and generate a comprehensive review report.

## Output Format

The review should produce a detailed markdown report saved as `REVIEW_${REVIEW_NUM}.md` that can be used to:
- Post feedback on Gerrit
- Track review progress
- Share with other reviewers
- Document review decisions
