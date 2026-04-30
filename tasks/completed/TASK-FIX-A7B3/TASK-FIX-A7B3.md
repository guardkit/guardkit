---
id: TASK-FIX-A7B3
title: Detect wave-internal source-file overlap in /feature-plan and warn or auto-serialise
status: completed
task_type: feature
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T21:45:00Z
completed: 2026-04-30T21:45:00Z
completed_location: tasks/completed/TASK-FIX-A7B3/
previous_state: in_review
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
  status: passed
  coverage: null
  last_run: 2026-04-30T21:30:00Z
  details:
    new_unit_tests: 32       # tests/unit/test_wave_overlap_detector.py
    new_integration_tests: 10  # tests/integration/feature_plan/test_wave_overlap_detection.py
    producer_regression: 161   # tests/unit/test_generate_feature_yaml.py + tests/integration/feature_plan/* + tests/unit/commands/feature_plan/* (existing, all green)
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

- [x] AC-001: During plan generation in `/feature-plan`, each task's
      expected file edit set is inferred from the task description.
      Inputs to the inference: explicit code-block paths, BDD scenario
      anchors (`features/<slug>.feature` and the corresponding glue
      module), seam-test stubs that name a target test file, and any
      `## Files Likely To Change` section if present.
- [x] AC-002: For each `parallel_groups` entry with `len(tasks) > 1`,
      the pairwise file-overlap is computed and reported.
- [x] AC-003: If overlap is non-empty, behaviour depends on a new flag
      `--auto-serialise-overlap` (default: warn-only).
      - Default: emit a planner warning naming the overlapping tasks and
        files; plan is otherwise unchanged.
      - With `--auto-serialise-overlap`: split the offending parallel
        group into two sequential entries (offending tasks moved to a
        follow-on group); emit an info-level note explaining the split.
- [x] AC-004: Regression test: a feature plan with two tasks both naming
      `features/foo/test_foo.py` produces a warning at plan time
      (default mode) and produces a split plan when
      `--auto-serialise-overlap` is set.
- [x] AC-005: Existing single-task and zero-overlap plans are unchanged.
      No spurious warnings on disjoint edits.
- [x] AC-006: BDD glue files (`features/*/test_*.py`) are detected even
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

## Implementation Summary

Producer-runs-check, mirroring TASK-FIX-3C9D (AC linter) and TASK-FIX-RWOP1.2
(R2/R3 nudges) — the same shape that closes "runner without producer" gaps.

A new module `installer/core/commands/lib/wave_overlap_detector.py` exposes
four pure functions: `infer_task_files` derives a per-task source-file edit
set from the task's name + description + ACs (explicit path mentions plus
the AC-006 BDD-glue inference), `compute_wave_overlaps` runs pairwise
intersection within each parallel group (waves with `len(tasks) <= 1` are
skipped, AC-002 / AC-005), `serialize_overlapping_groups` rewrites a wave
into N+1 sequential entries when offenders are detected (innocents stay,
each offender gets its own follow-on wave so the conflict is genuinely
broken — AC-003), and `format_overlap_warning_summary` emits the stdout
banner. The detector is wired into `installer/core/commands/lib/generate_feature_yaml.py`
between `build_parallel_groups()` and `FeatureFile(...)` construction, and
the warning banner prints alongside the existing AC-linter / R2 / R3
banners. A new `--auto-serialise-overlap` CLI flag opts into the rewrite;
default behaviour is warn-only (AC-003).

`--quiet` continues to suppress the banner (preserves the
`FEAT-XXXX:path` parseable-output contract, mirroring the AC-linter and
nudge contracts).

The `wave_overlap_warnings` YAML block mentioned in §"Files Likely To Change"
was deferred — the stdout banner already gives downstream consumers a
human-readable report, and adding the block to `feature.to_dict()` would
require a `FeatureLoader.validate_yaml` schema change with no current
consumer. Easy to add later if a downstream consumer materialises.

## Approach

Surgical, additive change. One new module (`wave_overlap_detector.py`,
~250 LOC), one new unit-test file (32 tests), one new integration-test
file (10 tests). Three small edits to `generate_feature_yaml.py`: import
guard, CLI flag, accumulator + producer callsite. No existing module's
public API changed, no schema changed. All 161 pre-existing producer-side
tests stay green.

## Notes

- Regex alternation gotcha caught during unit-test run: Python regex
  alternation is leftmost-first, so longer extensions must precede
  shorter prefixes (`tsx` before `ts`, `jsx` before `js`, `yaml`
  before `yml`, `csproj` before `cs`). Otherwise `app/bar.tsx` parses
  as `app/bar.ts`. Same gotcha that the system prompt warns about for
  shell `find` regex alternation.
- Auto-serialise split shape was tightened during the eyeball-output
  pass: the literal AC-003 "split into two sequential entries" wording,
  combined with the failure-mode reality (two tasks both writing to the
  same shared glue file), means each offender must run in its own wave.
  Putting both offenders in a single follow-on wave preserves the same
  parallel-write race that triggered the warning. The implementation
  generalises naturally to N offenders → N follow-on waves.
- AC-006 BDD-glue inference is gated on a step-definition hint phrase
  (e.g. `step definition`, `pytest-bdd`, `@given`) co-occurring with a
  `features/<slug>/...feature` reference. Without the gate, a task that
  merely cites a `.feature` file as documentation would get a phantom
  `features/<slug>/test_<slug>.py` edit — a false-positive class
  AC-005 explicitly forbids.
- Sibling task TASK-FIX-A7B2 lives at the runtime safety-net layer
  (`coach_validator._detect_source_file_contention`). The two tasks are
  layered defences: this plan-time check prevents the conflict from
  being scheduled; A7B2 catches the cases that slip through (e.g.
  inference miss, descriptions without explicit paths).
