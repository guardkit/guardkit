---
id: TASK-AB-STALLTAX01
title: STALL_PARALLEL_INTERFERENCE co-fire stall subtype + failing-test aggregation in stall message
status: backlog
created: 2026-07-04T09:33:00Z
priority: medium
tags: [autobuild, stall-classification, parallel-waves, contention, observability]
complexity: 4
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: STALL_PARALLEL_INTERFERENCE co-fire stall subtype + failing-test aggregation

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 9 (R2 —
study-tutor FEAT-SMP-001 parallel-wave shared-worktree pollution).

When SMP-02 ∥ SMP-03 both retried in lock-step against the shared worktree,
both kept red-lining until 3 consecutive ran-and-failed checkpoints →
`context_pollution_stall_no_checkpoint` (`autobuild.py:2672-2684`, subtype
const `:317`). That label is a **true** description of the condition but
**silent about the cause**: the Coach layer *knew* per-turn (its
`parallel_contention` classification fired), but that knowledge is discarded
before the terminal label is chosen. The operator saw "context pollution"
and went hunting for a quality defect when the cause was isolation.

Fix, per the xref: add a `STALL_PARALLEL_INTERFERENCE` **co-fire** subtype
to `classify_stall`, keyed on the **schema-stable**
`failure_classification == 'parallel_contention'` field in the trailing
turns' test_verification issues — mirroring the shape of
`_extract_environment_stall_signal` (`autobuild.py:418-469`) and honouring
the TASK-FIX-7A07 precedent (**no string-matching on feedback text**; key on
structured fields only). Keep the top-level
`final_decision='unrecoverable_stall'` for backward compatibility.

Also: aggregate the per-turn failing-test descriptions (already present in
`coach_turn_N.json`) into the stall message (`autobuild.py:7272-7286`) so
the operator sees *which* tests failed, not just that a stall occurred.

## Acceptance Criteria

- [ ] AC-001: `classify_stall` emits a `STALL_PARALLEL_INTERFERENCE` co-fire
      subtype when the trailing turns' test_verification issues carry
      `failure_classification == 'parallel_contention'`. The detection reads
      the structured field only — no regex/string-matching over feedback
      prose.
- [ ] AC-002: The subtype **co-fires** alongside (does not replace)
      `context_pollution_stall_no_checkpoint`; top-level
      `final_decision='unrecoverable_stall'` is unchanged (backward-compat
      for every existing consumer of the terminal label).
- [ ] AC-003: The stall message aggregates the per-turn failing-test
      descriptions from the trailing turns' `coach_turn_N.json` records, so
      the terminal report names the failing tests.
- [ ] AC-004: The stall-tally semantics are untouched: only explicit
      `tests_passed is False` checkpoints count toward the
      consecutive-failure threshold; `None` still breaks the run (tri-state
      intact).
- [ ] AC-005: Regression tests: (a) contention-classified trailing turns →
      co-fire subtype present; (b) non-contention stall → subtype absent,
      existing label unchanged; (c) missing/absent `failure_classification`
      → no subtype (absent ≠ contention); (d) stall message contains the
      aggregated failing-test names.

## Implementation Notes

File:line anchors from the xref (§3 R2 item 4, §5 item 9):

- `guardkit/orchestrator/autobuild.py:2672-2684` — the
  `context_pollution_stall_no_checkpoint` firing site; subtype const at
  `:317`.
- `guardkit/orchestrator/autobuild.py:418-469` —
  `_extract_environment_stall_signal`, the shape to mirror (structured-field
  extraction from trailing turns).
- `guardkit/orchestrator/autobuild.py:7272-7286` — the stall message
  assembly (aggregate failing-test descriptions here).
- `guardkit/orchestrator/quality_gates/coach_validator.py:2298-2301` — the
  A7B2/ABFIX-005 parallel-amnesty assumption ("by the Player's next turn,
  peers have completed") that broke in lock-step retries; context for why
  the per-turn knowledge exists.
- Data source: the `parallel_contention` `failure_classification` on
  test_verification issues in `coach_turn_N.json` (already schema-stable —
  the classification the Coach layer produces per-turn today).

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **No string-matching on feedback text** (TASK-FIX-7A07 precedent, cited by
  xref §5 item 9): key detection on the schema-stable
  `failure_classification` field only. A prose-matching heuristic is the
  regression.
- **A7B2 overlap-forces-feedback veto and the contention amnesty are
  load-bearing** (§6): do NOT widen the amnesty to auto-approve
  (false-red → false-green conversion) and do NOT remove it while improving
  the label — operators can still hand-author overlapping waves.
- **Tri-state stays tri-state** (§6;
  `.claude/rules/absence-of-failure-is-not-success.md` item 4 /
  CKPTTESTRED01): the consecutive-failure tally counts only
  `cp.tests_passed is False` (`worktree_checkpoints.py:738`); an absent
  classification is `None`/absent, never treated as contention and never as
  an extra failure (`.claude/rules/absence-must-survive-every-reconciliation-layer.md`).
- **Backward-compat terminal label**: `final_decision='unrecoverable_stall'`
  stays; the subtype is additive observability, not a verdict change (the
  `.claude/rules/display-must-derive-from-enforcement-source-not-proxy.md`
  spirit — report what the enforcement layer actually decided, enriched, not
  re-derived).
- This is the labelling half of R2 only; the concurrency-control half is
  TASK-AB-WAVECTL01 and the structural fix is TASK-AB-WTISO01
  (design-first).
