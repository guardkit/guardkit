---
id: TASK-FIX-7B2E
previous_ids: [TASK-FIX-AC01]
title: Verify R1 (assertable-AC linter) is wired into /feature-plan
status: completed
task_type: verification
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
completed: 2026-04-22T00:00:00Z
priority: high
complexity: 2
tags: [autobuild, r1, verification, task-ac-53445, ac-linter, feature-plan, id-renamed]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 1
conductor_workspace: r2-pipeline-closure-wave1-r1-verify
depends_on: []
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-7B2E/
organized_files:
  - TASK-FIX-7B2E.md
state_transition_reason: "Completed via /task-complete. Dynamic verification + retro-grep produced a 'non-deterministically wired' verdict: R1 fired 6/6 in a fresh-session dynamic test against tests/fixtures/r1-verification/prose-ac-spec.md, but retro-grep of FEAT-JARVIS-001 planner history returned 0 matches. Remediation tracked in TASK-FIX-3C9D (priority: high; blocks TASK-COH-RUN1). All task ACs satisfied: fixture exists, dynamic run captured, evidence documented per PEX-014..020 bug class, finding recorded in .claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md, remediation task filed. ID renamed from TASK-FIX-AC01 → TASK-FIX-7B2E on 2026-04-22 to resolve collision with an unrelated February TASK-FIX-AC01 (FullDocParser fix) at tasks/completed/TASK-FIX-AC01/; previous_ids field preserves the mapping."
---

# Task: Verify R1 (assertable-AC linter) is wired into /feature-plan

## Problem Statement

TASK-REV-4D190 found no evidence that R1 (TASK-AC-53445) actually fired during the `/feature-plan` that produced FEAT-JARVIS-001.yaml. Silence could mean either (a) the linter is wired and the ACs were simply all assertable, or (b) the linter is not wired. We cannot tell from run artefacts alone. Before forge/study-tutor cohort runs, confirm the linter is live.

## Scope

### In-Scope

- Create a deliberately prose-phrased AC fixture (e.g., a feature description that would produce ACs like *"The system should handle errors gracefully"* — vague, non-testable).
- Run `/feature-plan` against the fixture.
- Observe whether the assertable-AC linter emits warnings on the prose ACs.
- Document activation evidence with file paths and warning output (or lack thereof).

### Out-of-Scope

- Fixing the linter if it is missing (file a separate task).
- Changing the linter rules.
- Extending it from warn-mode to block-mode.

## Acceptance Criteria

- [ ] A reproducible prose-AC fixture exists (feature description + expected linter trigger points documented).
- [ ] `/feature-plan` was invoked against the fixture; command output captured.
- [ ] Evidence documented: for each of the known PEX-014..020 bug classes (schema shape, stub semantic drift, path validation), whether a corresponding warning fired. Per TASK-REV-4D012's R1 acceptance criterion, ≥3 of 6 should fire.
- [ ] Finding recorded in `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`: wired / not wired / partially wired.
- [ ] If not wired, a remediation task is filed with specifics (what's missing, where) and linked to TASK-AC-53445.

## Implementation Notes

- Pre-flight: check whether TASK-AC-53445 is marked complete. If still in backlog/in-progress, that alone answers the question.
- Fixture should be minimal — one feature description, 3–6 deliberately prose ACs across different bug classes.
- A "wired and silent" result is expected if ACs are all assertable. Use the fixture to force non-silence.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§R1 per-remediation section)
- Predecessor review: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` (R1 acceptance criteria, §6)
- R1 task: `tasks/backlog/TASK-AC-53445-assertable-ac-linter-feature-plan.md`
