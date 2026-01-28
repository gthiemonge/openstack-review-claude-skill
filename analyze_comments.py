#!/usr/bin/env python3
"""
Analyze Gerrit review comments and check if they've been addressed.
"""

import json
import sys
import re
from datetime import datetime

def parse_review_data(review_file):
    """Parse review JSON data from Gerrit."""
    with open(review_file) as f:
        return json.load(f)

def extract_issues_from_message(message):
    """Extract actionable issues from a review message."""
    issues = []

    # Common patterns indicating issues
    issue_patterns = [
        r'-1:?\s*(.+)',  # -1 votes
        r'please\s+(.+)',  # Requests
        r'should\s+(.+)',  # Suggestions
        r'need(?:s)?\s+(?:to\s+)?(.+)',  # Requirements
        r'missing\s+(.+)',  # Missing items
        r'(?:bug|issue|problem|error):\s*(.+)',  # Explicit issues
    ]

    for pattern in issue_patterns:
        matches = re.finditer(pattern, message, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            issue = match.group(0).strip()
            if len(issue) > 10:  # Filter out too short matches
                issues.append(issue)

    return issues

def analyze_comments(review):
    """Analyze review comments and categorize them."""
    print("\n" + "=" * 80)
    print(f"REVIEW ANALYSIS FOR #{review['_number']}")
    print("=" * 80)

    print(f"\nSubject: {review['subject']}")
    print(f"Author: {review['owner']['name']} <{review['owner']['email']}>")
    print(f"Status: {review['status']}")
    print(f"Current Patchset: {review['current_revision_number']}")

    if 'messages' not in review or len(review['messages']) == 0:
        print("\n✓ No review comments found")
        return

    print(f"\nTotal messages: {len(review['messages'])}")

    # Track issues by patchset
    patchset_issues = {}
    all_reviewers = set()

    for msg in review['messages']:
        ps = msg.get('_revision_number', 'N/A')
        author = msg['author'].get('name', 'Unknown')
        all_reviewers.add(author)
        date = msg.get('date', '')
        message = msg.get('message', '')

        # Skip automated messages
        if 'Patch Set' in message and 'Uploaded patch set' in message:
            continue
        if author in ['Zuul', 'Jenkins', 'OpenStack Infra']:
            continue

        # Extract issues from message
        issues = extract_issues_from_message(message)

        if ps not in patchset_issues:
            patchset_issues[ps] = []

        patchset_issues[ps].append({
            'author': author,
            'date': date,
            'message': message,
            'issues': issues
        })

    # Display issues by patchset
    print("\n" + "-" * 80)
    print("REVIEW HISTORY BY PATCHSET")
    print("-" * 80)

    current_ps = review['current_revision_number']

    for ps in sorted(patchset_issues.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
        if not patchset_issues[ps]:
            continue

        is_current = (ps == current_ps)
        ps_marker = " (CURRENT)" if is_current else ""

        print(f"\n### Patchset {ps}{ps_marker} ###")

        for comment in patchset_issues[ps]:
            print(f"\n[{comment['date']}] {comment['author']}:")

            # Show message (truncated if too long)
            msg_lines = comment['message'].split('\n')
            for line in msg_lines[:10]:  # First 10 lines
                print(f"  {line}")
            if len(msg_lines) > 10:
                print(f"  ... ({len(msg_lines) - 10} more lines)")

            # Highlight extracted issues
            if comment['issues']:
                print("\n  🔍 Potential issues identified:")
                for issue in comment['issues'][:5]:  # Top 5 issues
                    print(f"     • {issue}")

    # Show current scores
    print("\n" + "-" * 80)
    print("CURRENT REVIEW SCORES")
    print("-" * 80)

    if 'labels' in review:
        for label, data in review['labels'].items():
            print(f"\n{label}:")
            if 'all' in data:
                votes = [(v['name'], v.get('value', 0)) for v in data['all'] if v.get('value', 0) != 0]
                if votes:
                    for name, value in votes:
                        print(f"  {name}: {value:+d}")
                else:
                    print("  (no votes)")
            else:
                print("  (no votes)")

    # Summary
    print("\n" + "=" * 80)
    print("REVIEW SUMMARY")
    print("=" * 80)

    print(f"\n• Reviewers: {', '.join(sorted(all_reviewers))}")
    print(f"• Patchsets with comments: {len([p for p in patchset_issues if patchset_issues[p]])}")
    print(f"• Current patchset: {current_ps}")

    # Count issues in older patchsets
    old_patchset_issues = []
    for ps in patchset_issues:
        if ps != 'N/A' and ps != current_ps and int(ps) < int(current_ps):
            for comment in patchset_issues[ps]:
                old_patchset_issues.extend(comment['issues'])

    if old_patchset_issues:
        print(f"\n⚠️  {len(old_patchset_issues)} potential issues identified in previous patchsets")
        print("   → Verify these have been addressed in the current patchset!")
    else:
        print("\n✓ No specific issues identified in previous patchsets")

    print("\n" + "=" * 80)

def main():
    if len(sys.argv) != 2:
        print("Usage: analyze_comments.py <review_json_file>")
        print("Example: analyze_comments.py /tmp/review_970404.json")
        sys.exit(1)

    review_file = sys.argv[1]

    try:
        review = parse_review_data(review_file)
        analyze_comments(review)
    except FileNotFoundError:
        print(f"Error: File {review_file} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {review_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
