#!/usr/bin/env python3
"""TASK-OPS-COACH31B — single-shot A/B Coach probe harness.

Sends a set of representative Coach prompts (mirroring
``agent_invoker._build_coach_prompt``) to an OpenAI-compatible
``/v1/chat/completions`` endpoint and records, per probe:

* JSON-verdict discipline — does the response END with a valid fenced
  ```json block carrying task_id / turn / decision?
* tool-calling discipline — given ``tools``, does it emit a clean
  ``tool_calls`` entry (vs prose)?
* convergence — reasoning_content length, content length, completion
  tokens, latency, finish_reason.
* verdict quality — extracted ``decision`` vs the probe's known answer.

Usage:
    probe_harness.py --base-url http://localhost:9000/v1 \
        --model gemma4-coach --label baseline-gc \
        --out docs/state/TASK-OPS-COACH31B/probes

The harness is substrate-agnostic — point ``--model`` at ``gemma4-coach``
for the baseline arm and ``gemma4:31b`` (or a standalone port) for the
31B arm. Coach posture (temp 0.1, top_p 0.9) is sent explicitly so the
two arms are compared under identical decoding params.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# --- Coach prompt scaffolding (trimmed mirror of _build_coach_prompt) -------

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


def coach_prompt(task_id, turn, requirements, criteria, player_report, extra=""):
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
{extra}
## Your Responsibilities

1. Independently verify the Player's claims
2. Run the tests yourself (don't trust Player's report)
3. Verify EACH acceptance criterion systematically
4. Either APPROVE or provide specific FEEDBACK
{_DECISION_FORMAT.format(task_id=task_id, turn=turn)}"""


# --- Probe set --------------------------------------------------------------

READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file at the given path so you can independently verify the Player's claims.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or repo-relative file path to read"}
            },
            "required": ["path"],
        },
    },
}
RUN_TESTS_TOOL = {
    "type": "function",
    "function": {
        "name": "run_tests",
        "description": "Run the test suite and return pass/fail counts so you do not have to trust the Player's report.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The pytest/npm/dotnet command to run"}
            },
            "required": ["command"],
        },
    },
}


def build_probes():
    probes = []

    # Probe A — clean approve, no tools. Known answer: approve.
    probes.append({
        "id": "A_clean_approve",
        "expect_decision": "approve",
        "tools": None,
        "messages": [{"role": "user", "content": coach_prompt(
            task_id="TASK-DEMO-A01", turn=1,
            requirements="Add a `slugify(text: str) -> str` helper to `src/text_utils.py` that lowercases, strips, and replaces runs of non-alphanumeric chars with a single hyphen. Add unit tests.",
            criteria=[
                {"id": "AC-001", "text": "slugify lowercases and hyphenates non-alphanumeric runs"},
                {"id": "AC-002", "text": "Unit tests cover empty string, leading/trailing spaces, and unicode"},
            ],
            player_report={
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
            })}],
    })

    # Probe B — clear feedback, no tools. Known answer: feedback.
    probes.append({
        "id": "B_clear_feedback",
        "expect_decision": "feedback",
        "tools": None,
        "messages": [{"role": "user", "content": coach_prompt(
            task_id="TASK-DEMO-B01", turn=1,
            requirements="Add a `retry(fn, attempts=3)` decorator to `src/retry.py` with exponential backoff. Add unit tests proving it retries on exception and gives up after `attempts`.",
            criteria=[
                {"id": "AC-001", "text": "retry retries the wrapped fn on exception up to `attempts` times"},
                {"id": "AC-002", "text": "Backoff is exponential between attempts"},
                {"id": "AC-003", "text": "Unit tests prove both retry and give-up behaviour"},
            ],
            player_report={
                "task_id": "TASK-DEMO-B01", "turn": 1,
                "files_created": ["src/retry.py"],
                "files_modified": [],
                "tests_written": [],
                "tests_run": True, "tests_passed": False,
                "test_output_summary": "1 failed, 0 passed: test_gives_up — AssertionError: expected 3 calls, got 1",
                "requirements_addressed": ["AC-001"],
                "requirements_remaining": ["AC-002", "AC-003"],
                "completion_promises": [
                    {"criterion_id": "AC-001", "status": "complete", "evidence": "src/retry.py"},
                    {"criterion_id": "AC-002", "status": "incomplete", "evidence": "no backoff implemented"},
                    {"criterion_id": "AC-003", "status": "incomplete", "evidence": "tests fail / missing"},
                ],
            })}],
    })

    # Probe C — tool-calling discipline. Given tools, expect a clean tool_call.
    probes.append({
        "id": "C_tool_calling",
        "expect_decision": None,  # we expect a tool_call, not a verdict, on turn 1
        "tools": [READ_FILE_TOOL, RUN_TESTS_TOOL],
        "messages": [{"role": "user", "content": coach_prompt(
            task_id="TASK-DEMO-C01", turn=1,
            requirements="Implement `parse_iso8601(s) -> datetime` in `src/dates.py`. Add tests.",
            criteria=[
                {"id": "AC-001", "text": "parse_iso8601 parses valid ISO-8601 timestamps"},
                {"id": "AC-002", "text": "Tests cover timezone-aware and naive inputs"},
            ],
            player_report={
                "task_id": "TASK-DEMO-C01", "turn": 1,
                "files_created": ["src/dates.py", "tests/test_dates.py"],
                "tests_run": True, "tests_passed": True,
                "test_output_summary": "6 passed",
                "requirements_addressed": ["AC-001", "AC-002"],
                "completion_promises": [
                    {"criterion_id": "AC-001", "status": "complete", "evidence": "src/dates.py:1-30"},
                    {"criterion_id": "AC-002", "status": "complete", "evidence": "tests/test_dates.py"},
                ],
            },
            extra="\n## Note\n\nYou have `read_file` and `run_tests` tools. Per responsibility 2, independently verify before deciding — do NOT trust the Player's report blindly.\n",
        )}],
    })

    # Probe D — convergence stress (mirrors run-14 TASK-FIX-IA03 shape: large
    # report, a specialist violation signal, mixed evidence). This is the
    # case that made the MoE Coach ramble 49,720 chars with no verdict.
    big_promises = [
        {"criterion_id": f"AC-{i:03d}", "status": ("complete" if i % 4 else "incomplete"),
         "evidence": f"src/module_{i}.py:{i*3}-{i*3+20}"}
        for i in range(1, 13)
    ]
    probes.append({
        "id": "D_convergence_stress",
        "expect_decision": "feedback",  # specialist violation + incompletes ⇒ feedback
        "tools": None,
        "messages": [{"role": "user", "content": coach_prompt(
            task_id="TASK-FIX-IA03", turn=1,
            requirements=(
                "Refactor the impact-analysis orchestrator to stream incremental results, add "
                "a results cache keyed by task-id, and surface a --depth flag. Maintain backward "
                "compatibility with the existing CLI. 12 acceptance criteria (AC-001..AC-012) cover "
                "streaming, caching, the depth flag, CLI back-compat, error handling, and tests."
            ),
            criteria=[{"id": f"AC-{i:03d}", "text": f"Criterion {i} of the impact-analysis refactor"} for i in range(1, 13)],
            player_report={
                "task_id": "TASK-FIX-IA03", "turn": 1,
                "files_created": [f"src/module_{i}.py" for i in range(1, 30)],
                "files_modified": ["src/cli.py", "src/orchestrator.py"],
                "tests_written": ["test_stream", "test_cache"],
                "tests_run": True, "tests_passed": True,
                "test_output_summary": "",  # empty — ambiguous signal, like the real run-14 report
                "implementation_notes": "Streaming + cache landed; depth flag partially wired.",
                "concerns": ["depth flag only covers depth<=2", "cache eviction not implemented"],
                "requirements_addressed": [f"AC-{i:03d}" for i in range(1, 10)],
                "requirements_remaining": ["AC-010", "AC-011", "AC-012"],
                "completion_promises": big_promises,
            },
            extra=(
                "\n## Evidence Bundle (deterministic gates)\n\n"
                "<evidence_bundle>\n"
                + json.dumps({
                    "gathering_status": "complete",
                    "tests": {"tests_run": True, "passed": True, "count": 2},
                    "coverage": {"line": 0.71, "branch": 0.62},
                    "plan_audit": {"violations": 1, "detail": "AC-010..AC-012 unimplemented but promised partial"},
                    "specialist": {"status": "violation", "detail": "test-orchestrator reported a contract violation"},
                }, indent=2)
                + "\n</evidence_bundle>\n\n"
                "## Absence-of-failure guards\n\n"
                "Treat ABSENT evidence (empty test_output_summary, coverage below threshold) as ABSENT SIGNAL, "
                "not as success. A specialist 'violation' is a real signal.\n"
            ),
        )}],
    })

    _NO_TOOLS = ("\n## CONSTRAINT — NO TOOLS THIS TURN\n\n"
                 "No tools are available to you this turn. Do NOT emit any tool call. "
                 "Treat the Player's report above as the COMPLETE and ONLY evidence. "
                 "Based solely on it, emit your fenced JSON verdict NOW.\n")

    # Probe E — toolless clean-approve. Isolates verdict-emission on the APPROVE
    # path (where the MoE rambled worst — probe A: 27,006c, no verdict).
    probes.append({
        "id": "E_toolless_approve",
        "expect_decision": "approve",
        "tools": None,
        "messages": [{"role": "user", "content": coach_prompt(
            task_id="TASK-DEMO-A01", turn=1,
            requirements="Add a `slugify(text: str) -> str` helper to `src/text_utils.py` that lowercases, strips, and replaces runs of non-alphanumeric chars with a single hyphen. Add unit tests.",
            criteria=[
                {"id": "AC-001", "text": "slugify lowercases and hyphenates non-alphanumeric runs"},
                {"id": "AC-002", "text": "Unit tests cover empty string, leading/trailing spaces, and unicode"},
            ],
            player_report={
                "task_id": "TASK-DEMO-A01", "turn": 1,
                "files_created": ["src/text_utils.py", "tests/test_text_utils.py"],
                "tests_written": ["test_basic", "test_empty", "test_unicode", "test_trim"],
                "tests_run": True, "tests_passed": True,
                "test_output_summary": "4 passed in 0.12s",
                "requirements_addressed": ["AC-001", "AC-002"],
                "completion_promises": [
                    {"criterion_id": "AC-001", "status": "complete", "evidence": "src/text_utils.py:1-14 slugify impl"},
                    {"criterion_id": "AC-002", "status": "complete", "evidence": "tests/test_text_utils.py 4 tests pass"},
                ],
            }, extra=_NO_TOOLS)}],
    })

    # Probe F — toolless clear-feedback.
    probes.append({
        "id": "F_toolless_feedback",
        "expect_decision": "feedback",
        "tools": None,
        "messages": [{"role": "user", "content": coach_prompt(
            task_id="TASK-DEMO-B01", turn=1,
            requirements="Add a `retry(fn, attempts=3)` decorator to `src/retry.py` with exponential backoff. Add unit tests proving it retries on exception and gives up after `attempts`.",
            criteria=[
                {"id": "AC-001", "text": "retry retries the wrapped fn on exception up to `attempts` times"},
                {"id": "AC-002", "text": "Backoff is exponential between attempts"},
                {"id": "AC-003", "text": "Unit tests prove both retry and give-up behaviour"},
            ],
            player_report={
                "task_id": "TASK-DEMO-B01", "turn": 1,
                "files_created": ["src/retry.py"], "tests_written": [],
                "tests_run": True, "tests_passed": False,
                "test_output_summary": "1 failed, 0 passed: test_gives_up — AssertionError: expected 3 calls, got 1",
                "requirements_addressed": ["AC-001"],
                "requirements_remaining": ["AC-002", "AC-003"],
                "completion_promises": [
                    {"criterion_id": "AC-001", "status": "complete", "evidence": "src/retry.py"},
                    {"criterion_id": "AC-002", "status": "incomplete", "evidence": "no backoff implemented"},
                    {"criterion_id": "AC-003", "status": "incomplete", "evidence": "tests fail / missing"},
                ],
            }, extra=_NO_TOOLS)}],
    })

    return probes


# --- HTTP + metrics ---------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_last_verdict(text):
    """Return (decision, parsed_dict) from the LAST fenced json block, or (None, None)."""
    if not text:
        return None, None
    blocks = _FENCE_RE.findall(text)
    for raw in reversed(blocks):
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if isinstance(d, dict) and "decision" in d and "task_id" in d:
            return d.get("decision"), d
    return None, None


def call(base_url, model, messages, tools, max_tokens, timeout):
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Authorization": "Bearer llama-swap-local-key"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    elapsed = time.time() - t0
    return payload, elapsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--only", default=None, help="comma-separated probe ids to run")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    only = set(args.only.split(",")) if args.only else None
    probes = [p for p in build_probes() if (only is None or p["id"] in only)]

    summary = []
    for p in probes:
        print(f"[{args.label}] probe {p['id']} ...", flush=True)
        rec = {"label": args.label, "model": args.model, "probe": p["id"],
               "expect_decision": p["expect_decision"]}
        try:
            payload, elapsed = call(args.base_url, args.model, p["messages"], p["tools"],
                                    args.max_tokens, args.timeout)
            choice = payload["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
            tool_calls = msg.get("tool_calls") or []
            finish = choice.get("finish_reason")
            usage = payload.get("usage", {})
            decision, verdict = extract_last_verdict(content)
            # Some models leak the verdict into reasoning; check there too (informational).
            r_decision, _ = extract_last_verdict(reasoning)

            rec.update({
                "ok": True,
                "latency_s": round(elapsed, 1),
                "finish_reason": finish,
                "content_chars": len(content),
                "reasoning_chars": len(reasoning),
                "completion_tokens": usage.get("completion_tokens"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "has_fenced_verdict": decision is not None,
                "verdict_decision": decision,
                "verdict_in_reasoning_only": (decision is None and r_decision is not None),
                "decision_correct": (p["expect_decision"] is not None and decision == p["expect_decision"]),
                "n_tool_calls": len(tool_calls),
                "tool_names": [tc.get("function", {}).get("name") for tc in tool_calls],
            })
            # Full transcript for forensic review.
            (out_dir / f"{args.label}__{p['id']}.transcript.json").write_text(json.dumps({
                "request": {"model": args.model, "tools": [t["function"]["name"] for t in (p["tools"] or [])]},
                "content": content, "reasoning_content": reasoning,
                "tool_calls": tool_calls, "finish_reason": finish, "usage": usage,
                "latency_s": round(elapsed, 1), "extracted_verdict": verdict,
            }, indent=2))
            tok_s = (usage.get("completion_tokens") or 0) / elapsed if elapsed else 0
            print(f"  -> finish={finish} verdict={decision} reasoning={len(reasoning)}c "
                  f"content={len(content)}c tools={rec['tool_names']} "
                  f"{elapsed:.0f}s ({tok_s:.1f} tok/s)", flush=True)
        except urllib.error.HTTPError as e:
            rec.update({"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:400]}"})
            print(f"  -> ERROR {rec['error']}", flush=True)
        except Exception as e:  # noqa: BLE001
            rec.update({"ok": False, "error": f"{type(e).__name__}: {e}"})
            print(f"  -> ERROR {rec['error']}", flush=True)
        summary.append(rec)

    (out_dir / f"{args.label}__summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n[{args.label}] wrote {out_dir}/{args.label}__summary.json")
    # Compact table
    print(f"\n{'probe':22} {'finish':10} {'verdict':9} {'correct':7} {'reason_c':9} {'cont_c':7} {'tools':14} {'lat_s':6}")
    for r in summary:
        if r.get("ok"):
            print(f"{r['probe']:22} {str(r['finish_reason']):10} {str(r['verdict_decision']):9} "
                  f"{str(r['decision_correct']):7} {r['reasoning_chars']:<9} {r['content_chars']:<7} "
                  f"{str(r['tool_names']):14} {r['latency_s']:<6}")
        else:
            print(f"{r['probe']:22} ERROR: {r.get('error')}")


if __name__ == "__main__":
    main()
