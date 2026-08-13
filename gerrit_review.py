#!/usr/bin/env python3
"""
Unified CLI for OpenStack Gerrit review operations.

Replaces inline shell scripts in SKILL.md with filtered, token-efficient output.

Usage:
    gerrit_review.py fetch <review_num>
    gerrit_review.py comments <review_num>
    gerrit_review.py backport-compare <original_sha>
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


def read_gitreview():
    """Parse .gitreview in the current directory."""
    path = Path(".gitreview")
    if not path.exists():
        print("Error: .gitreview not found in current directory", file=sys.stderr)
        sys.exit(1)
    config = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.startswith("["):
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()
    project = config.get("project", "").removesuffix(".git")
    host = config.get("host", "review.opendev.org")
    if not project:
        print("Error: no project= in .gitreview", file=sys.stderr)
        sys.exit(1)
    return host, project


def gerrit_api(host, endpoint):
    """Fetch a Gerrit REST API endpoint, stripping the XSSI prefix."""
    url = f"https://{host}{endpoint}"
    try:
        with urllib.request.urlopen(url) as resp:
            raw = resp.read().decode()
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)
    # Gerrit prepends )]}' to JSON
    for i, ch in enumerate(raw):
        if ch in "{[":
            return json.loads(raw[i:])
    print(f"Error: unexpected response from {url}", file=sys.stderr)
    sys.exit(1)


def project_encoded(project):
    return project.replace("/", "%2F")


# ── fetch ────────────────────────────────────────────────────────────────

def cmd_fetch(review_num):
    """Fetch and checkout a Gerrit review patchset."""
    host, project = read_gitreview()
    penc = project_encoded(project)

    detail = gerrit_api(host, f"/changes/{penc}~{review_num}/detail")
    patchset = detail["current_revision_number"]
    last_two = f"{review_num % 100:02d}"

    ref = f"refs/changes/{last_two}/{review_num}/{patchset}"
    print(f"Fetching {project} patchset {patchset} ({ref})")

    subprocess.run(
        ["git", "fetch", f"https://{host}/{project}", ref],
        check=True,
    )
    subprocess.run(["git", "checkout", "FETCH_HEAD"], check=True)

    # Concise summary
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H%nAuthor: %an <%ae>%nDate: %ad%nSubject: %s"],
        capture_output=True, text=True,
    )
    print(result.stdout)

    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD~1"],
        capture_output=True, text=True,
    )
    print("Files changed:")
    print(result.stdout)


# ── comments ─────────────────────────────────────────────────────────────

SKIP_AUTHORS = {"Zuul", "Jenkins", "OpenStack Infra"}

def cmd_comments(review_num):
    """Fetch review metadata, comments, and inline comments. Output only what matters."""
    host, project = read_gitreview()
    penc = project_encoded(project)

    detail = gerrit_api(
        host,
        f"/changes/{penc}~{review_num}/detail"
        "?o=ALL_REVISIONS&o=ALL_COMMITS&o=ALL_FILES"
        "&o=MESSAGES&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS",
    )

    current_ps = detail["current_revision_number"]

    # ── Header
    print(f"Review #{review_num}: {detail['subject']}")
    print(f"Author: {detail['owner'].get('name', '?')} <{detail['owner'].get('email', '?')}>")
    print(f"Status: {detail['status']}  |  Branch: {detail.get('branch', '?')}  |  Patchset: {current_ps}")

    # ── Labels / scores
    labels = detail.get("labels", {})
    if labels:
        print("\nScores:")
        for label, data in labels.items():
            votes = [
                (v.get("name", "?"), v.get("value", 0))
                for v in data.get("all", [])
                if v.get("value", 0) != 0
            ]
            if votes:
                parts = ", ".join(f"{name}: {val:+d}" for name, val in votes)
                print(f"  {label}: {parts}")

    # ── Review messages (filtered)
    messages = detail.get("messages", [])
    human_msgs = []
    for msg in messages:
        author = msg.get("author", {}).get("name", "Unknown")
        if author in SKIP_AUTHORS:
            continue
        text = msg.get("message", "")
        if "Uploaded patch set" in text and len(text.split("\n")) <= 2:
            continue
        human_msgs.append(msg)

    if human_msgs:
        print(f"\nReview messages ({len(human_msgs)} human):")
        by_ps = {}
        for msg in human_msgs:
            ps = msg.get("_revision_number", 0)
            by_ps.setdefault(ps, []).append(msg)

        for ps in sorted(by_ps):
            marker = " (CURRENT)" if ps == current_ps else ""
            print(f"\n--- Patchset {ps}{marker} ---")
            for msg in by_ps[ps]:
                author = msg["author"].get("name", "?")
                date = msg.get("date", "")[:16]
                text = msg.get("message", "").strip()
                # Truncate very long messages
                lines = text.split("\n")
                if len(lines) > 15:
                    text = "\n".join(lines[:15]) + f"\n  ... ({len(lines) - 15} more lines)"
                print(f"\n[{date}] {author}:")
                for line in text.split("\n"):
                    print(f"  {line}")

    # ── Inline comments (all patchsets)
    for ps in range(1, current_ps + 1):
        try:
            inline = gerrit_api(
                host,
                f"/changes/{penc}~{review_num}/revisions/{ps}/comments",
            )
        except SystemExit:
            continue

        if not inline:
            continue

        filtered = {}
        for filepath, comments in inline.items():
            relevant = []
            for c in comments:
                author = c.get("author", {}).get("name", "?")
                if author in SKIP_AUTHORS:
                    continue
                relevant.append({
                    "line": c.get("line", "?"),
                    "author": author,
                    "message": c.get("message", "").strip(),
                    "unresolved": c.get("unresolved", False),
                })
            if relevant:
                filtered[filepath] = relevant

        if filtered:
            print(f"\n--- Inline comments (patchset {ps}) ---")
            for filepath, comments in sorted(filtered.items()):
                for c in comments:
                    status = " [UNRESOLVED]" if c["unresolved"] else ""
                    print(f"  {filepath}:{c['line']} ({c['author']}){status}")
                    for line in c["message"].split("\n"):
                        print(f"    {line}")

    # ── Summary of potential issues
    old_issues = []
    for msg in human_msgs:
        ps = msg.get("_revision_number", 0)
        if ps < current_ps:
            text = msg.get("message", "")
            for pattern in [r"-1", r"please\s+fix", r"needs?\s+to", r"missing"]:
                if re.search(pattern, text, re.IGNORECASE):
                    author = msg["author"].get("name", "?")
                    old_issues.append(f"PS{ps} ({author}): {text[:120]}")
                    break

    if old_issues:
        print(f"\nPrevious patchset concerns ({len(old_issues)}):")
        for issue in old_issues:
            lines = issue.split("\n")
            print(f"  - {lines[0]}")
    else:
        print("\nNo flagged concerns from previous patchsets.")


# ── backport-compare ─────────────────────────────────────────────────────

def cmd_backport_compare(original_sha):
    """Compare current HEAD (backport) against the original commit."""
    # Ensure we have the original commit
    result = subprocess.run(
        ["git", "cat-file", "-t", original_sha],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Original commit {original_sha} not found locally, fetching master...")
        subprocess.run(["git", "fetch", "origin", "master"], check=True)

    # Get both diffs
    orig = subprocess.run(
        ["git", "diff", f"{original_sha}~1..{original_sha}"],
        capture_output=True, text=True,
    )
    backport = subprocess.run(
        ["git", "diff", "HEAD~1..HEAD"],
        capture_output=True, text=True,
    )

    if orig.stdout == backport.stdout:
        print("Backport is identical to original commit — clean cherry-pick.")
        return

    # Show only the differences between the two diffs
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f1:
        f1.write(orig.stdout)
        f1_path = f1.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f2:
        f2.write(backport.stdout)
        f2_path = f2.name

    result = subprocess.run(
        ["diff", "-u", "--label", "original", f1_path, "--label", "backport", f2_path],
        capture_output=True, text=True,
    )
    os.unlink(f1_path)
    os.unlink(f2_path)

    print("Backport differs from original. Differences:")
    print(result.stdout)

    # Check commit message for Conflicts: section
    commit_msg = subprocess.run(
        ["git", "log", "-1", "--format=%B"],
        capture_output=True, text=True,
    ).stdout
    if "Conflicts:" in commit_msg:
        start = commit_msg.index("Conflicts:")
        print("\nDocumented conflicts:")
        for line in commit_msg[start:].split("\n"):
            if not line.strip():
                break
            print(f"  {line}")
    else:
        print("\nWARNING: No 'Conflicts:' section in commit message despite differences.")


# ── main ─────────────────────────────────────────────────────────────────

COMMANDS = {
    "fetch": (cmd_fetch, "review_num"),
    "comments": (cmd_comments, "review_num"),
    "backport-compare": (cmd_backport_compare, "original_sha"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: {sys.argv[0]} <command> <arg>")
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(1)

    cmd_name = sys.argv[1]
    func, arg_name = COMMANDS[cmd_name]

    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} {cmd_name} <{arg_name}>")
        sys.exit(1)

    arg = sys.argv[2]
    if arg_name == "review_num":
        try:
            arg = int(arg)
        except ValueError:
            print(f"Error: {arg_name} must be an integer", file=sys.stderr)
            sys.exit(1)

    func(arg)


if __name__ == "__main__":
    main()
