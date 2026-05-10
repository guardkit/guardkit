---
id: TASK-FREEZE-ABST
title: Declare 7-day gate-stack freeze (2026-05-11 → 2026-05-17) and add commit-time guard
status: completed
created: 2026-05-10T18:30:00Z
updated: 2026-05-10T19:05:00Z
completed: 2026-05-10T19:05:00Z
completed_location: tasks/completed/TASK-FREEZE-ABST/
priority: high
tags: [freeze, gate-stack, autobuild, narrow-recommendation, process]
parent_review: TASK-REV-ABST
complexity: 2
implementation_mode: task-work
estimated_effort_hours: 1
actual_effort_hours: 0.5
previous_state: in_review
state_transition_reason: "All 4 ACs satisfied; pytest guard passes (1 passed, 1 skipped-on-out-of-window for today 2026-05-10)."
organized_files:
  - TASK-FREEZE-ABST.md
deliverables:
  - .claude/state/gate-freeze-2026-05-17.md
  - tests/rules/test_gate_freeze.py
  - CLAUDE.md (Project Status section added)
---

## Implementation Summary

Filed the 7-day gate-stack freeze (2026-05-11 → 2026-05-17 inclusive)
recommended by TASK-REV-ABST §8.1.1 (Narrow). Three deliverables:

1. **Freeze record** at `.claude/state/gate-freeze-2026-05-17.md` —
   captures the window, frozen paths, permitted-vs-forbidden commit
   classes, exception protocol (one-line override entry under
   `## Granted overrides`), and cross-references to the originating
   review and the two sibling rules (`absence-of-failure-is-not-success`
   and `path-string-mismatch-is-not-dishonesty`).

2. **Pytest guard** at `tests/rules/test_gate_freeze.py` — two tests:
   - `test_freeze_record_present_and_parseable` always runs and asserts
     the record exists with the canonical structure (window dates,
     `## Granted overrides` section, link to the review).
   - `test_gate_freeze_no_forbidden_commits` is `@pytest.mark.skipif`'d
     on out-of-window dates; inside the window it walks `git log` over
     the frozen paths, classifies each commit (revert / docs-or-test /
     ≤3-line guard / out-of-scope / forbidden), and fails if any
     forbidden-class commit lands without a matching `TASK-XXX` entry
     in `## Granted overrides`. Verified locally: `1 passed, 1 skipped`
     on 2026-05-10 (one day before the window opens) with the skip
     reason naming the window correctly.

3. **CLAUDE.md pointer** — added a `## Project Status` section near
   the top with the one-line freeze notice exactly per AC-003. To be
   removed by TASK-REV-ABST.1 on 2026-05-17.

## Notes

- The pytest guard does **not** auto-revert offending commits — it
  fails loudly so the operator decides. Auto-revert would be a
  destructive default.
- The single-line-guard heuristic counts only added lines (`+`) ≤3 and
  rejects diffs that introduce new `def`/`class`/`async def` symbols on
  frozen paths. Counting added-only (rather than added+removed) matches
  the "single-line defensive guard" intent better — a 1-line
  replacement is one new line of behaviour, not two.
- The override-section parser lives in the same module as the guard;
  if the freeze record's structure changes, both must move together.
  The presence test enforces a small structural invariant
  (`## Granted overrides` heading + window dates + review backlink) so
  drift is caught even outside the window.

# Task: Declare 7-day gate-stack freeze + commit-time guard

> **Why this exists**: TASK-REV-ABST recommended **Narrow** with a 7-day freeze
> on the autobuild gate stack to give consumer repos a stable target while the
> May 6 (1B4A/B/C + 7E3F) and May 10 (AB-001/003/004) fixes bake. This task
> records the freeze, scopes it, and adds a commit-time guard so an in-flight
> agent does not silently land a new gate during the window.

## Description

Between **2026-05-11 and 2026-05-17 inclusive (7 days)**, no NEW_GATE commits
are permitted to the autobuild quality-gate stack. FIX_FOR_NEW_GATE commits
are permitted only if they are reverts or single-line guards on already-landed
code. The freeze ends at end-of-day 2026-05-17, at which point TASK-REV-ABST.1
re-evaluates the trajectory and either lifts the freeze (Continue), extends it
(Hold-Narrow), or escalates to Pivot.

**Frozen paths** (any commit touching these triggers the guard):

- `guardkit/orchestrator/agent_invoker.py`
- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/orchestrator/quality_gates/coach_verification.py`
- `guardkit/orchestrator/quality_gates/bdd_runner.py`
- `guardkit/orchestrator/quality_gates/honesty.py` (if exists)
- `guardkit/tasks/state_bridge.py`
- `installer/core/templates/common/features/conftest.py.template`

**Permitted-during-freeze classes**:

- Reverts (any commit whose subject begins with `revert(...)`).
- Single-line defensive guards on already-landed code (no new behavioural
  surface; identifiable by diff size ≤3 lines AND no new function/class/method).
- Documentation-only changes (rules, READMEs, CHANGELOG).
- Test-only changes (no production-code changes).
- Out-of-scope edits (any path NOT in the frozen list above).

**Forbidden-during-freeze**:

- New gate classes (no `NEW_GATE` per the bucketing in TASK-REV-ABST §2).
- New behavioural surface in the frozen paths (new function/class/method, new
  Coach short-circuit branch, new Player prompt mandate).
- Re-landing of a previously-reverted gate (e.g. TASK-FIX-7A08 Player Task-tool
  mandate).

## Acceptance criteria

### AC-001 — Freeze record persisted
**WHEN** this task completes, **THE SYSTEM SHALL** have a freeze record at
`.claude/state/gate-freeze-2026-05-17.md` containing:
- Start date (2026-05-11) and end date (2026-05-17, inclusive).
- Frozen paths (verbatim from the list above).
- Permitted-during-freeze classes.
- Forbidden-during-freeze classes.
- Exception protocol (operator must record a one-line override in the freeze
  record before merging any forbidden-class commit).
- Link back to TASK-REV-ABST review report.

### AC-002 — Commit-time guard installed
**WHEN** an operator attempts to commit a change touching any frozen path,
**THE SYSTEM SHALL** check whether the commit subject is one of the permitted
classes (revert / docs / test / out-of-scope). **IF** the commit is in a
forbidden class **AND** the freeze record does not contain an explicit override
for it, **THE SYSTEM SHALL** abort the commit with a message pointing to the
freeze record. The guard is implemented as either:
- A pre-commit hook in `.git/hooks/pre-commit` (operator-installed), OR
- A pytest test under `tests/rules/test_gate_freeze.py` that asserts no
  forbidden-class commit lands during the window (run in CI).
The pytest variant is preferred because it survives a `git clone` and runs in
CI; the hook is a belt-and-braces addition.

### AC-003 — Freeze documented in CLAUDE.md
**WHEN** this task completes, **THE SYSTEM SHALL** have a one-line entry in
`CLAUDE.md` under "Project Status" or equivalent section pointing to
`.claude/state/gate-freeze-2026-05-17.md`. Example: *"⏸️ **Gate-stack freeze
active 2026-05-11→2026-05-17** (TASK-FREEZE-ABST) — see
.claude/state/gate-freeze-2026-05-17.md before touching frozen paths."* This
entry is removed automatically by `TASK-REV-ABST.1` on 2026-05-17.

### AC-004 — Freeze record references the review
**THE SYSTEM SHALL** ensure `.claude/state/gate-freeze-2026-05-17.md` cross-
references `.claude/reviews/TASK-REV-ABST-review-report.md` (specifically
§8.1.1) so future agents can trace the rationale.

## Implementation notes

- The freeze record is a markdown file, not a YAML config. Future agents read
  it; they don't need to parse it programmatically (the pytest guard reads
  `git log --since=2026-05-11 --until=2026-05-17` against the frozen paths).
- The pytest guard should be skip-on-out-of-window: `if today not in
  freeze_window: pytest.skip(...)`. It only fails if a forbidden commit lands
  during the window.
- Do not auto-revert offending commits; the guard should fail loudly and let
  the operator decide. Auto-revert is a destructive default.
- The exception protocol's "one-line override" is just a markdown line in the
  freeze record (e.g. `- 2026-05-13: Override granted for TASK-XXX (urgent
  security fix in coach_validator.py — see <issue link>).`).

## Files to create

- `.claude/state/gate-freeze-2026-05-17.md` (the freeze record)
- `tests/rules/test_gate_freeze.py` (the pytest guard, skip-on-out-of-window)

## Files to modify

- `CLAUDE.md` (add the one-line freeze status pointer; remove on 2026-05-17 in
  TASK-REV-ABST.1)

## References

- Originating review: `.claude/reviews/TASK-REV-ABST-review-report.md` §8.1.1
- Bucketing definition (NEW_GATE / FIX_FOR_NEW_GATE / REVERT): same review §2
- Sibling rule (predicting future failure-class shapes during the freeze):
  `.claude/rules/absence-of-failure-is-not-success.md`

## Definition of done

- [ ] AC-001: freeze record at `.claude/state/gate-freeze-2026-05-17.md`
- [ ] AC-002: pytest guard at `tests/rules/test_gate_freeze.py`
- [ ] AC-003: `CLAUDE.md` updated with freeze pointer
- [ ] AC-004: freeze record cross-references the review report
- [ ] Pytest guard passes locally with `pytest tests/rules/test_gate_freeze.py`
- [ ] Task moved to `completed` with provenance fields populated
