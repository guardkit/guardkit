#!/usr/bin/env python3
"""TASK-ARCH-COACHSPLIT — GB10 grammar-applies-when-toolless probe (gating step).

WHY THIS EXISTS
===============
The whole TASK-ARCH-COACHSPLIT design (B-min: toolless grammar-enforced Coach
verdict synthesis) rests on ONE empirical claim that must hold on the *actual*
GB10 llama.cpp build before any orchestration is wired:

    "A GBNF grammar passed PER-REQUEST is honoured by llama.cpp when the
     request carries NO `tools` field."

run-13 (TASK-OPS-COACHGRAMMAR) established the *negative*: a route-level
`--grammar-file` is a NO-OP when the request carries `tools` (llama.cpp bypasses
the grammar for tool-bound requests). This probe confirms the *positive* on the
toolless path, AND reproduces the run-13 negative as a control, AND tests the
exact mechanism the harness will use (a top-level per-request `grammar` field,
which is what `ChatOpenAI.bind(extra_body={"grammar": ...})` emits).

If CASE A passes, the architecture is validated — proceed to wire
`invoke_synthesis()`. If CASE A fails, STOP: the fallback is the llama.cpp
upgrade (b9570+) or an alt/higher-quant g31 GGUF (task Implementation notes).

OPERATOR PRECONDITIONS (same as run-15/17/18 recipe)
====================================================
  * Keepalive paused:  sudo systemctl stop llama-swap-keepalive.timer
  * g31 route live (cold-load verified); requesting `gemma4:31b` switches the
    Coach slot to the coach31 set (evicting gc). Confirm `free -m` headroom.
  * This probe issues 3 small requests; it cold-loads g31 (~50 GB) on first call.

USAGE
=====
From the Mac (or any host that can reach the GB10):
    OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
    OPENAI_API_KEY=llama-swap-local-key \
    python3 docs/state/TASK-ARCH-COACHSPLIT/probe_toolless_grammar.py

From the GB10 itself:
    OPENAI_BASE_URL=http://localhost:9000/v1 \
    OPENAI_API_KEY=llama-swap-local-key \
    python3 docs/state/TASK-ARCH-COACHSPLIT/probe_toolless_grammar.py

Override the model with PROBE_MODEL (default: gemma4:31b).
Only depends on the stdlib (urllib) — no extra installs.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://promaxgb10-41b1:9000/v1").rstrip("/")
API_KEY = os.environ.get("OPENAI_API_KEY", "llama-swap-local-key")
MODEL = os.environ.get("PROBE_MODEL", "gemma4:31b")

# The grammar the harness will send. Faithful to the wired design: read the
# primary verdict grammar from the repo so the probe and the implementation
# share one source of truth.
_GRAMMAR_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "research"
    / "dgx-spark"
    / "grammars"
    / "coach-verdict.gbnf"
)
GRAMMAR = _GRAMMAR_PATH.read_text()

# A representative *synthesis* prompt: the Coach is handed deterministic
# evidence + ACs + a player report and asked for ONLY the fenced verdict.
# Deliberately small so the probe is cheap; the point is grammar conformance,
# not reasoning depth. The "malformed-prone" instruction (asking the model to
# ramble with backticks first) stresses the grammar's free-reasoning prefix.
SYNTH_PROMPT = """You are the AutoBuild Coach. You have been given deterministic
evidence and must emit ONLY a verdict — do not investigate.

EVIDENCE BUNDLE (deterministic):
  tests: {"tests_run": 12, "tests_passed": 12}
  coverage: {"line_coverage": 0.91, "branch_coverage": 0.83}
  honesty: {"discrepancies": []}
  plan_audit: {"status": "passed", "severity": "low"}

ACCEPTANCE CRITERIA:
  AC-001: function foo() returns the sum of its args (verified by tests).

PLAYER REPORT: implemented foo(); 12/12 tests pass.

First think briefly (you may use `backticks` and ```fenced``` notes while
reasoning), then end your response with the fenced ```json verdict block:
task_id="TASK-PROBE", turn=1, decision="approve"|"feedback"."""

_FENCE = re.compile(r"```json\s*\n?(.+?)\s*\n?```", re.DOTALL)


def _post(body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return {"ok": True, "status": resp.status, "json": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        return {"ok": False, "status": e.code, "error": detail}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": None, "error": f"{type(e).__name__}: {e}"}


def _content(resp_json: dict) -> str:
    try:
        return resp_json["choices"][0]["message"].get("content") or ""
    except Exception:  # noqa: BLE001
        return ""


def _grammar_conformant(text: str) -> tuple[bool, str]:
    """A grammar-honoured verdict: response ends with a parseable ```json block
    whose last fence is an object with task_id / turn(int) / decision in
    {approve, feedback}. Mirrors coach_output_parser + _validate_coach_decision."""
    matches = _FENCE.findall(text)
    if not matches:
        return False, "no fenced ```json block"
    try:
        obj = json.loads(matches[-1])
    except json.JSONDecodeError as e:
        return False, f"last fence not valid JSON: {e}"
    if not isinstance(obj, dict):
        return False, "last fence is not a JSON object"
    for k in ("task_id", "turn", "decision"):
        if k not in obj:
            return False, f"missing required key {k!r}"
    if not isinstance(obj["turn"], int):
        return False, "turn is not a bare integer"
    if obj["decision"] not in ("approve", "feedback"):
        return False, f"decision not approve|feedback: {obj['decision']!r}"
    return True, "verdict object with task_id/turn(int)/decision"


def _base_body() -> dict:
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": SYNTH_PROMPT}],
        "max_tokens": 16384,
        "temperature": 0.0,
    }


def case(label: str, *, grammar: bool, tools: bool) -> tuple[str, bool, str]:
    body = _base_body()
    if grammar:
        body["grammar"] = GRAMMAR  # per-request, top-level — == bind(extra_body={"grammar":...})
    if tools:
        # A trivial tool to force the tool-bound code path (run-13 control).
        body["tools"] = [{
            "type": "function",
            "function": {
                "name": "noop", "description": "does nothing",
                "parameters": {"type": "object", "properties": {}},
            },
        }]
    r = _post(body)
    if not r["ok"]:
        return label, False, f"HTTP {r['status']}: {r['error'][:300]}"
    text = _content(r["json"])
    conformant, why = _grammar_conformant(text)
    snippet = text[-240:].replace("\n", "\\n")
    return label, conformant, f"{why} | tail: …{snippet}"


def main() -> int:
    print("=" * 72)
    print("TASK-ARCH-COACHSPLIT — toolless-grammar probe")
    print(f"  endpoint : {BASE_URL}/chat/completions")
    print(f"  model    : {MODEL}")
    print(f"  grammar  : {_GRAMMAR_PATH}  ({len(GRAMMAR)} bytes)")
    print("=" * 72)

    # CASE A — THE DESIGN: toolless + per-request grammar. MUST be conformant.
    a_label, a_ok, a_why = case("A toolless+grammar (DESIGN)", grammar=True, tools=False)
    # CASE B — baseline: toolless, no grammar. May or may not be conformant
    #          (shows whether prompt alone suffices; informational only).
    b_label, b_ok, b_why = case("B toolless+no-grammar (baseline)", grammar=False, tools=False)
    # CASE C — run-13 control: tool-bound + grammar. EXPECTED non-conformant
    #          (grammar bypassed for tool-bound requests) OR HTTP 500 tool-parse.
    c_label, c_ok, c_why = case("C toolbound+grammar (run-13 control)", grammar=True, tools=True)

    print()
    for label, ok, why in ((a_label, a_ok, a_why), (b_label, b_ok, b_why), (c_label, c_ok, c_why)):
        mark = "PASS" if ok else "----"
        print(f"  [{mark}] {label}")
        print(f"         {why}")
        print()

    print("=" * 72)
    print("INTERPRETATION")
    print("  • CASE A conformant  → grammar IS honoured toolless. ARCHITECTURE")
    print("    VALIDATED — proceed to wire invoke_synthesis(). This is the gate.")
    print("  • CASE A NOT conformant → STOP. Per-request grammar is not honoured")
    print("    on this build; pivot to the fallback (llama.cpp b9570+ upgrade or")
    print("    alt/higher-quant g31 GGUF) per the task Implementation notes.")
    print("  • CASE C non-conformant / HTTP 500 → reproduces run-13/run-18: tools")
    print("    bypass the grammar and risk the tool-parse-500. Expected. This is")
    print("    the failure the split is designed to eliminate.")
    print("  • CASE B is informational: if it is ALSO conformant, the prompt alone")
    print("    is strong on g31 — but the grammar is the guarantee we ship.")
    print("=" * 72)

    return 0 if a_ok else 1


if __name__ == "__main__":
    sys.exit(main())
