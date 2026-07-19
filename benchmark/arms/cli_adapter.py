"""Wiring for `model_call` against the LOCAL Claude CLI (subscription auth, no API key, no
paid API, no account creation). This is the concrete implementation the real_adapter.py stub
asks for, kept in a separate file so real_adapter.py stays provider-neutral.

WHY A SEPARATE FILE

arms/real_adapter.py is deliberately provider-agnostic (no vendor hardcoded, no network call on
import). This module is the one-time wiring decision: it shells out to the `claude` binary
already installed and authenticated on this machine (subscription session, not an API key), so
no secrets are read and nothing is billed beyond the existing subscription.

HOW IT AVOIDS THE HEADROOM ALIAS COLLISION

The interactive shell aliases `claude` to `headroom wrap claude`, and headroom's wrapper treats
`-p` as its own `--port` flag, which breaks the benchmark's use of `-p` (print/non-interactive
mode). This module calls the real binary directly by resolved path (`shutil.which` against a
subprocess with a controlled PATH, falling back to the known install path
`~/.local/bin/claude`), bypassing the shell alias entirely. It does not use headroom compression;
each call is a args-array subprocess.run, no shell involved, no alias resolution.

HOW EACH CALL IS ISOLATED

Every call is a fresh `claude -p` invocation: no session id is reused, so no conversation state
carries between calls. `--system-prompt` REPLACES the default system prompt with a minimal
verification-only instruction (no CLAUDE.md, no O1 project instructions, no tool access is
needed for a text verdict). The working directory is a neutral scratch directory outside any
project tree, so no CLAUDE.md auto-discovery can pull in Sarthak's personal project context.
This keeps the model call a clean text-in/text-out function, matching what the harness's
isolation contract (arms/base.isolate) assumes: the ONLY thing that differs between the
self-critic and independent arms is whether the prompt includes the reasoning trace, not
incidental context leakage from the CLI environment.

HARD CALL CAP

`CliCallCounter` enforces the plan's ~500-call ceiling. It raises before making a call that
would exceed the cap, so a run degrades loudly rather than burning an unbounded number of CLI
invocations.

TOKENS

Each call requests `--output-format json` and parses the real `usage` block Claude Code reports
(input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens). This is
the metered total for that call, not an assumed constant, matching the contract in
real_adapter.py's docstring.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from .real_adapter import ModelResponse

# Resolved once per process. Prefer the known local install path (this machine's actual binary,
# per `type -a claude` -> "claude is /Users/sarthak/.local/bin/claude"), fall back to PATH
# lookup for portability, explicitly skipping any shell alias (subprocess.run with a list
# argv never goes through the shell or ~/.zshrc aliases regardless).
_KNOWN_PATH = os.path.expanduser("~/.local/bin/claude")

CLI_SYSTEM_PROMPT = (
    "You are a careful verification assistant. You check whether a candidate answer to a "
    "task is correct. Reply with exactly PASS if it is correct, or FLAG followed by one short "
    "reason if it is wrong. Do not use any tools. Do not ask questions. Give only the verdict."
)


def _resolve_cli_path() -> str:
    if os.path.isfile(_KNOWN_PATH) and os.access(_KNOWN_PATH, os.X_OK):
        return _KNOWN_PATH
    found = shutil.which("claude")
    if found:
        return found
    raise RuntimeError(
        "Local Claude CLI binary not found (checked ~/.local/bin/claude and PATH). "
        "The real benchmark run requires the local CLI; install/auth it first."
    )


@dataclass
class CliCallCounter:
    """Hard cap enforcement. Shared across both real arms in one run so the total (self_critic +
    independent) calls, not each arm separately, is what's bounded."""

    cap: int
    made: int = 0

    def note_and_check(self) -> None:
        if self.made >= self.cap:
            raise RuntimeError(
                f"CLI call cap reached ({self.made}/{self.cap}). Stopping before making another "
                "call so the run degrades loudly instead of running past its budget."
            )
        self.made += 1


def _extract_tokens(usage: dict) -> int:
    """Sum the real metered token fields Claude Code's --output-format json reports for one
    call. Includes cache-creation and cache-read tokens because those are real tokens billed/
    consumed by the call, not free; input_tokens + output_tokens alone would undercount."""
    return (
        int(usage.get("input_tokens", 0))
        + int(usage.get("output_tokens", 0))
        + int(usage.get("cache_creation_input_tokens", 0))
        + int(usage.get("cache_read_input_tokens", 0))
    )


def make_cli_model_call(
    model: str = "haiku",
    counter: Optional[CliCallCounter] = None,
    cwd: Optional[str] = None,
    timeout_s: int = 90,
    retries: int = 2,
):
    """Build a `model_call(prompt) -> ModelResponse` function wired to the local Claude CLI.

    model     : alias passed to `--model` (default "haiku", the cheapest/fastest tier, matching
                the plan's "haiku-tier arms" instruction).
    counter   : a CliCallCounter shared across arms to enforce the hard cap. If None, a fresh
                uncapped counter is created (only for ad hoc/manual use; run_real.py always
                passes a shared, capped counter).
    cwd       : working directory for the subprocess. Defaults to a neutral scratch directory
                (not this repo, not any project with a CLAUDE.md) so no project instructions
                leak into the verification prompt.
    timeout_s : per-call subprocess timeout.
    retries   : number of retries on a transient (non-zero exit, timeout) failure before raising.
    """
    cli_path = _resolve_cli_path()
    work_dir = cwd or "/tmp"
    local_counter = counter or CliCallCounter(cap=10_000)

    def model_call(prompt: str) -> ModelResponse:
        local_counter.note_and_check()
        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                proc = subprocess.run(
                    [
                        cli_path,
                        "-p",
                        "--model", model,
                        "--output-format", "json",
                        "--system-prompt", CLI_SYSTEM_PROMPT,
                        prompt,
                    ],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env={**os.environ},
                )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"claude CLI exit {proc.returncode}: {proc.stderr.strip()[:300]}"
                    )
                payload = json.loads(proc.stdout)
                if payload.get("is_error"):
                    raise RuntimeError(f"claude CLI reported error: {payload}")
                text = payload.get("result", "")
                usage = payload.get("usage", {}) or {}
                tokens = _extract_tokens(usage)
                return ModelResponse(text=text, tokens=tokens)
            except Exception as exc:  # noqa: BLE001 - retry loop, re-raised on final attempt
                last_err = exc
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise RuntimeError(f"CLI call failed after {retries + 1} attempts: {exc}") from last_err
        raise RuntimeError(f"unreachable: {last_err}")  # pragma: no cover

    return model_call
