#!/usr/bin/env python3
"""TASK-OPS-COACHMOE01 — Step 1 gate: does the GBNF grammar contain the MoE ramble?

WHY THIS EXISTS
===============
The disqualification of ``gemma4-coach`` (the base Gemma-4 **26B-A4B MoE**,
~3.8B active) as Coach happened as F24 — the run-14 49,720-char ramble — in the
**tool-bound agentic loop**, which TASK-ARCH-COACHSPLIT then *removed* from the
verdict path. Nobody has ever run the MoE on the shipped **B-min toolless +
grammar** path. The known risk this gate addresses:

    The COACHSPLIT grammar gate (`probe_toolless_grammar.py`) ran only against
    g31 (the dense 31B). The one logged MoE ramble (COACH31B probe A, 27,006c on
    the APPROVE path) was toolless but had NO grammar attached. Whether a
    per-request GBNF ``grammar`` *contains* the MoE's ramble is untested.

The grammar (``coach-verdict.gbnf``) is "free-reasoning prefix + guaranteed
final verdict fence". Its ``prefix ::= ( [^\\`] | "\\`" )*`` is **unbounded text**
— so the grammar CANNOT, by construction, force convergence before the
``max_tokens`` cap (the grammar header's own "RESIDUAL RISK" note states this).
The gate is therefore a genuine empirical question: GIVEN the grammar, does the
MoE *choose* to emit the verdict fence within the token budget, or ramble in the
prefix to ``finish_reason=length`` with no verdict?

    TRUST THE METRIC, NOT PATTERN-MATCHING ON OUTPUT.
    The authoritative convergence signal is ``finish_reason``:
      * ``stop``   + a parseable final ```json verdict  ⇒ CONTAINED (the gate's PASS)
      * ``length`` (hit max_tokens), or no verdict       ⇒ RAMBLE SURVIVED (FAIL)
    (per docs/state/TASK-OPS-COACH31B/README.md:123-128).

ARMS (all TOOLLESS, against gemma4-coach, temp 0.0 — matching the production
B-min ``_build_synthesis_model`` which builds ChatOpenAI(temperature=0.0)):

  1. A_rambleprone_grammar       probe-A "verify yourself" APPROVE shape + grammar
                                 — the WORST case (the prompt that spiralled to 27,006c).
  2. A_rambleprone_nogrammar     same prompt, NO grammar — control: does it still
                                 ramble on this build/route, or does --reasoning auto
                                 already converge?
  3. E_synthesis_approve_grammar production B-min TOOLLESS-SYNTHESIS APPROVE prompt + grammar.
  4. F_synthesis_feedback_grammar production B-min TOOLLESS-SYNTHESIS FEEDBACK prompt + grammar.
  5. A_rambleprone_grammar_rb<N> probe-A shape + grammar + reasoning_budget=<N>
                                 — Lever-2 (GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET):
                                 if grammar alone rambles, does a reasoning cap contain it?
                                 This is the FIRST live exercise of the reasoning_budget
                                 wire-field on this llama.cpp build (never logged before).

AC-001 requires the APPROVE and FEEDBACK paths with grammar (arms 1/3 approve,
4 feedback); arms 2 (control) and 5 (Lever-2) are enrichment that also de-risk
the Step-2/Step-3 decision.

OPERATOR PRECONDITIONS
======================
  * gemma4-coach is in the keepalive allowlist, so it is normally already warm —
    this probe targets ONLY gemma4-coach (no g31 eviction, NO config edit). The
    COACH31B keepalive/eviction hazard does NOT apply here.
  * Do NOT edit /opt/llama-swap/config/config.yaml while this probe is in flight
    (a -watch-config matrix reload returns 502/500 to in-flight requests).

USAGE
=====
From the GB10 itself:
    OPENAI_BASE_URL=http://localhost:9000/v1 \
    OPENAI_API_KEY=llama-swap-local-key \
    python3 docs/state/TASK-OPS-COACHMOE01/probe_toolless_grammar_gc.py \
        --out docs/state/TASK-OPS-COACHMOE01/probes

Override the model with --model (default: gemma4-coach) and the reasoning-budget
arm value with --reasoning-budget (default: 2048). Only depends on the stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:9000/v1").rstrip("/")
API_KEY = os.environ.get("OPENAI_API_KEY", "llama-swap-local-key")

# Packaged grammar (the one the orchestrator wires at runtime; byte-identical to
# docs/research/dgx-spark/grammars/coach-verdict.gbnf — parity pinned by
# tests/unit/test_coach_grammar.py).
_GRAMMAR_PATH = (
    Path(__file__).resolve().parents[3]
    / "guardkit"
    / "orchestrator"
    / "grammars"
    / "coach-verdict.gbnf"
)
GRAMMAR = _GRAMMAR_PATH.read_text(encoding="utf-8")

# Production synthesis ceiling (guardkitfactory _SYNTHESIS_MAX_TOKENS_DEFAULT).
MAX_TOKENS = 16384

# ---------------------------------------------------------------------------
# Coach prompt scaffolding — faithful mirror of COACH31B probe_harness.py
# (which itself mirrors agent_invoker._build_coach_prompt).
# ---------------------------------------------------------------------------

_DECISION_FORMAT = """
## Decision Format

End your response with a fenced JSON block. Do **NOT** use Bash to write a file —
the orchestrator parses your decision directly from your response text.

The fenced JSON block MUST appear at the end of your response, after all prose
reasoning, in this exact form:

```json
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "approve" | "feedback",
  "validation_results": {{ "tests_run": true, "tests_passed": true }},
  "criteria_verification": [
    {{ "criterion_id": "AC-001", "result": "verified", "notes": "..." }}
  ],
  "rationale": "Why you decided this"
}}
```

**CRITICAL**: The fenced ```json block MUST be the LAST thing in your response.
Do not write any prose after the closing fence. The orchestrator takes only the
LAST fenced block.
"""

# The B-min production "TOOLLESS SYNTHESIS" banner, verbatim from
# agent_invoker._build_coach_prompt (synthesis=True, evidence_bundle present).
_SYNTHESIS_BANNER = """\
**TOOLLESS SYNTHESIS** — You have NO tools available (no Read, Bash, Grep, or
Glob). Do not attempt to run tests or read files; you cannot. The orchestrator
has ALREADY run the tests, coverage, honesty checks, plan audit, BDD oracle,
and architectural review independently — their results are in the Deterministic
Evidence Bundle above. Base your verdict ENTIRELY on that evidence, the
acceptance criteria, the Player's report, and the honesty verification.

"""


def _verify_yourself_prompt(task_id, turn, requirements, criteria, player_report):
    """Probe-A shape: responsibilities tell the Coach to RUN THE TESTS ITSELF, but
    no tools are provided. This is the prompt that made the MoE spiral (27,006c,
    finish=length, no verdict) on the APPROVE path."""
    crit = "\n".join(f"- **{c['id']}**: {c['text']}" for c in criteria)
    return f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

## Original Requirements

{requirements}

## Acceptance Criteria to Verify

Verify EACH criterion and create a criteria_verification entry:

{crit}

## Player's Report

{json.dumps(player_report, indent=2)}

## Your Responsibilities

1. Independently verify the Player's claims
2. Run the tests yourself (don't trust Player's report)
3. Verify EACH acceptance criterion systematically
4. Either APPROVE or provide specific FEEDBACK
{_DECISION_FORMAT.format(task_id=task_id, turn=turn)}"""


def _synthesis_prompt(task_id, turn, requirements, criteria, player_report, evidence):
    """B-min production shape: a rendered Deterministic Evidence Bundle + the
    TOOLLESS SYNTHESIS banner ("orchestrator already ran everything; synthesise
    the verdict from the evidence")."""
    crit = "\n".join(f"- **{c['id']}**: {c['text']}" for c in criteria)
    return f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

## Deterministic Evidence Bundle

{json.dumps(evidence, indent=2)}

## Original Requirements

{requirements}

## Acceptance Criteria to Verify

Verify EACH criterion and create a criteria_verification entry:

{crit}

## Player's Report

{json.dumps(player_report, indent=2)}

{_SYNTHESIS_BANNER}## Your Responsibilities

1. Synthesise a verdict from the Deterministic Evidence Bundle above — do NOT
   attempt to investigate (you have no tools)
2. Treat the bundle's independent_tests / tests / coverage as the authoritative
   test signal (the orchestrator ran them, not the Player)
3. Verify EACH acceptance criterion against the evidence systematically
4. Honour the absence-of-failure guards: an ABSENT or zero-cardinality oracle is
   NOT a pass — when the evidence for a criterion is missing, that is FEEDBACK
{_DECISION_FORMAT.format(task_id=task_id, turn=turn)}"""


# --- Fixtures (slugify=approve, retry=feedback — same shapes COACH31B used) ---

_APPROVE_REQ = (
    "Add a `slugify(text: str) -> str` helper to `src/text_utils.py` that "
    "lowercases, strips, and replaces runs of non-alphanumeric chars with a "
    "single hyphen. Add unit tests."
)
_APPROVE_CRIT = [
    {"id": "AC-001", "text": "slugify lowercases and hyphenates non-alphanumeric runs"},
    {"id": "AC-002", "text": "Unit tests cover empty string, leading/trailing spaces, and unicode"},
]
_APPROVE_REPORT = {
    "task_id": "TASK-DEMO-A01", "turn": 1,
    "files_created": ["src/text_utils.py", "tests/test_text_utils.py"],
    "files_modified": [],
    "tests_written": ["test_basic", "test_empty", "test_unicode", "test_trim"],
    "tests_run": True, "tests_passed": True,
    "test_output_summary": "4 passed in 0.12s",
    "requirements_addressed": ["AC-001", "AC-002"],
    "completion_promises": [
        {"criterion_id": "AC-001", "status": "complete", "evidence": "src/text_utils.py:1-14 slugify impl"},
        {"criterion_id": "AC-002", "status": "complete", "evidence": "tests/test_text_utils.py 4 tests pass"},
    ],
}
_APPROVE_EVIDENCE = {
    "independent_tests": {"tests_run": 4, "tests_passed": 4, "command": "pytest tests/test_text_utils.py", "summary": "4 passed in 0.12s"},
    "coverage": {"line_coverage": 0.93, "branch_coverage": 0.81},
    "honesty": {"discrepancies": []},
    "plan_audit": {"status": "passed", "severity": "low"},
}

_FEEDBACK_REQ = (
    "Add a `retry(fn, attempts=3)` decorator to `src/retry.py` with exponential "
    "backoff. Add unit tests proving it retries on exception and gives up after "
    "`attempts`."
)
_FEEDBACK_CRIT = [
    {"id": "AC-001", "text": "retry retries the wrapped fn on exception up to `attempts` times"},
    {"id": "AC-002", "text": "Backoff is exponential between attempts"},
    {"id": "AC-003", "text": "Unit tests prove both retry and give-up behaviour"},
]
_FEEDBACK_REPORT = {
    "task_id": "TASK-DEMO-B01", "turn": 1,
    "files_created": ["src/retry.py"], "tests_written": [],
    "tests_run": True, "tests_passed": False,
    "test_output_summary": "1 failed, 0 passed: test_gives_up — AssertionError: expected 3 calls, got 1",
    "requirements_addressed": ["AC-001"],
    "completion_promises": [
        {"criterion_id": "AC-001", "status": "partial", "evidence": "src/retry.py retry loop present"},
        {"criterion_id": "AC-002", "status": "missing", "evidence": "no backoff implemented"},
        {"criterion_id": "AC-003", "status": "missing", "evidence": "no give-up test"},
    ],
}
_FEEDBACK_EVIDENCE = {
    "independent_tests": {"tests_run": 1, "tests_passed": 0, "tests_failed": 1, "command": "pytest tests/test_retry.py", "summary": "1 failed"},
    "coverage": {"line_coverage": 0.41, "branch_coverage": 0.30},
    "honesty": {"discrepancies": []},
    "plan_audit": {"status": "passed", "severity": "low"},
}

_FENCE = re.compile(r"```json\s*\n?(.+?)\s*\n?```", re.DOTALL)


def _post(body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        method="POST",
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            payload = json.loads(resp.read())
            return {"ok": True, "status": resp.status, "json": payload, "wall_s": time.monotonic() - t0}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode(errors="replace"), "wall_s": time.monotonic() - t0}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": None, "error": f"{type(e).__name__}: {e}", "wall_s": time.monotonic() - t0}


def _grammar_conformant(text: str) -> tuple[bool, str, dict | None]:
    """A grammar-honoured verdict ends with a parseable ```json object carrying
    task_id / turn(int) / decision in {approve,feedback}. Mirrors
    coach_output_parser + _validate_coach_decision."""
    matches = _FENCE.findall(text)
    if not matches:
        return False, "no fenced ```json block", None
    try:
        obj = json.loads(matches[-1])
    except json.JSONDecodeError as e:
        return False, f"last fence not valid JSON: {e}", None
    if not isinstance(obj, dict):
        return False, "last fence is not a JSON object", None
    for k in ("task_id", "turn", "decision"):
        if k not in obj:
            return False, f"missing required key {k!r}", obj
    if not isinstance(obj["turn"], int):
        return False, "turn is not a bare integer", obj
    if obj["decision"] not in ("approve", "feedback"):
        return False, f"decision not approve|feedback: {obj['decision']!r}", obj
    return True, "verdict object with task_id/turn(int)/decision", obj


def run_arm(label: str, prompt: str, *, grammar: bool, reasoning_budget: int | None,
            expect_decision: str, model: str) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.0,
    }
    extra: dict = {}
    if grammar:
        body["grammar"] = GRAMMAR  # per-request, top-level (== bind(extra_body={"grammar":...}))
    if reasoning_budget is not None:
        body["reasoning_budget"] = reasoning_budget  # Lever-2 wire-field (llama.cpp)
    r = _post(body)
    rec: dict = {
        "label": label, "model": model, "grammar": grammar,
        "reasoning_budget": reasoning_budget, "expect_decision": expect_decision,
        "wall_s": round(r["wall_s"], 2), "http_ok": r["ok"], "http_status": r["status"],
    }
    if not r["ok"]:
        rec["error"] = (r.get("error") or "")[:500]
        return rec
    j = r["json"]
    choice = (j.get("choices") or [{}])[0]
    msg = choice.get("message", {}) or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    usage = j.get("usage", {}) or {}
    finish = choice.get("finish_reason")
    conformant, why, verdict = _grammar_conformant(content)
    completion_tokens = usage.get("completion_tokens")
    tok_s = round(completion_tokens / r["wall_s"], 1) if completion_tokens and r["wall_s"] else None
    rec.update({
        "finish_reason": finish,
        "content_chars": len(content),
        "reasoning_chars": len(reasoning),
        "total_chars": len(content) + len(reasoning),
        "completion_tokens": completion_tokens,
        "tok_s": tok_s,
        "grammar_conformant": conformant,
        "conformance_detail": why,
        "verdict_decision": (verdict or {}).get("decision") if verdict else None,
        "decision_matches_expected": ((verdict or {}).get("decision") == expect_decision) if verdict else False,
        "criteria_verification_n": len((verdict or {}).get("criteria_verification", []) or []) if verdict else 0,
        "tail": content[-280:].replace("\n", "\\n"),
    })
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4-coach")
    ap.add_argument("--reasoning-budget", type=int, default=2048)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "probes"))
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("TASK-OPS-COACHMOE01 — gc grammar-containment probe (Step 1 gate)")
    print(f"  endpoint : {BASE_URL}/chat/completions")
    print(f"  model    : {args.model}")
    print(f"  grammar  : {_GRAMMAR_PATH.name}  ({len(GRAMMAR)} bytes)")
    print(f"  max_tok  : {MAX_TOKENS}   temp: 0.0   reasoning_budget arm: {args.reasoning_budget}")
    print("=" * 78)

    arms = [
        ("A_rambleprone_grammar",
         _verify_yourself_prompt("TASK-DEMO-A01", 1, _APPROVE_REQ, _APPROVE_CRIT, _APPROVE_REPORT),
         {"grammar": True, "reasoning_budget": None, "expect_decision": "approve"}),
        ("A_rambleprone_nogrammar",
         _verify_yourself_prompt("TASK-DEMO-A01", 1, _APPROVE_REQ, _APPROVE_CRIT, _APPROVE_REPORT),
         {"grammar": False, "reasoning_budget": None, "expect_decision": "approve"}),
        ("E_synthesis_approve_grammar",
         _synthesis_prompt("TASK-DEMO-A01", 1, _APPROVE_REQ, _APPROVE_CRIT, _APPROVE_REPORT, _APPROVE_EVIDENCE),
         {"grammar": True, "reasoning_budget": None, "expect_decision": "approve"}),
        ("F_synthesis_feedback_grammar",
         _synthesis_prompt("TASK-DEMO-B01", 1, _FEEDBACK_REQ, _FEEDBACK_CRIT, _FEEDBACK_REPORT, _FEEDBACK_EVIDENCE),
         {"grammar": True, "reasoning_budget": None, "expect_decision": "feedback"}),
        (f"A_rambleprone_grammar_rb{args.reasoning_budget}",
         _verify_yourself_prompt("TASK-DEMO-A01", 1, _APPROVE_REQ, _APPROVE_CRIT, _APPROVE_REPORT),
         {"grammar": True, "reasoning_budget": args.reasoning_budget, "expect_decision": "approve"}),
    ]

    results = []
    for label, prompt, kw in arms:
        print(f"\n▶ {label} ...", flush=True)
        rec = run_arm(label, prompt, model=args.model, **kw)
        results.append(rec)
        # Write the full transcript per arm for the audit trail.
        (out_dir / f"{label}.json").write_text(json.dumps(rec, indent=2))
        mark = "PASS" if rec.get("grammar_conformant") else "----"
        print(f"  [{mark}] finish={rec.get('finish_reason')} "
              f"content={rec.get('content_chars')}c reasoning={rec.get('reasoning_chars')}c "
              f"tok/s={rec.get('tok_s')} wall={rec.get('wall_s')}s "
              f"decision={rec.get('verdict_decision')} (expect {kw['expect_decision']}) "
              f"crit_n={rec.get('criteria_verification_n')}")
        if not rec.get("http_ok"):
            print(f"         HTTP {rec.get('http_status')}: {rec.get('error','')[:200]}")
        else:
            print(f"         {rec.get('conformance_detail')}")

    summary_path = out_dir / "gc-grammar-probe-summary.json"
    summary_path.write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 78)
    print("SUMMARY (trust finish_reason; ramble = finish=length OR no verdict)")
    print("-" * 78)
    print(f"{'arm':<34}{'finish':<8}{'content':>8}{'reason':>8}{'tok/s':>7}{'wall':>7}  verdict")
    for r in results:
        print(f"{r['label']:<34}{str(r.get('finish_reason')):<8}"
              f"{str(r.get('content_chars')):>8}{str(r.get('reasoning_chars')):>8}"
              f"{str(r.get('tok_s')):>7}{str(r.get('wall_s')):>7}  "
              f"{r.get('verdict_decision')} ({'ok' if r.get('decision_matches_expected') else 'MISS'})")
    print("=" * 78)

    # GATE verdict: the production B-min paths (synthesis approve + feedback) MUST
    # be contained by grammar. The ramble-prone arm is the worst-case stress.
    prod = {r["label"]: r for r in results}
    gate_arms = ["E_synthesis_approve_grammar", "F_synthesis_feedback_grammar"]
    gate_pass = all(prod.get(a, {}).get("grammar_conformant") for a in gate_arms)
    stress = prod.get("A_rambleprone_grammar", {})
    print("\nGATE (AC-001):")
    print(f"  production B-min approve+feedback contained by grammar: "
          f"{'PASS' if gate_pass else 'FAIL'}")
    print(f"  worst-case ramble-prone approve contained by grammar : "
          f"{'PASS' if stress.get('grammar_conformant') else 'FAIL (finish=%s, %sc)' % (stress.get('finish_reason'), stress.get('content_chars'))}")
    print(f"\n  artifacts: {out_dir}/  (summary: {summary_path.name})")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
