"""
Claude provider: wraps the Claude Agent SDK.

This preserves the original review behavior exactly — the SDK supplies the
agentic loop and the built-in Read/Bash/Grep/Glob/WebFetch/Write tools.

Vertex AI is auto-detected by the SDK from environment variables
(CLAUDE_CODE_USE_VERTEX, ANTHROPIC_VERTEX_PROJECT_ID, CLOUD_ML_REGION), so no
explicit configuration is needed here.
"""

from pathlib import Path

from .base import ReviewProvider, ReviewResult


class ClaudeProvider(ReviewProvider):
    name = "claude"

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
        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                ResultMessage,
                AssistantMessage,
                UserMessage,
            )
        except ImportError as e:
            raise RuntimeError(
                "The 'claude-agent-sdk' package is required for the claude "
                "provider. Install it with: pip install claude-agent-sdk"
            ) from e

        options = ClaudeAgentOptions(
            model=model,
            allowed_tools=["Read", "Bash", "Grep", "Glob", "WebFetch", "Write"],
            permission_mode="acceptEdits",
            cwd=work_dir,
            add_dirs=[output_dir, str(skill_dir)],
            env={"SKILL_DIR": str(skill_dir)},
            system_prompt=system_prompt,
            max_turns=max_turns,
        )

        result = ReviewResult(success=False, provider=self.name)

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
                result.subtype = message.subtype
                result.success = message.subtype == "success"
                result.usage = getattr(message, "usage", None)
                result.model_usage = getattr(message, "model_usage", None)
                result.total_cost_usd = getattr(message, "total_cost_usd", None)
                result.session_id = getattr(message, "session_id", None)

        return result
