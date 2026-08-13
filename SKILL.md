---
name: openstack-review
description: Review OpenStack Gerrit changes for code quality, correctness, and OpenStack best practices
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebFetch, Write
---

# OpenStack Code Review Skill

Review OpenStack Gerrit change $ARGUMENTS for code quality, compliance with OpenStack standards, and correctness.

All helper scripts are in the skill directory. Set it once:
```bash
SKILL_DIR="${SKILL_DIR:-$HOME/.claude/skills/openstack-review}"
```

## Review Process

### 1. Fetch the Change

```bash
python3 ${SKILL_DIR}/gerrit_review.py fetch $ARGUMENTS
```

### 2. Fetch Previous Review Comments

```bash
python3 ${SKILL_DIR}/gerrit_review.py comments $ARGUMENTS
```

The script outputs filtered human comments, inline comments, review scores, and flags concerns from previous patchsets. Use this to verify whether prior feedback has been addressed.

### 3. Analyze the Changes

```bash
git show --stat
git show HEAD
```

### 4. Verify Previous Feedback Has Been Addressed

Using the comments output from step 2:

1. **Check each comment from previous patchsets** — identify issues needing fixes, -1 votes, unresolved discussions
2. **Verify fixes in current patchset** — check if flagged files were updated, tests added, docs updated
3. **If issues remain unaddressed** — note them in the review report and consider -1

### 5. Code Quality Checks

**Do NOT run linters, test suites, or security scanners** (pep8, pylint, bandit, pytest, tox, etc.) — CI already handles all automated checks. This step is a **manual code review**: read the diff and assess the changes against these criteria:

#### a. HACKING.rst Compliance

Check the project's HACKING.rst. Common standards:

- **Import Order**: stdlib, third-party, project
- **Logging**: `LOG.warning()` not `LOG.warn()`, no `_()` around logs, DO translate exception messages
- **JSON**: Use `oslo_serialization.jsonutils` instead of `json`
- **Line Continuation**: Parentheses, not backslashes
- **Mutable Defaults**: No mutable default arguments
- **TaskFlow Reverts**: Must accept `**kwargs`

#### b. Test Coverage

- New features should have unit tests — check if test files were added/modified
- Bug fixes should include a test for the fixed behavior
- Test tree should mirror code structure: `<project>/common/utils.py` → `<project>/tests/unit/common/test_utils.py`

#### c. Database Changes

- Schema changes need an Alembic migration
- Model updates must be compatible with existing data
- Verify proper use of oslo.db utilities

#### d. API Changes

- API changes must be versioned
- Verify input validation
- Don't break existing API contracts
- Check for microversions if applicable

#### e. Configuration Changes

- New config options need proper `oslo.config` definitions
- If new options are added, check that sample config generation would pick them up

#### f. Security

- All user inputs must be validated
- Use SQLAlchemy ORM, not raw SQL
- Sanitize inputs to shell commands
- No hardcoded credentials
- Check certificate validation is not disabled

### 6. Review Commit Message

Required format:
```
Short summary (50 chars max, no period)

Longer description explaining what and why (not how).
Wrap at 72 characters.

Closes-Bug: #XXXXXX
Implements: blueprint name-of-blueprint
Change-Id: IXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 7. Backport Review

If the change targets a `stable/*` or `unmaintained/*` branch, or the commit message contains `(cherry picked from commit <sha>)`, it is a backport. Follow the backport-specific review **instead of** the full code-quality review in step 5.

#### a. Compare with the Original Commit

Extract the SHA from the `(cherry picked from commit <sha>)` line, then:

```bash
python3 ${SKILL_DIR}/gerrit_review.py backport-compare <original_sha>
```

The script diffs the original against the backport and checks for documented conflicts.

#### b. Backport Policy

Backports to stable branches must comply with the [OpenStack Stable Branch Policy](https://docs.openstack.org/project-team-guide/stable-branches.html). Reject if it introduces:

| Forbidden in backports | Why |
|---|---|
| New features | Stable branches are bug-fix only |
| Database schema changes | Risk of data loss or upgrade breakage |
| Config option changes that alter defaults | Deployers expect stable defaults |
| API changes | Consumers depend on stable contracts |
| New or bumped dependencies | Stability and packaging constraints |
| Large refactors | High risk, not appropriate for stable |

Minor adaptations are acceptable only when strictly necessary for a clean cherry-pick and documented in `Conflicts:`.

#### c. What to Check

- **Conflict resolution correctness**: resolved code must match the original intent
- **Test applicability**: do backported tests pass? Are any missing due to stable branch differences?
- **Release note**: normally not needed unless the fix was not release-noted on main
- **Commit message**: must include `(cherry picked from commit …)`

### 8. Generate Review Report

Create `REVIEW_${REVIEW_NUM}.md` with:

1. **Summary**: What the change does
2. **Patchset History**: Current patchset, previous scores
3. **Previous Review Feedback**: Addressed vs unresolved issues
4. **Files Changed**
5. **Code Quality Issues**: HACKING.rst violations, style issues
6. **Testing**: Are tests present for new code? Coverage adequate? (CI runs the tests)
7. **Security Concerns**
8. **Performance Impact**
9. **Backward Compatibility**
10. **Documentation**
11. **Backport Assessment** (if applicable): Original SHA, differences, policy compliance
12. **Recommendation**:
    - ✅ **Approve** (+2/+1): Ready to merge
    - ⚠️ **Needs Work** (-1): Issues to address
    - ❌ **Reject** (-2): Major problems or backport policy violation

### 9. Additional Considerations

- **Design Principles**: Idempotent? Scalable? Follows project conventions?
- **Dependencies**: New deps in requirements.txt? Compatible with global-requirements? License OK?
- **Documentation**: Release note needed? (`reno new slug-name`)
- **Upgrade Impact**: Affects rolling upgrades?
- **Configuration**: New options properly defined with oslo.config?

## Example Usage

```
/openstack-review 970404
```
