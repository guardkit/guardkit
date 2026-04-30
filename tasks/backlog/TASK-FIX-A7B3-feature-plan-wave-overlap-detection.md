---
id: TASK-FIX-A7B3
title: Detect wave-internal source-file overlap in /feature-plan and warn or auto-serialise
status: backlog
task_type: feature
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: medium
complexity: 5
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md
related_tasks:
  - TASK-FIX-A7B2  # Runtime-side safety net for the same failure mode
related_features: [feature-plan, planner, parallel-execution]
tags: [feature-plan, planner, parallel-execution, prevention]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Detect wave-internal source-file overlap in /feature-plan and warn or auto-serialise

## Description

When `/feature-plan` builds `parallel_groups`, it has each task's intended
file edits available (from the task descriptions, the seam-test stubs,
and the BDD scenario locations). It currently does **not** check whether
multiple tasks within the same parallel group edit overlapping files.

The most common case — and the one that broke FEAT-70A4 in the sibling
study-tutor repo — is a single shared `features/<slug>/test_<slug>.py`
BDD glue module containing step definitions for multiple tasks. The
planner happily scheduled TASK-PRV-002 and TASK-PRV-003 into the same
parallel group despite both tasks naming the same shared glue file in
their `## Seam Tests` and step-definition references.

This task adds the prevention pass at plan time. TASK-FIX-A7B2 (sibling
task) handles the runtime safety net for cases that slip through.

## Cross-reference

§3 of `<sibling>/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md`
for the wave-2 BDD glue collision; §5 of the main report for the
plan-time recommendation.

## Acceptance Criteria

- [ ] AC-001: During plan generation in `/feature-plan`, each task's
      expected file edit set is inferred from the task description.
      Inputs to the inference: explicit code-block paths, BDD scenario
      anchors (`features/<slug>.feature` and the corresponding glue
      module), seam-test stubs that name a target test file, and any
      `## Files Likely To Change` section if present.
- [ ] AC-002: For each `parallel_groups` entry with `len(tasks) > 1`,
      the pairwise file-overlap is computed and reported.
- [ ] AC-003: If overlap is non-empty, behaviour depends on a new flag
      `--auto-serialise-overlap` (default: warn-only).
      - Default: emit a planner warning naming the overlapping tasks and
        files; plan is otherwise unchanged.
      - With `--auto-serialise-overlap`: split the offending parallel
        group into two sequential entries (offending tasks moved to a
        follow-on group); emit an info-level note explaining the split.
- [ ] AC-004: Regression test: a feature plan with two tasks both naming
      `features/foo/test_foo.py` produces a warning at plan time
      (default mode) and produces a split plan when
      `--auto-serialise-overlap` is set.
- [ ] AC-005: Existing single-task and zero-overlap plans are unchanged.
      No spurious warnings on disjoint edits.
- [ ] AC-006: BDD glue files (`features/*/test_*.py`) are detected even
      when the task description references them only via step-definition
      imports, not explicit file paths. Inference is best-effort but
      should catch this most common case.

## Files Likely To Change

- `guardkit/commands/feature_plan/` (or wherever `/feature-plan`'s
  parallel-group construction lives — search for `parallel_groups` in
  `guardkit/`). Audit the planner's existing task-metadata extraction
  to find the natural extension point.
- The `feature.yaml` schema, if a `wave_overlap_warnings` block is added
  to the emitted plan for downstream visibility.
- CLI flag wiring for `--auto-serialise-overlap`.
- Tests under `tests/commands/feature_plan/` (or equivalent).

## Out Of Scope

- Static analysis of source files to discover transitive edit
  dependencies. Inference is from task descriptions only.
- Editing the `coach_validator.py` runtime-side rule — that's TASK-FIX-A7B2.
- Cross-wave overlap detection (only intra-wave parallel-group overlap
  is in scope; cross-wave edits are sequential by construction).
