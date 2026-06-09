---
id: TASK-FIX-COACHFG01
title: Fail-closed when the Coach's independent-test oracle is absent (signal_absent) — close the run-19 false-green
status: backlog
task_type: fix
created: 2026-06-09T19:45:00Z
updated: 2026-06-09T19:45:00Z
priority: high
complexity: 4
parent_task: TASK-ARCH-COACHSPLIT
related: [TASK-ARCH-COACHSPLIT, TASK-ARCH-COACHBFULL, TASK-FIX-COACHTESTTO, TASK-OPS-COACH31B, TASK-AB-FIX-INVAB1]
implementation_mode: task-work
intensity: strict
tags: [autobuild, coach, oracle, false-green, absence-of-failure, harness-migration]
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  mode: tdd
---

# Task: Fail-closed when the Coach's independent-test oracle is absent

## Why this task exists

The two "green" runs the run-13→20 arc celebrates (run-19, run-20-second-attempt)
are **false-greens** by the project's own
[`absence-of-failure-is-not-success`](../../../.claude/rules/absence-of-failure-is-not-success.md)
rule. In run-19 the Coach's independent trust-but-verify pytest run **timed out**:

```
ERROR ...coach_validator:SDK coach test execution timed out after 300s
INFO  ...coach_validator:SDK independent tests failed in 300.0s
...
  ✓ Coach approved - ready for human review
INFO  ...autobuild:Criteria Progress (Turn 1): 0/5 verified (0%)
INFO  ...autobuild:Coach approved on turn 1
```
([run-19:197-220](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md#L197-L220))

The Coach **approved anyway** — on the Player's self-reported gates plus the
other deterministic checks — even though its own independent oracle produced **no
signal at all**. This is the exact false-green the project documented twice before
(JUnit `tests=0`, BDD `scenarios_run=0`).

**The guard already exists — but only as a prompt instruction the local model
ignores.** `agent_invoker.py:3230-3241` ("6. INDEPENDENT-TEST ABSENT GUARD") tells
the synthesising Coach:

> If `evidence_bundle.independent_tests.signal_absent == true` … do NOT approve …
> Surface as feedback … Rule: `.claude/rules/absence-of-failure-is-not-success.md`.

That instruction is handed to `gemma4:31b`, which **disregarded it and emitted
`approve`**. The toolless GBNF grammar constrains the verdict's *shape*
(`approve|feedback`), not whether the model *honored guard #6*. There is **no
deterministic code backstop**: `IndependentTestResult.signal_absent` is *set* at
six sites in `coach_validator.py` and **read by nothing** — the post-synthesis
decision path (`agent_invoker.py:2189-2190`) only schema-validates the verdict.

This is the canonical `absence-of-failure-is-not-success` remediation applied to
the **synthesis path**: *"Wire the verifier into the primary path, not just the
LLM. Verify on disk, not on Player report. Refuse to approve when the
attempted-count is zero or absent."* Guard #6 must become **code**, not a prompt.

## The defect (precise surface)

| Element | Location | State |
|---|---|---|
| `signal_absent` field + contract | `guardkit/orchestrator/quality_gates/coach_validator.py:240-260` | defined; docstring says absent ⇒ feedback, never approve |
| `signal_absent = True` set-sites (timeout / transport / exception) | `coach_validator.py:2698, 2778, 3012, 3023, 3255, 3266` | correctly set |
| Bundle carries it to synthesis | `guardkit/orchestrator/quality_gates/coach_evidence.py:171` (`CoachEvidenceBundle.independent_tests`) | present |
| Guard #6 (prompt-only) | `guardkit/orchestrator/agent_invoker.py:3230-3241` | **instruction to the LLM; not enforced** |
| Post-synthesis decision accepted | `agent_invoker.py:2189-2190` (`_load_agent_report` + `_validate_coach_decision`) | **no `signal_absent` reconciliation** |

Net: `signal_absent` is **produced and never consumed as a gate** anywhere in the
orchestrator.

## The fix

Add a **deterministic post-synthesis reconciliation guard** that runs after the
Coach verdict is loaded and schema-validated, and **before** the
`AgentInvocationResult` is returned (the natural seam is right after
`_validate_coach_decision(decision)` at `agent_invoker.py:2190`). When:

- `decision["decision"] == "approve"`, **AND**
- `evidence_bundle is not None` and `evidence_bundle.independent_tests is not None`
  and `evidence_bundle.independent_tests.signal_absent is True`

then **override the verdict to `feedback`** with a synthetic, operator-legible
issue (category `absence_of_failure`, the same category the honesty gate uses),
preserving `evidence_bundle.independent_tests.test_output_summary` verbatim in the
rationale so operators can see whether it timed out or errored. Log the override at
WARNING with the task_id, turn, and the original (overridden) decision.

Design constraints:

- **Fail-closed, identity-bounded, narrow.** Only override an `approve`. A
  `feedback` verdict is left untouched. This does not touch the
  `gathering_status` guard (#5) or the honesty short-circuit — it is strictly the
  `independent_tests.signal_absent` case.
- **Deterministic, not advisory.** The override must not depend on the LLM having
  read guard #6. Keep guard #6 in the prompt as defence-in-depth (it is cheap and
  correct), but the code override is now the load-bearing enforcement.
- **Respect the existing conditional-approval semantics.** `signal_absent` is
  distinct from "ran and failed" (`tests_passed=False, signal_absent=False`) — do
  NOT broaden this to genuine test *failures* (those already route through
  `_classify_test_failure` / conditional-approval at `coach_validator.py:1289+`).
  This task is *only* about absent signal.
- **Category surfaced** so stall classifiers and dashboards can see it (mirror
  TASK-AB-FIX-INVAB1 AC-002's `category` convention).

## Acceptance criteria

- [ ] AC-1: A deterministic guard in `agent_invoker.py` overrides a synthesised
  `approve`→`feedback` whenever
  `evidence_bundle.independent_tests.signal_absent is True`, independent of the
  LLM-emitted decision. The override fires after `_validate_coach_decision` and
  before the `AgentInvocationResult` is returned.
- [ ] AC-2: The overridden verdict's rationale names the cause ("Independent test
  verification did not complete (signal absent) — cannot independently confirm the
  Player's reported tests") and quotes `independent_tests.test_output_summary`
  verbatim. Emitted with `category: "absence_of_failure"`.
- [ ] AC-3: The override is logged at WARNING with `task_id`, `turn`, and the
  original decision value.
- [ ] AC-4 (reproducer): a regression test reconstructs the run-19 case — an
  `evidence_bundle` whose `independent_tests` has `signal_absent=True,
  tests_passed=False` and a synthesised `approve` verdict — and asserts the
  returned decision is `feedback`. The test MUST fail on `main` (proving it
  reproduces the false-green) and pass after the fix.
- [ ] AC-5 (no over-reach): a verdict where independent tests **ran and genuinely
  failed** (`tests_passed=False, signal_absent=False`) is NOT short-circuited by
  this guard — it continues to flow through the existing
  `_classify_test_failure` / conditional-approval path unchanged. Covered by a
  second test.
- [ ] AC-6 (no regression on the happy path): a verdict with
  `independent_tests.tests_passed=True, signal_absent=False` and decision `approve`
  is returned as `approve` untouched.
- [ ] AC-7: existing Coach test suites
  (`tests/orchestrator/`, `tests/integration/orchestrator/test_coach_*`) stay green.

## Scope boundary (what this task is NOT)

- **Not** TASK-ARCH-COACHBFULL. That task restores the *investigating* Coach so
  `criteria_verification` is populated (verdict *substance*). COACHFG01 is the
  narrower, mechanical *fail-closed* fix for *absent oracle signal* (verdict
  *honesty about its own evidence*). The run-19 line `0/5 verified` is COACHBFULL's
  province; the run-19 line `independent tests failed in 300.0s → approved` is this
  task's. They are complementary and non-overlapping.
- **Not** a change to test timeout values (that is TASK-FIX-COACHTESTTO territory),
  to the grammar, or to the gather/synthesis split.
- **Not** a broadening of guard #5 (`gathering_status`) or the honesty
  short-circuit.

## Notes

- This is a textbook instance of the
  [`absence-of-failure-is-not-success`](../../../.claude/rules/absence-of-failure-is-not-success.md)
  meta-frame and its "wire the verifier into the *primary* path, not just the LLM"
  remediation — here the "primary path" is the toolless-synthesis decision path
  introduced by TASK-ARCH-COACHSPLIT (D-3), which silently dropped the enforcement
  that the older LLM-Coach prompt only ever *advised*.
- Diagnosed in [`docs/retro/player-coach-why-so-hard-verdict.md`](../../../docs/retro/player-coach-why-so-hard-verdict.md)
  (the false-green section) as the single highest-leverage open defect in the
  supposedly-green state.
