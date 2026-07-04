---
id: TASK-AB-ZEROTESTLOUD01
title: Zero-collected-tests must surface as verifier infrastructure, not Player quality — loud diagnosis, stall co-fire, honest feedback framing
status: backlog
created: 2026-07-04T10:06:00Z
priority: high
tags: [autobuild, absent-signal, stall-classification, phase-4, actionability]
complexity: 5
source: docs/retro/abl005-autobuild-infra-chain-2026-07-04.md
---

# Task: A Phase-4 record with zero collected tests can never mean "Player code is bad" — say so

> Implementation in progress 2026-07-04 (same session that filed this task); this file is
> the tracking record.

## Description

ABL-005 run 4: 8 consecutive turns recorded `absent test signal (deterministic Phase 4):
tests_run=0` (root cause: the TASK-AB-RESUMEVENV01 interpreter defect). The absent-signal
machinery worked as designed — no false green, no false-red checkpoint stall (tri-state
`None` kept the pollution tally broken), the run terminated at max turns with
`success=False`. What FAILED was diagnosis and attribution:

- "the Coach *appeared* to be rejecting the Player on quality for 8 straight turns, when
  it was actually blind (`tests_run=0` was recorded in the specialist record all along —
  the signal existed, nothing surfaced it)."
- The Player received feedback framed as quality rejection each turn; the operator needed
  a hand reproduction session to discover the verifier never ran a test.

Retro lesson #1: "`tests_run=0` must be a loud, first-class failure, not an input to a
stall heuristic. Any Phase-4 record with zero collected tests should abort the turn with a
verifier-infrastructure verdict — it can never mean 'Player code is bad'." This task
implements the loudness/attribution half WITHOUT changing verdict semantics (the absent
signal must remain absent — see constraints; "abort the turn with a
verifier-infrastructure verdict" is implemented as feedback-with-infrastructure-framing +
stall co-fire, not as a new verdict kind).

## Acceptance Criteria

- [ ] AC-001: The deterministic Phase-4 absent-signal branch (zero collected tests) and
      the absent-independent-test override attach a machine-readable
      `verifier_infrastructure` marker (with the resolved interpreter and probed test
      command in details) to the turn's issue/record — schema-additive, never
      string-matched.
- [ ] AC-002: Player-facing feedback for an absent test signal states explicitly:
      "verification infrastructure could not collect/run any tests (interpreter: X,
      command: Y) — this is NOT a signal about your code; do not rewrite the
      implementation in response" (wording to fit existing feedback style).
- [ ] AC-003: A trailing window of turns that ALL carry the `verifier_infrastructure`
      marker co-fires an environment-class stall subtype (reuse
      `STALL_ENVIRONMENT` / `_extract_environment_stall_signal`'s schema-match pattern —
      extend it or add a sibling extractor accepting the new marker), so the terminal
      summary names verifier infrastructure, the resolved interpreter, and the
      remediation (rebootstrap / check worktree venv) instead of implying Player quality.
- [ ] AC-004: The marker does NOT feed the ABSR-2468 environment-class conditional-
      approval amnesty (an absent signal must never become an approval input); the
      `signal_absent` guard #6 override still fires first and unchanged.
- [ ] AC-005: Regression tests for AC-001..004, including: absent signal with the marker
      still yields tri-state None in checkpoints; three marked turns co-fire the
      environment stall; a genuine ran-and-failed turn is untouched.

## Implementation Notes

- Phase-4 absent branch: `guardkit/orchestrator/specialist_invocations.py` (~:1092
  `error="absent test signal …"`; both branches return status="failed" distinguishable by
  error prefix — see `.claude/rules/absence-must-survive-every-reconciliation-layer.md`).
- Reconciliation: `guardkit/orchestrator/agent_invoker.py` (`reconciled_absent` branch;
  `_reconcile_absent_independent_test_signal` ~:5542 after today's edits).
- Stall wiring precedent: `_extract_environment_stall_signal`
  (`guardkit/orchestrator/autobuild.py:~418-469`, keys on schema-stable
  `failure_classification=='infrastructure'`; TASK-FIX-7A07 "no feedback-text
  string-matching") and today's TASK-AB-STALLTAX01 interference extractor (same file) —
  mirror one of these.
- Resolved-interpreter availability comes from TASK-AB-RESUMEVENV01 (AC-003 there);
  implement that first.

## Regression constraints

- `.claude/rules/absence-of-failure-is-not-success.md` +
  `absence-must-survive-every-reconciliation-layer.md` — the absent signal stays `None`
  at every layer; NO coercion to pass/fail; the terminal guard
  (`cp.tests_passed is False`) untouched; max-turns termination with `success=False`
  for a never-verified task is CORRECT and must remain (false-green-by-non-termination
  bound).
- `.claude/rules/deterministic-verdict-override-must-persist-to-disk.md` — if feedback
  framing is applied at the post-synthesis seam, the re-persist contract applies.
- `.claude/rules/structural-defence-beats-prompt-instruction.md` — the marker + stall
  co-fire are structural; do not rely on prompt text alone.
- Backward-compat: `final_decision` labels unchanged; new info rides
  `decision_subtype`/co-fires and issue fields only (same contract as
  TASK-AB-STALLTAX01).
