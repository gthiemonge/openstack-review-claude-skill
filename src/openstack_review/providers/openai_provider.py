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

    def __init__(self, base_url: str = None, price_input: float = None,
                 price_output: float = None):
        # Resolution order: explicit arg -> env -> official default (None).
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        # Per-1M-token price overrides (USD). None means fall back to the
        # OPENAI_PRICING table in review_config for the model being used.
        self.price_input = _first_float(price_input, os.getenv("OPENAI_PRICE_INPUT"))
        self.price_output = _first_float(price_output, os.getenv("OPENAI_PRICE_OUTPUT"))

    async def run_review(
        self,
        *,
        model: str,
        max_turns: int,
        effort: str = None,
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
        # Cost reported by an OpenAI-compatible gateway (e.g. litellm sends it
        # in the x-litellm-response-cost response header). When present this is
        # authoritative; otherwise we fall back to the local pricing table.
        api_cost = 0.0
        api_cost_seen = False

        # We keep the full conversation client-side and resend it every turn,
        # rather than chaining with previous_response_id. Server-side response
        # storage is an OpenAI-specific feature; OpenAI-compatible backends
        # (litellm, vLLM, ...) typically don't persist responses, so
        # previous_response_id lookups fail with "Response ... not found".
        # Carrying history ourselves works on every endpoint.
        input_items = [{"role": "user", "content": prompt}]

        for turn in range(max_turns):
            # Use with_raw_response so we can read response headers (gateways
            # like litellm return the per-request cost there).
            request = {
                "model": model,
                "instructions": system_prompt,
                "input": input_items,
                "tools": _tools.OPENAI_TOOL_SCHEMAS,
            }
            if effort is not None:
                request["reasoning"] = {"effort": effort}
            raw = client.responses.with_raw_response.create(**request)
            response = raw.parse()

            turn_cost = _header_cost(raw)
            if turn_cost is not None:
                api_cost += turn_cost
                api_cost_seen = True

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

        # Cost: prefer what the gateway reported (authoritative); otherwise
        # compute from token usage using rate overrides or the pricing table.
        if api_cost_seen:
            result.total_cost_usd = api_cost
        else:
            rates = self._resolve_rates(model)
            if rates is not None:
                result.total_cost_usd = (
                    total_input * rates["input"] + total_output * rates["output"]
                ) / 1_000_000
            else:
                result.notes.append(
                    f"Cost: unknown — no cost reported for model '{model}'."
                )

        return result

    def _resolve_rates(self, model: str) -> dict:
        """Return {'input', 'output'} USD-per-1M-token rates, or None."""
        if self.price_input is not None and self.price_output is not None:
            return {"input": self.price_input, "output": self.price_output}

        try:
            from ..review_config import get_openai_pricing
        except ImportError:
            from review_config import get_openai_pricing
        return get_openai_pricing(model)


# Response headers that OpenAI-compatible gateways use to report per-request
# cost in USD. litellm uses the first; others are accepted defensively.
_COST_HEADERS = ("x-litellm-response-cost", "x-response-cost", "x-cost-usd")


def _header_cost(raw) -> float:
    """Extract a USD cost from an OpenAI SDK raw response's headers, or None."""
    headers = getattr(raw, "headers", None)
    if not headers:
        return None
    for key in _COST_HEADERS:
        value = headers.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _first_float(*values) -> float:
    """Return the first value that can be parsed as a float, else None."""
    for v in values:
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


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
