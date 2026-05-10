---
id: TASK-RETIRE-AC
title: Audit assumption-confidence warn-mode gate against 17-day RP record; retire if no real-positive cited
status: backlog
created: 2026-05-10T18:40:00Z
updated: 2026-05-10T18:40:00Z
priority: medium
tags: [audit, retire-candidate, narrow-recommendation, coach-validator, gate-pruning]
parent_review: TASK-REV-ABST
complexity: 3
implementation_mode: task-work
estimated_effort_hours: 2
---

# Task: Audit `assumption-confidence` warn-mode gate; retire if no RP cited

> **Why this exists**: TASK-REV-ABST §5.1 classified the `assumption-
> confidence` warn-mode gate (introduced 2026-04-23 in commit `fb37f72f`,
> TASK-FIX-RWOP1.4a) as **incidental** — 17 days post-landing with **no
> measured real-positive** in the trajectory window. A warn-mode gate that
> blocks nothing and catches nothing consumes Coach context budget for zero
> observed benefit. This task does the formal retire/keep audit.

## Description

Read every artefact that could plausibly cite the assumption-confidence gate
(Coach turn JSONs, review reports, recent task descriptions, design rules).
**IF** any cite the gate as the *reason* for a feedback-loop, AC failure, or
useful warning, document the citation and DO NOT retire — instead, escalate
to a separate task to promote the gate to block-mode with a regression test.
**ELSE** retire the gate: remove the production code, remove the test (if
any), document the decision under `.claude/rules/`, and update the review's
gate-by-gate matrix.

The audit is intentionally narrow: 17 days is short, but it covers the entire
post-landing window. If the gate had real value, *some* trace of it firing
usefully should appear in the 25 fix-up commits, the 25 reviews, or the
operator's incident reports. If it doesn't, the gate is a candidate for
retirement.

## Acceptance criteria

### AC-001 — Locate the gate code
**THE SYSTEM SHALL** identify the source code that implements the assumption-
confidence gate. Starting points:
- `git show fb37f72f` to see the original landing diff.
- Grep for `assumption_confidence`, `assumption-confidence`, and
  `AssumptionConfidence` across `guardkit/orchestrator/` and the tests tree.

### AC-002 — Citation grep
**THE SYSTEM SHALL** grep all of the following for non-self-references to the
gate (i.e. references that are NOT the gate's own implementation, tests, or
landing commit message):

- `**/coach_turn_*.json` across all consumer-repo worktrees and the GuardKit
  repo's `.guardkit/worktrees/*/.guardkit/autobuild/*/`.
- `.claude/reviews/TASK-REV-*.md` (all 250+ review reports).
- `tasks/{backlog,in_progress,in_review,blocked,completed}/**/*.md` task
  descriptions.
- `.claude/feedback/` (if exists).
- `installer/core/agents/*.md` for any agent that references the gate.
- Recent operator messages in `docs/history/*` if any happen to call out the
  gate by name.

### AC-003 — Classify each citation
**THE SYSTEM SHALL** classify every non-self-reference into one of:
- **REAL_POSITIVE**: the gate fired and the citation describes the firing as
  catching a genuine Player issue (e.g. "Coach surfaced low assumption
  confidence; Player corrected and re-submitted").
- **FALSE_POSITIVE**: the gate fired and the citation describes the firing as
  spurious (e.g. "Coach flagged low assumption confidence on a turn that was
  otherwise correct").
- **NULL_FIRING**: the gate fired but there is no signal of effect either way
  (likely the warn-mode-with-no-action shape — the gate emitted output that
  nobody acted on).
- **OUT_OF_WINDOW**: the citation predates the gate's landing
  (`fb37f72f` / 2026-04-23) and is not relevant.

### AC-004 — Decision rule
**WHEN** the count of REAL_POSITIVE citations is ≥1 AND the count of
FALSE_POSITIVE citations is ≤2 × REAL_POSITIVE, **THE SYSTEM SHALL** keep the
gate AND file a follow-up task to promote it to block-mode with a regression
test exercising at least one of the cited REAL_POSITIVE cases.

**WHEN** the count of REAL_POSITIVE citations is 0, **THE SYSTEM SHALL** retire
the gate (see AC-005).

**WHEN** the count of REAL_POSITIVE citations is ≥1 AND FALSE_POSITIVE > 2 ×
REAL_POSITIVE, **THE SYSTEM SHALL** mark the gate "demote-and-rescope" and
file a follow-up task to narrow the gate's firing condition before re-
evaluating.

### AC-005 — Retirement (if AC-004 picks retire)
**WHEN** retiring, **THE SYSTEM SHALL**:
- Remove the gate's production code (typically a function in
  `coach_validator.py` and any wiring in `agent_invoker.py`).
- Remove or skip-mark any test that exercises the gate exclusively.
- Add an entry under `.claude/rules/retired-gates.md` (create if it doesn't
  exist) documenting:
  - Gate name, landing commit, retirement commit, retirement date.
  - The 17-day RP record (citation count = 0, citation grep evidence).
  - The decision rationale citing TASK-REV-ABST §5.1.
- Update `.claude/reviews/TASK-REV-ABST-review-report.md` §4.1 row to mark the
  gate "retired 2026-05-DD per TASK-RETIRE-AC".

### AC-006 — Audit report persisted
**THE SYSTEM SHALL** persist the audit findings (the citation grep result,
classification, and decision) to
`.claude/state/TASK-RETIRE-AC-audit-2026-05-DD.md`. This is the regression-
proof artifact that the next reviewer reads if anyone questions the
retirement. Format:

```
## Citation grep results
- Self-references: N
- REAL_POSITIVE: N (cite each)
- FALSE_POSITIVE: N (cite each)
- NULL_FIRING: N
- OUT_OF_WINDOW: N

## Decision
[Retire | Promote | Demote-and-rescope]

## Rationale
[Per AC-004]
```

### AC-007 — Falsifier acknowledgement
**IF** during the audit the operator discovers that the gate has been modified
since `fb37f72f` (e.g. additional fixes landed that changed its behaviour) or
that the gate is referenced from a load-bearing path the report missed, **THE
SYSTEM SHALL** document the discrepancy in the audit report and escalate to
the operator before retiring. Retirement is **never** unilateral when
unexpected wiring is found.

## Implementation notes

- This is mostly a grep-and-classify task. Do not over-engineer.
- The Coach JSON globs are large (many turns × many tasks × many features).
  Stream the grep — don't read every file fully. `rg
  "assumption[_-]confidence"` is fine.
- For the retirement step, the smallest possible diff is preferred. If the
  gate is wired through multiple sites, do not "while I'm here" refactor —
  remove the wiring and stop. Refactoring is out of scope.
- If retirement requires changes to `coach_validator.py`, ensure the
  TASK-FREEZE-ABST guard does not block this change. Per the freeze record:
  *"single-line defensive guards on already-landed code"* are permitted; gate
  retirement is permitted as a *removal* of existing code (no new behavioural
  surface). Document the override in `.claude/state/gate-freeze-2026-05-17.md`
  before merging.

## Files to read

- `guardkit/orchestrator/quality_gates/coach_validator.py` (locate the gate)
- `guardkit/orchestrator/agent_invoker.py` (check wiring sites)
- `tests/orchestrator/quality_gates/test_coach_validator.py` (check tests)
- All paths under AC-002 for citation grep

## Files to potentially modify (only if retiring)

- `guardkit/orchestrator/quality_gates/coach_validator.py` (remove gate)
- `guardkit/orchestrator/agent_invoker.py` (remove wiring)
- `tests/orchestrator/quality_gates/test_coach_validator.py` (remove test)
- `.claude/rules/retired-gates.md` (create or append)
- `.claude/reviews/TASK-REV-ABST-review-report.md` (annotate §4.1)
- `.claude/state/gate-freeze-2026-05-17.md` (record override if needed)

## Files to create

- `.claude/state/TASK-RETIRE-AC-audit-2026-05-DD.md` (the audit report)

## References

- Originating review: `.claude/reviews/TASK-REV-ABST-review-report.md` §4.1,
  §5.1
- Landing commit: `fb37f72f` — feat(coach): wire assumption-confidence
  warn-mode gate (TASK-FIX-RWOP1.4a)
- Sibling rule (don't approve on absent oracle output):
  `.claude/rules/absence-of-failure-is-not-success.md` — same shape: a gate
  that produces NULL_FIRING for 17 days is the absence-of-failure pattern
  applied to the gate-evaluator itself.
- Freeze constraint: `.claude/state/gate-freeze-2026-05-17.md` (created by
  TASK-FREEZE-ABST)

## Dependencies

- **Blocks on**: `TASK-FREEZE-ABST` (freeze must be declared so the override
  protocol exists)
- **Does not block**: any other ABST follow-up

## Definition of done

- [ ] AC-001: gate code located and documented in audit report
- [ ] AC-002: citation grep run; results in audit report
- [ ] AC-003: every citation classified
- [ ] AC-004: decision recorded (retire / promote / demote-and-rescope)
- [ ] AC-005: if retire, gate code removed and rules updated
- [ ] AC-006: audit report at `.claude/state/TASK-RETIRE-AC-audit-2026-05-DD.md`
- [ ] AC-007: any unexpected wiring escalated rather than silently handled
- [ ] If retire path: `pytest tests/orchestrator/quality_gates/` green
- [ ] If retire path: review report annotated
- [ ] Task moved to `completed` with provenance fields populated
