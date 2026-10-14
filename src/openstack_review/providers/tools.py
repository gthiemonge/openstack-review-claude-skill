"""
Local tool implementations for providers that do not ship their own agentic
toolset (currently OpenAI).

The Claude Agent SDK provides Read/Write/Bash/Grep/Glob/WebFetch for free. To
run the exact same review workflow (SKILL.md) through OpenAI, we reimplement the
same tools here with matching names and semantics, expose JSON-schema
definitions for OpenAI function calling, and provide a dispatch() executor.

All paths are resolved relative to the working directory (the cloned repo).
Writes are permitted anywhere the process can write (the review needs to write
its report into the output directory), matching the Claude SDK's acceptEdits
behavior for this workflow.
"""

import glob as _glob
import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ToolContext:
    """Runtime context shared by all tool calls during one review."""

    work_dir: str
    output_dir: str
    skill_dir: str
    # Cap on bytes returned by any single tool call, to protect the context.
    max_output_chars: int = 30000


def _resolve(ctx: ToolContext, path: str) -> Path:
    """Resolve a possibly-relative path against the working directory."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(ctx.work_dir) / p
    return p


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text) - limit} more chars]"


# ── individual tools ───────────────────────────────────────────────────────


def tool_read(ctx: ToolContext, file_path: str, offset: int = None, limit: int = None) -> str:
    path = _resolve(ctx, file_path)
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory"
    except Exception as e:
        return f"Error reading {path}: {e}"

    start = (offset - 1) if offset and offset > 0 else 0
    end = (start + limit) if limit else len(lines)
    chunk = lines[start:end]

    numbered = []
    for i, line in enumerate(chunk, start=start + 1):
        numbered.append(f"{i}\t{line.rstrip(chr(10))}")
    return _truncate("\n".join(numbered), ctx.max_output_chars)


def tool_write(ctx: ToolContext, file_path: str, content: str) -> str:
    path = _resolve(ctx, file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
    except Exception as e:
        return f"Error writing {path}: {e}"
    return f"Wrote {len(content)} chars to {path}"


def tool_bash(ctx: ToolContext, command: str, description: str = "", timeout: int = 300) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=ctx.work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as e:
        return f"Error running command: {e}"

    out = result.stdout or ""
    err = result.stderr or ""
    parts = []
    if out:
        parts.append(out)
    if err:
        parts.append(f"[stderr]\n{err}")
    if result.returncode != 0:
        parts.append(f"[exit code: {result.returncode}]")
    return _truncate("\n".join(parts) if parts else "(no output)", ctx.max_output_chars)


def tool_grep(ctx: ToolContext, pattern: str, path: str = None, glob: str = None) -> str:
    search_path = str(_resolve(ctx, path)) if path else ctx.work_dir

    if shutil.which("rg"):
        cmd = ["rg", "--line-number", "--no-heading", "--color", "never"]
        if glob:
            cmd += ["--glob", glob]
        cmd += [pattern, search_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout or ""
            if not output and result.returncode not in (0, 1):
                output = result.stderr or ""
            return _truncate(output or "(no matches)", ctx.max_output_chars)
        except Exception as e:
            return f"Error running grep: {e}"

    # Fallback: pure-Python recursive search.
    import re as _re

    try:
        regex = _re.compile(pattern)
    except _re.error as e:
        return f"Error: invalid pattern: {e}"

    matches: List[str] = []
    for root, _dirs, files in os.walk(search_path):
        if ".git" in root.split(os.sep):
            continue
        for name in files:
            if glob and not Path(name).match(glob):
                continue
            fpath = os.path.join(root, name)
            try:
                with open(fpath, "r", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append(f"{fpath}:{lineno}:{line.rstrip()}")
            except Exception:
                continue
    return _truncate("\n".join(matches) if matches else "(no matches)", ctx.max_output_chars)


def tool_glob(ctx: ToolContext, pattern: str, path: str = None) -> str:
    base = str(_resolve(ctx, path)) if path else ctx.work_dir
    results = _glob.glob(os.path.join(base, pattern), recursive=True)
    results.sort()
    return _truncate("\n".join(results) if results else "(no matches)", ctx.max_output_chars)


def tool_webfetch(ctx: ToolContext, url: str, prompt: str = "") -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "openstack-review/agent"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode(errors="replace")
    except Exception as e:
        return f"Error fetching {url}: {e}"
    # Gerrit prepends )]}' to JSON responses — strip it if present so the model
    # gets clean content, matching gerrit_review.py's behavior.
    stripped = raw.lstrip()
    if stripped.startswith(")]}'"):
        raw = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[4:]
    return _truncate(raw, ctx.max_output_chars)


# ── OpenAI function-calling schemas ────────────────────────────────────────

OPENAI_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "Read",
        "description": "Read a file from the filesystem. Returns line-numbered content.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file (absolute or relative to the repo)."},
                "offset": {"type": "integer", "description": "1-based line to start from (optional)."},
                "limit": {"type": "integer", "description": "Max number of lines to read (optional)."},
            },
            "required": ["file_path"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "Write",
        "description": "Write (or overwrite) a file with the given content.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to write (absolute or relative to the repo)."},
                "content": {"type": "string", "description": "Full file content to write."},
            },
            "required": ["file_path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "Bash",
        "description": "Run a shell command in the repo working directory and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run."},
                "description": {"type": "string", "description": "One short sentence on why you run it."},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "Grep",
        "description": "Search file contents for a regular expression. Returns file:line:match rows.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regular expression to search for."},
                "path": {"type": "string", "description": "Directory or file to search (optional, defaults to repo)."},
                "glob": {"type": "string", "description": "Only search files matching this glob (optional)."},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "Glob",
        "description": "Find files matching a glob pattern (supports ** for recursion).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py'."},
                "path": {"type": "string", "description": "Base directory (optional, defaults to repo)."},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "WebFetch",
        "description": "Fetch the contents of a URL (e.g. a Gerrit REST endpoint) and return the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch."},
                "prompt": {"type": "string", "description": "What you are looking for (optional)."},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
]


_DISPATCH = {
    "Read": tool_read,
    "Write": tool_write,
    "Bash": tool_bash,
    "Grep": tool_grep,
    "Glob": tool_glob,
    "WebFetch": tool_webfetch,
}


def dispatch(name: str, args: Dict[str, Any], ctx: ToolContext) -> str:
    """Execute a tool by name with keyword args from the model."""
    func = _DISPATCH.get(name)
    if func is None:
        return f"Error: unknown tool '{name}'"
    try:
        return func(ctx, **args)
    except TypeError as e:
        return f"Error: bad arguments for {name}: {e}"
    except Exception as e:
        return f"Error executing {name}: {e}"
