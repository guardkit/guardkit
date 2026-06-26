---
id: TASK-REV-COSE
title: Diagnose Coach SDK-test-execution opaque-stderr fallback in coach_validator
status: backlog
task_type: review
review_mode: diagnostic
review_depth: standard
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: low
tags: [autobuild, coach-validator, sdk-test-execution, observability, R7]
related_reviews:
  - TASK-REV-9D13  # Origin review (filed this as sidequest)
related_features: []
complexity: 3
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-REV-COSE — Diagnose Coach SDK-test-execution opaque-stderr fallback

> **RESOLVED 2026-06-26 — option (a) chosen and implemented.** The diagnosis
> is confirmed: both harnesses dropped the tool result (SDK dropped the
> `UserMessage`/`ToolResultBlock`; LangGraph never walked `ToolMessage`
> history), so `_run_tests_via_sdk` captured the Coach agent's *narration*
> not the pytest stdout. The operator chose the **capture fix (a)** over the
> subprocess-default (b) to keep the SDK path a real oracle. Implemented as
> **TASK-FIX-COACHTRES01** (`tasks/in_review/`): emit `ToolResultEvent` on
> both substrates; the consumer's pre-existing branch already prefers the real
> `bash_output`. The absent-vs-classified asymmetry is handed to TASK-FIX-DF44.
> This review can be closed referencing COACHTRES01.

## Context

Filed as a sidequest from [TASK-REV-9D13 v2 §4 R7](../../.claude/reviews/TASK-REV-9D13-report.md#r7--coach-sdk-test-execution-opaque-stderr-sidequest-separate-review). Originating evidence at jarvis run-2 history lines 2989-2995:

```
ERROR:claude_agent_sdk._internal.query:Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution failed (error_class=Exception): Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
WARNING:guardkit.orchestrator.quality_gates.coach_validator:SDK test execution failed (error_class=Exception), falling back to subprocess.
INFO:guardkit.orchestrator.quality_gates.coach_validator:Independent tests passed in 3.3s
```

The Coach's SDK-mediated test-execution path raised `Command failed with exit code 1` whose `Error output:` was literally `"Check stderr output for details"` — uninformative. The subprocess fallback worked correctly (3.3 s, 18 tests passed). **The defect is the diagnostic surface, not the orchestration outcome.** Operators investigating the failure need to know *why* the SDK path failed.

## Goal

Produce a diagnostic report identifying:

1. Where the SDK-mediated test-execution path constructs and reads stderr in `guardkit/orchestrator/quality_gates/coach_validator.py`
2. Why the actual stderr is being lost between `claude_agent_sdk._internal.query` and the catch block in `coach_validator`
3. Whether the issue is upstream in `claude_agent_sdk` (transport/subprocess layer) or in GuardKit's exception-translation
4. A targeted fix proposal that surfaces the actual stderr without changing the fallback semantics (subprocess fallback should remain in place; only the diagnostic surface needs improvement)

## Investigation Scope

- `guardkit/orchestrator/quality_gates/coach_validator.py` — locate the `_run_independent_tests_via_sdk` (or equivalently named) method
- `claude_agent_sdk._internal.query` and `claude_agent_sdk._internal.transport.subprocess_cli` for the stderr capture pattern
- Whether the bundled `claude` CLI (`claude_agent_sdk/_bundled/claude`) writes to a different fd than the SDK reads
- Cross-reference with any existing related Graphiti facts (search `claude_agent_sdk MessageParseError SDK timeout subprocess` in `guardkit__project_decisions` and `guardkit__task_outcomes`)

## Acceptance Criteria

- [ ] Root cause of the opaque stderr identified with file:line evidence
- [ ] Determination: is this a GuardKit defect, an upstream `claude_agent_sdk` defect, or a `claude` CLI bundling issue?
- [ ] Targeted fix proposal (with file:line and ~5-10 line code sketch)
- [ ] Regression risk analysis (the subprocess fallback must continue to work; this is purely improving diagnostics)
- [ ] Report saved to `.claude/reviews/TASK-REV-COSE-report.md` per `/task-review` convention

## Out of Scope

- Removing the subprocess fallback (load-bearing for the case where SDK path fails for any reason)
- Refactoring the Coach validator beyond the stderr-capture path
- Investigating why the SDK-path was failing in the first place — that is a deeper rabbit hole; this review focuses on the **diagnostic surface**

## Suggested Workflow

```bash
/task-review TASK-REV-COSE --mode=diagnostic --depth=standard
```

Read `coach_validator.py` first; then trace through `claude_agent_sdk._internal.query` to understand how the `Fatal error in message reader` is constructed. Cross-check against the bundled `claude` CLI's output convention (does it write structured JSON to stdout and free-form errors to stderr, or interleave?).

---

## Addendum (2026-06-26) — the SDK path captures agent narration, not pytest stdout

> Added from the FEAT-HARV autobuild session (handoff:
> `docs/handoff/autobuild-coach-test-gathering-handoff-2026-06-26.md`). This
> widens COSE's scope from "opaque *stderr* on failure" to the deeper structural
> defect: on the **success** path the SDK independent runner can capture the
> Coach agent's **narration** instead of the actual pytest output. Pair with
> `TASK-FIX-DF44` (which owns the *classification + approval* response); this task
> owns the *capture* root cause.

### Finding

`_run_tests_via_sdk` (`guardkit/orchestrator/quality_gates/coach_validator.py`)
runs `pytest` via the harness substrate. **The SDK harness does not yield a
`ToolResultEvent`** (documented in the method's own `ToolResultEvent` note,
origin TASK-HMIG-006.3) — `sdk_harness.py` only surfaces
`AssistantMessage` / `ResultMessage` / `ToolUseEvent`. So `bash_output` stays
`None`, and the only captured text is the agent's assistant message
(`collected_text`). When the Coach agent narrates ("I'll run the test command and
show you the full output.") without echoing the pytest output in its final text,
`output_text` is that narration. The pass/fail heuristic then finds no
`passed`/`failed` marker.

This is the structural cause of BOTH symptoms:
- COSE's original "opaque stderr" (the agent's error narration replaces the real
  stderr), and
- The FEAT-HARV TASK-HARV-003 stall (narration with no marker, while the
  deterministic subprocess pytest passed **8601/8601** every turn).

### Why it is intermittent / high-impact

The capture depends on the Coach LLM's response shape, so it varies run-to-run
(FEAT-HARV wave-1 002/004 passed in one run, the same tasks went absent in the
next). Its impact is normally *masked* by the conditional-approval mechanism
(TASK-ABFIX-005) — a classified SDK failure + all gates pass → approve — which is
why this has lurked. It surfaces hard whenever the narration is routed to an
*absent* signal (Guard #6 hard-blocks) rather than a classified failure.

### Expanded diagnosis goals

1. Confirm the no-`ToolResultEvent` mechanism in `sdk_harness.py` and whether the
   Bash tool result is available in the SDK message stream at all (e.g. in a
   `UserMessage` with a `ToolResultBlock` the harness currently drops).
2. Decide between the two real fixes (with regression analysis):
   - **(a) Capture fix** — surface the Bash tool stdout as a `ToolResultEvent`
     (or walk `UserMessage` content) so real pytest output reaches the heuristic.
     Highest-fidelity; touches the harness (and the langgraph substrate in
     guardkitfactory).
   - **(b) Substrate fix** — default `coach_test_execution` to `subprocess`
     (the deterministic path that runs real pytest and is already the reliable
     fallback). Lowest-risk; removes the flaky LLM-mediated capture entirely.
     Confirm the subprocess path's env/interpreter parity (it already resolves
     the worktree venv — see the `Test execution environment` log line).
3. Hand the *classification/approval* response to `TASK-FIX-DF44` (a no-marker
   capture should be conditional-approvable when gates pass, reconciled against
   the deterministic subprocess result — not a hard absent block).

### Additional Acceptance Criteria (this addendum)

- [ ] Mechanism confirmed with file:line: where the Bash tool result is (or is
      not) available on the SDK substrate, and where `bash_output` is left `None`.
- [ ] Recommendation (a) vs (b) with regression analysis. Strong prior toward
      (b) `coach_test_execution=subprocess` as the default for reliability,
      unless (a) is cheap and the langgraph substrate already yields tool results.
- [ ] The absent-vs-classified asymmetry (Guard #6 stricter than a classified
      failure) is flagged to TASK-FIX-DF44 for resolution.

### Evidence

- FEAT-HARV TASK-HARV-003 `coach_evidence_turn_*.json`:
  `independent_tests.raw_output` = the literal narration; `signal_absent=true`;
  deterministic `Phase-4 executed deterministically (subprocess pytest):
  status=passed tests_run=8601 tests_failed=0`.
- Run logs under `.guardkit/autobuild/_runs/FEAT-HARV-sdk-fresh-*.log`.
