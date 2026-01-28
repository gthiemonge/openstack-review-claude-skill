# OpenStack Review Skill - Changelog

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
