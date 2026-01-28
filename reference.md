# OpenStack Code Review Reference

This file provides additional reference information for reviewing OpenStack code.

## Checking Previous Review Comments

### Why This Matters

One of the most important aspects of code review is ensuring that feedback from previous reviewers has been addressed. Authors often upload multiple patchsets to fix issues, and it's critical to verify those fixes before approving.

### How to Check Previous Comments

1. **Fetch review metadata:**
   ```bash
   PROJECT=$(grep "^project=" .gitreview | cut -d= -f2 | sed 's/\.git$//')
   GERRIT_HOST=$(grep "^host=" .gitreview | cut -d= -f2)
   PROJECT_ENCODED=$(echo "$PROJECT" | sed 's/\//%2F/g')
   REVIEW_NUM=970404  # Your review number

   # Download review data
   curl -s "https://${GERRIT_HOST}/changes/${PROJECT_ENCODED}~${REVIEW_NUM}/detail?o=ALL_REVISIONS&o=MESSAGES&o=DETAILED_LABELS" | tail -n +2 > /tmp/review_${REVIEW_NUM}.json

   # Analyze comments
   python3 .claude/skills/openstack-review/analyze_comments.py /tmp/review_${REVIEW_NUM}.json
   ```

2. **Read the output carefully:**
   - Look for -1 votes with specific concerns
   - Note any requests for tests, documentation, or fixes
   - Check if questions were asked that need answers

3. **Verify in the current code:**
   - Open files that were criticized
   - Check if the issues are fixed
   - Verify tests were added if requested
   - Confirm documentation was updated if requested

### Common Scenarios

#### Scenario 1: Tests Were Requested

**Previous comment (Patchset 3):**
```
-1: This change needs unit tests for the new validate_config() function.
```

**What to check in current patchset (Patchset 5):**
```bash
# Search for new tests
git show | grep -A 10 "test_validate_config"

# Check if test file was modified
git diff --name-only HEAD~1 | grep test_
```

If tests are present → ✓ Issue addressed
If tests are missing → ⚠️ Issue NOT addressed, should remain -1

#### Scenario 2: Documentation Was Requested

**Previous comment (Patchset 2):**
```
-1: This adds a new config option but doesn't document it. Please update the config reference.
```

**What to check:**
```bash
# Check if config was regenerated
git diff --name-only HEAD~1 | grep "config"

# Check for new documentation
git diff --name-only HEAD~1 | grep -E "\.(rst|md)$"

# Check commit for genconfig run
git show | grep -i "genconfig\|sample.*config"
```

#### Scenario 3: Security Issue Was Raised

**Previous comment (Patchset 4):**
```
-2: This is vulnerable to SQL injection. Please use parameterized queries.
```

**What to check:**
```bash
# Review the vulnerable code in current patchset
git show | grep -B 5 -A 5 "execute\|query"

# Look for parameterized queries
git show | grep "session.query\|:param\|:id"
```

If still using string concatenation → ❌ BLOCK the review
If using parameterized queries → ✓ Issue addressed

#### Scenario 4: Refactoring Was Suggested

**Previous comment (Patchset 1):**
```
-1: This duplicates logic from utils.py. Please refactor to use the existing function.
```

**What to check:**
```bash
# Check if utils.py is being imported/used
git show | grep "from.*utils import\|utils\."

# Look for the duplicate code
git show | grep -A 20 "def.*function_name"
```

### Red Flags for Unaddressed Comments

🚩 **Author uploaded new patchset but didn't reply to comments**
   → They may have ignored feedback

🚩 **Same -1 vote on multiple patchsets**
   → Issue is recurring and not being fixed

🚩 **Questions from reviewers remain unanswered**
   → Author needs to clarify or explain

🚩 **Multiple reviewers raised the same concern**
   → This is a critical issue that must be addressed

### Example Review Comment

When you find unaddressed issues:

```
-1: Previous feedback has not been fully addressed.

In patchset 3, reviewer Alice pointed out that unit tests are missing
for the new validate_quota() function. I don't see these tests in the
current patchset.

Additionally, Bob asked about error handling in patchset 5, but this
question remains unanswered.

Please:
1. Add unit tests for validate_quota() as requested
2. Respond to Bob's question about error handling
3. Update the patchset once these are addressed

Once these items are resolved, I'll be happy to review again.
```

## Common Issues to Check

### 1. Import Order Violations

**Bad:**
```python
from octavia.common import utils
import json
import os
```

**Good:**
```python
import json
import os

from octavia.common import utils
```

Groups: stdlib, third-party, project (separated by blank lines)

### 2. Logging Issues

**Bad:**
```python
LOG.warn(_("User %(user)s failed") % {'user': user})  # Wrong: warn() and translation
```

**Good:**
```python
LOG.warning("User %s failed", user)  # Correct: warning() and no translation
```

**Exception messages (DO translate):**
```python
raise Exception(_("Invalid configuration"))
```

### 3. JSON Module Usage

**Bad:**
```python
import json
data = json.dumps(obj)
```

**Good:**
```python
from oslo_serialization import jsonutils
data = jsonutils.dumps(obj)
```

### 4. TaskFlow Revert Signatures

**Bad:**
```python
def revert(self, result):
    # Cleanup
```

**Good:**
```python
def revert(self, result, **kwargs):
    # Cleanup - **kwargs required for TaskFlow
```

### 5. Mutable Default Arguments

**Bad:**
```python
def process(self, items=[]):
    items.append('new')
```

**Good:**
```python
def process(self, items=None):
    items = items or []
    items.append('new')
```

### 6. Line Continuation

**Bad:**
```python
long_string = "This is a very long string that " \
              "spans multiple lines"
```

**Good:**
```python
long_string = ("This is a very long string that "
               "spans multiple lines")
```

## Security Review Checklist

### SQL Injection Prevention

**Bad:**
```python
query = "SELECT * FROM users WHERE id = %s" % user_id
session.execute(query)
```

**Good:**
```python
# Use ORM
user = session.query(models.User).filter_by(id=user_id).first()

# Or parameterized queries
session.execute("SELECT * FROM users WHERE id = :id", {'id': user_id})
```

### Command Injection Prevention

**Bad:**
```python
os.system("ping -c 1 " + ip_address)
```

**Good:**
```python
import subprocess
subprocess.run(['ping', '-c', '1', ip_address], check=True)
```

### Path Traversal Prevention

**Bad:**
```python
file_path = "/var/lib/octavia/" + user_provided_path
with open(file_path) as f:
    data = f.read()
```

**Good:**
```python
import os
base_dir = "/var/lib/octavia/"
safe_path = os.path.realpath(os.path.join(base_dir, user_provided_path))
if not safe_path.startswith(base_dir):
    raise ValueError("Invalid path")
with open(safe_path) as f:
    data = f.read()
```

## Database Review Checklist

### Migration Required?

Changes to database models typically need migrations:
- Look for files like `<project>/db/models.py` or similar
- Migration location varies: `<project>/db/migration/`, `<project>/db/migrations/`, etc.
- Typically uses Alembic for SQLAlchemy-based projects

### Repository Pattern

Some projects use repository pattern for database access. Check project conventions:

**Example (if repository pattern is used):**
```python
# Bad - Direct query
def get_resource(session, resource_id):
    return session.query(models.Resource).filter_by(id=resource_id).first()

# Good - Repository pattern
from <project>.db import repositories
repo = repositories.ResourceRepository()
resource = repo.get(session, id=resource_id)
```

## Testing Review Checklist

### Test Structure

Code and test paths must mirror each other:

| Code Path | Test Path |
|-----------|-----------|
| `<project>/common/utils.py` | `<project>/tests/unit/common/test_utils.py` |
| `<project>/api/v2/controllers/pool.py` | `<project>/tests/unit/api/v2/controllers/test_pool.py` |
| `<project>/controller/worker/tasks/database_tasks.py` | `<project>/tests/unit/controller/worker/tasks/test_database_tasks.py` |

### Test Coverage Requirements

- Check project-specific coverage requirements (varies by project)
  - Octavia requires ≥92%
  - Some projects may have different thresholds
- New code should have high coverage (aim for 100%)
- Bug fixes MUST include a test that reproduces the bug

### Test Types

1. **Unit Tests** (`<project>/tests/unit/`): Fast, isolated, mock external dependencies
2. **Functional Tests** (`<project>/tests/functional/`): Test with simulated services (if applicable)
3. **Integration/Scenario Tests** (`<project>/tests/scenario/` or `<project>/tests/integration/`): Full integration tests (require deployment)

## API Changes Review Checklist

### Versioning

API changes should be versioned:
- Check project's API structure (may be versioned directories like `<project>/api/v2/`)
- Some projects use API microversions

### Type Definitions

API types validation varies by project:
- Some use WSME for validation (types defined in `<project>/api/v*/types/`)
- Others use JSON Schema or other frameworks
- Must validate all inputs
- Must define proper types (string, int, bool, enum, etc.)

### Backward Compatibility

Questions to ask:
- Does this change break existing API contracts?
- Are new fields optional?
- Are deleted fields deprecated first?
- Is there a migration path for users?

## Performance Considerations

### Database Queries

**Bad - N+1 queries:**
```python
for item in parent.children:
    # This triggers a query for each child
    print(item.status)
```

**Good - Eager loading:**
```python
parent = session.query(models.Parent).options(
    sqlalchemy.orm.joinedload('children')
).filter_by(id=parent_id).first()

for item in parent.children:
    print(item.status)  # Already loaded
```

### Large Data Sets

Be careful with:
- Loading all records without pagination
- Deep object graphs without lazy loading
- Serializing large objects

## Commit Message Examples

### Good Commit Message

```
Fix VRRP failover when primary amphora is deleted

When the primary amphora is deleted, the VRRP configuration
needs to be updated on the secondary amphora to promote it
to primary. Previously, this update was skipped, causing
the VIP to become unavailable.

This patch ensures the VRRP configuration is always updated
when amphorae are removed from a load balancer.

Closes-Bug: #1234567
Change-Id: I1234567890abcdef1234567890abcdef12345678
```

### Bad Commit Message

```
Fix bug

Fixed the thing that was broken.

Change-Id: I1234567890abcdef1234567890abcdef12345678
```

Issues:
- Vague summary
- No explanation of what or why
- No bug reference

## Common Gerrit Review Comments

### Style Issues

```
-1: Please fix import order (stdlib imports should come before project imports)
```

```
-1: Use LOG.warning() instead of LOG.warn() per HACKING.rst
```

### Testing Issues

```
-1: This change needs unit tests. Please add tests to <project>/tests/unit/path/to/test_module.py
```

```
-1: Coverage dropped below project requirements. Please add tests to meet the required threshold.
```

### Design Issues

```
-1: This adds a new database query in a loop (N+1 problem). Consider using eager loading with joinedload()
```

```
-1: Direct database access should follow project patterns. Check if this project uses the repository pattern.
```

### Documentation Issues

```
-1: This adds a new config option. Please run 'tox -e genconfig' to update the sample config file.
```

```
-1: This is a user-facing change. Please add a release note with 'reno new <slug-name>'
```

## Useful Commands

### Review the Change

```bash
# Show commit details
git show --stat
git show

# Show diff from parent
git diff HEAD~1

# Show only modified files
git diff --name-only HEAD~1
```

### Run Tests

```bash
# All unit tests
tox -e py3

# Specific test file
tox -e py3 <project>.tests.unit.common.test_utils

# Specific test method
tox -e py3 <project>.tests.unit.common.test_utils.TestUtils.test_specific_method

# With coverage
tox -e cover

# Functional tests (if available)
tox -e functional

# Linting
tox -e pep8
```

### Check Test Structure

```bash
./tools/check_unit_test_structure.sh
```

### Generate Configs

```bash
# Sample config
tox -e genconfig

# Sample policy
tox -e genpolicy
```

## Resources

- **OpenStack Projects**: https://opendev.org/openstack/
- **Project Docs**: https://docs.openstack.org/<project>/
- **Gerrit**: https://review.opendev.org/
- **Review Guidelines**: https://docs.openstack.org/contributors/code-and-documentation/code-review.html
- **Commit Messages**: https://wiki.openstack.org/wiki/GitCommitMessages
- **Contributor Guide**: https://docs.openstack.org/contributors/
