---
id: TASK-DEMOTE-PA
title: At 2026-05-17 follow-up — audit plan-audit (PA-001/002) RP rate; demote to warn-mode if RP/(RP+FP) < 0.5
status: backlog
created: 2026-05-10T18:45:00Z
updated: 2026-05-10T18:45:00Z
priority: medium
tags: [audit, plan-audit, demote-candidate, narrow-recommendation, deferred-2026-05-17]
parent_review: TASK-REV-ABST
complexity: 3
implementation_mode: task-work
estimated_effort_hours: 2
not_actionable_until: 2026-05-17
depends_on:
  - TASK-OBS-ABST
---

# Task: Audit plan-audit gate at 2026-05-17 follow-up

> **Why this exists**: TASK-REV-ABST §4.1 and §5.1 classified plan-audit
> (TASK-GK-PA-001 / TASK-GK-PA-002, landed 2026-05-07) as **load-bearing
> (new)** with insufficient evidence — only 3 days post-landing at review
> time. The recommendation defers retire/demote/keep until 2026-05-17, when
> 10 days of post-landing data is available. This task is the formal audit.
>
> **Do not start this task before 2026-05-17.** It depends on
> `TASK-OBS-ABST` having produced a metric snapshot (so that "RP rate" is a
> measurable thing, not a guess) and on the freeze (`TASK-FREEZE-ABST`)
> having held — the audit assumes plan-audit's behaviour is unchanged from
> its 2026-05-07 landing.

## Description

Read every Coach turn JSON dated between 2026-05-07 (PA-001 landing) and
2026-05-17 (audit date) across every consumer-repo worktree. Identify every
turn where plan-audit fired (look for `plan_audit` field in the JSON or
`category: "plan_audit"` in `issues[*]`). Classify each firing as:

- **REAL_POSITIVE**: Player wrote files outside its declared
  `files_to_modify` scope AND those files are not legitimately part of the
  task (e.g. wrote into another task's territory, or wrote into a directory
  the plan said it wouldn't touch).
- **FALSE_POSITIVE**: Player legitimately wrote files outside the declared
  scope (e.g. the plan's `files_to_modify` was incomplete, or the Player
  needed to update an import in an adjacent file).
- **NULL_FIRING**: gate fired but operator/test outcome shows no signal of
  effect either way (warn-mode-with-no-action shape).

Compute `RP / (RP + FP)`. If < 0.5, demote PA-001/002 to warn-mode (do not
short-circuit; emit feedback only). If ≥ 0.5, keep as block-mode.

This is the same decision shape as `TASK-RETIRE-AC` but applied to a different
gate, with a measurable RP rate instead of a "did anyone cite it" check.
Plan-audit fires more often than assumption-confidence, so the citation grep
shape isn't the right tool — direct turn-by-turn classification is.

## Acceptance criteria

### AC-001 — Eligibility check
**WHEN** the operator starts this task, **THE SYSTEM SHALL** verify:
- Today's date is on or after 2026-05-17.
- TASK-OBS-ABST has produced a metric snapshot at
  `.claude/observability/run-success-snapshot-*.json` covering the audit
  window.
- TASK-FREEZE-ABST held — `git log --since=2026-05-11 --until=2026-05-17`
  against `guardkit/orchestrator/quality_gates/coach_validator.py` shows no
  new behavioural surface in plan-audit.

**IF** any of those preconditions fail, **THE SYSTEM SHALL** abort and
escalate to the operator rather than proceeding with stale data.

### AC-002 — Plan-audit firing inventory
**THE SYSTEM SHALL** identify every Coach turn JSON between 2026-05-07 and
2026-05-17 where plan-audit fired. Source globs:

- `~/Projects/appmilla_github/*/\.guardkit/worktrees/*/.guardkit/autobuild/*/coach_turn_*.json`
- `.guardkit/worktrees/*/.guardkit/autobuild/*/coach_turn_*.json` in the
  GuardKit repo itself

A "firing" is any of:
- `plan_audit_failed: true` in the gate flags.
- `issues[*].category: "plan_audit"`.
- A `rationale` containing `"plan_audit"` or `"files_to_modify"` or
  `"plan-implementation divergence"`.

Inventory output:
- Total firings: N
- Per-feature breakdown
- Firing-to-task ratio

### AC-003 — Per-firing classification
**FOR EACH** firing, **THE SYSTEM SHALL** classify as REAL_POSITIVE,
FALSE_POSITIVE, or NULL_FIRING using the criteria above. Classification
requires reading:
- The turn's `task_work_results.json` (Player self-report) for `files_modified`
- The task spec markdown for the declared `## Files to Modify` section
- The turn's `coach_feedback_for_turn_*.json` (if exists) for whether the
  Player corrected behaviour next turn (signal of REAL_POSITIVE)

### AC-004 — Decision rule
**WHEN** `RP / (RP + FP)` ≥ 0.5 **AND** firings ≥ 5 (sample-size guard), **THE
SYSTEM SHALL** keep plan-audit in block-mode. Document the audit and close
this task with `decision: keep`.

**WHEN** `RP / (RP + FP)` < 0.5 **AND** firings ≥ 5, **THE SYSTEM SHALL**
demote plan-audit to warn-mode (Coach emits feedback but does not short-
circuit). The demote pattern follows TASK-FIX-1B4B's precedent (single path-
only honesty discrepancy → should_fix). Specifically: change the
short-circuit branch in `coach_validator.py` to emit a `should_fix` issue
rather than a `must_fix` issue when the only firing is plan-audit.

**WHEN** firings < 5, **THE SYSTEM SHALL** mark the audit as `inconclusive,
extend window` and re-run on 2026-05-24.

### AC-005 — If demoting: regression test
**WHEN** demoting, **THE SYSTEM SHALL** ship a regression test under
`tests/orchestrator/quality_gates/test_plan_audit_demotion.py` exercising:
- A turn with a single plan-audit firing → `decision: feedback` (not error,
  not approve).
- A turn with plan-audit + 1 other must_fix issue → still short-circuit on
  the other issue.
- A turn with plan-audit + content-hash mismatch → still short-circuit
  (plan-audit is not the only signal).

### AC-006 — If keeping: harden the gate
**WHEN** keeping, **THE SYSTEM SHALL** add at least one regression test
exercising one of the audited REAL_POSITIVE cases (replay the captured
`task_work_results.json` and `coach_turn_*.json`, assert plan-audit fires
correctly). This proves the gate's RP class is testable, not anecdotal.

### AC-007 — Audit report persisted
**THE SYSTEM SHALL** write
`.claude/state/TASK-DEMOTE-PA-audit-2026-05-17.md` containing:
- Firing inventory (per AC-002).
- Per-firing classification (per AC-003).
- Computed RP / (RP + FP) and firings count.
- Decision (keep / demote / inconclusive).
- Citations to specific turn JSONs that drove the decision.

### AC-008 — Update review report
**WHEN** decision is keep or demote, **THE SYSTEM SHALL** update
`.claude/reviews/TASK-REV-ABST-review-report.md` §4.1 row for plan-audit with
the audit outcome and a link to the audit report.

## Implementation notes

- Like TASK-RETIRE-AC, this is mostly a grep-and-classify task. Do not over-
  engineer.
- The most expensive step is reading `task_work_results.json` per task to
  resolve the `files_modified` ↔ `Files to Modify` comparison. Consider
  extending `TASK-OBS-ABST` with a `--include-plan-audit` flag rather than
  duplicating the JSON parser.
- The classification criteria are inherently judgement calls. When uncertain,
  default to NULL_FIRING (do not over-count REAL_POSITIVE).
- Follow `TASK-FIX-1B4B`'s precedent: demotion is a `must_fix` → `should_fix`
  severity change for the *single-firing* case; multi-firing cases retain
  must_fix. Do not blanket-demote.

## Files to read

- `coach_turn_*.json` across all worktrees (per AC-002 globs)
- `task_work_results.json` for each firing
- Task spec markdown for each fired task (frontmatter `files_to_modify` field
  + body `## Files to Modify` section)
- TASK-OBS-ABST output snapshot

## Files to potentially modify (only if demoting)

- `guardkit/orchestrator/quality_gates/coach_validator.py` (severity demotion)
- `tests/orchestrator/quality_gates/test_plan_audit_demotion.py` (new
  regression test, per AC-005)
- `.claude/rules/retired-gates.md` (annotate the demotion if relevant)
- `.claude/reviews/TASK-REV-ABST-review-report.md` (annotate §4.1)

## Files to create

- `.claude/state/TASK-DEMOTE-PA-audit-2026-05-17.md`

## References

- Originating review: `.claude/reviews/TASK-REV-ABST-review-report.md` §4.1,
  §5.1
- Landing commits:
  - `6c950d75` — TASK-GK-PA-001: plan-audit compares files_to_modify against
    git-modified set
  - `c610426c` — TASK-GK-PA-002: honour explicit Files-to-Create/Modify
    sections in plan-audit AC fallback
- Demote-pattern precedent: `074a6f03` — TASK-FIX-1B4B (single path-only
  honesty discrepancy demoted from must_fix to should_fix)
- Sibling rule (must apply demote-pattern when single low-fidelity oracle
  signal short-circuits): `.claude/rules/absence-of-failure-is-not-success.md`
  meta-frame paragraph

## Dependencies

- **Blocks on**: `TASK-OBS-ABST` (need metric snapshot)
- **Blocks on**: `TASK-FREEZE-ABST` (need freeze to have held)
- **Earliest start**: 2026-05-17

## Definition of done

- [ ] AC-001: preconditions verified
- [ ] AC-002: firing inventory complete
- [ ] AC-003: per-firing classification complete
- [ ] AC-004: decision recorded
- [ ] If demote: AC-005 regression test green
- [ ] If keep: AC-006 regression test green
- [ ] AC-007: audit report persisted
- [ ] AC-008: review report annotated
- [ ] `pytest tests/orchestrator/quality_gates/` green
- [ ] Task moved to `completed` with provenance fields populated
