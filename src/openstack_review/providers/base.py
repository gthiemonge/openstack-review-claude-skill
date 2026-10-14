"""
Provider abstraction for the OpenStack review agent.

A provider knows how to run an agentic code review: given a system prompt, a
task prompt, a working directory (the cloned repo) and an output directory, it
drives a model through the review process using filesystem/bash/web tools and
writes the final report.

The two concrete providers are:
  - ClaudeProvider  (providers/claude.py)       -> Claude Agent SDK
  - OpenAIProvider  (providers/openai_provider.py) -> OpenAI Responses API

Both return a ReviewResult so the CLI can print a uniform usage summary.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ReviewResult:
    """Outcome of a review run, normalized across providers."""

    success: bool
    # "success", "error_max_turns", "error", ...
    subtype: str = "success"
    # Aggregate token usage. Claude populates the SDK dict shape; OpenAI uses a
    # simpler {"input_tokens", "output_tokens"} shape.
    usage: Optional[Dict[str, Any]] = None
    # Per-model breakdown (Claude SDK only).
    model_usage: Optional[Dict[str, Any]] = None
    # Total cost in USD when the provider reports it (Claude only).
    total_cost_usd: Optional[float] = None
    # Session identifier for resuming (Claude only).
    session_id: Optional[str] = None
    # Which provider produced this result ("claude" / "openai").
    provider: str = ""
    # Extra free-form notes to print.
    notes: list = field(default_factory=list)


class ReviewProvider(ABC):
    """Base class every provider implements."""

    name: str = "base"

    @abstractmethod
    async def run_review(
        self,
        *,
        model: str,
        max_turns: int,
        system_prompt: str,
        prompt: str,
        work_dir: str,
        output_dir: str,
        skill_dir: Path,
        report_path: Path,
    ) -> ReviewResult:
        """Run a single review end-to-end and return a ReviewResult."""
        raise NotImplementedError


def print_usage_summary(result: ReviewResult, report_path: Path) -> None:
    """Print a uniform result + token-usage summary for any provider."""
    print("-" * 60)

    if not result.success:
        if result.subtype == "error_max_turns":
            msg = "Hit turn limit before finishing."
            if result.session_id:
                msg += f" Resume session {result.session_id} to continue."
            print(msg)
        else:
            print(f"Stopped: {result.subtype}")
        return

    print("✓ Review complete.")
    print()

    usage = result.usage
    if usage and isinstance(usage, dict):
        print("Token Usage:")

        inp = usage.get("input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)

        out = usage.get("output_tokens", 0)
        thinking = usage.get("output_tokens_details", {}).get("thinking_tokens", 0)

        total_input = inp + cache_read + cache_create
        total_all = total_input + out

        print(f"  Input:  {inp:,} new")
        if cache_read:
            print(f"          {cache_read:,} cache read")
        if cache_create:
            print(f"          {cache_create:,} cache created")
        if cache_read or cache_create:
            print(f"          {total_input:,} total input")

        print(f"  Output: {out:,} tokens")
        if thinking:
            print(f"          ({thinking:,} thinking tokens)")

        print(f"  Total:  {total_all:,} tokens")
        print()

    if result.model_usage:
        print("Per-Model Breakdown:")
        for model_name, stats in result.model_usage.items():
            if isinstance(stats, dict):
                print(f"  Model: {model_name}")
                model_inp = stats.get("inputTokens", 0)
                model_cache_read = stats.get("cacheReadInputTokens", 0)
                model_cache_create = stats.get("cacheCreationInputTokens", 0)
                model_out = stats.get("outputTokens", 0)
                model_thinking = stats.get("thinkingTokens", 0)
                model_cost = stats.get("costUSD", 0)
                provider = stats.get("provider", "")

                print(f"    Provider:    {provider}")
                print(
                    f"    Input:       {model_inp:,} new / "
                    f"{model_cache_read:,} cache read / "
                    f"{model_cache_create:,} cache created"
                )
                print(f"    Output:      {model_out:,} tokens", end="")
                if model_thinking:
                    print(f" ({model_thinking:,} thinking)")
                else:
                    print()
                print(f"    Cost:        ${model_cost:.4f}")
            else:
                print(f"  {model_name}: {stats}")
        print()

    if result.total_cost_usd:
        print(f"Total Cost: ${result.total_cost_usd:.4f}")
        print()

    for note in result.notes:
        print(note)

    if report_path.exists():
        print(f"Report saved to: {report_path}")
