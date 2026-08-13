#!/usr/bin/env python3
"""
OpenStack Gerrit Code Review Agent

Uses the Claude Agent SDK with the openstack-review skill to perform
automated code reviews of OpenStack Gerrit changes.

The agent clones the project from Gerrit automatically — no pre-existing
checkout is needed.

Usage:
    python review_agent.py <review-number> [--output-dir DIR] [--gerrit-host HOST]

Requirements:
    pip install claude-agent-sdk
    export ANTHROPIC_API_KEY=your-api-key
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, AssistantMessage


SKILL_DIR = Path(__file__).resolve().parent


def fetch_change_metadata(gerrit_host: str, review_number: int) -> dict:
    url = f"https://{gerrit_host}/changes/{review_number}/detail"
    with urllib.request.urlopen(url) as resp:
        # Gerrit prepends ")]}'" to JSON responses
        raw = resp.read().decode()
        return json.loads(raw.split("\n", 1)[1])


def clone_project(gerrit_host: str, project: str, dest: str) -> None:
    url = f"https://{gerrit_host}/{project}"
    subprocess.run(
        ["git", "clone", "--depth", "50", url, dest],
        check=True,
    )


def build_system_prompt(
    review_number: int, output_dir: str, gerrit_host: str
) -> str:
    skill_md = (SKILL_DIR / "SKILL.md").read_text()
    reference_md = (SKILL_DIR / "reference.md").read_text()

    # Strip YAML frontmatter from the skill file
    lines = skill_md.split("\n")
    if lines[0].strip() == "---":
        end = next(
            (i for i in range(1, len(lines)) if lines[i].strip() == "---"), 0
        )
        skill_md = "\n".join(lines[end + 1 :])

    return f"""\
You are an expert OpenStack code reviewer. Your task is to review Gerrit
change {review_number} following the process below.

IMPORTANT: The helper scripts are located at:
  SKILL_DIR="{SKILL_DIR}"

When running gerrit_review.py, use the full path:
  python3 {SKILL_DIR}/gerrit_review.py fetch {review_number}
  python3 {SKILL_DIR}/gerrit_review.py comments {review_number}

The Gerrit host is: {gerrit_host}

Replace $ARGUMENTS with {review_number} everywhere in the instructions.

The repository has already been cloned into your working directory.
You do NOT need to clone it again — just run fetch_review.sh to check out
the correct patchset.

Save the final review report (REVIEW_{review_number}.md) to: {output_dir}

---

{skill_md}

---

## Reference Material

{reference_md}
"""


async def run_review(
    review_number: int,
    output_dir: str,
    gerrit_host: str,
    work_dir: str,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    options = ClaudeAgentOptions(
        model="claude-sonnet-5",
        allowed_tools=["Read", "Bash", "Grep", "Glob", "WebFetch", "Write"],
        permission_mode="acceptEdits",
        cwd=work_dir,
        add_dirs=[output_dir, str(SKILL_DIR)],
        env={"SKILL_DIR": str(SKILL_DIR)},
        system_prompt=build_system_prompt(review_number, output_dir, gerrit_host),
        max_turns=50,
    )

    report_path = Path(output_dir) / f"REVIEW_{review_number}.md"
    prompt = (
        f"Review OpenStack Gerrit change {review_number}. "
        f"Follow the review process in your instructions step by step: "
        f"fetch the change, analyze previous comments, review the code, "
        f"run automated checks, and generate the review report as "
        f"{report_path}."
    )

    print("-" * 60)

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        print(block.text)
                    elif hasattr(block, "name"):
                        print(f"  [tool] {block.name}")

            elif isinstance(message, ResultMessage):
                print("-" * 60)
                if message.subtype == "success":
                    print("Review complete.")
                    if message.total_cost_usd:
                        print(f"Total cost: ${message.total_cost_usd:.4f}")
                    usage_by_model = getattr(message, "usage_by_model", None)
                    if usage_by_model:
                        for model_name, usage in usage_by_model.items():
                            parts = [f"  {model_name}:"]
                            cost = getattr(usage, "cost_usd", None)
                            if cost is not None:
                                parts.append(f"${cost:.4f}")
                            inp = getattr(usage, "input_tokens", None)
                            out = getattr(usage, "output_tokens", None)
                            if inp is not None and out is not None:
                                parts.append(f"— {inp} in / {out} out")
                            print(" ".join(parts))
                            cache_read = getattr(usage, "cache_read_tokens", 0)
                            if cache_read:
                                cache_create = getattr(
                                    usage, "cache_creation_tokens", 0
                                )
                                print(
                                    f"    cache: {cache_read} read"
                                    f" / {cache_create} created"
                                )
                    if report_path.exists():
                        print(f"Report saved to: {report_path}")
                elif message.subtype == "error_max_turns":
                    print(
                        "Hit turn limit before finishing. "
                        f"Resume session {message.session_id} to continue."
                    )
                else:
                    print(f"Stopped: {message.subtype}")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review an OpenStack Gerrit change using Claude"
    )
    parser.add_argument("review_number", type=int, help="Gerrit review number")
    parser.add_argument(
        "--output-dir",
        default=os.getcwd(),
        help="Directory for the review report (default: current directory)",
    )
    parser.add_argument(
        "--gerrit-host",
        default="review.opendev.org",
        help="Gerrit hostname (default: review.opendev.org)",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)

    print(f"Fetching metadata for change {args.review_number}...")
    try:
        meta = fetch_change_metadata(args.gerrit_host, args.review_number)
    except Exception as exc:
        print(
            f"Error: could not fetch change {args.review_number} "
            f"from {args.gerrit_host}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    project = meta["project"]
    subject = meta.get("subject", "")
    print(f"Project: {project}")
    print(f"Subject: {subject}")

    work_dir = tempfile.mkdtemp(prefix="osr-")
    repo_dir = os.path.join(work_dir, project.split("/")[-1])

    print(f"Cloning {project} into {repo_dir}...")
    try:
        clone_project(args.gerrit_host, project, repo_dir)
    except subprocess.CalledProcessError as exc:
        print(f"Error: git clone failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Output directory: {output_dir}")
    print(f"Skill directory:  {SKILL_DIR}")

    asyncio.run(run_review(args.review_number, output_dir, args.gerrit_host, repo_dir))


if __name__ == "__main__":
    main()
