#!/bin/bash
# Helper script to fetch OpenStack Gerrit reviews

set -e

REVIEW_NUM=$1

if [ -z "$REVIEW_NUM" ]; then
    echo "Usage: $0 <review-number>"
    echo "Example: $0 970404"
    exit 1
fi

# Extract project name from .gitreview file
if [ ! -f ".gitreview" ]; then
    echo "Error: .gitreview file not found in current directory"
    echo "Make sure you're in an OpenStack project directory"
    exit 1
fi

PROJECT=$(grep "^project=" .gitreview | cut -d= -f2 | sed 's/\.git$//')
GERRIT_HOST=$(grep "^host=" .gitreview | cut -d= -f2)

if [ -z "$PROJECT" ]; then
    echo "Error: Could not extract project name from .gitreview"
    exit 1
fi

echo "Project: $PROJECT"
echo "Gerrit host: $GERRIT_HOST"

# URL-encode the project name for API calls (replace / with %2F)
PROJECT_ENCODED=$(echo "$PROJECT" | sed 's/\//%2F/g')

# Extract last 2 digits for the ref path
LAST_TWO=$(printf "%02d" $((REVIEW_NUM % 100)))

echo "Fetching review $REVIEW_NUM..."

# Get the latest patchset number from Gerrit API
echo "Getting latest patchset number..."
PATCHSET=$(curl -s "https://${GERRIT_HOST}/changes/${PROJECT_ENCODED}~${REVIEW_NUM}/detail" | tail -n +2 | python3 -c "import sys, json; print(json.load(sys.stdin)['current_revision_number'])")

echo "Latest patchset: $PATCHSET"

# Fetch the change
echo "Fetching refs/changes/${LAST_TWO}/${REVIEW_NUM}/${PATCHSET}..."
git fetch https://${GERRIT_HOST}/${PROJECT} refs/changes/${LAST_TWO}/${REVIEW_NUM}/${PATCHSET}

echo "Checking out FETCH_HEAD..."
git checkout FETCH_HEAD

echo ""
echo "Review $REVIEW_NUM (patchset $PATCHSET) checked out successfully!"
echo ""
echo "Commit details:"
git log -1 --format="%H%nAuthor: %an <%ae>%nDate: %ad%nSubject: %s%n" HEAD

echo ""
echo "Files changed:"
git diff --name-only HEAD~1

echo ""
echo "Run 'git show' to see the full diff"
