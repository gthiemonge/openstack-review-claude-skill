#!/usr/bin/env python3
"""
OpenStack Gerrit Code Review Agent

Performs automated code reviews of OpenStack Gerrit changes using the
openstack-review skill. Supports multiple AI providers:
  - claude  (via the Claude Agent SDK)
  - openai  (via the OpenAI Responses API)

The agent clones the project from Gerrit automatically — no pre-existing
checkout is needed.

Usage:
    python review_agent.py <review-number> [--provider claude|openai]
        [--output-dir DIR] [--gerrit-host HOST]

Requirements:
    # Claude provider:
    pip install claude-agent-sdk
    export ANTHROPIC_API_KEY=your-api-key

    # OpenAI provider:
    pip install openai
    export OPENAI_API_KEY=your-api-key
    # optional custom endpoint:
    export OPENAI_BASE_URL=https://your-endpoint/v1
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
    from .providers import get_provider, print_usage_summary
except ImportError:
    # Fallback for standalone script execution
    from review_config import get_model_config, list_presets
    from providers import get_provider, print_usage_summary


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
    provider: str = None,
    preset: str = None,
    model_override: str = None,
    openai_base_url: str = None,
    openai_price_input: float = None,
    openai_price_output: float = None,
    max_turns_override: int = None,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    # Get provider + model configuration based on preset or override
    model_config = get_model_config(
        provider=provider, preset=preset, model_override=model_override
    )

    # An explicit --max-turns wins over the preset/model default.
    if max_turns_override is not None:
        model_config["max_turns"] = max_turns_override

    print(f"Using provider: {model_config['provider']}")
    print(f"Using model: {model_config['model']} (from {model_config['source']})")
    max_turns_source = "--max-turns" if max_turns_override is not None else "config"
    print(f"Max turns: {model_config['max_turns']} (from {max_turns_source})")

    # Note (claude provider): Vertex AI is auto-detected from environment
    # variables (CLAUDE_CODE_USE_VERTEX, ANTHROPIC_VERTEX_PROJECT_ID,
    # CLOUD_ML_REGION) by the Agent SDK — no explicit config needed here.

    report_path = Path(output_dir) / f"REVIEW_{review_number}.md"
    prompt = (
        f"Review OpenStack Gerrit change {review_number}. "
        f"Follow the review process in your instructions step by step: "
        f"fetch the change, analyze previous comments, review the code, "
        f"run automated checks, and generate the review report as "
        f"{report_path}."
    )

    system_prompt = build_system_prompt(review_number, output_dir, gerrit_host)

    print("-" * 60)

    try:
        review_provider = get_provider(
            model_config["provider"],
            openai_base_url=openai_base_url,
            openai_price_input=openai_price_input,
            openai_price_output=openai_price_output,
        )
        result = await review_provider.run_review(
            model=model_config["model"],
            max_turns=model_config["max_turns"],
            system_prompt=system_prompt,
            prompt=prompt,
            work_dir=work_dir,
            output_dir=output_dir,
            skill_dir=SKILL_DIR,
            report_path=report_path,
        )
        print_usage_summary(result, report_path)
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
        "--provider",
        choices=["claude", "openai"],
        help="AI provider to use (claude/openai). "
        "Override with REVIEW_PROVIDER environment variable. Default: claude.",
    )
    parser.add_argument(
        "--openai-base-url",
        help="Custom OpenAI endpoint base URL (Azure / OpenAI-compatible / "
        "proxy / self-hosted). Override with OPENAI_BASE_URL environment "
        "variable. Only used with --provider openai.",
    )
    parser.add_argument(
        "--preset",
        choices=["quick", "standard", "thorough"],
        help="Review preset (quick/standard/thorough). See presets below. "
        "Override with REVIEW_PRESET environment variable.",
    )
    parser.add_argument(
        "--model",
        help="Specific model to use (overrides preset). "
        "Examples: claude-sonnet-5, claude-opus-5, gpt-5, gpt-5-mini. "
        "Override with REVIEW_MODEL environment variable.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        help="Maximum number of agent turns (overrides the preset/model "
        "default).",
    )
    parser.add_argument(
        "--openai-price-input",
        type=float,
        help="OpenAI input price in USD per 1M tokens (overrides the "
        "OPENAI_PRICING table). Override with OPENAI_PRICE_INPUT env var. "
        "Only used with --provider openai.",
    )
    parser.add_argument(
        "--openai-price-output",
        type=float,
        help="OpenAI output price in USD per 1M tokens (overrides the "
        "OPENAI_PRICING table). Override with OPENAI_PRICE_OUTPUT env var. "
        "Only used with --provider openai.",
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
            provider=args.provider,
            preset=args.preset,
            model_override=args.model,
            openai_base_url=args.openai_base_url,
            openai_price_input=args.openai_price_input,
            openai_price_output=args.openai_price_output,
            max_turns_override=args.max_turns,
        )
    )


if __name__ == "__main__":
    main()
