---
id: TASK-AB-SKIPVIS01
title: Thread tests_skipped through the independent-test oracle as advisory evidence
status: backlog
created: 2026-07-04T09:32:00Z
priority: medium
tags: [autobuild, coach, independent-tests, skip-count, evidence, advisory]
complexity: 3
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Thread tests_skipped through the independent-test oracle as advisory evidence

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 8 (R1 —
FEAT-ABL-001 `nats_core` stub).

The Coach is completely blind to skip counts. In R1, a missing
`bootstrap_extras` declaration meant the `memory` extra was never installed
in the worktree venv, so the relevant tests would *skip* — and **nothing
surfaces "N tests will skip due to missing extras"**. Verified state of the
blindness:

- `skipped` is intentionally excluded from `_PYTEST_COUNT_RE`
  (`specialist_invocations.py:174-180`);
- the regex group that would capture it is discarded
  (`agent_invoker.py:868-880` and `:1090-1100`);
- `IndependentTestResult` has no skip field;
- `rg tests_skipped` → 0 hits repo-wide.

The parse capture already exists and is thrown away today — this task keeps
it and threads it through as an **advisory** evidence field. It is a
visibility fix, not a new gate: a high skip count alone must never reject a
turn; it gives the Coach (and the operator) the signal that the environment
may be silently under-testing, which is the precondition R1's Player
exploited.

## Acceptance Criteria

- [ ] AC-001: The pytest output parsers capture the skipped count where
      present and expose it as `tests_skipped` (`specialist_invocations.py`
      count regex + the `agent_invoker.py` parse sites).
- [ ] AC-002: `IndependentTestResult` gains a `tests_skipped:
      Optional[int]` field. Absent/unparseable skip count → `None` — never
      coerced to `0`, never to a failure, at every layer.
- [ ] AC-003: The field survives serialization: it is carried by the
      evidence bundle's `to_dict()` and appears in the Coach-visible
      evidence (the ABFIX-010 lesson — a flag omitted from `to_dict()` makes
      the downstream branch dead).
- [ ] AC-004: The skip count is **advisory only**: it never flips a verdict
      on its own, never joins the turn-rejecting set, and contributes
      nothing to the consecutive-failure stall tally. It MAY be surfaced in
      Coach feedback text (e.g. "N tests skipped — check optional extras").
- [ ] AC-005: Regression tests: (a) skip count parsed and threaded end to
      end; (b) absent skip count stays `None` through parse →
      IndependentTestResult → to_dict → checkpoint; (c) a
      green-with-many-skips run still approves (no new false-red).

## Implementation Notes

File:line anchors from the xref (§3 R1 item 4, §5 item 8):

- `guardkit/orchestrator/specialist_invocations.py:174-180` —
  `_PYTEST_COUNT_RE` (skipped currently excluded by design; extend).
- `guardkit/orchestrator/agent_invoker.py:868-880` and `:1090-1100` — the
  parse sites where the captured skip group is discarded today.
- `IndependentTestResult` (in
  `guardkit/orchestrator/quality_gates/coach_validator.py`) — add the
  optional field; check its `to_dict()` (~1160) carries it.
- Downstream reads: `autobuild.py` evidence extraction — additive only, no
  verdict logic keyed on the new field.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Tri-state stays tri-state** (§6): "a skip, a missing classification, an
  unparseable count → `None`, never 0/False, at **every** layer" —
  `.claude/rules/absence-must-survive-every-reconciliation-layer.md`. Do not
  let any reconciliation/serialization hop coerce an absent skip count.
- **Never turn-rejecting alone** (xref §5 item 8; §6 "new heuristics start
  advisory, never join the turn-rejecting set lightly"). A skip count is not
  a failure; treating it as one would be a fresh
  `.claude/rules/absence-of-failure-is-not-success.md` false-red (the
  CKPTTESTRED01 shape in reverse).
- **Serialization must carry the field** — the ABFIX-010 /
  `signal_absent`-omitted-from-`to_dict()` lesson in
  `absence-must-survive-every-reconciliation-layer.md`: confirm the flag
  survives `to_dict()` or the downstream branch is dead code.
- **Do not disturb the existing count semantics**: `tests_passed` /
  `tests_run` parsing, the `signal_absent` chain, and the guard-#6 backstop
  are untouched; fingerprints (`reconciled_absent`,
  `tests_passed: Optional[bool]`) must still match.
- The class-level fix for R1 (skip-guard dependency parity probe) is
  TASK-AB-ENVTAMPER01; this task is the cheap visibility slice that stands
  alone.
