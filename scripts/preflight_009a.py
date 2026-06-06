#!/usr/bin/env python3
"""TASK-HMIG-009A preflight — AC-001A + AC-001B.

Verifies that the operator-selected AutoBuild Player model
(default: ``qwen36-workhorse``) is reachable on the live GB10 llama-swap
AND that it emits well-formed ``tool_use`` / ``tool_calls`` blocks in
response to the actual design-phase prompt used by the canary.

This is the **load-bearing post-reconfig gate** for TASK-HMIG-009A.
Pass: proceed to AC-001C/D (end-to-end one-rep smokes) then the 12-run
batch. Fail on AC-001B: halt — file a parser-config audit task scoped
to the current model post-reconfig.

Probes both wire formats so we know which harness will struggle if
either fails:

* **OpenAI-compat** (``POST :9000/v1/chat/completions``) — what the
  LangGraph harness uses via ``init_chat_model("openai:...")``.
* **Anthropic-compat** (``POST :9000/v1/messages``) — what the SDK
  harness uses via ``claude-agent-sdk`` → bundled Claude CLI →
  ``ANTHROPIC_BASE_URL``. This is the historical F2 failure path.

Usage::

    # Default — qwen36-workhorse against the configured GB10 endpoint
    python scripts/preflight_009a.py

    # Try a different model (e.g. compare against qwen3-coder-30b control)
    python scripts/preflight_009a.py --model qwen3-coder-30b

    # Different endpoint
    python scripts/preflight_009a.py --endpoint http://localhost:9000

    # Skip one wire format (e.g. if you only care about the SDK path)
    python scripts/preflight_009a.py --skip-openai

See ``tasks/backlog/hmig-pre-canary-fixes/TASK-HMIG-009A-...md`` for the
full AC list and ``.guardkit/autobuild/TASK-REV-HMIG-canary-set.json``
for the model-choice audit trail.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from guardkit.orchestrator.quality_gates.task_work_interface import (  # noqa: E402
    TaskWorkInterface,
)

DEFAULT_ENDPOINT = "http://promaxgb10-41b1:9000"
DEFAULT_MODEL = "qwen36-workhorse"
DEFAULT_TASK_ID = "TASK-FIX-A7D3"
DEFAULT_OUT_DIR = ".guardkit/autobuild/TASK-HMIG-009A-canary/preflight"


# Tool surface used by the autobuild design phase
# (see task_work_interface.py: ClaudeAgentOptions(allowed_tools=[...])).
# Replicated here with minimal-but-realistic schemas so the model has a
# representative surface to call against.
_TOOL_DEFS = [
    ("Read",  "Read a file from the local filesystem.",
     {"file_path": ("string", "Absolute path to the file")}, ["file_path"]),
    ("Write", "Write contents to a file (overwrite if exists).",
     {"file_path": ("string", "Absolute path"),
      "content":   ("string", "File contents")}, ["file_path", "content"]),
    ("Edit",  "Replace one string in a file with another.",
     {"file_path":  ("string", "Absolute path"),
      "old_string": ("string", "Exact text to replace"),
      "new_string": ("string", "Replacement text")},
     ["file_path", "old_string", "new_string"]),
    ("Bash",  "Run a bash command and return its output.",
     {"command":     ("string", "Shell command to run"),
      "description": ("string", "What this command does")},
     ["command", "description"]),
    ("Grep",  "Search files for a regex pattern.",
     {"pattern": ("string", "Regex pattern"),
      "path":    ("string", "Search root")}, ["pattern"]),
    ("Glob",  "Find files matching a glob pattern.",
     {"pattern": ("string", "Glob pattern"),
      "path":    ("string", "Search root")}, ["pattern"]),
]


def _openai_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": t, "description": d}
                        for k, (t, d) in props.items()
                    },
                    "required": required,
                },
            },
        }
        for name, desc, props, required in _TOOL_DEFS
    ]


def _anthropic_tools() -> list[dict]:
    return [
        {
            "name": name,
            "description": desc,
            "input_schema": {
                "type": "object",
                "properties": {
                    k: {"type": t, "description": d} for k, (t, d) in props.items()
                },
                "required": required,
            },
        }
        for name, desc, props, required in _TOOL_DEFS
    ]


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def _verdict(label: str, passed: bool, detail: str) -> None:
    icon = _color("✓", "32") if passed else _color("✗", "31")
    status = _color("PASS", "32") if passed else _color("FAIL", "31")
    print(f"  {icon} {label}: {status} — {detail}")


def ac_001a(endpoint: str, model: str) -> tuple[bool, str]:
    """AC-001A — endpoint reachable, model listed, tiny completion returns content."""
    try:
        r = httpx.get(f"{endpoint}/v1/models", timeout=10)
        r.raise_for_status()
        models = [m["id"] for m in r.json().get("data", [])]
    except Exception as e:
        return False, f"GET {endpoint}/v1/models failed: {e}"

    if model not in models:
        return False, (
            f"model {model!r} not listed. Available: {', '.join(sorted(models))}"
        )

    try:
        r = httpx.post(
            f"{endpoint}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with the single word OK."}],
                "max_tokens": 10,
            },
            timeout=60,
        )
        r.raise_for_status()
        content = (r.json()["choices"][0]["message"].get("content") or "").strip()
    except Exception as e:
        return False, f"completion smoke failed: {e}"

    if not content:
        return False, "completion returned empty content"

    return True, f"{model} listed; completion: {content[:50]!r}"


def build_design_prompt(task_id: str) -> str:
    """Build the actual design-phase prompt the canary will send."""
    iface = TaskWorkInterface(worktree_path=REPO_ROOT)
    return iface._build_autobuild_design_prompt(task_id, {"docs": "minimal"})


def ac_001b_openai(
    endpoint: str, model: str, prompt: str, out_dir: Path
) -> tuple[bool, str]:
    """AC-001B (OpenAI-compat) — expect tool_calls in chat-completions response."""
    try:
        r = httpx.post(
            f"{endpoint}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "tools": _openai_tools(),
                "max_tokens": 2000,
            },
            timeout=300,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        return False, f"POST /v1/chat/completions failed: {e}"

    (out_dir / "AC-001B-openai-response.json").write_text(json.dumps(payload, indent=2))

    msg = payload["choices"][0]["message"]
    tool_calls = msg.get("tool_calls") or []
    content = (msg.get("content") or "").strip()

    if tool_calls:
        names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
        return True, f"{len(tool_calls)} tool_call(s): {names}"

    preview = content[:200].replace("\n", " ") if content else "(empty)"
    return False, f"no tool_calls; model returned prose: {preview!r}"


def ac_001b_anthropic(
    endpoint: str, model: str, prompt: str, out_dir: Path
) -> tuple[bool, str]:
    """AC-001B (Anthropic-compat) — expect content[].type=='tool_use'. Historical F2 path."""
    try:
        r = httpx.post(
            f"{endpoint}/v1/messages",
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": "vllm-local-key",
            },
            json={
                "model": model,
                "max_tokens": 2000,
                "tools": _anthropic_tools(),
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=300,
        )
    except Exception as e:
        return False, f"POST /v1/messages failed (transport): {e}"

    # Anthropic-compat endpoint may not exist on this llama-swap deployment.
    if r.status_code == 404:
        return False, (
            f"/v1/messages returned 404 — Anthropic-compat endpoint not available "
            f"on {endpoint}. SDK harness will need a different deployment."
        )

    try:
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        body = r.text[:200] if hasattr(r, "text") else ""
        return False, f"POST /v1/messages failed: {e}; body: {body!r}"

    (out_dir / "AC-001B-anthropic-response.json").write_text(json.dumps(payload, indent=2))

    blocks = payload.get("content", [])
    tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
    texts = [b for b in blocks if b.get("type") == "text"]

    if tool_uses:
        names = [tu.get("name", "?") for tu in tool_uses]
        return True, f"{len(tool_uses)} tool_use block(s): {names}"

    text_preview = (
        texts[0].get("text", "")[:200].replace("\n", " ") if texts else "(no text block)"
    )
    return False, f"no tool_use blocks; model returned text: {text_preview!r}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TASK-HMIG-009A preflight (AC-001A + 001B against both wire formats)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                        help=f"llama-swap base URL (default: {DEFAULT_ENDPOINT})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Model alias to probe (default: {DEFAULT_MODEL})")
    parser.add_argument("--task-id", default=DEFAULT_TASK_ID,
                        help=f"Task ID for the design-phase prompt (default: {DEFAULT_TASK_ID})")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                        help=f"Where to save raw responses (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--skip-openai", action="store_true",
                        help="Skip the OpenAI-compat probe (LangGraph wire format)")
    parser.add_argument("--skip-anthropic", action="store_true",
                        help="Skip the Anthropic-compat probe (SDK wire format)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 72
    print(f"\n{sep}")
    print(f"TASK-HMIG-009A preflight — {datetime.now().isoformat(timespec='seconds')}")
    print(sep)
    print(f"  Endpoint: {args.endpoint}")
    print(f"  Model:    {args.model}")
    print(f"  Task ID:  {args.task_id}")
    print(f"  Out dir:  {out_dir}\n")

    # AC-001A
    print(f"{sep}\nAC-001A — endpoint reachable + model listed + small completion\n{sep}")
    a_pass, a_detail = ac_001a(args.endpoint, args.model)
    _verdict("AC-001A", a_pass, a_detail)
    if not a_pass:
        print(f"\n{_color('✗ HALT', '31')}: AC-001A failed. Cannot proceed to AC-001B.\n")
        return 1

    # AC-001B
    print(f"\n{sep}\nAC-001B — design-phase prompt + tool surface → expect tool_use/tool_calls\n{sep}")
    print(f"Building design-phase prompt for {args.task_id}...")
    prompt = build_design_prompt(args.task_id)
    print(f"  Prompt length: {len(prompt)} chars\n")

    results: list[tuple[str, bool, str]] = []

    if not args.skip_openai:
        print("Probing OpenAI-compat (POST /v1/chat/completions) — LangGraph wire format...")
        ok, detail = ac_001b_openai(args.endpoint, args.model, prompt, out_dir)
        _verdict("AC-001B [OpenAI-compat]", ok, detail)
        results.append(("AC-001B [OpenAI-compat / LangGraph]", ok, detail))

    if not args.skip_anthropic:
        print("\nProbing Anthropic-compat (POST /v1/messages) — SDK wire format (historical F2 path)...")
        ok, detail = ac_001b_anthropic(args.endpoint, args.model, prompt, out_dir)
        _verdict("AC-001B [Anthropic-compat]", ok, detail)
        results.append(("AC-001B [Anthropic-compat / SDK]", ok, detail))

    # Summary
    print(f"\n{sep}\nSummary\n{sep}")
    _verdict("AC-001A", a_pass, a_detail)
    for name, ok, detail in results:
        _verdict(name, ok, detail)
    print(f"\n  Raw responses: {out_dir}/")

    all_green = a_pass and all(ok for _, ok, _ in results)

    print(f"\n{sep}")
    if all_green:
        print(f"{_color('✓ ALL GREEN', '32')} — safe to proceed to AC-001C/D, then 12-run batch.")
        print(sep)
        print("\nNext steps:\n")
        print(f"  # AC-001C — SDK end-to-end one-rep smoke")
        print(f"  GUARDKIT_HARNESS=sdk \\")
        print(f"    guardkit autobuild task {args.task_id} --no-pre-loop")
        print()
        print(f"  # AC-001D — LangGraph end-to-end one-rep smoke")
        print(f"  GUARDKIT_HARNESS=langgraph \\")
        print(f"    guardkit autobuild task {args.task_id} --no-pre-loop")
        print()
        print(f"  # AC-003 — 12-run batch (~10h on GB10)")
        print(f"  python scripts/canary_validation_runner.py --variant 009a")
        print(f"  python scripts/canary_validation_runner.py --variant 009a --aggregate")
        print()
        return 0

    print(f"{_color('✗ HALT', '31')} — preflight RED. Inspect raw responses in {out_dir}/")
    print(sep)
    print("\nDiagnosis hints:")
    print("  - If only [Anthropic-compat] failed → SDK harness path is broken; LangGraph may work.")
    print("  - If only [OpenAI-compat] failed → LangGraph path is broken; SDK may work.")
    print("  - If both failed → post-reconfig llama-swap has not resolved marker-contract for")
    print(f"    this model. File a parser-config audit task scoped to {args.model} specifically.")
    print(f"  - Try a control: python scripts/preflight_009a.py --model qwen3-coder-30b")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
