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

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    UserMessage,
)


# Determine where skill files are located
# When installed as package: repo root or installed data directory
# When run from source: same directory as this file
SKILL_DIR = Path(__file__).resolve().parent
if not (SKILL_DIR / "SKILL.md").exists():
    # Not in same dir, try parent directories (installed case)
    candidate = SKILL_DIR.parent.parent.parent
    if (candidate / "SKILL.md").exists():
        SKILL_DIR = candidate
    else:
        # Try package data location
        import importlib.resources
        try:
            SKILL_DIR = Path(str(importlib.resources.files("openstack_review")))
        except:
            pass  # Fallback to current dir

try:
    from .review_config import get_model_config, list_presets
except ImportError:
    # Fallback for standalone script execution
    from review_config import get_model_config, list_presets


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
You do NOT need to clone it again — just run gerrit_review.py fetch to
check out the correct patchset.

Save the final review report (REVIEW_{review_number}.md) to: {output_dir}

OUTPUT STYLE: Before each tool call, write one short sentence explaining
WHY you are doing it (not what — the tool call itself shows that).
Examples: "Checking if the spec was approved.", "Looking for missing test
coverage for the new validation logic.", "The branch is stable/ so this
is a backport — comparing with the original."
Do not be verbose — one sentence is enough.

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
    preset: str = None,
    model_override: str = None,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    # Get model configuration based on preset or override
    model_config = get_model_config(preset=preset, model_override=model_override)

    print(f"Using model: {model_config['model']} (from {model_config['source']})")
    print(f"Max turns: {model_config['max_turns']}")

    # Vertex AI configuration from environment variables
    use_vertex = os.getenv("CLAUDE_CODE_USE_VERTEX")
    vertex_project = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID")
    vertex_region = os.getenv("CLOUD_ML_REGION", "global")

    # Build options with Vertex AI support
    options_kwargs = {
        "model": model_config["model"],
        "allowed_tools": ["Read", "Bash", "Grep", "Glob", "WebFetch", "Write"],
        "permission_mode": "acceptEdits",
        "cwd": work_dir,
        "add_dirs": [output_dir, str(SKILL_DIR)],
        "env": {"SKILL_DIR": str(SKILL_DIR)},
        "system_prompt": build_system_prompt(review_number, output_dir, gerrit_host),
        "max_turns": model_config["max_turns"],
    }

    # Add Vertex AI parameters if enabled
    if use_vertex and vertex_project:
        print(f"Using Vertex AI (project: {vertex_project}, region: {vertex_region})")
        options_kwargs["vertex_project_id"] = vertex_project
        options_kwargs["vertex_region"] = vertex_region

    options = ClaudeAgentOptions(**options_kwargs)

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
                        inputs = getattr(block, "input", {}) or {}
                        if block.name == "Bash":
                            cmd = inputs.get("command", "")
                            desc = inputs.get("description", "")
                            label = desc if desc else cmd[:120]
                            print(f"  [Bash] {label}")
                        elif block.name == "Read":
                            print(f"  [Read] {inputs.get('file_path', '?')}")
                        elif block.name == "Write":
                            print(f"  [Write] {inputs.get('file_path', '?')}")
                        elif block.name == "Grep":
                            print(f"  [Grep] {inputs.get('pattern', '?')}")
                        else:
                            print(f"  [{block.name}]")

            elif isinstance(message, UserMessage):
                for block in message.content:
                    text = ""
                    if hasattr(block, "text"):
                        text = block.text or ""
                    elif hasattr(block, "content"):
                        text = block.content if isinstance(block.content, str) else ""
                    if text:
                        lines = text.strip().split("\n")
                        if len(lines) <= 20:
                            for line in lines:
                                print(f"    {line}")
                        else:
                            for line in lines[:10]:
                                print(f"    {line}")
                            print(f"    ... ({len(lines) - 10} more lines)")
                        print()

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
        description="Review an OpenStack Gerrit change using Claude",
        epilog=list_presets(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    parser.add_argument(
        "--preset",
        choices=["quick", "standard", "thorough"],
        help="Review preset (quick/standard/thorough). See presets below. "
        "Override with REVIEW_PRESET environment variable.",
    )
    parser.add_argument(
        "--model",
        help="Specific Claude model to use (overrides preset). "
        "Examples: claude-sonnet-5, claude-opus-5, claude-sonnet-4-5. "
        "Override with REVIEW_MODEL environment variable.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available presets and exit",
    )
    args = parser.parse_args()

    if args.list_presets:
        print(list_presets())
        sys.exit(0)

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

    asyncio.run(
        run_review(
            args.review_number,
            output_dir,
            args.gerrit_host,
            repo_dir,
            preset=args.preset,
            model_override=args.model,
        )
    )


if __name__ == "__main__":
    main()
