---
id: TASK-FIX-A7B4
title: Coach should fail (not warn) when task ## Seam Tests section is non-empty but no @pytest.mark.seam test was collected
status: completed
task_type: bugfix
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T20:50:00Z
completed: 2026-04-30T20:50:00Z
previous_state: in_review
state_transition_reason: "Task complete — all 7 acceptance criteria met, all quality gates passed"
completed_location: tasks/completed/TASK-FIX-A7B4/
organized_files:
  - TASK-FIX-A7B4.md
priority: medium
complexity: 4
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md
related_features: [coach-validator, seam-first-testing]
tags: [coach-validator, seam-tests, contract-tests, blocking-gate]
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-30T20:46:00Z
  unit_tests:
    new: tests/unit/test_coach_seam_tests_blocking_gate.py (19 tests)
    regression: tests/unit/test_coach_validator.py (262 tests)
    autobuild_regression: tests/unit/test_autobuild_orchestrator.py (147 tests)
---

# Task: Coach should fail (not warn) when task ## Seam Tests section is non-empty but no @pytest.mark.seam test was collected

## Description

When a task description contains a `## Seam Tests` section with code
stubs, the Player is expected to implement those tests as
`@pytest.mark.seam` (or a similar marker) tests in the worktree.

In the FEAT-70A4 run (sibling study-tutor repo), both TASK-PRV-002 and
TASK-PRV-003 had explicit `## Seam Tests` sections with full code stubs
in their task files. The Players skipped them. The Coach validator
emitted an info-level "no seam/contract/boundary tests detected" log
message but did **not** block — the tasks were conditionally approved
(see TASK-FIX-A7B2 for the related conditional-approval defect) without
their seam tests ever running.

This is the most concerning latent failure mode in the autobuild stack
because seam tests are precisely the defence against the cross-task
contract violations that broke the FEAT-70A4 wave-2 verification. A
silent skip turns a designed safety net into theatre.

## Cross-reference

- §5 of `<sibling>/.claude/reviews/TASK-REV-AB7A-report.md`
- §1 and §6 of `<sibling>/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md`

## Acceptance Criteria

- [x] AC-001: The Coach validator detects the `## Seam Tests` section in
      a task description (markdown header parse, case-insensitive). The
      detection is precise: an empty `## Seam Tests` section with no
      code stubs does not trigger the gate.
- [x] AC-002: When a non-empty `## Seam Tests` section is present, the
      Coach counts `@pytest.mark.seam` tests collected from the
      worktree that reference the task's modules. (Tolerate any of
      `seam`, `contract`, `boundary` markers if there is established
      precedent — audit existing usage and match.)
- [x] AC-003: If the count is zero, the Coach gate **fails** with a
      `feedback` decision (not `approve`, not warn). The feedback
      message points the Player at the stub in the task description and
      requires implementation in a follow-up turn.
- [x] AC-004: If the count is non-zero, behaviour is unchanged.
- [x] AC-005: Regression test: a Player turn that ignores a task's
      `## Seam Tests` block produces a Coach `feedback` decision (not
      `approve`), and the feedback text cites the missing seam test by
      name or by stub reference.
- [x] AC-006: Regression test: a task with no `## Seam Tests` section
      and no seam tests produces no spurious failure (existing tasks
      not retroactively broken).
- [x] AC-007: Regression test: a task with a `## Seam Tests` section
      and the corresponding `@pytest.mark.seam` tests collected
      successfully produces a normal `approve` decision.

## Files Likely To Change

- `guardkit/orchestrator/quality_gates/coach_validator.py` — the
  decision-emitting code path. The current info-level "no
  seam/contract/boundary tests detected" log line is the natural
  anchor; search for it.
- Possibly a small helper for parsing task-description headers if one
  doesn't already exist (audit `guardkit/tasks/` for existing
  description parsers).
- Tests under `tests/orchestrator/quality_gates/`.

## Out Of Scope

- Auto-generating seam tests from the stub. The Player must implement
  them; this task only changes the gate from warn to fail.
- Other gate types (BDD scenario coverage, contract tests beyond seam)
  unless they share the parsing utility being introduced.

## Implementation Summary

Promoted Coach's seam-tests check from a warn-only soft gate to a
description-driven blocking gate. When a task description carries a
non-empty `## Seam Tests` markdown section, Coach now requires at least
one test in `tests_written` decorated with `@pytest.mark.seam`,
`@pytest.mark.contract`, or `@pytest.mark.boundary`; otherwise the turn
is rejected with a `must_fix` `feedback` issue that quotes the stub
from the task description.

Distinct from the pre-existing `_check_seam_test_recommendation` (a
profile-driven, filename-based soft gate that still fires as a non-
blocking advisory). The new gate is content-driven — it reads each
test file under the worktree and counts marker decorators rather than
filename heuristics, so a `test_integration_*.py` file that contains
no seam-class marker no longer silently satisfies a contract.

### Approach

- Added module-level `_extract_seam_tests_section(description)` helper
  that detects `## Seam Tests` headers at any markdown level (case-
  insensitive, anchored to line start so prose like "Seam Tests are
  useful…" doesn't false-trigger). The section closes at the next
  equal-or-shallower header. Empty bodies (whitespace only) return
  `None` so existing tasks aren't retroactively broken (AC-001, AC-006).
- Added `CoachValidator._check_seam_tests_implemented(task,
  task_work_results)` and `_count_seam_marker_tests(tests_written)`.
  The counter reads file contents from `self.worktree_path` and grep-
  matches `@pytest.mark.{seam,contract,boundary}` (AC-002).
- Wired the gate into `validate()` immediately after the BDD blocking
  check, returning a `feedback` decision with the stub snippet quoted
  in both the issue description and the rationale (AC-003, AC-005).
- Threaded the raw task description (`requirements: str`) from
  `_invoke_coach_safely` into the validator's task dict so Coach can
  see the section content.

### Tests

- New: `tests/unit/test_coach_seam_tests_blocking_gate.py` — 19 tests
  covering helper, counter, gate, and end-to-end `validate()` behaviour
  for AC-005/006/007 plus the AC-001 empty-section regression.
- Regression: `tests/unit/test_coach_validator.py` — 262 tests still
  pass (the legacy soft gate at `_check_seam_test_recommendation` is
  unchanged and continues to fire as a non-blocking `consider` issue).
- Regression: `tests/unit/test_autobuild_orchestrator.py` — 147 tests
  still pass against the autobuild → validator description plumbing.

### Files Changed

- `guardkit/orchestrator/quality_gates/coach_validator.py` — helper +
  two new methods + new gate wiring (~150 LOC added).
- `guardkit/orchestrator/autobuild.py` — single-line change adding
  `description=requirements or ""` to the validator's task dict.
- `tests/unit/test_coach_seam_tests_blocking_gate.py` — new (~400 LOC).

### Lessons

- The original soft gate's filename-based detection
  (`seam`/`contract`/`boundary`/`integration` substring in path) was
  too generous for a blocking promotion: a generic `test_integration_*`
  file would silently satisfy a contract obligation. Marker-based
  detection on file content is the right granularity for a hard gate
  even though the soft gate keeps the looser filename heuristic.
- The header regex must be anchored (`re.MULTILINE` + `^` and `$`) to
  avoid false-triggering on prose that happens to contain "Seam
  Tests". A leading-whitespace allowance matters because nested lists
  or code-block indentation can introduce minor whitespace before the
  header on some markdown renderers.
- The `## Seam Tests` block was already an established convention in
  the FEAT-70A4 task files (study-tutor sibling repo), so this task
  was implementation-only — no new convention needed to be socialised.
