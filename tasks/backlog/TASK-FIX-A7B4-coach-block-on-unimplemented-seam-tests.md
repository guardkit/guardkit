---
id: TASK-FIX-A7B4
title: Coach should fail (not warn) when task ## Seam Tests section is non-empty but no @pytest.mark.seam test was collected
status: backlog
task_type: bugfix
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
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
  status: pending
  coverage: null
  last_run: null
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

- [ ] AC-001: The Coach validator detects the `## Seam Tests` section in
      a task description (markdown header parse, case-insensitive). The
      detection is precise: an empty `## Seam Tests` section with no
      code stubs does not trigger the gate.
- [ ] AC-002: When a non-empty `## Seam Tests` section is present, the
      Coach counts `@pytest.mark.seam` tests collected from the
      worktree that reference the task's modules. (Tolerate any of
      `seam`, `contract`, `boundary` markers if there is established
      precedent — audit existing usage and match.)
- [ ] AC-003: If the count is zero, the Coach gate **fails** with a
      `feedback` decision (not `approve`, not warn). The feedback
      message points the Player at the stub in the task description and
      requires implementation in a follow-up turn.
- [ ] AC-004: If the count is non-zero, behaviour is unchanged.
- [ ] AC-005: Regression test: a Player turn that ignores a task's
      `## Seam Tests` block produces a Coach `feedback` decision (not
      `approve`), and the feedback text cites the missing seam test by
      name or by stub reference.
- [ ] AC-006: Regression test: a task with no `## Seam Tests` section
      and no seam tests produces no spurious failure (existing tasks
      not retroactively broken).
- [ ] AC-007: Regression test: a task with a `## Seam Tests` section
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
