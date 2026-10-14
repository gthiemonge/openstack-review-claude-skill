"""
OpenAI provider: a hand-written agentic loop on the OpenAI Responses API.

OpenAI has no agent SDK with built-in filesystem/bash tools, so this module
drives the model through the review by:
  1. sending the task with the local tool schemas (providers/tools.py),
  2. executing any function calls the model requests,
  3. feeding the outputs back and continuing until the model stops or the
     turn cap is hit.

A custom endpoint (Azure / OpenAI-compatible / proxy / self-hosted) is supported
via base_url: --openai-base-url -> OPENAI_BASE_URL -> official API default.
"""

import json
import os
from pathlib import Path

from .base import ReviewProvider, ReviewResult
from . import tools as _tools


class OpenAIProvider(ReviewProvider):
    name = "openai"

    def __init__(self, base_url: str = None):
        # Resolution order: explicit arg -> env -> official default (None).
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or None

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
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "The 'openai' package is required for the openai provider. "
                "Install it with: pip install openai"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it before running with "
                "--provider openai."
            )

        client_kwargs = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if os.getenv("OPENAI_ORG"):
            client_kwargs["organization"] = os.getenv("OPENAI_ORG")

        endpoint = self.base_url or "https://api.openai.com/v1 (default)"
        print(f"Using OpenAI endpoint: {endpoint}")

        client = OpenAI(**client_kwargs)

        ctx = _tools.ToolContext(
            work_dir=work_dir,
            output_dir=output_dir,
            skill_dir=str(skill_dir),
        )

        result = ReviewResult(success=False, provider=self.name)
        total_input = 0
        total_output = 0

        # We keep the full conversation client-side and resend it every turn,
        # rather than chaining with previous_response_id. Server-side response
        # storage is an OpenAI-specific feature; OpenAI-compatible backends
        # (litellm, vLLM, ...) typically don't persist responses, so
        # previous_response_id lookups fail with "Response ... not found".
        # Carrying history ourselves works on every endpoint.
        input_items = [{"role": "user", "content": prompt}]

        for turn in range(max_turns):
            response = client.responses.create(
                model=model,
                instructions=system_prompt,
                input=input_items,
                tools=_tools.OPENAI_TOOL_SCHEMAS,
            )

            usage = getattr(response, "usage", None)
            if usage is not None:
                total_input += getattr(usage, "input_tokens", 0) or 0
                total_output += getattr(usage, "output_tokens", 0) or 0

            # Record assistant outputs into our local history and collect any
            # tool calls. We reconstruct minimal items (dropping server-assigned
            # ids) so non-OpenAI backends accept the echoed history.
            tool_calls = []
            for item in response.output:
                itype = getattr(item, "type", None)
                if itype == "message":
                    text = _message_text(item)
                    if text:
                        print(text)
                        input_items.append({"role": "assistant", "content": text})
                elif itype == "function_call":
                    tool_calls.append(item)
                    input_items.append(
                        {
                            "type": "function_call",
                            "call_id": item.call_id,
                            "name": item.name,
                            "arguments": item.arguments,
                        }
                    )

            if not tool_calls:
                # Model produced a final answer with no further tool use.
                result.success = True
                result.subtype = "success"
                break

            # Execute each requested tool and append its output to the history.
            for call in tool_calls:
                name = call.name
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                _print_tool_call(name, args)
                output = _tools.dispatch(name, args, ctx)

                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": output,
                    }
                )
        else:
            # Loop exhausted without a final answer.
            result.subtype = "error_max_turns"
            result.success = False

        result.usage = {
            "input_tokens": total_input,
            "output_tokens": total_output,
        }
        return result


def _message_text(item) -> str:
    """Join the text blocks of a Responses API 'message' output item."""
    parts = []
    for block in getattr(item, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def _print_tool_call(name: str, inputs: dict) -> None:
    """Mirror the Claude provider's compact tool-call logging."""
    if name == "Bash":
        cmd = inputs.get("command", "")
        desc = inputs.get("description", "")
        label = desc if desc else cmd[:120]
        print(f"  [Bash] {label}")
    elif name == "Read":
        print(f"  [Read] {inputs.get('file_path', '?')}")
    elif name == "Write":
        print(f"  [Write] {inputs.get('file_path', '?')}")
    elif name == "Grep":
        print(f"  [Grep] {inputs.get('pattern', '?')}")
    elif name == "Glob":
        print(f"  [Glob] {inputs.get('pattern', '?')}")
    elif name == "WebFetch":
        print(f"  [WebFetch] {inputs.get('url', '?')}")
    else:
        print(f"  [{name}]")
