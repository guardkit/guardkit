---
id: TASK-FPTC-007
title: "Consolidate feature-plan-smoke-gate-validation/ into feature-plan-defects/ + write classification guide"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T13:30:00Z
completed: 2026-05-03T13:30:00Z
completed_location: tasks/backlog/feature-plan-defects/class-c-task-design-mismatch/
completion_note: "Kept in feature folder for /feature-complete to archive with siblings (FPTC-001/002/003/004/005/006). Final task in FPTC Wave 4."
previous_state: in_review
state_transition_reason: "All 6 ACs satisfied; pytest 5/5 passing; folder consolidation done via git mv preserving history"
priority: medium
task_type: documentation
implementation_mode: task-work
tags:
  - docs
  - folder-consolidation
  - feature-plan-defects
  - class-c
  - cross-class-coordination
complexity: 3
estimated_minutes: 60
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 4
conductor_workspace: feature-plan-defects-wave4-1
dependencies:
  - TASK-FPTC-001
  - TASK-FPTC-002
  - TASK-FPTC-003
  - TASK-FPTC-004
  - TASK-FPTC-005
  - TASK-FPTC-006
---

# Task: Folder consolidation + classification guide

## Description

`/feature-plan` has three known classes of defect:

- **Class A**: invented paths (forge FEAT-DEA8 reproducer) — covered
  by `feature-plan-smoke-gate-validation/` (FPSG-002, FPSG-003 +
  drafts for 001, 004, 005).
- **Class B**: temporal mis-sequencing (study-tutor FEAT-FD32 Run 2
  reproducer) — covered by the same FPSG suite.
- **Class C**: task-design mismatch (this workstream — TASK-REV-AUTM
  reproducers TASK-GR-SEED, TASK-GR-DEMO).

This task is the final consolidation: move the existing FPSG folder
under a renamed parent, add a classification guide, and update
cross-references. It depends on FPTC-001..006 because some of those
edit `feature-plan.md` (which the new guide cross-links) and the
guide describes the operator_handoff escape hatch they together
implement.

## Acceptance Criteria

- [x] **AC-FPTC-007-01** —
      `tasks/backlog/feature-plan-smoke-gate-validation/` no longer
      exists. Its files have moved to:
      - `tasks/backlog/feature-plan-defects/class-a-invented-paths/`
        (FPSG-002, plus any FPSG-001 / FPSG-004 / FPSG-005 drafts
        that landed)
      - `tasks/backlog/feature-plan-defects/class-b-temporal-sequencing/`
        (FPSG-003 + the temporal-check additions to FPSG-002, FPSG-004,
        FPSG-005 — see the Class B carve-out in the existing README)
      Existing FPSG-* task IDs do NOT change. Only the folder layout
      changes.
- [x] **AC-FPTC-007-02** — `tasks/backlog/feature-plan-defects/README.md`
      is rewritten to cover all three classes with cross-links to
      each subfolder, the parent reviews (TASK-REV-DEA8 for A/B,
      TASK-REV-AUTM for C), and a brief problem-statement-per-class
      summary.
- [x] **AC-FPTC-007-03** — `docs/guides/feature-plan-task-classification.md`
      exists and contains:
      - Description of the three defect classes (A: paths, B:
        temporal, C: task-design)
      - The Class C strong/weak signal taxonomy (cross-referenced
        from `feature-plan.md`)
      - The `operator_handoff` escape hatch and how it surfaces in
        `/feature-complete`
      - Philosophy: *plan-time prevention beats runtime detection*
- [x] **AC-FPTC-007-04** — `CLAUDE.md` (root) "Feature Planning &
      Build" section contains a one-line cross-reference to
      `docs/guides/feature-plan-task-classification.md`.
- [x] **AC-FPTC-007-05** — `installer/core/commands/feature-plan.md`
      "Detection Rules" section (added by TASK-FPTC-001) gains a
      cross-link to the new guide.
- [x] **AC-FPTC-007-06** — Pytest test asserts the new guide path
      exists and contains the strings: "Class A", "Class B",
      "Class C", "operator_handoff".

## Implementation Notes

- Use `git mv` for the folder rename to preserve history.
- The Class B carve-out in the existing FPSG README (the bullet
  about "Class B fixture: YAML with `smoke_gates.command:
  pytest tests/created/by_wave_3.py -x` and `after_wave: [2]`")
  is currently spread across multiple FPSG tasks. The split into
  class-a/ and class-b/ folders is best-effort: if a single FPSG
  task spans both classes, leave it under whichever class is
  primary and cross-link from the other.
- The classification guide should be ~200–300 lines — concise,
  reference-style, not a tutorial. Cross-links over duplication.

## Cross-component contract

**Consumes**:
- The detection rules text in `feature-plan.md` (TASK-FPTC-001)
- The `operator_handoff` task type (TASK-FPTC-002)
- The orchestrator skip behaviour (TASK-FPTC-003)
- The validator behaviour (TASK-FPTC-004)
- The feature-complete surface (TASK-FPTC-005)

The guide describes what these together provide — it is the
user-facing documentation surface.

## Files

- `tasks/backlog/feature-plan-defects/README.md` (rewrite)
- `tasks/backlog/feature-plan-defects/class-a-invented-paths/` (new
  via `git mv`)
- `tasks/backlog/feature-plan-defects/class-b-temporal-sequencing/`
  (new via `git mv`)
- `tasks/backlog/feature-plan-smoke-gate-validation/` (removed)
- `docs/guides/feature-plan-task-classification.md` (new)
- `CLAUDE.md` (edit)
- `installer/core/commands/feature-plan.md` (edit — small cross-link
  addition only)
- `tests/unit/docs/test_feature_plan_classification_guide.py` (new
  — for AC-FPTC-007-06)

## Out of Scope

- Implementing the detector or the operator_handoff machinery (those
  are FPTC-001..006).
- Retroactive labelling of completed features (see parent-review
  AC-AUTM-04).
